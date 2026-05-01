import { useState, useEffect, useRef } from "react";

interface CalibProgress {
  status: string;
  point:  number;
  total:  number;
  failed: number[];
  error?: string;
  points_collected?: number;
}

export function CalibrationPanel() {
  const [progress,     setProgress]     = useState<CalibProgress | null>(null);
  const [isCalibrated, setIsCalibrated] = useState(false);
  const [offsetX,      setOffsetX]      = useState(0);
  const [offsetY,      setOffsetY]      = useState(0);
  const [trimX,        setTrimX]        = useState(0);
  const [trimY,        setTrimY]        = useState(0);
  const [trimDirty,    setTrimDirty]    = useState(false);
  const [trimSaved,    setTrimSaved]    = useState(false);
  const [testPx,       setTestPx]       = useState(640);
  const [testPy,       setTestPy]       = useState(480);
  const [testResult,   setTestResult]   = useState<{
    mx: number; my: number; trimX: number; trimY: number;
  } | null>(null);
  const [testError,    setTestError]    = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchStatus();
    fetchOffset();
  }, []);

  useEffect(() => {
    if (progress?.status === "running"  ||
        progress?.status === "homing"   ||
        progress?.status === "starting") {
      pollingRef.current = setInterval(fetchStatus, 1000);
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [progress?.status]);

  async function fetchStatus() {
    const r    = await fetch("/api/calibration/status");
    const json = await r.json();
    setIsCalibrated(json.is_calibrated);
    setProgress(json.progress);
  }

  async function fetchOffset() {
    const r    = await fetch("/api/calibration/offset");
    const json = await r.json();
    if (json.ok) {
      setTrimX(json.offset_x);
      setTrimY(json.offset_y);
      setTrimDirty(false);
    }
  }

  async function saveOffset() {
    const r = await fetch("/api/calibration/offset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offset_x: trimX, offset_y: trimY }),
    });
    const json = await r.json();
    if (json.ok) {
      setTrimDirty(false);
      setTrimSaved(true);
      setTimeout(() => setTrimSaved(false), 2000);
    }
  }

  async function startCalibration() {
    const r = await fetch("/api/calibration/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        grabber_offset_x: offsetX,
        grabber_offset_y: offsetY,
      }),
    });
    const json = await r.json();
    if (json.ok) {
      setProgress({ status: "starting", point: 0, total: 0, failed: [] });
    } else {
      setTestError(`Error: ${json.error}`);
    }
  }

  async function testTransform() {
    setTestResult(null);
    setTestError(null);
    const r    = await fetch("/api/calibration/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ px: testPx, py: testPy }),
    });
    const json = await r.json();
    if (json.ok) {
      setTestResult({
        mx: json.machine_x, my: json.machine_y,
        trimX, trimY,
      });
    } else {
      setTestError(json.error ?? "Transform failed");
    }
  }

  const isRunning = progress?.status === "running"  ||
                    progress?.status === "homing"    ||
                    progress?.status === "starting";

  const inp = (w: number): React.CSSProperties => ({
    padding: "4px 6px", background: "#2a2a2a", color: "#eee",
    border: "1px solid #444", borderRadius: 4, width: w,
    textAlign: "center" as const,
  });

  const btn = (bg = "#2a4a7f", disabled = false): React.CSSProperties => ({
    padding: "7px 12px", background: disabled ? "#333" : bg,
    color: disabled ? "#666" : "#eee",
    border: "none", borderRadius: 4,
    cursor: disabled ? "not-allowed" : "pointer",
  });

  const sec = (text: string) => (
    <div style={{ fontSize: 11, color: "#555", letterSpacing: 1,
                  marginBottom: 6, marginTop: 14 }}>{text}</div>
  );

  const lbl = (text: string) => (
    <div style={{ fontSize: 11, color: "#888", marginBottom: 3 }}>{text}</div>
  );

  function progressColour(status: string) {
    if (status === "complete") return "#4caf50";
    if (status === "failed")   return "#f44336";
    if (isRunning)             return "#7eb6ff";
    return "#888";
  }

  function progressBar() {
    if (!progress || progress.total === 0) return null;
    const pct = Math.round((progress.point / progress.total) * 100);
    return (
      <div style={{ marginTop: 8 }}>
        <div style={{ background: "#2a2a2a", borderRadius: 4,
                      height: 8, overflow: "hidden" }}>
          <div style={{
            height: "100%", borderRadius: 4, width: `${pct}%`,
            background: progressColour(progress.status),
            transition: "width 0.5s",
          }} />
        </div>
        <div style={{ fontSize: 11, color: "#888", marginTop: 4 }}>
          {progress.point} / {progress.total} points
          {progress.failed.length > 0 && ` (${progress.failed.length} failed)`}
          {progress.points_collected !== undefined &&
            ` — ${progress.points_collected} collected`}
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: "#1c1c1c", borderRadius: 8, padding: 14 }}>
      <h3 style={{ margin: "0 0 4px", fontSize: 14, color: "#aaa",
                   textTransform: "uppercase", letterSpacing: 1 }}>
        Camera Calibration
      </h3>

      <div style={{ fontSize: 12,
                    color: isCalibrated ? "#4caf50" : "#f44336",
                    marginBottom: 8 }}>
        {isCalibrated ? "✓ Calibrated" : "✗ Not calibrated"}
      </div>

      {/* Grabber offset (used during calibration grid) */}
      {sec("GRABBER OFFSET (mm)  —  used during calibration")}
      <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
        <div>{lbl("X")}<input type="number" value={offsetX} step={0.1}
             onChange={e => setOffsetX(+e.target.value)} style={inp(72)} /></div>
        <div>{lbl("Y")}<input type="number" value={offsetY} step={0.1}
             onChange={e => setOffsetY(+e.target.value)} style={inp(72)} /></div>
      </div>

      {/* Run calibration */}
      {sec("CALIBRATION ROUTINE")}
      <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>
        Machine will home, lower bed, then step through a 6×6 grid.
        Fit toolhead circle marker before starting.
      </div>
      <button style={btn("#7f2a2a", isRunning)}
              onClick={startCalibration} disabled={isRunning}>
        {isRunning ? "Running..." : "▶ Run Calibration"}
      </button>

      {progress && progress.status !== "idle" && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: progressColour(progress.status) }}>
            {progress.status.charAt(0).toUpperCase() + progress.status.slice(1)}
            {progress.error && `: ${progress.error}`}
          </div>
          {progressBar()}
        </div>
      )}

      {/* Runtime position trim */}
      {sec("POSITION TRIM (mm)  —  applied to every pickup")}
      <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>
        Dial out residual coarse position error without recalibrating.
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-end",
                    flexWrap: "wrap" }}>
        <div>
          {lbl("X trim")}
          <input type="number" value={trimX} step={0.1}
                 onChange={e => { setTrimX(+e.target.value); setTrimDirty(true); }}
                 style={{
                   ...inp(72),
                   borderColor: trimDirty ? "#e2b714" : "#444",
                 }} />
        </div>
        <div>
          {lbl("Y trim")}
          <input type="number" value={trimY} step={0.1}
                 onChange={e => { setTrimY(+e.target.value); setTrimDirty(true); }}
                 style={{
                   ...inp(72),
                   borderColor: trimDirty ? "#e2b714" : "#444",
                 }} />
        </div>
        <button
          style={btn(trimSaved ? "#2a7f4a" : trimDirty ? "#7f6a00" : "#2a4a7f")}
          onClick={saveOffset}>
          {trimSaved ? "✓ Saved" : trimDirty ? "● Save" : "Save"}
        </button>
      </div>

      {/* Test transform */}
      {isCalibrated && (
        <>
          {sec("TEST TRANSFORM")}
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end",
                        flexWrap: "wrap" }}>
            <div>{lbl("Pixel X")}<input type="number" value={testPx}
                 onChange={e => setTestPx(+e.target.value)} style={inp(72)} /></div>
            <div>{lbl("Pixel Y")}<input type="number" value={testPy}
                 onChange={e => setTestPy(+e.target.value)} style={inp(72)} /></div>
            <button style={btn()} onClick={testTransform}>Test</button>
          </div>

          {testResult && (
            <div style={{ marginTop: 8, background: "#2a2a2a", borderRadius: 4,
                          padding: "8px 10px", fontFamily: "monospace",
                          fontSize: 12 }}>
              <div style={{ color: "#7fc97f" }}>
                Machine: X={testResult.mx.toFixed(3)}  Y={testResult.my.toFixed(3)} mm
              </div>
              <div style={{ color: "#888", marginTop: 4 }}>
                Includes trim: X={testResult.trimX >= 0 ? "+" : ""}
                {testResult.trimX.toFixed(3)}  
                Y={testResult.trimY >= 0 ? "+" : ""}
                {testResult.trimY.toFixed(3)} mm
              </div>
            </div>
          )}

          {testError && (
            <div style={{ marginTop: 6, fontSize: 12, color: "#f44336",
                          fontFamily: "monospace" }}>
              {testError}
            </div>
          )}
        </>
      )}
    </div>
  );
}
