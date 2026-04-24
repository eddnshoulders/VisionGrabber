"""REST routes for sequence control."""

from flask import Blueprint, current_app, jsonify, request

sequence_bp = Blueprint("sequence", __name__)


def _coordinator():
    return current_app.extensions["vg"]["coordinator"]


@sequence_bp.route("/start", methods=["POST"])
def start():
    _coordinator().trigger("start")
    return jsonify({"ok": True})


@sequence_bp.route("/stop", methods=["POST"])
def stop():
    _coordinator().trigger("stop")
    return jsonify({"ok": True})


@sequence_bp.route("/operator", methods=["POST"])
def operator():
    data   = request.get_json(force=True)
    action = data.get("action", "")
    if action not in ("retry", "reset"):
        return jsonify({"ok": False, "error": "action must be retry or reset"}), 400
    _coordinator().trigger(action)
    return jsonify({"ok": True})


@sequence_bp.route("/state")
def state():
    return jsonify({"state": _coordinator().state.value})
