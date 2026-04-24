"""
OpenCV detection pipeline for VisionGrabber.

Stateless functions - takes a frame and params, returns annotated frames
and a detection result. Called by CameraThread on each captured frame.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from camera.params import CameraParams

logger = logging.getLogger(__name__)


def _odd(n: int) -> int:
    n = max(1, int(n))
    return n if n % 2 == 1 else n + 1


@dataclass
class DetectionResult:
    """Result of circle detection on a single frame."""
    detected:    bool
    px:          Optional[int]   = None  # pixel x of detected circle centre
    py:          Optional[int]   = None  # pixel y of detected circle centre
    radius:      Optional[int]   = None
    area:        Optional[float] = None
    circularity: Optional[float] = None
    timestamp:   Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "detected":    self.detected,
            "px":          self.px,
            "py":          self.py,
            "radius":      self.radius,
            "area":        self.area,
            "circularity": self.circularity,
            "timestamp":   self.timestamp,
        }


def run_pipeline(
    frame_bgr: np.ndarray,
    params: CameraParams,
) -> tuple[dict[str, np.ndarray], DetectionResult]:
    """
    Run the full detection pipeline on a single frame.

    Returns:
        frames    - dict of named debug views (raw, gray, mask, contours,
                    annotated, tiled)
        detection - DetectionResult for the best accepted circle
    """
    import time
    ts  = time.time()
    raw = frame_bgr.copy()
    p   = params

    # ── Preprocessing ────────────────────────────────────────────────
    gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (_odd(p.blur_kernel),) * 2, 0)

    # ── Threshold / mask ─────────────────────────────────────────────
    if p.threshold_mode == "hsv":
        hsv  = cv2.cvtColor(raw, cv2.COLOR_BGR2HSV)
        lo1  = np.array([p.hsv_h1_lo, p.hsv_s_lo, p.hsv_v_lo])
        hi1  = np.array([p.hsv_h1_hi, p.hsv_s_hi, p.hsv_v_hi])
        lo2  = np.array([p.hsv_h2_lo, p.hsv_s_lo, p.hsv_v_lo])
        hi2  = np.array([p.hsv_h2_hi, p.hsv_s_hi, p.hsv_v_hi])
        mask = cv2.bitwise_or(cv2.inRange(hsv, lo1, hi1),
                              cv2.inRange(hsv, lo2, hi2))
    elif p.threshold_mode == "adaptive":
        block = max(3, _odd(p.adaptive_block_size))
        mask  = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block, p.adaptive_c,
        )
    elif p.threshold_mode == "inverse":
        _, mask = cv2.threshold(blur, p.threshold_value, 255,
                                cv2.THRESH_BINARY_INV)
    else:
        _, mask = cv2.threshold(blur, p.threshold_value, 255,
                                cv2.THRESH_BINARY)

    k    = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

    # ── ROI ──────────────────────────────────────────────────────────
    roi = np.zeros_like(mask)
    roi[p.roi_y_min:p.roi_y_max, p.roi_x_min:p.roi_x_max] = 255
    mask = cv2.bitwise_and(mask, roi)

    # ── Contour detection ────────────────────────────────────────────
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    accepted = []
    for c in contours:
        area = cv2.contourArea(c)
        if not (p.min_area <= area <= p.max_area):
            continue
        peri = cv2.arcLength(c, True)
        if peri <= 0:
            continue
        circ = 4.0 * np.pi * area / (peri * peri)
        if circ < p.circularity_min:
            continue
        (x, y), radius = cv2.minEnclosingCircle(c)
        radius = int(radius)
        if not (p.min_radius <= radius <= p.max_radius):
            continue
        accepted.append({
            "contour": c, "center": (int(x), int(y)),
            "radius": radius, "area": float(area),
            "circularity": float(circ),
        })

    best = max(accepted, key=lambda a: a["area"]) if accepted else None

    # ── Build debug views ────────────────────────────────────────────
    contours_vis = raw.copy()
    annotated    = raw.copy()

    if p.show_all_contours:
        cv2.drawContours(contours_vis, contours, -1, (0, 0, 255), 1)
    if p.show_accepted_contours:
        for item in accepted:
            cv2.drawContours(contours_vis, [item["contour"]], -1, (0, 255, 0), 2)
            cv2.circle(contours_vis, item["center"], item["radius"],
                       (255, 0, 0), 1)

    if best:
        x, y, r = best["center"][0], best["center"][1], best["radius"]
        cv2.circle(annotated, (x, y), r, (0, 255, 0), 2)
        cv2.circle(annotated, (x, y), 2, (0, 255, 255), -1)
        cv2.putText(annotated,
                    f"x={x} y={y} r={r} A={best['area']:.0f} "
                    f"C={best['circularity']:.2f}",
                    (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (0, 255, 0), 2, cv2.LINE_AA)
    else:
        cv2.putText(annotated, "No detection",
                    (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (0, 0, 255), 2, cv2.LINE_AA)

    cv2.putText(annotated, p.debug_view,
                (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 255, 0), 2, cv2.LINE_AA)
    cv2.rectangle(annotated,
                  (p.roi_x_min, p.roi_y_min),
                  (p.roi_x_max, p.roi_y_max),
                  (0, 255, 255), 1)

    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    tw, th   = raw.shape[1] // 2, raw.shape[0] // 2
    fit      = lambda img: cv2.resize(img, (tw, th))
    tiled    = np.vstack([
        np.hstack([fit(raw), fit(gray_bgr)]),
        np.hstack([fit(mask_bgr), fit(annotated)]),
    ])

    frames = {
        "raw":       raw,
        "gray":      gray_bgr,
        "mask":      mask_bgr,
        "contours":  contours_vis,
        "annotated": annotated,
        "tiled":     tiled,
    }

    detection = DetectionResult(
        detected=best is not None,
        px=best["center"][0] if best else None,
        py=best["center"][1] if best else None,
        radius=best["radius"] if best else None,
        area=best["area"] if best else None,
        circularity=best["circularity"] if best else None,
        timestamp=ts,
    )

    return frames, detection
