"""REST routes for physical button handler connection status."""

from flask import Blueprint, jsonify

from api.messages import (
    IndicatorButtonConnectedMessage,
    IndicatorButtonConnectedPayload,
    HealthButtonMessage,
    HealthButtonPayload,
    ButtonState,
)
from api.websocket import ws_manager

button_bp = Blueprint("button", __name__)


def _emit_button_status(connected: bool):
    ws_manager.emit(IndicatorButtonConnectedMessage(
        payload=IndicatorButtonConnectedPayload(connected=connected)
    ))
    ws_manager.emit(HealthButtonMessage(
        payload=HealthButtonPayload(
            status=ButtonState.CONNECTED if connected else ButtonState.NOT_CONNECTED
        )
    ))


@button_bp.route("/connected", methods=["POST"])
def connected():
    import app as _app
    _app._button_connected = True
    _emit_button_status(True)
    return jsonify({"ok": True})


@button_bp.route("/disconnected", methods=["POST"])
def disconnected():
    import app as _app
    _app._button_connected = False
    _emit_button_status(False)
    return jsonify({"ok": True})


@button_bp.route("/status")
def status():
    import app as _app
    return jsonify({"ok": True, "connected": _app._button_connected})
