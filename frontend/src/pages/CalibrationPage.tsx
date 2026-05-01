import { CameraFeed }       from "../components/CameraFeed";
import { CalibrationPanel } from "../components/CalibrationPanel";
import { MachineControl }   from "../components/MachineControl";
import { HealthPanel }      from "../components/HealthPanel";
import { SystemState }      from "../hooks/useSystemState";

interface Props {
  state: SystemState;
}

export function CalibrationPage({ state }: Props) {
  return (
    <div style={{ padding: 16 }}>

      {/* Camera feeds */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr",
                    gap: 16, marginBottom: 16 }}>
        <CameraFeed id="toolhead" title="Toolhead Camera" />
        <CameraFeed id="overhead" title="Overhead Camera" />
      </div>

      {/* Controls */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr",
                    gap: 16 }}>
        <CalibrationPanel />
        <MachineControl />
        <HealthPanel state={state} />
      </div>

    </div>
  );
}
