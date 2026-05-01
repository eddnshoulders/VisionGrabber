import { SystemState } from "../hooks/useSystemState";
import { sequenceApi } from "../api/client";
import { SequenceState } from "../types/messages";

interface Props {
  state: SystemState;
}

const STATE_LABELS: Record<SequenceState, string> = {
  startup:           "Starting up...",
  ready:             "Ready",
  scanning:          "Scanning bed",
  planning:          "Planning path",
  moving_to_pickup:  "Moving to pickup",
  fine_tuning:       "Fine-tuning position",
  picking_up:        "Picking up",
  moving_to_dropoff: "Moving to dropoff",
  verifying_dropoff: "Verifying dropoff",
  dropped:           "Dropped - returning home",
  awaiting_operator: "Awaiting operator",
  hard_fault:        "FAULT - restart required",
};

const STATE_COLOUR: Partial<Record<SequenceState, string>> = {
  ready:             "#2a7f4a",
  awaiting_operator: "#BA7517",
  hard_fault:        "#7f2a2a",
};

function btn(label: string, onClick: () => void,
             colour = "#2a4a7f", disabled = false) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "8px 16px", background: disabled ? "#333" : colour,
        color: "#eee", border: "none", borderRadius: 5,
        cursor: disabled ? "default" : "pointer", fontWeight: "bold",
      }}
    >
      {label}
    </button>
  );
}

export function SequenceControl({ state }: Props) {
  const seq     = state.sequenceState;
  const running = seq && !["ready", "startup", "awaiting_operator",
                            "hard_fault"].includes(seq);

  return (
    <div style={{ background: "#1c1c1c", borderRadius: 8, padding: 14 }}>
      <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#aaa",
                   textTransform: "uppercase", letterSpacing: 1 }}>
        Sequence
      </h3>

      {/* State display */}
      <div style={{
        padding: "10px 14px", borderRadius: 6,
        background: "#111",
        borderLeft: `4px solid ${STATE_COLOUR[seq ?? "startup"] ?? "#444"}`,
        marginBottom: 14,
      }}>
        <div style={{ fontSize: 15, fontWeight: "bold" }}>
          {seq ? STATE_LABELS[seq] : "Connecting to system..."}
        </div>
        {state.indicatorOn && (
          <div style={{ fontSize: 12, color: "#BA7517", marginTop: 4 }}>
            ● Awaiting input
          </div>
        )}
      </div>

      {/* Main controls */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {btn("▶ Start", () => sequenceApi.start(),
             "#2a7f4a", running || seq === "awaiting_operator")}
        {btn("■ Stop",  () => sequenceApi.stop(),
             "#7f2a2a", !running)}
      </div>

      {/* Operator prompt */}
      {state.awaitingOperator && (
        <div style={{ marginTop: 16, padding: 12, background: "#1a1200",
                      border: "1px solid #BA7517", borderRadius: 6 }}>
          <div style={{ fontWeight: "bold", color: "#e2b714", marginBottom: 8 }}>
            {state.operatorFault === "operator_stop"
              ? "Sequence stopped"
              : "Operator action required"}
          </div>
          <div style={{ fontSize: 13, color: "#ccc", marginBottom: 10 }}>
            {state.operatorFault === "operator_stop"
              ? "Machine halted. Reset to open gripper and home."
              : `Fault: ${state.operatorFault?.replace(/_/g, " ")}`}
          </div>

          {/* Evidence images - not shown for operator_stop */}
          {state.operatorFault !== "operator_stop" && state.operatorImage1 && (
            <div style={{ display: "flex", gap: 8, marginBottom: 12,
                          flexWrap: "wrap" }}>
              <img src={state.operatorImage1} alt="Evidence 1"
                   style={{ width: "calc(50% - 4px)", minWidth: 120,
                            borderRadius: 4, border: "1px solid #444" }} />
              {state.operatorImage2 && (
                <img src={state.operatorImage2} alt="Evidence 2"
                     style={{ width: "calc(50% - 4px)", minWidth: 120,
                              borderRadius: 4, border: "1px solid #444" }} />
              )}
            </div>
          )}

          <div style={{ display: "flex", gap: 8 }}>
            {state.operatorFault !== "operator_stop" && (
              btn("↺ Retry", () => sequenceApi.retry(), "#2a4a7f")
            )}
            {btn("⌂ Reset", () => sequenceApi.reset(), "#7f4a2a")}
          </div>
        </div>
      )}

      {/* Hard fault */}
      {state.hardFault && (
        <div style={{ marginTop: 16, padding: 12, background: "#1a0000",
                      border: "1px solid #7f2a2a", borderRadius: 6 }}>
          <div style={{ fontWeight: "bold", color: "#cf7f7f" }}>
            Hard fault — service will restart
          </div>
          {state.hardFaultDetail && (
            <div style={{ fontSize: 12, color: "#888", marginTop: 6,
                          fontFamily: "monospace" }}>
              {state.hardFaultDetail}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
