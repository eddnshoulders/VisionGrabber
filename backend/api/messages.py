"""
WebSocket message types for VisionGrabber.
Mirrors frontend/src/types/messages.ts - keep in sync.

All messages serialise to:
    {"type": "...", "ts": <unix ms>, "payload": {...}}
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Literal, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Shared enums  (mirror TypeScript union types)
# ---------------------------------------------------------------------------

class SequenceState(str, Enum):
    STARTUP             = "startup"
    READY               = "ready"
    SCANNING            = "scanning"
    PLANNING            = "planning"
    MOVING_TO_PICKUP    = "moving_to_pickup"
    FINE_TUNING         = "fine_tuning"
    PICKING_UP          = "picking_up"
    MOVING_TO_DROPOFF   = "moving_to_dropoff"
    VERIFYING_DROPOFF   = "verifying_dropoff"
    DROPPED             = "dropped"
    AWAITING_OPERATOR   = "awaiting_operator"
    HARD_FAULT          = "hard_fault"


class SoftFaultType(str, Enum):
    FINE_TUNE_TIMEOUT   = "fine_tune_timeout"
    TARGET_NOT_FOUND    = "target_not_found"
    OBJECT_STILL_PRESENT = "object_still_present"


class MachineState(str, Enum):
    UNHOMED                   = "UNHOMED"
    HOMING_X_INITIAL_STEPBACK = "HOMING_X_INITIAL_STEPBACK"
    HOMING_X_FAST             = "HOMING_X_FAST"
    HOMING_X_STEPBACK         = "HOMING_X_STEPBACK"
    HOMING_X_SLOW             = "HOMING_X_SLOW"
    HOMING_Y_INITIAL_STEPBACK = "HOMING_Y_INITIAL_STEPBACK"
    HOMING_Y_FAST             = "HOMING_Y_FAST"
    HOMING_Y_STEPBACK         = "HOMING_Y_STEPBACK"
    HOMING_Y_SLOW             = "HOMING_Y_SLOW"
    HOMING_Z_INITIAL_STEPBACK = "HOMING_Z_INITIAL_STEPBACK"
    HOMING_Z_FAST             = "HOMING_Z_FAST"
    HOMING_Z_STEPBACK         = "HOMING_Z_STEPBACK"
    HOMING_Z_SLOW             = "HOMING_Z_SLOW"
    HOMED                     = "HOMED"
    IDLE                      = "IDLE"
    MOVING                    = "MOVING"
    STOPPING                  = "STOPPING"
    FAULT                     = "FAULT"


class MachineCommsStatus(str, Enum):
    OK    = "ok"
    FAULT = "fault"


class CameraState(str, Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    FAULT    = "fault"


class GrabberState(str, Enum):
    OPEN             = "open"
    CLOSED           = "closed"
    SUSPECTED_FAULT  = "suspected_fault"


class ButtonState(str, Enum):
    CONNECTED     = "connected"
    NOT_CONNECTED = "not_connected"


# ---------------------------------------------------------------------------
# Base message  (handles serialisation for all message types)
# ---------------------------------------------------------------------------

@dataclass
class _BaseMessage:
    type: str
    payload: object
    ts: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_dict(self) -> dict:
        """Serialise to the wire format: {type, ts, payload}."""
        d = asdict(self)
        # Convert any nested Enum values to their string values
        return _serialise(d)


def _serialise(obj):
    """Recursively convert Enum members to their values for JSON serialisation."""
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialise(v) for v in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj


# ---------------------------------------------------------------------------
# Payload dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MachineResponsePayload:
    response: str


@dataclass
class MachineStatePayload:
    state: MachineState


@dataclass
class MachineHeartbeatLostPayload:
    consecutive_failures: int


@dataclass
class SequenceStatePayload:
    state: SequenceState


@dataclass
class SequenceAwaitingOperatorPayload:
    fault: SoftFaultType
    image1: str
    image2: Optional[str] = None   # only present for object_still_present


@dataclass
class SequenceFaultPayload:
    fault: str     # hard fault description
    detail: str    # exception message or context


@dataclass
class IndicatorReadyPayload:
    on: bool       # mirrors physical LED state


@dataclass
class IndicatorButtonConnectedPayload:
    connected: bool


@dataclass
class HealthCameraPayload:
    state: CameraState


@dataclass
class HealthMachinePayload:
    comms: MachineCommsStatus


@dataclass
class HealthGrabberPayload:
    status: GrabberState


@dataclass
class HealthButtonPayload:
    status: ButtonState


# ---------------------------------------------------------------------------
# Message dataclasses  (one per WsMessageType)
# ---------------------------------------------------------------------------

@dataclass
class MachineResponseMessage(_BaseMessage):
    type: str = field(default="machine.response", init=False)
    payload: MachineResponsePayload = field(default=None)


@dataclass
class MachineStateMessage(_BaseMessage):
    type: str = field(default="machine.state", init=False)
    payload: MachineStatePayload = field(default=None)


@dataclass
class MachineHeartbeatLostMessage(_BaseMessage):
    type: str = field(default="machine.heartbeat_lost", init=False)
    payload: MachineHeartbeatLostPayload = field(default=None)


@dataclass
class SequenceStateMessage(_BaseMessage):
    type: str = field(default="sequence.state", init=False)
    payload: SequenceStatePayload = field(default=None)


@dataclass
class SequenceAwaitingOperatorMessage(_BaseMessage):
    type: str = field(default="sequence.awaiting_operator", init=False)
    payload: SequenceAwaitingOperatorPayload = field(default=None)


@dataclass
class SequenceFaultMessage(_BaseMessage):
    type: str = field(default="sequence.fault", init=False)
    payload: SequenceFaultPayload = field(default=None)


@dataclass
class IndicatorReadyMessage(_BaseMessage):
    type: str = field(default="indicator.ready", init=False)
    payload: IndicatorReadyPayload = field(default=None)


@dataclass
class IndicatorButtonConnectedMessage(_BaseMessage):
    type: str = field(default="indicator.button_connected", init=False)
    payload: IndicatorButtonConnectedPayload = field(default=None)


@dataclass
class HealthToolheadCameraMessage(_BaseMessage):
    type: str = field(default="health.toolhead_camera", init=False)
    payload: HealthCameraPayload = field(default=None)


@dataclass
class HealthOverheadCameraMessage(_BaseMessage):
    type: str = field(default="health.overhead_camera", init=False)
    payload: HealthCameraPayload = field(default=None)


@dataclass
class HealthMachineMessage(_BaseMessage):
    type: str = field(default="health.machine", init=False)
    payload: HealthMachinePayload = field(default=None)


@dataclass
class HealthGrabberMessage(_BaseMessage):
    type: str = field(default="health.grabber", init=False)
    payload: HealthGrabberPayload = field(default=None)


@dataclass
class HealthButtonMessage(_BaseMessage):
    type: str = field(default="health.button", init=False)
    payload: HealthButtonPayload = field(default=None)


# ---------------------------------------------------------------------------
# Convenience type alias  (mirrors TypeScript WsMessage union)
# ---------------------------------------------------------------------------

WsMessage = (
    MachineResponseMessage
    | MachineStateMessage
    | MachineHeartbeatLostMessage
    | SequenceStateMessage
    | SequenceAwaitingOperatorMessage
    | SequenceFaultMessage
    | IndicatorReadyMessage
    | IndicatorButtonConnectedMessage
    | HealthToolheadCameraMessage
    | HealthOverheadCameraMessage
    | HealthMachineMessage
    | HealthGrabberMessage
    | HealthButtonMessage
)