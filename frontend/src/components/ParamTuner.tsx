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
  ["roi_x_min",          0, 1280,  1],
  ["roi_x_max",          0, 1280,  1],
  ["roi_y_min",          0,  960,  1],
  ["roi_y_max",          0,  960,  1],
  ["jpeg_quality",      30,   90,  1],
  ["stream_fps",         1,   20,  1],
];

const VIEW_OPTIONS = ["raw","gray","mask","contours","annotated","tiled"];
const THRESHOLD_MODES = ["binary","inverse","hsv","adaptive"];

export function ParamTuner({ id }: Props) {
  const [params, setParams]       = useState<Params | null>(null);
  const [saveMsg, setSaveMsg]     = useState<string | null>(null);
  const [presets, setPresets]     = useState<string[]>([]);
  const [activePreset, setActive] = useState<string | null>(null);
  const [presetName, setPresetName] = useState("");

  useEffect(() => {
    cameraApi.getParams(id).then(setParams);
    refreshPresets();
  }, [id]);

  async function refreshPresets() {
    const r = await cameraApi.getPresets(id);
    setPresets(r.presets ?? []);
    setActive(r.active ?? null);
  }

  const update = useCallback(async (key: string, value: unknown) => {
    setParams((p) => p ? { ...p, [key]: value } : p);
    await cameraApi.patchParams(id, { [key]: value });
  }, [id]);

  async function save() {
    const name = presetName.trim();
    const r    = await cameraApi.saveParams(id, name || undefined);
    setSaveMsg(r.saved_to ?? "saved");
    await refreshPresets();
    setTimeout(() => setSaveMsg(null), 3000);
  }

  async function load() {
    const name = presetName.trim();
    const r    = await cameraApi.loadPreset(id, name || undefined);
    if (r.params) setParams(r.params);
  }

  async function setDefault() {
    const name = presetName.trim();
    if (!name) return;
    const r = await cameraApi.setDefaultPreset(id, name);
    if (r.ok) {
      setActive(name);
      await refreshPresets();
    }
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

  const btnStyle = (bg: string): React.CSSProperties => ({
    padding: "5px 10px", background: bg, color: "#eee",
    border: "none", borderRadius: 4, cursor: "pointer",
    fontSize: 12, whiteSpace: "nowrap" as const,
  });

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

      {/* Presets */}
      <div style={{ marginTop: 16, borderTop: "1px solid #333",
                    paddingTop: 14 }}>
        <div style={{ fontSize: 12, color: "#666", letterSpacing: 1,
                      marginBottom: 8 }}>PRESETS</div>

        {/* Dropdown populates name field */}
        {presets.length > 0 && (
          <>
            {label("Select preset")}
            <select
              value={presetName}
              style={{ ...inputStyle, marginBottom: 6 }}
              onChange={(e) => setPresetName(e.target.value)}>
              <option value="">— select —</option>
              {presets.map((p) => (
                <option key={p} value={p}>
                  {p === activePreset ? `★ ${p}` : p}
                </option>
              ))}
            </select>
          </>
        )}

        {/* Editable name field */}
        {label("Preset name (blank = default)")}
        <input
          type="text"
          value={presetName}
          placeholder="type new name or select above"
          onChange={(e) => setPresetName(e.target.value)}
          style={{ ...inputStyle, marginBottom: 8 }}
        />

        {/* Action buttons */}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button style={btnStyle("#2a7f4a")} onClick={save}>
            Save
          </button>
          <button style={btnStyle("#2a4a7f")} onClick={load}>
            Load
          </button>
          {presetName.trim() && presetName.trim() !== activePreset && (
            <button style={btnStyle("#7f6a00")} onClick={setDefault}
                    title="Set as default on startup">
              ★ Set default
            </button>
          )}
        </div>

        {/* Active preset indicator */}
        {activePreset && (
          <div style={{ fontSize: 11, color: "#888", marginTop: 6 }}>
            Default on startup: <span style={{ color: "#e2b714" }}>
              ★ {activePreset}
            </span>
          </div>
        )}

        {saveMsg && (
          <div style={{ fontSize: 11, color: "#7fc97f", marginTop: 6 }}>
            ✓ {saveMsg}
          </div>
        )}
      </div>
    </div>
  );
}
