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
  const [progress,       setProgress]       = useState<CalibProgress | null>(null);
  const [isCalibrated,   setIsCalibrated]   = useState(false);
  const [offsetX,        setOffsetX]        = useState(0);
  const [offsetY,        setOffsetY]        = useState(0);
  const [testPx,         setTestPx]         = useState(640);
  const [testPy,         setTestPy]         = useState(480);
  const [testResult,     setTestResult]     = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load initial status
  useEffect(() => {
    fetchStatus();
  }, []);

  // Poll progress while running
  useEffect(() => {
    if (progress?.status === "running" || progress?.status === "homing" ||
        progress?.status === "starting") {
      pollingRef.current = setInterval(fetchStatus, 1000);
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [progress?.status]);

  async function fetchStatus() {
    const r    = await fetch("/api/calibration/status");
    const json = await r.json();
    setIsCalibrated(json.is_calibrated);
    setProgress(json.progress);
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
      setTestResult(`Error: ${json.error}`);
    }
  }

  async function testTransform() {
    const r    = await fetch("/api/calibration/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ px: testPx, py: testPy }),
    });
    const json = await r.json();
    if (json.ok) {
      setTestResult(
        `(${testPx}, ${testPy}) px → X:${json.machine_x.toFixed(2)} Y:${json.machine_y.toFixed(2)} mm`
      );
    } else {
      setTestResult(`${json.error}`);
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
            height: "100%", borderRadius: 4,
            width: `${pct}%`,
            background: progressColour(progress.status),
            transition: "width 0.5s",
          }} />
        </div>
        <div style={{ fontSize: 11, color: "#888", marginTop: 4 }}>
          {progress.point} / {progress.total} points
          {progress.failed.length > 0 &&
            ` (${progress.failed.length} failed)`}
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

      <div style={{ fontSize: 12, color: isCalibrated ? "#4caf50" : "#f44336",
                    marginBottom: 8 }}>
        {isCalibrated ? "✓ Calibrated" : "✗ Not calibrated"}
      </div>

      {/* Grabber offset */}
      {sec("GRABBER OFFSET (mm)")}
      <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
        <div>{lbl("X offset")}<input type="number" value={offsetX} step={0.1}
             onChange={e => setOffsetX(+e.target.value)} style={inp(72)} /></div>
        <div>{lbl("Y offset")}<input type="number" value={offsetY} step={0.1}
             onChange={e => setOffsetY(+e.target.value)} style={inp(72)} /></div>
      </div>

      {/* Run calibration */}
      {sec("CALIBRATION ROUTINE")}
      <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>
        Machine will home, lower bed, then step through a{" "}
        {/* Grid size from config - shown as static text */}
        6×6 grid capturing overhead frames.
        Ensure toolhead circle marker is fitted before starting.
      </div>
      <button style={btn("#7f2a2a", isRunning)} onClick={startCalibration}
              disabled={isRunning}>
        {isRunning ? "Running..." : "▶ Run Calibration"}
      </button>

      {/* Progress */}
      {progress && progress.status !== "idle" && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12,
                        color: progressColour(progress.status) }}>
            {progress.status.charAt(0).toUpperCase() + progress.status.slice(1)}
            {progress.error && `: ${progress.error}`}
          </div>
          {progressBar()}
        </div>
      )}

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
            <div style={{ fontSize: 12, fontFamily: "monospace",
                          color: testResult.includes("Error") ||
                                 testResult.includes("Outside")
                                 ? "#f44336" : "#7fc97f",
                          marginTop: 6 }}>
              {testResult}
            </div>
          )}
        </>
      )}
    </div>
  );
}
