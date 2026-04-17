from flask import Flask, Response, request, render_template_string, jsonify
import cv2
import numpy as np
import threading
import time
import json
from picamera2 import Picamera2

app = Flask(__name__)

state_lock = threading.Lock()
latest_bgr = None
latest_timestamp = 0.0
fps_estimate = 0.0
latest_detection = None   # dict with px, py, radius, area, circularity -- or None

params = {
    "debug_view": "annotated",   # raw, gray, mask, contours, annotated, tiled
    "blur_kernel": 5,
    "threshold_mode": "adaptive",    # binary, inverse, hsv, adaptive
    "threshold_value": 110,
    "adaptive_block_size": 40,       # must be odd, size of local neighbourhood
    "adaptive_c": -5,                # constant subtracted from local mean
    # HSV red mask params
    "hsv_h1_lo": 0,
    "hsv_h1_hi": 10,
    "hsv_h2_lo": 160,
    "hsv_h2_hi": 180,
    "hsv_s_lo": 100,
    "hsv_s_hi": 255,
    "hsv_v_lo": 50,
    "hsv_v_hi": 255,
    "min_area": 7500,
    "max_area": 60000,
    "circularity_min": 0.80,
    "min_radius": 45,
    "max_radius": 135,
    "show_all_contours": True,
    "show_accepted_contours": True,
    # Region of interest -- detections outside this pixel region are ignored
    "roi_x_min": 183,
    "roi_x_max": 457,
    "roi_y_min": 100,
    "roi_y_max": 323,
    "frame_width": 640,
    "frame_height": 480,
    "jpeg_quality": 65,
    "stream_fps": 10,
}

processed_cache = {
    "raw": None,
    "gray": None,
    "mask": None,
    "contours": None,
    "annotated": None,
    "tiled": None,
}


def odd(n: int) -> int:
    n = max(1, int(n))
    return n if n % 2 == 1 else n + 1


class CameraThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.picam = None

    def run(self):
        global latest_bgr, latest_timestamp, fps_estimate

        self.picam = Picamera2()
        config = self.picam.create_preview_configuration(
            main={"size": (int(params["frame_width"]), int(params["frame_height"])),
                  "format": "BGR888"}
        )
        self.picam.configure(config)
        self.picam.start()
        time.sleep(2)  # let auto-exposure settle

        last_time = time.time()

        while self.running:
            frame = self.picam.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            now = time.time()
            dt = max(now - last_time, 1e-6)
            last_time = now
            inst_fps = 1.0 / dt
            fps_estimate = 0.85 * fps_estimate + 0.15 * inst_fps if fps_estimate else inst_fps

            with state_lock:
                latest_bgr = frame
                latest_timestamp = now
                build_debug_views(frame)

        self.picam.stop()

    def stop(self):
        self.running = False

    def capture_fresh(self):
        """Capture a single frame directly from the sensor -- no buffer latency."""
        if self.picam is None:
            return None
        return self.picam.capture_array()


camera_thread = CameraThread()


def build_mask(frame_bgr, p):
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (odd(p["blur_kernel"]), odd(p["blur_kernel"])), 0)

    if p["threshold_mode"] == "hsv":
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        lo1 = np.array([int(p["hsv_h1_lo"]), int(p["hsv_s_lo"]), int(p["hsv_v_lo"])])
        hi1 = np.array([int(p["hsv_h1_hi"]), int(p["hsv_s_hi"]), int(p["hsv_v_hi"])])
        lo2 = np.array([int(p["hsv_h2_lo"]), int(p["hsv_s_lo"]), int(p["hsv_v_lo"])])
        hi2 = np.array([int(p["hsv_h2_hi"]), int(p["hsv_s_hi"]), int(p["hsv_v_hi"])])
        mask1 = cv2.inRange(hsv, lo1, hi1)
        mask2 = cv2.inRange(hsv, lo2, hi2)
        mask = cv2.bitwise_or(mask1, mask2)
    elif p["threshold_mode"] == "adaptive":
        block = odd(int(p["adaptive_block_size"]))
        block = max(3, block)
        c = int(p["adaptive_c"])
        mask = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block, c
        )
    else:
        thresh_type = cv2.THRESH_BINARY_INV if p["threshold_mode"] == "inverse" else cv2.THRESH_BINARY
        _, mask = cv2.threshold(blur, int(p["threshold_value"]), 255, thresh_type)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Apply ROI -- zero out everything outside the region of interest
    roi = np.zeros_like(mask)
    roi[int(p["roi_y_min"]):int(p["roi_y_max"]),
        int(p["roi_x_min"]):int(p["roi_x_max"])] = 255
    mask = cv2.bitwise_and(mask, roi)

    return gray, mask


def build_debug_views(frame_bgr: np.ndarray):
    p = params.copy()

    raw = frame_bgr.copy()
    gray, mask = build_mask(raw, p)

    contours_vis = raw.copy()
    annotated = raw.copy()

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    accepted = []

    for c in contours:
        area = cv2.contourArea(c)
        if area < p["min_area"] or area > p["max_area"]:
            continue

        peri = cv2.arcLength(c, True)
        if peri <= 0:
            continue

        circularity = 4.0 * np.pi * area / (peri * peri)
        if circularity < p["circularity_min"]:
            continue

        (x, y), radius = cv2.minEnclosingCircle(c)
        radius = int(radius)
        if radius < p["min_radius"] or radius > p["max_radius"]:
            continue

        accepted.append({
            "contour": c,
            "center": (int(x), int(y)),
            "radius": radius,
            "area": float(area),
            "circularity": float(circularity),
        })

    if p["show_all_contours"]:
        cv2.drawContours(contours_vis, contours, -1, (0, 0, 255), 1)

    if p["show_accepted_contours"]:
        for item in accepted:
            cv2.drawContours(contours_vis, [item["contour"]], -1, (0, 255, 0), 2)
            cv2.circle(contours_vis, item["center"], item["radius"], (255, 0, 0), 1)

    global latest_detection
    best = None
    if accepted:
        best = max(accepted, key=lambda a: a["area"])
        latest_detection = {
            "px": best["center"][0],
            "py": best["center"][1],
            "radius": best["radius"],
            "area": best["area"],
            "circularity": best["circularity"],
            "timestamp": latest_timestamp,
        }
    else:
        latest_detection = None

    if best is not None:
        x, y = best["center"]
        r = best["radius"]
        cv2.circle(annotated, (x, y), r, (0, 255, 0), 2)
        cv2.circle(annotated, (x, y), 2, (0, 255, 255), -1)
        cv2.putText(
            annotated,
            f"x={x} y={y} r={r} A={best['area']:.0f} C={best['circularity']:.2f}",
            (10, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    else:
        cv2.putText(
            annotated,
            "No accepted contour",
            (10, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    cv2.putText(
        annotated,
        f"FPS {fps_estimate:.1f} | view={p['debug_view']}",
        (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )

    # Draw ROI boundary
    cv2.rectangle(
        annotated,
        (int(p["roi_x_min"]), int(p["roi_y_min"])),
        (int(p["roi_x_max"]), int(p["roi_y_max"])),
        (0, 255, 255), 1
    )

    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    tile_w = raw.shape[1] // 2
    tile_h = raw.shape[0] // 2

    def fit(img):
        return cv2.resize(img, (tile_w, tile_h))

    tiled = np.vstack([
        np.hstack([fit(raw), fit(gray_bgr)]),
        np.hstack([fit(mask_bgr), fit(annotated)]),
    ])

    processed_cache["raw"] = raw
    processed_cache["gray"] = gray_bgr
    processed_cache["mask"] = mask_bgr
    processed_cache["contours"] = contours_vis
    processed_cache["annotated"] = annotated
    processed_cache["tiled"] = tiled


def current_output_frame():
    with state_lock:
        view = params["debug_view"]
        cached = processed_cache.get(view)

    if cached is not None:
        return cached

    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(blank, "Waiting for camera...", (140, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    return blank


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pi Circle Detector</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #111; color: #eee; }
    .wrap { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; padding: 16px; }
    .panel { background: #1c1c1c; border-radius: 8px; padding: 12px; }
    img { width: 100%; height: auto; background: #000; border-radius: 6px; }
    label { display: block; margin-top: 10px; font-size: 14px; }
    input[type=range], input[type=number], select { width: 100%; }
    .row { display: grid; grid-template-columns: 1fr 80px; gap: 8px; align-items: center; }
    .small { font-size: 12px; color: #bbb; }
    button { margin-top: 10px; padding: 8px 10px; }
    #hsv-controls { display: none; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <h2>Video</h2>
      <img src="/stream" alt="video stream">
      <p class="small">Views: raw, gray, mask, contours, annotated, tiled</p>
    </div>
    <div class="panel">
      <h2>Controls</h2>

      <label>Debug view</label>
      <select id="debug_view"></select>

      <label>Threshold mode</label>
      <select id="threshold_mode">
        <option value="binary">binary</option>
        <option value="inverse">inverse</option>
        <option value="hsv">hsv (colour)</option>
        <option value="adaptive">adaptive</option>
      </select>

      <div id="gray-controls">
        <div id="threshold_value_wrap"></div>
      </div>

      <div id="adaptive-controls" style="display:none">
        <div id="adaptive_block_size_wrap"></div>
        <div id="adaptive_c_wrap"></div>
      </div>

      <div id="hsv-controls">
        <p class="small">Hue range 1 (red low, wraps near 0)</p>
        <div id="hsv_h1_lo_wrap"></div>
        <div id="hsv_h1_hi_wrap"></div>
        <p class="small">Hue range 2 (red high, wraps near 180)</p>
        <div id="hsv_h2_lo_wrap"></div>
        <div id="hsv_h2_hi_wrap"></div>
        <p class="small">Saturation</p>
        <div id="hsv_s_lo_wrap"></div>
        <div id="hsv_s_hi_wrap"></div>
        <p class="small">Value (brightness)</p>
        <div id="hsv_v_lo_wrap"></div>
        <div id="hsv_v_hi_wrap"></div>
      </div>

      <label><input type="checkbox" id="show_all_contours"> Show all raw contours</label>
      <label><input type="checkbox" id="show_accepted_contours"> Show accepted contours</label>

      <div id="controls"></div>

      <button onclick="saveParams()">Save current params to JSON</button>
      <pre id="status" class="small"></pre>
    </div>
  </div>

<script>
const views = ["raw", "gray", "mask", "contours", "annotated", "tiled"];

const numericControls = [
  ["blur_kernel", 1, 15, 2],
  ["min_area", 0, 50000, 10],
  ["max_area", 100, 300000, 100],
  ["circularity_min", 0.1, 1.0, 0.01],
  ["min_radius", 0, 200, 1],
  ["max_radius", 0, 300, 1],
  ["roi_x_min", 0, 640, 1],
  ["roi_x_max", 0, 640, 1],
  ["roi_y_min", 0, 480, 1],
  ["roi_y_max", 0, 480, 1],
  ["jpeg_quality", 30, 90, 1],
  ["stream_fps", 1, 20, 1],
];

const hsvControls = [
  ["hsv_h1_lo", 0, 30, 1],
  ["hsv_h1_hi", 0, 30, 1],
  ["hsv_h2_lo", 150, 180, 1],
  ["hsv_h2_hi", 150, 180, 1],
  ["hsv_s_lo", 0, 255, 1],
  ["hsv_s_hi", 0, 255, 1],
  ["hsv_v_lo", 0, 255, 1],
  ["hsv_v_hi", 0, 255, 1],
];

async function getParams() {
  const r = await fetch('/params');
  return await r.json();
}

async function setParam(key, value) {
  await fetch('/set_param', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({key, value})
  });
}

function makeNumericControl(name, min, max, step, current, containerId) {
  const wrap = document.createElement('div');
  wrap.innerHTML = `
    <label>${name}</label>
    <div class="row">
      <input type="range" id="${name}" min="${min}" max="${max}" step="${step}" value="${current}">
      <input type="number" id="${name}_num" min="${min}" max="${max}" step="${step}" value="${current}">
    </div>
  `;

  const slider = wrap.querySelector(`#${name}`);
  const num = wrap.querySelector(`#${name}_num`);

  slider.addEventListener('input', async () => {
    num.value = slider.value;
    await setParam(name, parseFloat(slider.value));
  });

  num.addEventListener('change', async () => {
    slider.value = num.value;
    await setParam(name, parseFloat(num.value));
  });

  if (containerId) {
    document.getElementById(containerId).appendChild(wrap);
  }
  return wrap;
}

function updateModeVisibility(mode) {
  document.getElementById('gray-controls').style.display = (mode === 'binary' || mode === 'inverse') ? 'block' : 'none';
  document.getElementById('hsv-controls').style.display = (mode === 'hsv') ? 'block' : 'none';
  document.getElementById('adaptive-controls').style.display = (mode === 'adaptive') ? 'block' : 'none';
}

async function init() {
  const p = await getParams();

  const viewSel = document.getElementById('debug_view');
  views.forEach(v => {
    const o = document.createElement('option');
    o.value = v;
    o.textContent = v;
    if (v === p.debug_view) o.selected = true;
    viewSel.appendChild(o);
  });
  viewSel.addEventListener('change', async () => setParam('debug_view', viewSel.value));

  const tm = document.getElementById('threshold_mode');
  tm.value = p.threshold_mode;
  tm.addEventListener('change', async () => {
    await setParam('threshold_mode', tm.value);
    updateModeVisibility(tm.value);
  });
  updateModeVisibility(p.threshold_mode);

  for (const key of ['show_all_contours', 'show_accepted_contours']) {
    const el = document.getElementById(key);
    el.checked = !!p[key];
    el.addEventListener('change', async () => setParam(key, el.checked));
  }

  // Gray threshold control
  makeNumericControl("threshold_value", 0, 255, 1, p["threshold_value"], "threshold_value_wrap");

  // Adaptive controls
  makeNumericControl("adaptive_block_size", 3, 99, 2, p["adaptive_block_size"], "adaptive_block_size_wrap");
  makeNumericControl("adaptive_c", -20, 40, 1, p["adaptive_c"], "adaptive_c_wrap");

  // HSV controls
  hsvControls.forEach(([name, min, max, step]) => {
    makeNumericControl(name, min, max, step, p[name], `${name}_wrap`);
  });

  // Shared numeric controls
  const controls = document.getElementById('controls');
  numericControls.forEach(([name, min, max, step]) => {
    controls.appendChild(makeNumericControl(name, min, max, step, p[name]));
  });
}

async function saveParams() {
  const r = await fetch('/save_params', {method: 'POST'});
  const msg = await r.json();
  document.getElementById('status').textContent = JSON.stringify(msg, null, 2);
}

init();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/params")
def get_params_route():
    return jsonify(params)


@app.route("/set_param", methods=["POST"])
def set_param_route():
    data = request.get_json(force=True)
    key = data["key"]
    value = data["value"]

    if key not in params:
        return jsonify({"ok": False, "error": f"Unknown parameter: {key}"}), 400

    if isinstance(params[key], bool):
        params[key] = bool(value)
    elif isinstance(params[key], int):
        params[key] = int(float(value))
    elif isinstance(params[key], float):
        params[key] = float(value)
    else:
        params[key] = value

    if key == "blur_kernel":
        params[key] = odd(params[key])

    return jsonify({"ok": True, "params": params})


@app.route("/save_params", methods=["POST"])
def save_params_route():
    path = "circle_detector_params.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
    return jsonify({"ok": True, "saved_to": path})


@app.route("/detect")
def detect_route():
    with state_lock:
        det = latest_detection
        ts = latest_timestamp
    if det is None:
        return jsonify({"detected": False, "timestamp": ts})
    return jsonify({"detected": True, "timestamp": ts, **det})


@app.route("/capture")
def capture_route():
    """Capture a fresh frame directly from the sensor and run detection on it.
    No buffer latency -- the frame is captured at the moment this is called."""
    frame = camera_thread.capture_fresh()
    if frame is None:
        return jsonify({"detected": False, "error": "camera not ready"})

    p = params.copy()
    gray, mask = build_mask(frame, p)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    accepted = []

    for c in contours:
        area = cv2.contourArea(c)
        if area < p["min_area"] or area > p["max_area"]:
            continue
        peri = cv2.arcLength(c, True)
        if peri <= 0:
            continue
        circularity = 4.0 * np.pi * area / (peri * peri)
        if circularity < p["circularity_min"]:
            continue
        (x, y), radius = cv2.minEnclosingCircle(c)
        radius = int(radius)
        if radius < p["min_radius"] or radius > p["max_radius"]:
            continue
        accepted.append({
            "center": (int(x), int(y)),
            "radius": radius,
            "area": float(area),
            "circularity": float(circularity),
        })

    if not accepted:
        return jsonify({"detected": False, "timestamp": time.time()})

    best = max(accepted, key=lambda a: a["area"])
    return jsonify({
        "detected": True,
        "timestamp": time.time(),
        "px": best["center"][0],
        "py": best["center"][1],
        "radius": best["radius"],
        "area": best["area"],
        "circularity": best["circularity"],
    })


@app.route("/stream")
def stream():
    def generate():
        while True:
            frame = current_output_frame()
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(params["jpeg_quality"])]
            ok, jpg = cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                continue
            chunk = jpg.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + chunk + b"\r\n"
            )
            time.sleep(1.0 / max(1, int(params["stream_fps"])))

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    camera_thread.start()
    try:
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        camera_thread.stop()