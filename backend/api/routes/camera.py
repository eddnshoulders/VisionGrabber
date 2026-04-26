"""REST routes for camera control, MJPEG streaming, and parameter tuning."""

import time
from flask import Blueprint, Response, current_app, jsonify, request, abort

from camera.camera_thread import CameraId
from camera.params import save_params, list_presets, load_params

camera_bp = Blueprint("camera", __name__)


def _cam(camera_id: str):
    vg = current_app.extensions["vg"]
    if camera_id == "toolhead":
        return vg["toolhead_cam"]
    elif camera_id == "overhead":
        return vg["overhead_cam"]
    abort(404)


def _cam_id(camera_id: str) -> CameraId:
    if camera_id == "toolhead":
        return CameraId.TOOLHEAD
    elif camera_id == "overhead":
        return CameraId.OVERHEAD
    abort(404)


# ── Stream control ────────────────────────────────────────────────────────────

@camera_bp.route("/<camera_id>/stream/start", methods=["POST"])
def stream_start(camera_id):
    _cam(camera_id).start_streaming()
    return jsonify({"ok": True})


@camera_bp.route("/<camera_id>/stream/stop", methods=["POST"])
def stream_stop(camera_id):
    _cam(camera_id).stop_streaming()
    return jsonify({"ok": True})


@camera_bp.route("/<camera_id>/stream")
def stream(camera_id):
    """MJPEG stream endpoint."""
    cam = _cam(camera_id)

    def generate():
        while True:
            jpg = cam.get_jpeg(cam.params.debug_view)
            if jpg:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                       + jpg + b"\r\n")
            time.sleep(1.0 / max(1, cam.params.stream_fps))

    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@camera_bp.route("/<camera_id>/frame")
@camera_bp.route("/<camera_id>/frame/<label>")
def frame(camera_id, label=None):
    """Single JPEG frame. label selects the debug view."""
    cam  = _cam(camera_id)
    view = label or cam.params.debug_view
    jpg  = cam.get_jpeg(view)
    if jpg is None:
        abort(503)
    return Response(jpg, mimetype="image/jpeg")


# ── Detection result ──────────────────────────────────────────────────────────

@camera_bp.route("/<camera_id>/detect")
def detect(camera_id):
    """Latest detection result - all detected objects."""
    result = _cam(camera_id).latest_detection
    if result is None:
        return jsonify({"detected": False, "count": 0, "detections": []})
    return jsonify(result.to_dict())


@camera_bp.route("/<camera_id>/detect/single", methods=["POST"])
def detect_single(camera_id):
    """Trigger a single-frame capture and return all detections."""
    result = _cam(camera_id).capture_single(timeout=10.0)
    if result is None:
        return jsonify({"ok": False, "error": "capture timed out"}), 504
    return jsonify({"ok": True, **result.to_dict()})


# ── Parameters ────────────────────────────────────────────────────────────────

@camera_bp.route("/<camera_id>/params")
def params_get(camera_id):
    return jsonify(_cam(camera_id).params.to_dict())


@camera_bp.route("/<camera_id>/params", methods=["PATCH"])
def params_patch(camera_id):
    cam  = _cam(camera_id)
    data = request.get_json(force=True)
    errors = {}
    for key, value in data.items():
        if not cam.params.update(key, value):
            errors[key] = "unknown parameter"
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    return jsonify({"ok": True})


@camera_bp.route("/<camera_id>/params/save", methods=["POST"])
def params_save(camera_id):
    cam  = _cam(camera_id)
    cid  = _cam_id(camera_id)
    data = request.get_json(force=True) or {}
    name = data.get("name")
    path = save_params(cam.params, cid, name)
    return jsonify({"ok": True, "saved_to": str(path)})


@camera_bp.route("/<camera_id>/params/presets")
def params_presets(camera_id):
    cid     = _cam_id(camera_id)
    presets = list_presets(cid)
    return jsonify({"presets": presets})


@camera_bp.route("/<camera_id>/params/load", methods=["POST"])
def params_load(camera_id):
    cam  = _cam(camera_id)
    cid  = _cam_id(camera_id)
    data = request.get_json(force=True) or {}
    name = data.get("name")
    loaded = load_params(cid) if not name else _load_named(cid, name)
    cam.params = loaded
    return jsonify({"ok": True, "params": cam.params.to_dict()})


def _load_named(cid: CameraId, name: str):
    """Load a named preset file."""
    import json
    from pathlib import Path
    from camera.params import CameraParams, PRESETS_PATH
    path = PRESETS_PATH / f"{name}.json"
    if not path.exists():
        abort(404)
    params = CameraParams()
    overrides = json.loads(path.read_text())
    for k, v in overrides.items():
        params.update(k, v)
    return params
