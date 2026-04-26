"""
Overhead camera to machine position calibration for VisionGrabber.

Runs a grid of machine positions, captures an overhead frame at each,
detects the toolhead circle, and builds a thin-plate spline transform
mapping pixel coordinates to machine coordinates.

The calibration boundary is the rectangle defined by the outermost grid
points. Any pixel coordinate outside this boundary is flagged as
unreachable - no extrapolation is performed.

Calibration data is saved to CALIB_FILE as JSON and loaded at startup.

Usage:
    from camera.calibration import CalibrationManager
    calib = CalibrationManager(ipc_client, overhead_cam)
    await calib.run()  # blocking, runs in a thread
    machine_xy = calib.pixel_to_machine(px, py)
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Callable

from camera.camera_thread import CameraThread
from camera.params import CameraParams, load_params, save_params
from camera.opencv_pipeline import PipelineResult
from machine.ipc import IpcClient
from config import (
    SCAN_X_START, SCAN_X_END,
    SCAN_Y_START, SCAN_Y_END,
    Z_BED_DOWN, BED_FEEDRATE, MOVE_FEEDRATE,
    CALIB_GRID_X, CALIB_GRID_Y,
    CALIB_MARGIN_X_MIN, CALIB_MARGIN_X_MAX,
    CALIB_MARGIN_Y_MIN, CALIB_MARGIN_Y_MAX,
    CALIB_GRABBER_OFFSET_X, CALIB_GRABBER_OFFSET_Y,
    CALIB_FILE,
)

logger = logging.getLogger(__name__)

CALIB_PATH = Path(__file__).parent.parent / CALIB_FILE


@dataclass
class CalibPoint:
    """A single calibration measurement."""
    machine_x: float
    machine_y: float
    pixel_x:   float
    pixel_y:   float


@dataclass
class CalibrationData:
    """Full calibration result."""
    points:           list[CalibPoint]
    boundary_x_min:   float   # pixel boundary for interpolation
    boundary_x_max:   float
    boundary_y_min:   float
    boundary_y_max:   float
    grabber_offset_x: float
    grabber_offset_y: float
    image_height:     float   # pixels, needed for Y axis inversion
    timestamp:        float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["points"] = [asdict(p) for p in self.points]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CalibrationData":
        points = [CalibPoint(**p) for p in d["points"]]
        return cls(
            points=points,
            boundary_x_min=d["boundary_x_min"],
            boundary_x_max=d["boundary_x_max"],
            boundary_y_min=d["boundary_y_min"],
            boundary_y_max=d["boundary_y_max"],
            grabber_offset_x=d["grabber_offset_x"],
            grabber_offset_y=d["grabber_offset_y"],
            image_height=d.get("image_height", 960.0),  # default for old files
            timestamp=d["timestamp"],
        )


class CalibrationTransform:
    """
    Thin-plate spline transform from pixel coordinates to machine coordinates.
    Built from a CalibrationData object.
    Only interpolates within the calibrated boundary.
    """

    def __init__(self, data: CalibrationData):
        try:
            from scipy.interpolate import RBFInterpolator
        except ImportError:
            raise RuntimeError("scipy is required for calibration. "
                               "Run: pip install scipy --break-system-packages")

        self._data         = data
        self._image_height = data.image_height
        points = data.points

        src   = [[p.pixel_x, p.pixel_y] for p in points]
        dst_x = [p.machine_x for p in points]
        dst_y = [p.machine_y for p in points]

        import numpy as np
        src_arr   = np.array(src,   dtype=float)
        dst_x_arr = np.array(dst_x, dtype=float)
        dst_y_arr = np.array(dst_y, dtype=float)

        self._rbf_x = RBFInterpolator(src_arr, dst_x_arr,
                                      kernel="thin_plate_spline")
        self._rbf_y = RBFInterpolator(src_arr, dst_y_arr,
                                      kernel="thin_plate_spline")

        logger.info(f"[Calibration] Transform built from {len(points)} points")

    def in_bounds(self, px: float, py: float) -> bool:
        """Check if pixel coordinate is within the calibrated boundary."""
        d = self._data
        return (d.boundary_x_min <= px <= d.boundary_x_max and
                d.boundary_y_min <= py <= d.boundary_y_max)

    def pixel_to_machine(
        self, px: float, py: float
    ) -> Optional[tuple[float, float]]:
        """
        Convert raw pixel coordinates to machine coordinates (mm).
        Inverts Y axis, applies parallax correction space, checks boundary,
        queries spline, applies grabber offset.
        Returns None if outside calibrated boundary.
        """
        import numpy as np

        # Invert pixel Y to match machine Y axis direction
        # Must be done before boundary check since boundary is in inverted space
        inverted_py = self._image_height - py

        if not self.in_bounds(px, inverted_py):
            logger.warning(
                f"[Calibration] ({px:.0f},{py:.0f}) outside calibrated boundary"
            )
            return None

        query = np.array([[px, inverted_py]], dtype=float)
        mx = float(self._rbf_x(query)[0])
        my = float(self._rbf_y(query)[0])

        # Apply grabber offset
        mx += self._data.grabber_offset_x
        my += self._data.grabber_offset_y

        return mx, my


class CalibrationManager:
    """
    Manages the calibration routine and the loaded transform.

    The calibration routine:
    1. Homes the machine
    2. Lowers bed to Z_BED_DOWN
    3. Loads calibration camera params
    4. Steps through grid of XY positions
    5. At each point, captures an overhead frame and detects the
       toolhead circle (smallest detected object)
    6. Builds thin-plate spline transform from collected points
    7. Saves calibration data to JSON
    """

    def __init__(self, ipc: IpcClient, overhead_cam: CameraThread):
        self._ipc          = ipc
        self._overhead_cam = overhead_cam
        self._transform:   Optional[CalibrationTransform] = None
        self._data:        Optional[CalibrationData]      = None
        self._running      = False
        self._progress:    dict = {"status": "idle", "point": 0, "total": 0,
                                   "failed": []}
        self._lock         = threading.Lock()

        # Status callback for WebSocket progress updates
        self._on_progress: Optional[Callable[[dict], None]] = None

        # Load existing calibration if available
        self._load()

    def set_progress_callback(self, cb: Callable[[dict], None]):
        self._on_progress = cb

    @property
    def is_calibrated(self) -> bool:
        return self._transform is not None

    @property
    def progress(self) -> dict:
        with self._lock:
            return dict(self._progress)

    def pixel_to_machine(
        self, px: float, py: float
    ) -> Optional[tuple[float, float]]:
        if self._transform is None:
            logger.error("[Calibration] No transform available - run calibration first")
            return None
        return self._transform.pixel_to_machine(px, py)

    # ------------------------------------------------------------------
    # Calibration routine
    # ------------------------------------------------------------------

    def run(
        self,
        grabber_offset_x: float = CALIB_GRABBER_OFFSET_X,
        grabber_offset_y: float = CALIB_GRABBER_OFFSET_Y,
    ) -> bool:
        """
        Run the full calibration routine. Blocking - call in a thread.
        Returns True on success.
        """
        if self._running:
            logger.warning("[Calibration] Already running")
            return False

        self._running = True
        self._set_progress(status="starting", point=0, total=0, failed=[])

        try:
            return self._run(grabber_offset_x, grabber_offset_y)
        except Exception as exc:
            logger.exception(f"[Calibration] Failed: {exc}")
            self._set_progress(status="failed", error=str(exc))
            return False
        finally:
            self._running = False

    def _run(self, grabber_offset_x: float, grabber_offset_y: float) -> bool:
        import numpy as np

        # Build grid points
        x_min = float(SCAN_X_END)   + CALIB_MARGIN_X_MIN
        x_max = float(SCAN_X_START) - CALIB_MARGIN_X_MAX
        y_min = float(SCAN_Y_END)   + CALIB_MARGIN_Y_MIN
        y_max = float(SCAN_Y_START) - CALIB_MARGIN_Y_MAX

        xs = np.linspace(x_min, x_max, CALIB_GRID_X)
        ys = np.linspace(y_min, y_max, CALIB_GRID_Y)

        grid = [(float(x), float(y)) for y in ys for x in xs]
        total = len(grid)

        self._set_progress(status="homing", point=0, total=total, failed=[])
        logger.info(f"[Calibration] Starting {CALIB_GRID_X}x{CALIB_GRID_Y} "
                    f"grid ({total} points)")

        # Home machine
        resp = self._ipc.send("G28")
        if resp.startswith("ERROR:"):
            raise RuntimeError(f"Homing failed: {resp}")

        # Lower bed
        resp = self._ipc.send(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
        if resp.startswith("ERROR:"):
            raise RuntimeError(f"Bed lower failed: {resp}")

        # Load calibration params for overhead camera
        self._set_progress(status="running")
        calib_params = self._load_calib_params()
        original_params = self._overhead_cam.params
        self._overhead_cam.params = calib_params
        self._overhead_cam.start_streaming()

        points: list[CalibPoint] = []
        failed: list[int]        = []

        try:
            for i, (mx, my) in enumerate(grid):
                self._set_progress(
                    status="running", point=i + 1, total=total, failed=failed
                )
                logger.info(f"[Calibration] Point {i+1}/{total}: "
                            f"machine ({mx:.1f}, {my:.1f})")

                # Move to grid position
                resp = self._ipc.send(
                    f"G0 X{mx:.2f} Y{my:.2f} F{MOVE_FEEDRATE}"
                )
                if resp.startswith("ERROR:"):
                    logger.warning(f"[Calibration] Move failed at point {i+1}: {resp}")
                    failed.append(i)
                    continue

                # Settle after move
                time.sleep(1.0)

                # Take multiple frames and require consistent detection
                det = self._stable_detection(attempts=5, interval=0.3)
                if det is None:
                    logger.warning(
                        f"[Calibration] No stable detection at point {i+1} "
                        f"({mx:.1f}, {my:.1f})"
                    )
                    failed.append(i)
                    continue

                logger.info(
                    f"[Calibration] Detected at ({det.px}, {det.py}) "
                    f"area={det.area:.0f}"
                )

                points.append(CalibPoint(
                    machine_x=mx,
                    machine_y=my,
                    pixel_x=float(det.px),
                    pixel_y=float(det.py),
                ))

        finally:
            self._overhead_cam.stop_streaming()
            self._overhead_cam.params = original_params

        # Need enough points for a meaningful spline
        if len(points) < 9:
            raise RuntimeError(
                f"Only {len(points)} points collected - need at least 9. "
                f"Check toolhead circle detection params."
            )

        # Parallax correction
        # The calibration circle is at a different height to the cylinder tops.
        # Scale each pixel offset from the image centre by the ratio of
        # distances so the transform applies correctly at cylinder height.
        from config import (
            CALIB_CAMERA_TO_TOOLHEAD, CALIB_CAMERA_TO_BED_DOWN,
        )
        scale = CALIB_CAMERA_TO_TOOLHEAD / CALIB_CAMERA_TO_BED_DOWN
        cx    = self._overhead_cam.params.frame_width  / 2.0
        cy    = self._overhead_cam.params.frame_height / 2.0

        logger.info(
            f"[Calibration] Applying parallax correction: "
            f"scale={scale:.4f} "
            f"(toolhead {CALIB_CAMERA_TO_TOOLHEAD}mm, "
            f"bed {CALIB_CAMERA_TO_BED_DOWN}mm)"
        )

        corrected_points = []
        image_height = float(self._overhead_cam.params.frame_height)
        for p in points:
            # Invert pixel Y to match machine Y axis direction
            # (camera Y increases downward, machine Y increases upward)
            inverted_py = image_height - p.pixel_y
            corrected_points.append(CalibPoint(
                machine_x=p.machine_x,
                machine_y=p.machine_y,
                pixel_x=cx + (p.pixel_x - cx) * scale,
                pixel_y=cy + (inverted_py - cy) * scale,
            ))

        # Compute pixel boundary from corrected outermost grid points
        px_vals = [p.pixel_x for p in corrected_points]
        py_vals = [p.pixel_y for p in corrected_points]

        data = CalibrationData(
            points=corrected_points,
            boundary_x_min=min(px_vals),
            boundary_x_max=max(px_vals),
            boundary_y_min=min(py_vals),
            boundary_y_max=max(py_vals),
            grabber_offset_x=grabber_offset_x,
            grabber_offset_y=grabber_offset_y,
            image_height=image_height,
            timestamp=time.time(),
        )

        self._data      = data
        self._transform = CalibrationTransform(data)
        self._save(data)

        self._set_progress(
            status="complete",
            point=total,
            total=total,
            failed=failed,
            points_collected=len(points),
        )
        logger.info(
            f"[Calibration] Complete: {len(points)}/{total} points, "
            f"{len(failed)} failed"
        )
        return True

    def _stable_detection(
        self, attempts: int = 5, interval: float = 0.3
    ):
        """
        Capture multiple frames and return the median centroid if detection
        is consistent across all attempts. Returns None if any frame fails
        to detect or if the centroid variance is too high.
        """
        from camera.opencv_pipeline import DetectionResult
        detections = []

        for _ in range(attempts):
            result = self._overhead_cam.capture_single(timeout=5.0)
            if result is None or not result.detected:
                return None   # require detection in every frame
            det = result.smallest
            detections.append((det.px, det.py))
            time.sleep(interval)

        # Check variance - reject if toolhead circle is jumping around
        xs = [d[0] for d in detections]
        ys = [d[1] for d in detections]
        if max(xs) - min(xs) > 5 or max(ys) - min(ys) > 5:
            logger.warning(
                f"[Calibration] Centroid unstable: "
                f"x range={max(xs)-min(xs):.1f}px "
                f"y range={max(ys)-min(ys):.1f}px"
            )
            return None

        # Return median position as a simple DetectionResult-like object
        import statistics

        class _Det:
            px = round(statistics.median(xs))
            py = round(statistics.median(ys))
            area = 0.0

        return _Det()

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------

    def _save(self, data: CalibrationData):
        CALIB_PATH.parent.mkdir(parents=True, exist_ok=True)
        CALIB_PATH.write_text(json.dumps(data.to_dict(), indent=2))
        logger.info(f"[Calibration] Saved to {CALIB_PATH}")

    def _load(self):
        if not CALIB_PATH.exists():
            logger.info("[Calibration] No calibration file found")
            return
        try:
            data            = CalibrationData.from_dict(
                json.loads(CALIB_PATH.read_text())
            )
            self._data      = data
            self._transform = CalibrationTransform(data)
            logger.info(
                f"[Calibration] Loaded {len(data.points)} points from {CALIB_PATH}"
            )
        except Exception as exc:
            logger.warning(f"[Calibration] Failed to load calibration: {exc}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_progress(self, **kwargs):
        with self._lock:
            self._progress.update(kwargs)
        if self._on_progress:
            self._on_progress(self.progress)

    def _load_calib_params(self) -> CameraParams:
        """
        Load calibration-specific overhead params.
        Falls back to current overhead params if not found.
        """
        from camera.camera_thread import CameraId
        calib_preset = Path(__file__).parent.parent / CALIB_FILE.replace(
            "calibration.json", ""
        ) / "overhead_calibration.json"

        if calib_preset.exists():
            params = CameraParams()
            import json as _json
            overrides = _json.loads(calib_preset.read_text())
            for k, v in overrides.items():
                params.update(k, v)
            logger.info(f"[Calibration] Using calibration params from {calib_preset}")
            return params

        logger.warning(
            "[Calibration] No overhead_calibration.json found - "
            "using current overhead params"
        )
        return self._overhead_cam.params
