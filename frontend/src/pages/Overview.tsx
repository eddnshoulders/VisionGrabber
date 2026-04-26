import { CameraFeed }       from "../components/CameraFeed";
import { SequenceControl }  from "../components/SequenceControl";
import { MachineControl }   from "../components/MachineControl";
import { HealthPanel }      from "../components/HealthPanel";
import { CalibrationPanel } from "../components/CalibrationPanel";
import { SystemState }      from "../hooks/useSystemState";

interface Props {
  state: SystemState;
}

export function Overview({ state }: Props) {
  return (
    <div style={{ padding: 16 }}>

      {/* Camera feeds */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr",
                    gap: 16, marginBottom: 16 }}>
        <CameraFeed id="toolhead" title="Toolhead Camera" />
        <CameraFeed id="overhead" title="Overhead Camera" />
      </div>

      {/* Controls row 1 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr",
                    gap: 16, marginBottom: 16 }}>
        <SequenceControl state={state} />
        <MachineControl />
        <HealthPanel state={state} />
      </div>

      {/* Controls row 2 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr",
                    gap: 16 }}>
        <CalibrationPanel />
        <div /> {/* placeholder for future panels */}
      </div>

    </div>
  );
}
