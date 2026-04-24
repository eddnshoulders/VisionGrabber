import { SystemState } from "../hooks/useSystemState";

interface Props {
  state: SystemState;
}

type Status = "ok" | "fault" | "unknown";

function Indicator({ label, status }: { label: string; status: Status }) {
  const colour =
    status === "ok"    ? "#2a7f4a" :
    status === "fault" ? "#7f2a2a" : "#444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
      <div style={{
        width: 12, height: 12, borderRadius: "50%",
        background: colour, flexShrink: 0,
      }} />
      <span style={{ fontSize: 13, color: "#ccc" }}>{label}</span>
    </div>
  );
}

export function HealthPanel({ state }: Props) {
  const commsStatus = state.machineComms === "ok"    ? "ok"
                    : state.machineComms === "fault"  ? "fault" : "unknown";
  const toolStatus  = state.toolheadCameraState === "active" ? "ok"
                    : state.toolheadCameraState === "fault"  ? "fault" : "unknown";
  const overStatus  = state.overheadCameraState === "active" ? "ok"
                    : state.overheadCameraState === "fault"  ? "fault" : "unknown";
  const grabStatus  = state.grabberState === "suspected_fault" ? "fault"
                    : state.grabberState ? "ok" : "unknown";
  const btnStatus   = state.buttonState === "connected" ? "ok"
                    : state.buttonState === "not_connected" ? "fault" : "unknown";

  return (
    <div style={{ background: "#1c1c1c", borderRadius: 8, padding: 14 }}>
      <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#aaa",
                   textTransform: "uppercase", letterSpacing: 1 }}>
        System Health
      </h3>
      <Indicator label="Machine comms"    status={commsStatus} />
      <Indicator label="Toolhead camera"  status={toolStatus}  />
      <Indicator label="Overhead camera"  status={overStatus}  />
      <Indicator label={`Grabber (${state.grabberState ?? "unknown"})`}
                 status={grabStatus} />
      <Indicator label={`Button (${state.buttonState ?? "unknown"})`}
                 status={btnStatus} />

      {state.machineState && (
        <div style={{ marginTop: 10, fontSize: 12, color: "#888",
                      fontFamily: "monospace" }}>
          MCU: {state.machineState}
        </div>
      )}
      {state.lastMachineResponse && (
        <div style={{ marginTop: 4, fontSize: 12, color: "#7fc97f",
                      fontFamily: "monospace", wordBreak: "break-all" }}>
          Last response: {state.lastMachineResponse}
        </div>
      )}
    </div>
  );
}
