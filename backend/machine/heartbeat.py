"""
Heartbeat poller for VisionGrabber.

Polls the launcher process every HEARTBEAT_INTERVAL seconds via IPC,
sending a STATE command and emitting the result as WebSocket messages.

If N consecutive polls fail, emits a machine.heartbeat_lost message
and triggers a hard fault in the sequence coordinator.
"""

import logging
import threading
import time
from typing import Optional

from api.messages import (
    MachineCommsStatus,
    MachineState,
    MachineStateMessage,
    MachineStatePayload,
    MachineHeartbeatLostMessage,
    MachineHeartbeatLostPayload,
    HealthMachineMessage,
    HealthMachinePayload,
)
from api.websocket import WebSocketManager
from machine.ipc import IpcClient
from config import HEARTBEAT_INTERVAL, HEARTBEAT_MAX_FAILURES

logger = logging.getLogger(__name__)


class HeartbeatPoller(threading.Thread):

    def __init__(self, ipc: IpcClient, ws: WebSocketManager,
                 interval: float = HEARTBEAT_INTERVAL,
                 max_failures: int = HEARTBEAT_MAX_FAILURES):
        super().__init__(daemon=True, name="HeartbeatPoller")
        self._ipc          = ipc
        self._ws           = ws
        self._interval     = interval
        self._max_failures = max_failures
        self._failures     = 0
        self._running      = True
        self._fault_cb     = None   # called once when heartbeat is lost

    def set_fault_callback(self, cb):
        """Register a callback to invoke when heartbeat is lost."""
        self._fault_cb = cb

    @property
    def comms_ok(self) -> bool:
        return self._failures < self._max_failures

    def stop(self):
        self._running = False

    def run(self):
        logger.info(f"[Heartbeat] Polling every {self._interval}s, "
                    f"max failures: {self._max_failures}")
        while self._running:
            self._poll()
            time.sleep(self._interval)

    def _poll(self):
        resp = self._ipc.send("STATE")

        if resp.startswith("ERROR:"):
            self._failures += 1
            logger.warning(f"[Heartbeat] Poll failed ({self._failures}/"
                           f"{self._max_failures}): {resp}")

            # Emit health update
            self._ws.emit(HealthMachineMessage(
                payload=HealthMachinePayload(comms=MachineCommsStatus.FAULT)
            ))

            if self._failures >= self._max_failures:
                logger.error("[Heartbeat] Heartbeat lost - triggering hard fault")
                self._ws.emit(MachineHeartbeatLostMessage(
                    payload=MachineHeartbeatLostPayload(
                        consecutive_failures=self._failures
                    )
                ))
                if self._fault_cb:
                    self._fault_cb("Machine comms lost")
        else:
            if self._failures > 0:
                logger.info("[Heartbeat] Comms restored")
            self._failures = 0

            # Parse state string from response
            machine_state = self._parse_state(resp)

            self._ws.emit(MachineStateMessage(
                payload=MachineStatePayload(state=machine_state)
            ))
            self._ws.emit(HealthMachineMessage(
                payload=HealthMachinePayload(comms=MachineCommsStatus.OK)
            ))

    def _parse_state(self, resp: str) -> MachineState:
        """Map raw STATE response string to MachineState enum."""
        try:
            return MachineState(resp.strip())
        except ValueError:
            logger.debug(f"[Heartbeat] Unknown state string: {resp!r}, defaulting to IDLE")
            return MachineState.IDLE