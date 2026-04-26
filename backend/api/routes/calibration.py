"""REST routes for camera-to-machine calibration."""

import threading
from flask import Blueprint, current_app, jsonify, request

calibration_bp = Blueprint("calibration", __name__)


def _calib():
    return current_app.extensions["vg"]["calibration"]


@calibration_bp.route("/status")
def status():
    calib = _calib()
    return jsonify({
        "is_calibrated": calib.is_calibrated,
        "progress":      calib.progress,
    })


@calibration_bp.route("/run", methods=["POST"])
def run():
    calib = _calib()
    if calib.progress.get("status") == "running":
        return jsonify({"ok": False, "error": "Calibration already running"}), 409

    data             = request.get_json(force=True) or {}
    grabber_offset_x = float(data.get("grabber_offset_x", 0.0))
    grabber_offset_y = float(data.get("grabber_offset_y", 0.0))

    # Run in background thread - returns immediately
    def _run():
        calib.run(
            grabber_offset_x=grabber_offset_x,
            grabber_offset_y=grabber_offset_y,
        )

    threading.Thread(target=_run, daemon=True, name="CalibrationRun").start()
    return jsonify({"ok": True, "message": "Calibration started"})


@calibration_bp.route("/data")
def data():
    calib = _calib()
    if not calib.is_calibrated:
        return jsonify({"ok": False, "error": "Not calibrated"}), 404
    return jsonify({"ok": True, "data": calib._data.to_dict()})


@calibration_bp.route("/test", methods=["POST"])
def test():
    """Test pixel→machine conversion for a given pixel coordinate."""
    calib = _calib()
    if not calib.is_calibrated:
        return jsonify({"ok": False, "error": "Not calibrated"}), 404

    body = request.get_json(force=True)
    px   = float(body.get("px", 0))
    py   = float(body.get("py", 0))

    result = calib.pixel_to_machine(px, py)
    if result is None:
        return jsonify({"ok": False, "error": "Outside calibrated boundary",
                        "px": px, "py": py})
    mx, my = result
    return jsonify({"ok": True, "px": px, "py": py,
                    "machine_x": mx, "machine_y": my})
