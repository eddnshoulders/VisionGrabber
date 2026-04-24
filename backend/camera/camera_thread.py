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

from camera.opencv_pipeline import run_pipeline, DetectionResult
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
        self._latest_detection: Optional[DetectionResult] = None
        self._fps    = 0.0
        self._running = True

        # Single-frame request mechanism
        self._single_event  = threading.Event()
        self._single_result: Optional[DetectionResult] = None

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
    def latest_detection(self) -> Optional[DetectionResult]:
        with self._frame_lock:
            return self._latest_detection

    def start_streaming(self):
        with self._mode_lock:
            self._mode = CameraMode.STREAMING
        logger.info(f"[{self.name}] Streaming started")

    def stop_streaming(self):
        with self._mode_lock:
            self._mode = CameraMode.IDLE
        logger.info(f"[{self.name}] Streaming stopped")

    def capture_single(self, timeout: float = 5.0) -> Optional[DetectionResult]:
        """
        Request a single frame capture and block until result is available.
        Returns DetectionResult or None on timeout.
        """
        with self._mode_lock:
            prev_mode = self._mode
            self._mode = CameraMode.SINGLE
        self._single_event.clear()
        self._single_result = None

        if not self._single_event.wait(timeout=timeout):
            logger.warning(f"[{self.name}] Single capture timed out")
            with self._mode_lock:
                self._mode = prev_mode
            return None

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
            time.sleep(2)
            logger.info(f"[{self.name}] Camera opened")
        except Exception as exc:
            logger.error(f"[{self.name}] Failed to open camera: {exc}")
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
                time.sleep(0.5)
                continue

            now = time.time()
            dt  = max(now - last_t, 1e-6)
            last_t = now
            self._fps = 0.85 * self._fps + 0.15 * (1.0 / dt)

            frames, detection = run_pipeline(raw, self.params)

            with self._frame_lock:
                self._frames.update(frames)
                self._latest_detection = detection

            if mode == CameraMode.SINGLE:
                self._single_result = detection
                self._single_event.set()

            time.sleep(1.0 / max(1, self.params.stream_fps))

        picam.stop()
        logger.info(f"[{self.name}] Camera closed")
