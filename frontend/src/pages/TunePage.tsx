import { CameraFeed } from "../components/CameraFeed";
import { ParamTuner } from "../components/ParamTuner";
import { CameraId }   from "../api/client";

interface Props {
  id:    CameraId;
  title: string;
}

export function TunePage({ id, title }: Props) {
  return (
    <div style={{ padding: 16,
                  display: "grid",
                  gridTemplateColumns: "2fr 1fr",
                  gap: 16,
                  height: "calc(100vh - 50px)" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <h2 style={{ margin: 0, color: "#aaa", fontSize: 15,
                     textTransform: "uppercase", letterSpacing: 1 }}>
          {title}
        </h2>
        <CameraFeed id={id} title={title} />
      </div>
      <ParamTuner id={id} />
    </div>
  );
}
