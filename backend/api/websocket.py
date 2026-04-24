"""
WebSocket connection manager for VisionGrabber.

Provides a single ws_manager instance that any part of the backend can use
to emit messages to all connected browser clients.

Usage:
    from api.websocket import ws_manager
    from api.messages import SequenceStateMessage, SequenceStatePayload, SequenceState

    ws_manager.emit(SequenceStateMessage(
        payload=SequenceStatePayload(state=SequenceState.READY)
    ))

Flask route setup (in app.py):
    from flask_sock import Sock
    from api.websocket import ws_manager

    sock = Sock(app)

    @sock.route('/ws')
    def ws_handler(ws):
        ws_manager.handle(ws)
"""

import json
import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simple_websocket import Server as WsConnection

from api.messages import WsMessage

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages all active WebSocket client connections.

    Thread-safe - the sequence coordinator, heartbeat thread, and camera
    threads all call emit() from different threads.
    """

    def __init__(self):
        # Set of active WebSocket connections
        self._clients: set[WsConnection] = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def handle(self, ws: "WsConnection") -> None:
        """
        Called by Flask-Sock for each new WebSocket connection.
        Registers the client, then blocks until the connection closes.
        This runs in its own thread per client (Flask-Sock handles that).
        """
        self._register(ws)
        logger.info(f"[WS] Client connected. Total: {self._client_count()}")

        try:
            # Block here - we don't expect messages from the client over WS.
            # All client→server communication goes via REST.
            # If the client sends anything, discard it gracefully.
            while True:
                msg = ws.receive()
                if msg is None:
                    break  # connection closed
                logger.debug(f"[WS] Unexpected client message (ignored): {msg!r}")

        except Exception as exc:
            logger.debug(f"[WS] Connection error: {exc}")

        finally:
            self._unregister(ws)
            logger.info(f"[WS] Client disconnected. Total: {self._client_count()}")

    # ------------------------------------------------------------------
    # Emitting messages
    # ------------------------------------------------------------------

    def emit(self, message: WsMessage) -> None:
        """
        Serialise a message and send it to all connected clients.
        Dead connections are silently removed.
        Called from any thread.
        """
        payload = json.dumps(message.to_dict())
        self._broadcast(payload)

    def emit_raw(self, data: dict) -> None:
        """
        Emit a pre-built dictionary directly (for cases where a full
        message dataclass isn't warranted, e.g. one-off debug events).
        """
        self._broadcast(json.dumps(data))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register(self, ws: "WsConnection") -> None:
        with self._lock:
            self._clients.add(ws)

    def _unregister(self, ws: "WsConnection") -> None:
        with self._lock:
            self._clients.discard(ws)

    def _client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def _broadcast(self, payload: str) -> None:
        """Send a raw string to all clients. Remove any that have gone away."""
        dead: set[WsConnection] = set()

        with self._lock:
            clients = set(self._clients)  # snapshot to avoid holding lock during send

        for ws in clients:
            try:
                ws.send(payload)
            except Exception as exc:
                logger.debug(f"[WS] Send failed, removing client: {exc}")
                dead.add(ws)

        if dead:
            with self._lock:
                self._clients -= dead


# ---------------------------------------------------------------------------
# Singleton instance - import this everywhere
# ---------------------------------------------------------------------------
ws_manager = WebSocketManager()