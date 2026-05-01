"""
Camera thread for VisionGrabber.

Each CameraThread manages one physical camera. It supports three modes:
    idle        - not capturing frames
    streaming   - continuous capture + OpenCV pipeline (for debug streaming)
    single      - capture one frame on demand, run detection, return result

The OpenCV pipeline runs in the thread. The latest annotated frame is
always available for MJPEG streaming to the frontend.
"""

import logging
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from camera.opencv_pipeline import run_pipeline, PipelineResult
from camera.params import CameraParams, load_params, save_params
from config import (
    TOOLHEAD_CAMERA_INDEX,
    OVERHEAD_CAMERA_INDEX,
    PRESETS_DIR,
)

logger = logging.getLogger(__name__)


class CameraId(Enum):
    TOOLHEAD = TOOLHEAD_CAMERA_INDEX
    OVERHEAD  = OVERHEAD_CAMERA_INDEX


class CameraMode(Enum):
    IDLE      = "idle"
    STREAMING = "streaming"
    SINGLE    = "single"


class CameraThread(threading.Thread):

    def __init__(self, camera_id: CameraId):
        super().__init__(daemon=True, name=f"Camera-{camera_id.name}")
        self.camera_id   = camera_id
        self.params      = load_params(camera_id)
        self._mode       = CameraMode.IDLE
        self._mode_lock  = threading.Lock()
        self._frame_lock = threading.Lock()

        # Latest frames for each view
        self._frames: dict[str, Optional[np.ndarray]] = {
            "raw": None, "gray": None, "mask": None,
            "contours": None, "annotated": None, "tiled": None,
        }
        self._latest_detection: Optional[PipelineResult] = None
        self._fps    = 0.0
        self._running = True
        self._health_state: str = "inactive"  # inactive | active | fault

        # Optional health status callback - set by app.py after construction
        self._on_health = None

        # Single-frame request mechanism
        self._single_event  = threading.Event()
        self._single_result: Optional[PipelineResult] = None
        self._single_silent: bool = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def mode(self) -> CameraMode:
        with self._mode_lock:
            return self._mode

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def latest_detection(self) -> Optional[PipelineResult]:
        with self._frame_lock:
            return self._latest_detection

    def start_streaming(self):
        with self._mode_lock:
            self._mode = CameraMode.STREAMING
        self._emit_health("active")
        logger.info(f"[{self.name}] Streaming started")

    def stop_streaming(self):
        with self._mode_lock:
            self._mode = CameraMode.IDLE
        self._emit_health("inactive")
        logger.info(f"[{self.name}] Streaming stopped")

    def capture_single(self, timeout: float = 5.0,
                       silent: bool = False) -> Optional[PipelineResult]:
        """
        Request a single frame capture and block until result is available.
        Returns PipelineResult or None on timeout.
        If silent=True, the captured frame does not update the displayed feed.
        """
        with self._mode_lock:
            prev_mode = self._mode
            self._mode = CameraMode.SINGLE
        self._single_event.clear()
        self._single_result  = None
        self._single_silent  = silent

        if not self._single_event.wait(timeout=timeout):
            logger.warning(f"[{self.name}] Single capture timed out")
            self._emit_health("fault")
            with self._mode_lock:
                self._mode = prev_mode
            return None

        self._emit_health("active")
        with self._mode_lock:
            self._mode = prev_mode
        return self._single_result

    def get_frame(self, view: str = "annotated") -> Optional[np.ndarray]:
        with self._frame_lock:
            return self._frames.get(view)

    def get_jpeg(self, view: str = "annotated") -> Optional[bytes]:
        frame = self.get_frame(view)
        if frame is None:
            return None
        quality = self.params.jpeg_quality
        ok, jpg = cv2.imencode(".jpg", frame,
                               [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        return jpg.tobytes() if ok else None

    @property
    def health_state(self) -> str:
        return self._health_state

    def set_health_callback(self, cb):
        """Register callback(camera_id, status) called on health state changes."""
        self._on_health = cb

    def _emit_health(self, status: str):
        self._health_state = status
        if self._on_health:
            self._on_health(self.camera_id, status)

    def check_health(self):
        """
        Explicitly emit current health state.
        Call at sequence start, calibration start, etc.
        """
        self._emit_health(self._health_state)

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------
    # Thread main loop
    # ------------------------------------------------------------------

    def run(self):
        try:
            from picamera2 import Picamera2
            picam = Picamera2(self.camera_id.value)
            p = self.params
            cfg = picam.create_preview_configuration(
                main={"size": (p.frame_width, p.frame_height),
                      "format": "BGR888"}
            )
            picam.configure(cfg)
            picam.start()
            # USB cameras (uvcvideo) need longer to initialise than CSI cameras
            settle_time = 4.0 if self.camera_id == CameraId.OVERHEAD else 2.0
            time.sleep(settle_time)

            # Flush initial frames - first few can be corrupted while
            # the sensor and ISP initialise
            for _ in range(10 if self.camera_id == CameraId.OVERHEAD else 5):
                picam.capture_array()
                time.sleep(0.1)

            logger.info(f"[{self.name}] Camera opened")
            self._emit_health("active")

            # Capture one initial frame so the stream has something to show
            try:
                raw = picam.capture_array()
                raw = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
                result = run_pipeline(raw, self.params)
                with self._frame_lock:
                    self._frames.update(result.frames)
                    self._latest_detection = result
            except Exception:
                pass
        except Exception as exc:
            logger.error(f"[{self.name}] Failed to open camera: {exc}")
            self._emit_health("fault")
            return

        last_t = time.time()

        while self._running:
            with self._mode_lock:
                mode = self._mode

            if mode == CameraMode.IDLE:
                time.sleep(0.1)
                continue

            try:
                raw = picam.capture_array()
                raw = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
            except Exception as exc:
                logger.error(f"[{self.name}] Capture error: {exc}")
                self._emit_health("fault")
                time.sleep(0.5)
                continue

            now = time.time()
            dt  = max(now - last_t, 1e-6)
            last_t = now
            self._fps = 0.85 * self._fps + 0.15 * (1.0 / dt)

            result = run_pipeline(raw, self.params)

            with self._frame_lock:
                if mode != CameraMode.SINGLE or not self._single_silent:
                    self._frames.update(result.frames)
                self._latest_detection = result

            if mode == CameraMode.SINGLE:
                self._single_result = result
                self._single_event.set()

            time.sleep(1.0 / max(1, self.params.stream_fps))

        picam.stop()
        logger.info(f"[{self.name}] Camera closed")
