import { useState } from "react";
import { machineApi } from "../api/client";

export function MachineControl() {
  const [gripperOpen,  setGripperOpen]  = useState(23);
  const [gripperClose, setGripperClose] = useState(128);
  const [posX,         setPosX]         = useState(0);
  const [posY,         setPosY]         = useState(0);
  const [posZ,         setPosZ]         = useState(0);
  const [xyStep,       setXyStep]       = useState(10);
  const [zStep,        setZStep]        = useState(1);
  const [xyFeed,       setXyFeed]       = useState(3000);
  const [zFeed,        setZFeed]        = useState(1000);
  const [rawCmd,       setRawCmd]       = useState("");
  const [lastResp,     setLastResp]     = useState<string | null>(null);
  const [nudging,      setNudging]      = useState(false);

  async function send(cmd: string): Promise<string> {
    const r = await machineApi.sendCommand(cmd);
    const resp = r.queued ?? cmd;
    setLastResp(resp);
    return resp;
  }

  async function getCurrentPosition() {
    const r    = await fetch("/api/machine/position");
    const json = await r.json();
    if (!json.ok) return null;
    return { x: json.x, y: json.y, z: json.z };
  }

  async function nudgeXY(axis: "x" | "y", dir: 1 | -1) {
    if (nudging) return;
    setNudging(true);
    try {
      const cur = await getCurrentPosition();
      if (!cur) { setLastResp("Could not read position"); return; }
      const next = { ...cur, [axis]: +(cur[axis] + xyStep * dir).toFixed(2) };
      setPosX(next.x); setPosY(next.y); setPosZ(next.z);
      await send(`G0 X${next.x} Y${next.y} F${xyFeed}`);
    } finally {
      setNudging(false);
    }
  }

  async function nudgeZ(dir: 1 | -1) {
    if (nudging) return;
    setNudging(true);
    try {
      const cur = await getCurrentPosition();
      if (!cur) { setLastResp("Could not read position"); return; }
      const next = { ...cur, z: +(cur.z + zStep * dir).toFixed(2) };
      setPosX(next.x); setPosY(next.y); setPosZ(next.z);
      await send(`G0 Z${next.z} F${zFeed}`);
    } finally {
      setNudging(false);
    }
  }

  async function refreshPosition() {
    const cur = await getCurrentPosition();
    if (cur) { setPosX(cur.x); setPosY(cur.y); setPosZ(cur.z); }
  }

  // ── Styles ────────────────────────────────────────────────────────
  const inp = (width: number): React.CSSProperties => ({
    padding: "4px 6px", background: "#2a2a2a", color: "#eee",
    border: "1px solid #444", borderRadius: 4, width,
    textAlign: "center" as const,
  });

  const btn = (bg = "#2a4a7f"): React.CSSProperties => ({
    padding: "6px 10px", background: bg, color: "#eee",
    border: "none", borderRadius: 4, cursor: "pointer",
  });

  const arrowBtn = (bg = "#333"): React.CSSProperties => ({
    width: 36, height: 36, background: bg, color: "#eee",
    border: "none", borderRadius: 4, cursor: nudging ? "wait" : "pointer",
    fontSize: 16, display: "flex", alignItems: "center",
    justifyContent: "center", opacity: nudging ? 0.5 : 1,
  });

  const sec = (text: string) => (
    <div style={{ fontSize: 11, color: "#555", letterSpacing: 1,
                  marginBottom: 6, marginTop: 14 }}>{text}</div>
  );

  const lbl = (text: string) => (
    <div style={{ fontSize: 11, color: "#888", marginBottom: 3 }}>{text}</div>
  );

  return (
    <div style={{ background: "#1c1c1c", borderRadius: 8, padding: 14 }}>
      <h3 style={{ margin: "0 0 4px", fontSize: 14, color: "#aaa",
                   textTransform: "uppercase", letterSpacing: 1 }}>
        Machine Control
      </h3>

      {/* ── Gripper ────────────────────────────────────────────────── */}
      {sec("GRIPPER")}
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end",
                    flexWrap: "wrap" }}>
        <div>
          {lbl("Open value")}
          <input type="number" value={gripperOpen}
                 onChange={e => setGripperOpen(+e.target.value)}
                 style={inp(64)} />
        </div>
        <button style={btn("#2a7f4a")}
                onClick={() => send(`GRIPPER OPEN ${gripperOpen}`)}>
          Open
        </button>
        <div style={{ marginLeft: 8 }}>
          {lbl("Close value")}
          <input type="number" value={gripperClose}
                 onChange={e => setGripperClose(+e.target.value)}
                 style={inp(64)} />
        </div>
        <button style={btn("#7f4a2a")}
                onClick={() => send(`GRIPPER CLOSE ${gripperClose}`)}>
          Close
        </button>
      </div>

      {/* ── Go to position ─────────────────────────────────────────── */}
      {sec("GO TO POSITION")}
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end",
                    flexWrap: "wrap" }}>
        <div>{lbl("X")}<input type="number" value={posX}
             onChange={e => setPosX(+e.target.value)} style={inp(64)} /></div>
        <div>{lbl("Y")}<input type="number" value={posY}
             onChange={e => setPosY(+e.target.value)} style={inp(64)} /></div>
        <div>{lbl("Z")}<input type="number" value={posZ}
             onChange={e => setPosZ(+e.target.value)} style={inp(64)} /></div>
        <button style={btn()} onClick={() =>
          send(`G0 X${posX} Y${posY} Z${posZ} F${xyFeed}`)}>
          Go
        </button>
        <button style={btn("#444")} onClick={refreshPosition}
                title="Read current position from machine">
          ⟳ Get pos
        </button>
      </div>

      {/* ── Nudge ──────────────────────────────────────────────────── */}
      {sec("NUDGE")}
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start",
                    flexWrap: "wrap" }}>

        {/* XY cross */}
        <div>
          {lbl("X / Y")}
          <div style={{ display: "grid",
                        gridTemplateColumns: "36px 36px 36px",
                        gridTemplateRows:    "36px 36px 36px",
                        gap: 4 }}>
            {/* row 1: empty, Y+, empty */}
            <span />
            <button style={arrowBtn()} onClick={() => nudgeXY("y",  1)}>▲</button>
            <span />
            {/* row 2: X-, empty, X+ */}
            <button style={arrowBtn()} onClick={() => nudgeXY("x", -1)}>◀</button>
            <button style={{ ...arrowBtn("#1a3a1a"), fontSize: 9, flexDirection: "column" as const }}
                    onClick={() => send("G28 X Y")}
                    title="Home XY">
              <span>⌂</span><span style={{ fontSize: 7 }}>XY</span>
            </button>
            <button style={arrowBtn()} onClick={() => nudgeXY("x",  1)}>▶</button>
            {/* row 3: empty, Y-, empty */}
            <span />
            <button style={arrowBtn()} onClick={() => nudgeXY("y", -1)}>▼</button>
            <span />
          </div>
          <div style={{ marginTop: 8 }}>
            {lbl("Step (mm)")}
            <input type="number" value={xyStep} min={0.1} step={0.1}
                   onChange={e => setXyStep(+e.target.value)} style={inp(72)} />
          </div>
          <div style={{ marginTop: 6 }}>
            {lbl("Feedrate")}
            <input type="number" value={xyFeed} min={1} step={100}
                   onChange={e => setXyFeed(+e.target.value)} style={inp(72)} />
          </div>
        </div>

        {/* Z column */}
        <div>
          {lbl("Z")}
          <div style={{ display: "flex", flexDirection: "column",
                        gap: 4, alignItems: "center" }}>
            <button style={arrowBtn()} onClick={() => nudgeZ( 1)}>▲</button>
            <button style={{ ...arrowBtn("#1a3a1a"), fontSize: 9, flexDirection: "column" as const }}
                    onClick={() => send("G28 Z")}
                    title="Home Z">
              <span>⌂</span><span style={{ fontSize: 7 }}>Z</span>
            </button>
            <button style={arrowBtn()} onClick={() => nudgeZ(-1)}>▼</button>
          </div>
          <div style={{ marginTop: 8 }}>
            {lbl("Step (mm)")}
            <input type="number" value={zStep} min={0.1} step={0.1}
                   onChange={e => setZStep(+e.target.value)} style={inp(72)} />
          </div>
          <div style={{ marginTop: 6 }}>
            {lbl("Feedrate")}
            <input type="number" value={zFeed} min={1} step={100}
                   onChange={e => setZFeed(+e.target.value)} style={inp(72)} />
          </div>
        </div>

        {/* Current position readout + Home All */}
        <div>
          {lbl("Current position")}
          <div style={{ fontFamily: "monospace", fontSize: 13,
                        background: "#2a2a2a", borderRadius: 4,
                        padding: "6px 10px", color: "#7fc97f",
                        lineHeight: 1.8 }}>
            <div>X: {posX.toFixed(2)}</div>
            <div>Y: {posY.toFixed(2)}</div>
            <div>Z: {posZ.toFixed(2)}</div>
          </div>
          <button style={{ ...btn("#1a3a1a"), marginTop: 8, width: "100%" }}
                  onClick={() => send("G28")}>
            ⌂ Home All
          </button>
        </div>
      </div>

      {/* ── Raw command ────────────────────────────────────────────── */}
      {sec("RAW COMMAND")}
      <div style={{ display: "flex", gap: 6 }}>
        <input type="text" value={rawCmd} placeholder="e.g. G28"
               onChange={e => setRawCmd(e.target.value)}
               onKeyDown={e => { if (e.key === "Enter") send(rawCmd); }}
               style={{ ...inp(200), flex: 1, textAlign: "left" }} />
        <button style={btn()} onClick={() => send(rawCmd)}>Send</button>
      </div>

      {/* ── Last response ──────────────────────────────────────────── */}
      {lastResp && (
        <div style={{ fontSize: 12, color: "#7fc97f", fontFamily: "monospace",
                      marginTop: 8, wordBreak: "break-all" }}>
          ↳ {lastResp}
        </div>
      )}
    </div>
  );
}
