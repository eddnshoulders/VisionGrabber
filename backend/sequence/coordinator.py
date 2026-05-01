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


class StopRequested(Exception):
    """Raised when the operator presses Stop during a sequence."""
    pass

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
from camera.calibration import CalibrationManager
from machine.ipc import IpcClient
from config import *

logger = logging.getLogger(__name__)


class SequenceCoordinator(threading.Thread):

    def __init__(self, toolhead_cam: CameraThread, overhead_cam: CameraThread,
                 ipc: IpcClient, ws: WebSocketManager,
                 calibration: CalibrationManager):
        super().__init__(daemon=True, name="SequenceCoordinator")
        self._toolhead_cam = toolhead_cam
        self._overhead_cam = overhead_cam
        self._ipc          = ipc
        self._ws           = ws
        self._calibration  = calibration

        self._state        = SequenceState.STARTUP
        self._state_lock   = threading.Lock()
        self._running      = True

        # Trigger mechanism
        self._trigger      = threading.Event()
        self._trigger_lock = threading.Lock()
        self._pending: Optional[str] = None   # "start" | "stop" | "retry" | "reset"
        self._stop_requested = False

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
        if action == "stop":
            self._stop_requested = True
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
        """Wait for IPC socket to become available then move to ready."""
        logger.info("[Coordinator] Startup - waiting for IPC socket")

        for _ in range(30):
            if self._ipc.is_available():
                break
            time.sleep(1)
        else:
            self.hard_fault("Launcher IPC socket unavailable after 30s")
            return

        logger.info("[Coordinator] IPC available - ready")
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
            # Check camera health before starting
            self._toolhead_cam.check_health()
            self._overhead_cam.check_health()
            self._stop_requested = False

            # Ensure bed is at Z_BED_DOWN before scanning
            pos = self._get_position()
            if pos is not None:
                _, _, z = pos
                if abs(z - Z_BED_DOWN) > 0.5:
                    logger.info(f"[Coordinator] Bed at Z={z:.1f}, "
                                f"moving to Z_BED_DOWN={Z_BED_DOWN}")
                    self._machine(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")

            # 1. Scan overhead
            self._check_stop()
            detected, count = self._do_scanning()
            if not detected:
                self._soft_fault(SoftFaultType.TARGET_NOT_FOUND, image1="overhead")
                return
            self._pre_pickup_count = count

            # 2. Plan path
            self._check_stop()
            target = self._do_planning()
            if target is None:
                return

            # 3. Move to pickup
            self._check_stop()
            self._do_move_to_pickup(target)

            # 4. Fine-tune
            self._check_stop()
            success = self._do_fine_tuning()
            if not success:
                self._soft_fault(SoftFaultType.FINE_TUNE_TIMEOUT, image1="toolhead")
                return

            # 5. Pick up
            self._check_stop()
            self._do_pickup()

            # 6. Move to dropoff and drop
            self._check_stop()
            self._do_move_to_dropoff()

            # 7. Home
            self._set_state(SequenceState.DROPPED)
            self._machine(f"G0 X{SCAN_X_START} Y{SCAN_Y_START} F{MOVE_FEEDRATE}")

            # 8. Verify dropoff
            verified = self._do_verify_dropoff()
            if not verified:
                self._soft_fault(
                    SoftFaultType.OBJECT_STILL_PRESENT,
                    image1="overhead_before",
                    image2="overhead_after",
                )
                return

        except StopRequested:
            logger.info("[Coordinator] Stop requested - halting machine")
            self._ipc.send("STOP")
            self._toolhead_cam.stop_streaming()
            self._stop_requested = False
            self._soft_fault(SoftFaultType.OPERATOR_STOP, image1="")

        except Exception as exc:
            raise  # let the outer loop handle it
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

            # 6. Move to dropoff and drop
            self._do_move_to_dropoff()

            # 7. Home first - gantry out of the way before taking overhead frame
            self._set_state(SequenceState.DROPPED)
            self._machine(f"G0 X{SCAN_X_START} Y{SCAN_Y_START} F{MOVE_FEEDRATE}")

            # 8. Verify dropoff - overhead frame after homing shows full bed
            verified = self._do_verify_dropoff()
            if not verified:
                self._soft_fault(
                    SoftFaultType.OBJECT_STILL_PRESENT,
                    image1="overhead_before",
                    image2="overhead_after",
                )
                return

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
        return True, result.count  # count = number of cylinders detected

    def _do_planning(self):
        self._set_state(SequenceState.PLANNING)
        logger.info("[Coordinator] Planning path")

        result = self._overhead_cam.latest_detection
        if result is None or not result.detected:
            return None

        best   = result.best
        target = self._calibration.pixel_to_machine(best.px, best.py)
        mx, my = target

        # Enforce machine working area limits
        if not (SCAN_X_END <= mx <= SCAN_X_START and
                SCAN_Y_END <= my <= SCAN_Y_START):
            logger.warning(
                f"[Coordinator] Target ({mx:.1f},{my:.1f}) outside machine limits "
                f"(X:{SCAN_X_END}-{SCAN_X_START} Y:{SCAN_Y_END}-{SCAN_Y_START})"
            )
            return None

        logger.info(f"[Coordinator] Target: pixel ({best.px},{best.py}) "
                    f"→ machine ({mx:.2f},{my:.2f})")
        return mx, my

    def _do_move_to_pickup(self, target: tuple):
        self._set_state(SequenceState.MOVING_TO_PICKUP)
        x, y = target
        logger.info(f"[Coordinator] Moving to pickup ({x:.1f}, {y:.1f})")
        self._machine(f"G0 X{x:.2f} Y{y:.2f} F{MOVE_FEEDRATE}")

    def _do_fine_tuning(self) -> bool:
        self._set_state(SequenceState.FINE_TUNING)
        logger.info("[Coordinator] Fine-tuning position")

        # Always stream during fine-tuning for frontend display.
        # Track whether user had streaming on so we can restore state after.
        was_streaming = self._toolhead_cam.mode.value == "streaming"
        self._toolhead_cam.start_streaming()

        start   = time.time()
        attempt = 0

        try:
            while time.time() - start < FINE_TUNE_TIMEOUT:
                if attempt >= FINE_TUNE_MAX_ATTEMPTS:
                    return False

                time.sleep(0.5)

                result = self._toolhead_cam.capture_single(timeout=3.0)
                if result is None or not result.detected:
                    attempt += 1
                    continue

                best = result.best
                px   = best.px
                py   = best.py

                # Get current machine position
                pos = self._get_position()
                if pos is None:
                    attempt += 1
                    continue

                tx, ty, tz = pos

                # Compute absolute target (same as original scan_and_grab.py)
                offset_x = (px - PICKUP_CX) / SCALE_X
                offset_y = (py - PICKUP_CY) / SCALE_Y
                target_x = max(0, min(120, tx + offset_x))
                target_y = max(0, min(120, ty + offset_y))

                logger.info(
                    f"[Coordinator] Align: px={px:.1f} py={py:.1f} "
                    f"offset=({offset_x:.2f},{offset_y:.2f}) "
                    f"target=({target_x:.2f},{target_y:.2f})"
                )

                self._machine(
                    f"G0 X{target_x:.2f} Y{target_y:.2f} F{MOVE_FEEDRATE}"
                )
                time.sleep(STEP_SETTLE_TIME)

                # Check residual
                result2 = self._toolhead_cam.capture_single(timeout=3.0)
                if result2 is None or not result2.detected:
                    logger.warning("[Coordinator] No detection after alignment move")
                    attempt += 1
                    continue

                best2  = result2.best
                ofst_x = abs(best2.px - PICKUP_CX)
                ofst_y = abs(best2.py - PICKUP_CY)

                logger.info(
                    f"[Coordinator] Residual: dx={ofst_x:.1f} dy={ofst_y:.1f} "
                    f"(tol {ALIGN_THRESH_X}/{ALIGN_THRESH_Y})"
                )

                if ofst_x < ALIGN_THRESH_X and ofst_y < ALIGN_THRESH_Y:
                    logger.info(f"[Coordinator] Aligned after {attempt} attempts")
                    return True

                attempt += 1

            return False

        finally:
            if not was_streaming:
                self._toolhead_cam.stop_streaming()

    def _do_pickup(self):
        self._set_state(SequenceState.PICKING_UP)
        logger.info("[Coordinator] Picking up")
        self._machine(f"G0 Z{Z_BED_UP} F{BED_FEEDRATE}")
        self._machine(f"M280 S{GRIPPER_CLOSE}")
        time.sleep(1)
        self._machine(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
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
        self._ws.emit(HealthGrabberMessage(
            payload=HealthGrabberPayload(status=GrabberState.OPEN)
        ))
        # Z stays down - gantry moves back to home in _run_sequence after verify

    def _do_verify_dropoff(self) -> bool:
        self._set_state(SequenceState.VERIFYING_DROPOFF)
        logger.info("[Coordinator] Verifying dropoff")

        result = self._overhead_cam.capture_single(timeout=10.0)
        if result is None:
            return False

        after_count = result.count
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
                image1=f"/api/camera/overhead/frame/{image1}" if image1 else None,
                image2=f"/api/camera/overhead/frame/{image2}" if image2 else None,
            )
        ))
        self._set_indicator(True)

        # Wait for operator action
        self._trigger.wait()
        self._trigger.clear()
        self._set_indicator(False)

        action = self._consume_trigger()

        # operator_stop only supports reset
        if fault == SoftFaultType.OPERATOR_STOP or action == "reset":
            # Open gripper and home
            self._ipc.send(f"M280 S{GRIPPER_OPEN}")
            self._machine(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
            self._machine(f"G0 X{SCAN_X_START} Y{SCAN_Y_START} F{MOVE_FEEDRATE}")
        elif action == "retry":
            self._run_sequence()   # restart from scanning

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

    def _check_stop(self):
        """Raise StopRequested if operator pressed Stop."""
        if self._stop_requested:
            raise StopRequested()

    def _get_position(self) -> Optional[tuple[float, float, float]]:
        """Fetch current machine position via M114. Returns (x, y, z) or None."""
        import re
        resp  = self._ipc.send("M114")
        match = re.search(r"X:([\d.-]+)\s+Y:([\d.-]+)\s+Z:([\d.-]+)", resp)
        if not match:
            logger.warning(f"[Coordinator] Could not parse M114: {resp!r}")
            return None
        return (float(match.group(1)),
                float(match.group(2)),
                float(match.group(3)))

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
