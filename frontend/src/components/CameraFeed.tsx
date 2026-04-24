import { useState } from "react";
import { cameraApi, CameraId } from "../api/client";

interface Props {
  id:    CameraId;
  title: string;
}

export function CameraFeed({ id, title }: Props) {
  const [streaming, setStreaming] = useState(false);

  async function toggleStream() {
    if (streaming) {
      await cameraApi.streamStop(id);
      setStreaming(false);
    } else {
      await cameraApi.streamStart(id);
      setStreaming(true);
    }
  }

  return (
    <div style={{ background: "#1c1c1c", borderRadius: 8, padding: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between",
                    alignItems: "center", marginBottom: 10 }}>
        <h3 style={{ margin: 0, fontSize: 14, color: "#aaa",
                     textTransform: "uppercase", letterSpacing: 1 }}>
          {title}
        </h3>
        <button
          onClick={toggleStream}
          style={{
            padding: "4px 12px", fontSize: 12,
            background: streaming ? "#7f2a2a" : "#2a4a7f",
            color: "#eee", border: "none", borderRadius: 4,
            cursor: "pointer",
          }}
        >
          {streaming ? "■ Stop" : "▶ Stream"}
        </button>
      </div>

      <div style={{ background: "#000", borderRadius: 6, overflow: "hidden",
                    aspectRatio: "4/3" }}>
        {streaming ? (
          <img
            src={cameraApi.streamUrl(id)}
            alt={title}
            style={{ width: "100%", height: "100%", objectFit: "contain" }}
          />
        ) : (
          <div style={{ display: "flex", alignItems: "center",
                        justifyContent: "center", height: "100%",
                        color: "#444", fontSize: 13 }}>
            Stream stopped
          </div>
        )}
      </div>
    </div>
  );
}
