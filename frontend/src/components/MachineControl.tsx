import { useState } from "react";
import { machineApi } from "../api/client";

export function MachineControl() {
  const [gripperOpen,  setGripperOpen]  = useState(23);
  const [gripperClose, setGripperClose] = useState(128);
  const [posX,         setPosX]         = useState(0);
  const [posY,         setPosY]         = useState(0);
  const [rawCmd,       setRawCmd]       = useState("");
  const [lastResp,     setLastResp]     = useState<string | null>(null);

  async function send(cmd: string) {
    const r = await machineApi.sendCommand(cmd);
    setLastResp(r.queued ?? cmd);
  }

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "4px 6px",
    background: "#2a2a2a", color: "#eee",
    border: "1px solid #444", borderRadius: 4,
  };

  const btnStyle = (colour = "#2a4a7f"): React.CSSProperties => ({
    padding: "6px 12px", background: colour, color: "#eee",
    border: "none", borderRadius: 4, cursor: "pointer",
  });

  return (
    <div style={{ background: "#1c1c1c", borderRadius: 8, padding: 14 }}>
      <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#aaa",
                   textTransform: "uppercase", letterSpacing: 1 }}>
        Machine Control
      </h3>

      {/* Gripper */}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: "#888" }}>Gripper open value</label>
        <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
          <input type="number" value={gripperOpen}
                 onChange={(e) => setGripperOpen(+e.target.value)}
                 style={{ ...inputStyle, width: 70 }} />
          <button style={btnStyle("#2a7f4a")}
                  onClick={() => send(`GRIPPER OPEN ${gripperOpen}`)}>
            Open
          </button>
        </div>

        <label style={{ fontSize: 12, color: "#888", display: "block",
                        marginTop: 8 }}>
          Gripper close value
        </label>
        <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
          <input type="number" value={gripperClose}
                 onChange={(e) => setGripperClose(+e.target.value)}
                 style={{ ...inputStyle, width: 70 }} />
          <button style={btnStyle("#7f4a2a")}
                  onClick={() => send(`GRIPPER CLOSE ${gripperClose}`)}>
            Close
          </button>
        </div>
      </div>

      {/* Position */}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: "#888" }}>Move to position</label>
        <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
          <input type="number" value={posX} placeholder="X"
                 onChange={(e) => setPosX(+e.target.value)}
                 style={{ ...inputStyle, width: 60 }} />
          <input type="number" value={posY} placeholder="Y"
                 onChange={(e) => setPosY(+e.target.value)}
                 style={{ ...inputStyle, width: 60 }} />
          <button style={btnStyle()}
                  onClick={() => send(`MOVE ${posX} ${posY}`)}>
            Go
          </button>
        </div>
      </div>

      {/* Raw command */}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: "#888" }}>Raw command</label>
        <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
          <input type="text" value={rawCmd} placeholder="e.g. G28"
                 onChange={(e) => setRawCmd(e.target.value)}
                 onKeyDown={(e) => { if (e.key === "Enter") send(rawCmd); }}
                 style={{ ...inputStyle, flex: 1 }} />
          <button style={btnStyle()} onClick={() => send(rawCmd)}>Send</button>
        </div>
      </div>

      {/* Last response */}
      {lastResp && (
        <div style={{ fontSize: 12, color: "#7fc97f", fontFamily: "monospace",
                      marginTop: 6, wordBreak: "break-all" }}>
          ↳ {lastResp}
        </div>
      )}
    </div>
  );
}
