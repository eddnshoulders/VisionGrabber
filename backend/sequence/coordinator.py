"""
Sequence coordinator for VisionGrabber.

Owns the top-level state machine. Responds to trigger events (button press,
GUI start) and drives the full pick-and-place sequence.

State transitions are driven by:
  - External triggers (start, stop, operator actions) via trigger()
  - Internal results (detection success/failure, move completion)
  - Hard fault signals from the heartbeat poller

All machine commands go via IPC to the launcher process.
Camera captures are requested from the CameraThread instances.
State changes are emitted via WebSocket to all connected clients.
"""

import logging
import threading
import time
from typing import Optional

from api.messages import (
    SequenceState,
    SequenceStateMessage,
    SequenceStatePayload,
    SequenceAwaitingOperatorMessage,
    SequenceAwaitingOperatorPayload,
    SequenceFaultMessage,
    SequenceFaultPayload,
    SoftFaultType,
    IndicatorReadyMessage,
    IndicatorReadyPayload,
    HealthGrabberMessage,
    HealthGrabberPayload,
    GrabberState,
)
from api.websocket import WebSocketManager
from camera.camera_thread import CameraThread
from machine.ipc import IpcClient
from config import (
    SCAN_X_START, SCAN_Y_START, Z_BED_DOWN, Z_BED_UP,
    MOVE_FEEDRATE, BED_FEEDRATE,
    GRIPPER_OPEN, GRIPPER_CLOSE,
    DROP_X, DROP_Y,
    PICKUP_CX, PICKUP_CY, IMAGE_CX, IMAGE_CY,
    SCALE_X, SCALE_Y,
    ALIGN_THRESH_X, ALIGN_THRESH_Y,
    FINE_TUNE_TIMEOUT, FINE_TUNE_MAX_ATTEMPTS,
)

logger = logging.getLogger(__name__)


class SequenceCoordinator(threading.Thread):

    def __init__(self, toolhead_cam: CameraThread, overhead_cam: CameraThread,
                 ipc: IpcClient, ws: WebSocketManager):
        super().__init__(daemon=True, name="SequenceCoordinator")
        self._toolhead_cam = toolhead_cam
        self._overhead_cam = overhead_cam
        self._ipc          = ipc
        self._ws           = ws

        self._state        = SequenceState.STARTUP
        self._state_lock   = threading.Lock()
        self._running      = True

        # Trigger mechanism
        self._trigger      = threading.Event()
        self._trigger_lock = threading.Lock()
        self._pending: Optional[str] = None   # "start" | "stop" | "retry" | "reset"

        # Overhead detection count before pickup (for gripper verification)
        self._pre_pickup_count: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def state(self) -> SequenceState:
        with self._state_lock:
            return self._state

    def trigger(self, action: str):
        """
        Send a trigger to the coordinator from any thread.
        action: "start" | "stop" | "retry" | "reset"
        """
        with self._trigger_lock:
            self._pending = action
        self._trigger.set()
        logger.info(f"[Coordinator] Trigger: {action!r}")

    def hard_fault(self, reason: str):
        """Called by heartbeat poller or exception handler."""
        logger.error(f"[Coordinator] Hard fault: {reason}")
        self._set_state(SequenceState.HARD_FAULT)
        self._ws.emit(SequenceFaultMessage(
            payload=SequenceFaultPayload(
                fault="hard_fault",
                detail=reason,
            )
        ))

    def stop(self):
        self._running = False
        self._trigger.set()

    # ------------------------------------------------------------------
    # Thread main loop
    # ------------------------------------------------------------------

    def run(self):
        self._set_state(SequenceState.STARTUP)
        self._startup()

        while self._running:
            try:
                self._ready_loop()
            except Exception as exc:
                logger.exception(f"[Coordinator] Unhandled exception: {exc}")
                self.hard_fault(str(exc))
                # Wait for operator or systemd restart
                time.sleep(60)

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def _startup(self):
        """Wait for IPC and cameras to become available."""
        logger.info("[Coordinator] Startup - waiting for services")

        # Wait for launcher IPC socket
        for _ in range(30):
            if self._ipc.is_available():
                break
            time.sleep(1)
        else:
            self.hard_fault("Launcher IPC socket unavailable after 30s")
            return

        # Home the machine
        self._machine("G28")
        self._set_state(SequenceState.READY)
        self._set_indicator(True)

    # ------------------------------------------------------------------
    # Ready loop - waits for start trigger
    # ------------------------------------------------------------------

    def _ready_loop(self):
        self._set_state(SequenceState.READY)
        self._set_indicator(True)

        logger.info("[Coordinator] Ready - awaiting trigger")
        self._trigger.wait()
        self._trigger.clear()

        action = self._consume_trigger()
        if action == "start":
            self._set_indicator(False)
            self._run_sequence()

    # ------------------------------------------------------------------
    # Main sequence
    # ------------------------------------------------------------------

    def _run_sequence(self):
        try:
            # 1. Scan overhead
            detected, count = self._do_scanning()
            if not detected:
                self._soft_fault(SoftFaultType.TARGET_NOT_FOUND, image1="overhead")
                return
            self._pre_pickup_count = count

            # 2. Plan path (currently trivial - just the detected position)
            target = self._do_planning()
            if target is None:
                # No viable path - return to ready silently
                return

            # 3. Move to pickup
            self._do_move_to_pickup(target)

            # 4. Fine-tune
            success = self._do_fine_tuning()
            if not success:
                self._soft_fault(SoftFaultType.FINE_TUNE_TIMEOUT, image1="toolhead")
                return

            # 5. Pick up
            self._do_pickup()

            # 6. Move to dropoff
            self._do_move_to_dropoff()

            # 7. Verify dropoff
            verified = self._do_verify_dropoff()
            if not verified:
                self._soft_fault(
                    SoftFaultType.OBJECT_STILL_PRESENT,
                    image1="overhead_before",
                    image2="overhead_after",
                )
                return

            # 8. Done - home and loop
            self._set_state(SequenceState.DROPPED)
            self._machine(f"G0 X{SCAN_X_START} Y{SCAN_Y_START} "
                          f"Z{Z_BED_DOWN} F{BED_FEEDRATE}")
            self._machine(f"M280 S{GRIPPER_OPEN}")

        except Exception as exc:
            raise  # let the outer loop handle it

    # ------------------------------------------------------------------
    # Sequence steps
    # ------------------------------------------------------------------

    def _do_scanning(self) -> tuple[bool, int]:
        self._set_state(SequenceState.SCANNING)
        logger.info("[Coordinator] Scanning overhead")

        result = self._overhead_cam.capture_single(timeout=10.0)
        if result is None or not result.detected:
            return False, 0
        return True, 1  # count=1 for now; ML extension adds multi-cylinder

    def _do_planning(self):
        self._set_state(SequenceState.PLANNING)
        logger.info("[Coordinator] Planning path")

        result = self._overhead_cam.latest_detection
        if result is None or not result.detected:
            return None

        # Convert pixel coordinates to machine coordinates
        # (direct line for now; path planner extension goes here)
        dx = result.px - IMAGE_CX
        dy = result.py - IMAGE_CY
        target_x = SCAN_X_START + dx * (SCALE_X / 100.0)
        target_y = SCAN_Y_START + dy * (SCALE_Y / 100.0)
        return (target_x, target_y)

    def _do_move_to_pickup(self, target: tuple):
        self._set_state(SequenceState.MOVING_TO_PICKUP)
        x, y = target
        logger.info(f"[Coordinator] Moving to pickup ({x:.1f}, {y:.1f})")
        self._machine(f"G0 X{x:.2f} Y{y:.2f} F{MOVE_FEEDRATE}")

    def _do_fine_tuning(self) -> bool:
        self._set_state(SequenceState.FINE_TUNING)
        logger.info("[Coordinator] Fine-tuning position")
        self._toolhead_cam.start_streaming()

        start   = time.time()
        attempt = 0

        try:
            while time.time() - start < FINE_TUNE_TIMEOUT:
                if attempt >= FINE_TUNE_MAX_ATTEMPTS:
                    return False

                result = self._toolhead_cam.capture_single(timeout=3.0)
                if result is None or not result.detected:
                    attempt += 1
                    continue

                dx = result.px - PICKUP_CX
                dy = result.py - PICKUP_CY

                if abs(dx) <= ALIGN_THRESH_X and abs(dy) <= ALIGN_THRESH_Y:
                    logger.info(f"[Coordinator] Aligned after {attempt} attempts")
                    return True

                move_x = dx * (SCALE_X / 100.0)
                move_y = dy * (SCALE_Y / 100.0)
                self._machine(f"G0 X{move_x:.2f} Y{move_y:.2f} "
                              f"F{MOVE_FEEDRATE}")
                attempt += 1
                time.sleep(0.1)

            return False

        finally:
            self._toolhead_cam.stop_streaming()

    def _do_pickup(self):
        self._set_state(SequenceState.PICKING_UP)
        logger.info("[Coordinator] Picking up")
        self._machine(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
        self._machine(f"M280 S{GRIPPER_CLOSE}")
        time.sleep(0.5)
        self._machine(f"G0 Z{Z_BED_UP} F{BED_FEEDRATE}")
        self._ws.emit(HealthGrabberMessage(
            payload=HealthGrabberPayload(status=GrabberState.CLOSED)
        ))

    def _do_move_to_dropoff(self):
        self._set_state(SequenceState.MOVING_TO_DROPOFF)
        logger.info(f"[Coordinator] Moving to dropoff ({DROP_X}, {DROP_Y})")
        self._machine(f"G0 X{DROP_X} Y{DROP_Y} F{MOVE_FEEDRATE}")
        self._machine(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
        self._machine(f"M280 S{GRIPPER_OPEN}")
        time.sleep(0.3)
        self._machine(f"G0 Z{Z_BED_UP} F{BED_FEEDRATE}")
        self._ws.emit(HealthGrabberMessage(
            payload=HealthGrabberPayload(status=GrabberState.OPEN)
        ))

    def _do_verify_dropoff(self) -> bool:
        self._set_state(SequenceState.VERIFYING_DROPOFF)
        logger.info("[Coordinator] Verifying dropoff")

        result = self._overhead_cam.capture_single(timeout=10.0)
        if result is None:
            return False

        # If we detected an object before and none after, success
        after_count = 1 if result.detected else 0
        return after_count < self._pre_pickup_count

    # ------------------------------------------------------------------
    # Soft fault handling
    # ------------------------------------------------------------------

    def _soft_fault(self, fault: SoftFaultType,
                    image1: str, image2: str = None):
        self._set_state(SequenceState.AWAITING_OPERATOR)
        logger.warning(f"[Coordinator] Soft fault: {fault.value}")

        self._ws.emit(SequenceAwaitingOperatorMessage(
            payload=SequenceAwaitingOperatorPayload(
                fault=fault,
                image1=f"/api/camera/overhead/frame/{image1}",
                image2=f"/api/camera/overhead/frame/{image2}" if image2 else None,
            )
        ))
        self._set_indicator(True)  # prompt operator

        # Wait for operator action
        self._trigger.wait()
        self._trigger.clear()
        self._set_indicator(False)

        action = self._consume_trigger()
        if action == "retry":
            self._run_sequence()   # restart from scanning
        elif action == "reset":
            pass                   # fall through to ready_loop

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_state(self, state: SequenceState):
        with self._state_lock:
            self._state = state
        logger.debug(f"[Coordinator] State -> {state.value}")
        self._ws.emit(SequenceStateMessage(
            payload=SequenceStatePayload(state=state)
        ))

    def _set_indicator(self, on: bool):
        self._ws.emit(IndicatorReadyMessage(
            payload=IndicatorReadyPayload(on=on)
        ))

    def _machine(self, cmd: str) -> str:
        resp = self._ipc.send(cmd)
        if resp.startswith("ERROR:"):
            raise RuntimeError(f"Machine command failed: {cmd!r} -> {resp}")
        return resp

    def _consume_trigger(self) -> Optional[str]:
        with self._trigger_lock:
            action = self._pending
            self._pending = None
        return action
