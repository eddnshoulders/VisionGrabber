/**
 * Typed API client for VisionGrabber backend.
 * All components call these functions rather than fetch() directly.
 */

const BASE = "/api";

async function post(path: string, body?: object): Promise<Response> {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function get(path: string): Promise<Response> {
  return fetch(`${BASE}${path}`);
}

async function patch(path: string, body: object): Promise<Response> {
  return fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ── Sequence ──────────────────────────────────────────────────────────────────

export const sequenceApi = {
  start:    () => post("/sequence/start"),
  stop:     () => post("/sequence/stop"),
  retry:    () => post("/sequence/operator", { action: "retry" }),
  reset:    () => post("/sequence/operator", { action: "reset" }),
  getState: () => get("/sequence/state").then((r) => r.json()),
};

// ── Camera ────────────────────────────────────────────────────────────────────

export type CameraId = "toolhead" | "overhead";

export const cameraApi = {
  streamStart:   (id: CameraId) => post(`/camera/${id}/stream/start`),
  streamStop:    (id: CameraId) => post(`/camera/${id}/stream/stop`),
  streamUrl:     (id: CameraId) => `/api/camera/${id}/stream`,
  frameUrl:      (id: CameraId, view?: string) =>
    `/api/camera/${id}/frame${view ? `/${view}` : ""}`,

  getDetection:  (id: CameraId) =>
    get(`/camera/${id}/detect`).then((r) => r.json()),
  captureSingle: (id: CameraId) =>
    post(`/camera/${id}/detect/single`).then((r) => r.json()),

  getParams:     (id: CameraId) =>
    get(`/camera/${id}/params`).then((r) => r.json()),
  patchParams:   (id: CameraId, params: Record<string, unknown>) =>
    patch(`/camera/${id}/params`, params).then((r) => r.json()),
  saveParams:    (id: CameraId, name?: string) =>
    post(`/camera/${id}/params/save`, name ? { name } : {}).then((r) => r.json()),
  getPresets:    (id: CameraId) =>
    get(`/camera/${id}/params/presets`).then((r) => r.json()),
  loadPreset:    (id: CameraId, name: string) =>
    post(`/camera/${id}/params/load`, { name }).then((r) => r.json()),
};

// ── Machine ───────────────────────────────────────────────────────────────────

export const machineApi = {
  sendCommand: (cmd: string) =>
    post("/machine/command", { cmd }).then((r) => r.json()),
  getState:    () =>
    get("/machine/state").then((r) => r.json()),
};
