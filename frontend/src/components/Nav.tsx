import { NavLink } from "react-router-dom";
import { SystemState } from "../hooks/useSystemState";

interface Props {
  state: SystemState;
}

const linkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
  color:          isActive ? "#fff" : "#7eb6ff",
  textDecoration: "none",
  fontWeight:     "bold",
  padding:        "4px 8px",
  borderRadius:   4,
  background:     isActive ? "#2a4a7f" : "transparent",
});

export function Nav({ state }: Props) {
  const faultColour =
    state.hardFault        ? "#cf7f7f" :
    state.awaitingOperator ? "#e2b714" : "#2a7f4a";

  return (
    <nav style={{
      background:  "#1a1a2e",
      padding:     "10px 16px",
      display:     "flex",
      gap:         16,
      alignItems:  "center",
    }}>
      <span style={{ color: "#e2b714", fontWeight: "bold",
                     fontSize: 17, marginRight: "auto" }}>
        VisionGrabber
      </span>

      <NavLink to="/"               style={linkStyle}>Overview</NavLink>
      <NavLink to="/calibration"    style={linkStyle}>Calibration</NavLink>
      <NavLink to="/tune/toolhead"  style={linkStyle}>Tune Toolhead</NavLink>
      <NavLink to="/tune/overhead"  style={linkStyle}>Tune Overhead</NavLink>

      {/* Sequence state pill */}
      <div style={{
        fontSize:     12,
        padding:      "3px 10px",
        borderRadius: 20,
        background:   faultColour + "33",
        border:       `1px solid ${faultColour}`,
        color:        faultColour,
        fontWeight:   "bold",
        marginLeft:   8,
      }}>
        {state.sequenceState?.replace(/_/g, " ") ?? "connecting"}
      </div>

      {/* Virtual LED */}
      <div title={state.indicatorOn ? "Awaiting input" : "Idle"}
           style={{
             width:        14, height: 14,
             borderRadius: "50%",
             background:   state.indicatorOn ? "#e2b714" : "#333",
             border:       "2px solid #555",
             transition:   "background 0.3s",
           }} />
    </nav>
  );
}
