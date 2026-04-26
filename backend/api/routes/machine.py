"""REST routes for machine command passthrough."""

from flask import Blueprint, current_app, jsonify, request

from machine.ipc import IpcClient

machine_bp = Blueprint("machine", __name__)


def _ipc() -> IpcClient:
    return current_app.extensions["vg"]["heartbeat"]._ipc


@machine_bp.route("/command", methods=["POST"])
def command():
    data = request.get_json(force=True)
    cmd  = str(data.get("cmd", "")).strip()
    if not cmd:
        return jsonify({"ok": False, "error": "empty command"}), 400

    # Emit ACK immediately - actual response comes via WebSocket
    from api.websocket import ws_manager
    from api.messages import MachineResponseMessage, MachineResponsePayload

    resp = current_app.extensions["vg"]["heartbeat"]._ipc.send(cmd)
    ws_manager.emit(MachineResponseMessage(
        payload=MachineResponsePayload(response=resp)
    ))
    return jsonify({"ok": True, "queued": cmd})


@machine_bp.route("/state")
def state():
    resp = current_app.extensions["vg"]["heartbeat"]._ipc.send("STATE")
    return jsonify({"response": resp})

@machine_bp.route("/position")
def position():
    import re
    resp  = current_app.extensions["vg"]["heartbeat"]._ipc.send("M114")
    match = re.search(r"X:([\d.-]+)\s+Y:([\d.-]+)\s+Z:([\d.-]+)", resp)
    if not match:
        return jsonify({"ok": False, "raw": resp}), 502
    return jsonify({
        "ok": True,
        "x": float(match.group(1)),
        "y": float(match.group(2)),
        "z": float(match.group(3)),
    })
