import { useState, useCallback } from "react";
import { useWebSocket } from "./useWebSocket";
import {
  SequenceState,
  MachineState,
  MachineCommsStatus,
  CameraState,
  GrabberState,
  ButtonState,
  SoftFaultType,
  WsMessage,
} from "../types/messages";

export interface SystemState {
  // Sequence
  sequenceState:      SequenceState | null;
  indicatorOn:        boolean;

  // Awaiting operator
  awaitingOperator:   boolean;
  operatorFault:      SoftFaultType | null;
  operatorImage1:     string | null;
  operatorImage2:     string | null;

  // Hard fault
  hardFault:          boolean;
  hardFaultDetail:    string | null;

  // Machine
  machineComms:       MachineCommsStatus | null;
  machineState:       MachineState | null;
  lastMachineResponse: string | null;

  // Health
  toolheadCameraState: CameraState | null;
  overheadCameraState: CameraState | null;
  grabberState:        GrabberState | null;
  buttonState:         ButtonState | null;
}

const initialState: SystemState = {
  sequenceState:       null,
  indicatorOn:         false,
  awaitingOperator:    false,
  operatorFault:       null,
  operatorImage1:      null,
  operatorImage2:      null,
  hardFault:           false,
  hardFaultDetail:     null,
  machineComms:        null,
  machineState:        null,
  lastMachineResponse: null,
  toolheadCameraState: null,
  overheadCameraState: null,
  grabberState:        null,
  buttonState:         null,
};

/**
 * useSystemState
 *
 * Subscribes to the WebSocket and maintains the full system state.
 * Import this once at the app root and pass state down via props or context.
 */
export function useSystemState() {
  const [state, setState] = useState<SystemState>(initialState);

  const handleMessage = useCallback((msg: WsMessage) => {
    setState((prev) => {
      switch (msg.type) {

        case "sequence.state":
          return {
            ...prev,
            sequenceState:    msg.payload.state,
            awaitingOperator: msg.payload.state === "awaiting_operator",
            hardFault:        msg.payload.state === "hard_fault",
            // Clear operator context when leaving awaiting_operator
            ...(msg.payload.state !== "awaiting_operator" ? {
              operatorFault:  null,
              operatorImage1: null,
              operatorImage2: null,
            } : {}),
          };

        case "sequence.awaiting_operator":
          return {
            ...prev,
            awaitingOperator: true,
            operatorFault:    msg.payload.fault,
            operatorImage1:   msg.payload.image1,
            operatorImage2:   msg.payload.image2 ?? null,
          };

        case "sequence.fault":
          return {
            ...prev,
            hardFault:       true,
            hardFaultDetail: msg.payload.detail,
          };

        case "machine.response":
          return { ...prev, lastMachineResponse: msg.payload.response };

        case "machine.state":
          return { ...prev, machineState: msg.payload.state };

        case "machine.heartbeat_lost":
          return { ...prev, machineComms: "fault" };

        case "indicator.ready":
          return { ...prev, indicatorOn: msg.payload.on };

        case "indicator.button_connected":
          return {
            ...prev,
            buttonState: msg.payload.connected ? "connected" : "not_connected",
          };

        case "health.toolhead_camera":
          return { ...prev, toolheadCameraState: msg.payload.state };

        case "health.overhead_camera":
          return { ...prev, overheadCameraState: msg.payload.state };

        case "health.machine":
          return { ...prev, machineComms: msg.payload.comms };

        case "health.grabber":
          return { ...prev, grabberState: msg.payload.status };

        case "health.button":
          return { ...prev, buttonState: msg.payload.status };

        default:
          return prev;
      }
    });
  }, []);

  useWebSocket(handleMessage);

  return state;
}
