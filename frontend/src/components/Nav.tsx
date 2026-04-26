import { Link } from "react-router-dom";
import { SystemState } from "../hooks/useSystemState";

interface NavProps {
  state: SystemState;
}

export function Nav({ state }: NavProps) {
  const commsOk = state.machineComms === "ok";
  const dot = (ok: boolean | null) => (
    <span style={{
      display: "inline-block", width: 8, height: 8,
      borderRadius: "50%", marginLeft: 6,
      background: ok === null ? "#666" : ok ? "#4caf50" : "#f44336",
    }} />
  );

  return (
    <nav style={{
      background: "#1a1a2e", padding: "10px 16px",
      display: "flex", gap: "20px", alignItems: "center"
    }}>
      <span style={{ color: "#e2b714", fontSize: "18px", marginRight: "auto" }}>
        VisionGrabber
      </span>
      <span style={{ fontSize: "12px", color: "#888" }}>
        machine{dot(commsOk)}
        &nbsp;&nbsp;
        toolhead{dot(state.toolheadCameraState === "active")}
        &nbsp;&nbsp;
        overhead{dot(state.overheadCameraState === "active")}
      </span>
      <Link to="/"              style={{ color: "#7eb6ff", textDecoration: "none", fontWeight: "bold" }}>Overview</Link>
      <Link to="/tune/toolhead" style={{ color: "#7eb6ff", textDecoration: "none", fontWeight: "bold" }}>Tune Toolhead</Link>
      <Link to="/tune/overhead" style={{ color: "#7eb6ff", textDecoration: "none", fontWeight: "bold" }}>Tune Overhead</Link>
    </nav>
  );
}
