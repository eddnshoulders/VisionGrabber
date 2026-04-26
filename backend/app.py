"""
VisionGrabber Backend - Flask entry point.

Run from the backend/ directory:
    flask --app app run --host=0.0.0.0 --port=5000

Or via systemd (see linux_configs/VisionGrabberWeb.service).

In production, the built frontend is served as static files from
frontend/dist/. In development, Vite runs its own dev server on
port 5173 and proxies /api and /ws to this process.
"""

import logging
import threading
from pathlib import Path

from flask import Flask, send_from_directory
from flask_sock import Sock

from api.websocket import ws_manager
from api.routes.sequence import sequence_bp
from api.routes.camera import camera_bp
from api.routes.machine import machine_bp
from api.routes.calibration import calibration_bp
from camera.camera_thread import CameraThread, CameraId
from camera.calibration import CalibrationManager
from machine.heartbeat import HeartbeatPoller
from machine.ipc import ipc_client
from sequence.coordinator import SequenceCoordinator
from config import FLASK_DEBUG, FLASK_PORT

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if FLASK_DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIST),
    static_url_path="",
)
sock = Sock(app)

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@sock.route("/ws")
def ws_handler(ws):
    ws_manager.handle(ws)

# ---------------------------------------------------------------------------
# REST blueprints
# ---------------------------------------------------------------------------
app.register_blueprint(sequence_bp,     url_prefix="/api/sequence")
app.register_blueprint(camera_bp,       url_prefix="/api/camera")
app.register_blueprint(machine_bp,      url_prefix="/api/machine")
app.register_blueprint(calibration_bp,  url_prefix="/api/calibration")

# ---------------------------------------------------------------------------
# Serve frontend (production)
# Single-page app: any unmatched route returns index.html so that
# React Router can handle client-side navigation.
# ---------------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    target = FRONTEND_DIST / path
    if path and target.exists():
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")

# ---------------------------------------------------------------------------
# Background services
# ---------------------------------------------------------------------------
def _start_background_services():
    """Start all long-running background threads."""

    # Camera threads
    toolhead_cam = CameraThread(CameraId.TOOLHEAD)
    overhead_cam  = CameraThread(CameraId.OVERHEAD)
    toolhead_cam.start()
    overhead_cam.start()
    logger.info("Camera threads started")

    # Heartbeat poller (STATE command to launcher every ~2s)
    heartbeat = HeartbeatPoller(
        ipc=ipc_client,
        ws=ws_manager,
        interval=2.0,
        max_failures=3,
    )
    heartbeat.start()
    logger.info("Heartbeat poller started")

    # Calibration manager (loads existing calibration if available)
    calibration = CalibrationManager(
        ipc=ipc_client,
        overhead_cam=overhead_cam,
    )
    calibration.set_progress_callback(
        lambda p: ws_manager.emit_raw({
            "type": "calibration.progress",
            "ts": int(__import__("time").time() * 1000),
            "payload": p,
        })
    )
    logger.info(f"Calibration manager ready "
                f"(calibrated: {calibration.is_calibrated})")

    # Sequence coordinator (owns the state machine)
    coordinator = SequenceCoordinator(
        toolhead_cam=toolhead_cam,
        overhead_cam=overhead_cam,
        ipc=ipc_client,
        ws=ws_manager,
        calibration=calibration,
    )
    coordinator.start()
    logger.info("Sequence coordinator started")

    # Store references so they aren't garbage collected
    app.extensions["vg"] = {
        "toolhead_cam": toolhead_cam,
        "overhead_cam":  overhead_cam,
        "coordinator":  coordinator,
        "heartbeat":    heartbeat,
        "calibration":  calibration,
    }

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    _start_background_services()
    app.run(
        host="0.0.0.0",
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
        use_reloader=False,  # reloader forks the process, breaks background threads
    )
