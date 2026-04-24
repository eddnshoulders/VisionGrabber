import { useState, useEffect, useCallback } from "react";
import { cameraApi, CameraId } from "../api/client";

interface Props {
  id: CameraId;
}

type Params = Record<string, unknown>;

const SLIDER_DEFS: Array<[string, number, number, number]> = [
  ["blur_kernel",        1,   15,  2],
  ["threshold_value",    0,  255,  1],
  ["adaptive_block_size",3,   99,  2],
  ["adaptive_c",       -20,   40,  1],
  ["min_area",           0, 50000, 100],
  ["max_area",           0,300000, 100],
  ["circularity_min",  0.1,  1.0, 0.01],
  ["min_radius",         0,  400,  1],
  ["max_radius",         0,  500,  1],
  ["roi_x_min",          0,  640,  1],
  ["roi_x_max",          0,  640,  1],
  ["roi_y_min",          0,  480,  1],
  ["roi_y_max",          0,  480,  1],
  ["jpeg_quality",      30,   90,  1],
  ["stream_fps",         1,   20,  1],
];

const VIEW_OPTIONS = ["raw","gray","mask","contours","annotated","tiled"];
const THRESHOLD_MODES = ["binary","inverse","hsv","adaptive"];

export function ParamTuner({ id }: Props) {
  const [params, setParams]     = useState<Params | null>(null);
  const [saveMsg, setSaveMsg]   = useState<string | null>(null);
  const [presets, setPresets]   = useState<string[]>([]);
  const [presetName, setPresetName] = useState("");

  useEffect(() => {
    cameraApi.getParams(id).then(setParams);
    cameraApi.getPresets(id).then((r) => setPresets(r.presets ?? []));
  }, [id]);

  const update = useCallback(async (key: string, value: unknown) => {
    setParams((p) => p ? { ...p, [key]: value } : p);
    await cameraApi.patchParams(id, { [key]: value });
  }, [id]);

  async function save() {
    const r = await cameraApi.saveParams(id, presetName || undefined);
    setSaveMsg(r.saved_to ?? "saved");
    cameraApi.getPresets(id).then((r) => setPresets(r.presets ?? []));
    setTimeout(() => setSaveMsg(null), 3000);
  }

  async function loadPreset(name: string) {
    const r = await cameraApi.loadPreset(id, name);
    if (r.params) setParams(r.params);
  }

  if (!params) return (
    <div style={{ color: "#888", padding: 14 }}>Loading params...</div>
  );

  const label = (text: string) => (
    <label style={{ display: "block", fontSize: 12, color: "#888",
                    marginTop: 10 }}>
      {text}
    </label>
  );

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "4px 6px",
    background: "#2a2a2a", color: "#eee",
    border: "1px solid #444", borderRadius: 4,
  };

  return (
    <div style={{ background: "#1c1c1c", borderRadius: 8, padding: 14,
                  overflowY: "auto", maxHeight: "88vh" }}>
      <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#aaa",
                   textTransform: "uppercase", letterSpacing: 1 }}>
        Parameters
      </h3>

      {/* Debug view */}
      {label("Debug view")}
      <select value={String(params.debug_view)} style={inputStyle}
              onChange={(e) => update("debug_view", e.target.value)}>
        {VIEW_OPTIONS.map((v) => <option key={v} value={v}>{v}</option>)}
      </select>

      {/* Threshold mode */}
      {label("Threshold mode")}
      <select value={String(params.threshold_mode)} style={inputStyle}
              onChange={(e) => update("threshold_mode", e.target.value)}>
        {THRESHOLD_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
      </select>

      {/* Checkboxes */}
      {["show_all_contours", "show_accepted_contours"].map((key) => (
        <label key={key} style={{ display: "flex", alignItems: "center",
                                  gap: 6, marginTop: 8, fontSize: 13,
                                  color: "#ccc", cursor: "pointer" }}>
          <input type="checkbox" checked={!!params[key]}
                 onChange={(e) => update(key, e.target.checked)} />
          {key.replace(/_/g, " ")}
        </label>
      ))}

      {/* Sliders */}
      {SLIDER_DEFS.map(([name, min, max, step]) => {
        const val = Number(params[name] ?? 0);
        return (
          <div key={name}>
            {label(name.replace(/_/g, " "))}
            <div style={{ display: "grid",
                          gridTemplateColumns: "1fr 70px", gap: 6 }}>
              <input type="range" min={min} max={max} step={step}
                     value={val}
                     onChange={(e) => update(name, +e.target.value)}
                     style={{ width: "100%" }} />
              <input type="number" min={min} max={max} step={step}
                     value={val}
                     onChange={(e) => update(name, +e.target.value)}
                     style={inputStyle} />
            </div>
          </div>
        );
      })}

      {/* Save */}
      <div style={{ marginTop: 16 }}>
        <label style={{ fontSize: 12, color: "#888" }}>
          Save as preset (blank = default)
        </label>
        <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
          <input type="text" value={presetName} placeholder="preset name"
                 onChange={(e) => setPresetName(e.target.value)}
                 style={{ ...inputStyle, flex: 1 }} />
          <button onClick={save}
                  style={{ padding: "4px 12px", background: "#2a4a7f",
                           color: "#eee", border: "none", borderRadius: 4,
                           cursor: "pointer" }}>
            Save
          </button>
        </div>
        {saveMsg && (
          <div style={{ fontSize: 11, color: "#7fc97f", marginTop: 4 }}>
            {saveMsg}
          </div>
        )}
      </div>

      {/* Load preset */}
      {presets.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <label style={{ fontSize: 12, color: "#888" }}>Load preset</label>
          <select style={{ ...inputStyle, marginTop: 4 }}
                  onChange={(e) => { if (e.target.value) loadPreset(e.target.value); }}
                  defaultValue="">
            <option value="" disabled>Select preset...</option>
            {presets.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
      )}
    </div>
  );
}
