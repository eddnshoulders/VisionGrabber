// ── Sequence ──────────────────────────────────────────────────────────────────

export type SequenceState =
  | "startup"
  | "ready"
  | "scanning"
  | "planning"
  | "moving_to_pickup"
  | "fine_tuning"
  | "picking_up"
  | "moving_to_dropoff"
  | "verifying_dropoff"
  | "dropped"
  | "awaiting_operator"
  | "hard_fault";

export type SoftFaultType =
  | "fine_tune_timeout"
  | "target_not_found"
  | "object_still_present";

// ── Machine ───────────────────────────────────────────────────────────────────

export type MachineState =
  | "UNHOMED"
  | "HOMING_X_INITIAL_STEPBACK"
  | "HOMING_X_FAST"
  | "HOMING_X_STEPBACK"
  | "HOMING_X_SLOW"
  | "HOMING_Y_INITIAL_STEPBACK"
  | "HOMING_Y_FAST"
  | "HOMING_Y_STEPBACK"
  | "HOMING_Y_SLOW"
  | "HOMING_Z_INITIAL_STEPBACK"
  | "HOMING_Z_FAST"
  | "HOMING_Z_STEPBACK"
  | "HOMING_Z_SLOW"
  | "HOMED"
  | "IDLE"
  | "MOVING"
  | "STOPPING"
  | "FAULT";

export type MachineCommsStatus = "ok" | "fault";

// ── Hardware states ───────────────────────────────────────────────────────────

export type CameraState = "active" | "inactive" | "fault";

export type GrabberState = "open" | "closed" | "suspected_fault";

export type ButtonState = "connected" | "not_connected";

// ── Payloads ──────────────────────────────────────────────────────────────────

export interface MachineResponsePayload {
  response: string;
}

export interface MachineStatePayload {
  state: MachineState;
}

export interface MachineHeartbeatLostPayload {
  consecutive_failures: number;
}

export interface SequenceStatePayload {
  state: SequenceState;
}

export interface SequenceAwaitingOperatorPayload {
  fault: SoftFaultType;
  image1: string;
  image2?: string;
}

export interface SequenceFaultPayload {
  fault: string;
  detail: string;
}

export interface IndicatorReadyPayload {
  on: boolean;
}

export interface IndicatorButtonConnectedPayload {
  connected: boolean;
}

export interface HealthCameraPayload {
  state: CameraState;
}

export interface HealthMachinePayload {
  comms: MachineCommsStatus;
}

export interface HealthGrabberPayload {
  status: GrabberState;
}

export interface HealthButtonPayload {
  status: ButtonState;
}

// ── Messages ──────────────────────────────────────────────────────────────────

export interface MachineResponseMessage {
  type: "machine.response";
  ts: number;
  payload: MachineResponsePayload;
}

export interface MachineStateMessage {
  type: "machine.state";
  ts: number;
  payload: MachineStatePayload;
}

export interface MachineHeartbeatLostMessage {
  type: "machine.heartbeat_lost";
  ts: number;
  payload: MachineHeartbeatLostPayload;
}

export interface SequenceStateMessage {
  type: "sequence.state";
  ts: number;
  payload: SequenceStatePayload;
}

export interface SequenceAwaitingOperatorMessage {
  type: "sequence.awaiting_operator";
  ts: number;
  payload: SequenceAwaitingOperatorPayload;
}

export interface SequenceFaultMessage {
  type: "sequence.fault";
  ts: number;
  payload: SequenceFaultPayload;
}

export interface IndicatorReadyMessage {
  type: "indicator.ready";
  ts: number;
  payload: IndicatorReadyPayload;
}

export interface IndicatorButtonConnectedMessage {
  type: "indicator.button_connected";
  ts: number;
  payload: IndicatorButtonConnectedPayload;
}

export interface HealthToolheadCameraMessage {
  type: "health.toolhead_camera";
  ts: number;
  payload: HealthCameraPayload;
}

export interface HealthOverheadCameraMessage {
  type: "health.overhead_camera";
  ts: number;
  payload: HealthCameraPayload;
}

export interface HealthMachineMessage {
  type: "health.machine";
  ts: number;
  payload: HealthMachinePayload;
}

export interface HealthGrabberMessage {
  type: "health.grabber";
  ts: number;
  payload: HealthGrabberPayload;
}

export interface HealthButtonMessage {
  type: "health.button";
  ts: number;
  payload: HealthButtonPayload;
}

// ── Union ─────────────────────────────────────────────────────────────────────

export type WsMessage =
  | MachineResponseMessage
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
  | HealthButtonMessage;
