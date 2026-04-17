import socket
import json
import time
import requests

# ── Configuration ─────────────────────────────────────────────────────────────

KLIPPER_SOCK      = "/home/pi/printer_data/comms/klippy.sock"
FLASK_URL         = "http://localhost:5000"

SCAN_FEEDRATE     = 3000    # mm/min -- scan step moves
MOVE_FEEDRATE     = 3000    # mm/min -- repositioning moves
BED_FEEDRATE      = 1000    # mm/min -- Z moves

SCAN_X_STEP       = 15      # mm -- X increment between scan points
SCAN_Y_STEP       = 20      # mm -- Y increment between scan rows
SCAN_X_START      = 120     # mm
SCAN_X_END        = 0       # mm
SCAN_Y_START      = 120     # mm
SCAN_Y_END        = 0       # mm

STEP_SETTLE_TIME  = 0.2     # seconds to wait after each move before checking detection

Z_BED_DOWN        = 30      # mm -- bed lowered (safe scanning height)
Z_BED_UP          = 5       # mm -- bed raised (pick height)

GRIPPER_OPEN      = "SET_SERVO SERVO=Grabber angle=32"
GRIPPER_CLOSE     = "SET_SERVO SERVO=Grabber angle=145"

DROP_X            = 20      # mm -- drop position
DROP_Y            = 0       # mm

PICKUP_CX         = 307     # image X position of circle centre when aligned for pickup
PICKUP_CY         = 219     # image Y position of circle centre when aligned for pickup
IMAGE_CX          = 320     # pixels -- image centre X (half of frame width)
IMAGE_CY          = 240     # pixels -- image centre Y (half of frame height)
SCALE_X           = -4.3    # pixels per mm
SCALE_Y           = 4.3     # pixels per mm

ALIGN_THRESH_X    = 2       # pixels -- alignment tolerance in X
ALIGN_THRESH_Y    = 2       # pixels -- alignment tolerance in Y

N_FRAMES          = 5       # number of frames to sample for confirmed detection
Y_DETECTIONS      = 3       # minimum positive detections required out of N_FRAMES
CONFIRM_TIMEOUT   = 3.0     # seconds to wait for N confirmed frames


# ── Klipper API ───────────────────────────────────────────────────────────────

class KlipperAPI:
    def __init__(self, sock_path=KLIPPER_SOCK):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(sock_path)
        self._id = 0

    def _next_id(self):
        self._id += 1
        return self._id

    def _send(self, method, params=None):
        payload = {"id": self._next_id(), "method": method, "params": params or {}}
        msg = json.dumps(payload) + "\x03"
        self.sock.sendall(msg.encode())
        return self._read_response()

    def _read_response(self):
        buf = ""
        while True:
            chunk = self.sock.recv(4096).decode()
            buf += chunk
            if "\x03" in buf:
                msg = buf.split("\x03")[0]
                return json.loads(msg)

    def gcode(self, script):
        print(f"  >> {script}")
        return self._send("gcode/script", {"script": script})

    def get_position(self):
        resp = self._send("objects/query", {"objects": {"toolhead": ["position"]}})
        pos = resp["result"]["status"]["toolhead"]["position"]
        return pos[0], pos[1]

    def move_and_wait(self, gcode):
        self.gcode(gcode)
        #print(f"  Before M400: {time.time():.3f}")
        self.gcode("M400")
        #print(f"  After M400:  {time.time():.3f}")

    def close(self):
        self.sock.close()


# ── Vision ────────────────────────────────────────────────────────────────────

def get_detection():
    """Single poll of /detect. Returns (detected, json)."""
    try:
        r = requests.get(f"{FLASK_URL}/detect", timeout=1.0)
        data = r.json()
        return data.get("detected", False), data
    except Exception:
        return False, None


def get_confirmed_detection(after_time):
    """
    Count N_FRAMES fresh frames captured after after_time.
    Return detected=True and averaged px/py if at least Y_DETECTIONS are positive.
    """
    deadline = time.time() + CONFIRM_TIMEOUT
    last_ts = 0
    frame_count = 0
    positive_px = []
    positive_py = []

    loop_count = 0

    while time.time() < deadline:
        
        loop_count = loop_count + 1
        print(f"Loop Count = {loop_count} at time = {time.time()}")

        det, data = get_detection()
        if data is None:
            time.sleep(0.02)
            continue

        ts = data.get("timestamp", 0)
        print(f"  ts={ts:.3f} after_time={after_time:.3f} diff={ts-after_time:.3f}")

        # Skip frames captured before the move completed or already seen
        if ts <= after_time or ts == last_ts:
            time.sleep(0.02)
            continue

        last_ts = ts
        frame_count += 1

        if det:
            positive_px.append(data["px"])
            positive_py.append(data["py"])
            print(f"  Frame {frame_count}/{N_FRAMES}: detected px={data['px']} py={data['py']}")
        else:
            print(f"  Frame {frame_count}/{N_FRAMES}: no detection")

        if frame_count >= N_FRAMES:
            if len(positive_px) >= Y_DETECTIONS:
                avg_px = sum(positive_px) / len(positive_px)
                avg_py = sum(positive_py) / len(positive_py)
                print(f"  Confirmed: {len(positive_px)}/{N_FRAMES} positive, avg px={avg_px:.1f} py={avg_py:.1f}")
                return True, {"px": avg_px, "py": avg_py}
            else:
                print(f"  Not confirmed: only {len(positive_px)}/{N_FRAMES} positive")
                return False, None

    print("  Warning: timed out waiting for confirmed detection")
    return False, None


# ── Main sequence ─────────────────────────────────────────────────────────────

def main():
    print("Connecting to Klipper...")
    klipper = KlipperAPI()
    print("Connected.")

    # Home
    print("\nHoming...")
    klipper.gcode("G28")

    # Bed down, gripper open
    klipper.gcode(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
    klipper.gcode(GRIPPER_OPEN)

    # Wait for user
    input("\nPlace cylinder on bed then press Enter to begin scan...")

    # Scan -- snake pattern, stop and check at each point
    print("\nScanning...")
    found = False
    detection = None

    y = SCAN_Y_START
    row = 0

    while y >= SCAN_Y_END and not found:
        # Alternate X direction each row
        if row % 2 == 0:
            x_points = range(SCAN_X_START, SCAN_X_END - 1, -SCAN_X_STEP)
        else:
            x_points = range(SCAN_X_END, SCAN_X_START + 1, SCAN_X_STEP)

        for x in x_points:
            print(f"  Scanning X={x} Y={y}")
            klipper.move_and_wait(f"G0 X{x} Y{y} F{SCAN_FEEDRATE}")
            move_complete_time = time.time()
            time.sleep(STEP_SETTLE_TIME)

            confirmed, data = get_confirmed_detection(move_complete_time)
            if confirmed:
                found = True
                detection = data
                break

        if not found:
            y -= SCAN_Y_STEP
            row += 1

    if not found:
        print("\nScan complete -- cylinder not found. Aborting.")
        klipper.close()
        return

    # Iterative alignment loop
    aligned = False

    while not aligned:
        tx, ty = klipper.get_position()
        px = detection["px"]
        py = detection["py"]

        offset_x = (px - PICKUP_CX) / SCALE_X
        offset_y = (py - PICKUP_CY) / SCALE_Y
        target_x = max(0, min(120, tx + offset_x))
        target_y = max(0, min(120, ty + offset_y))

        print(f"\n  Aligning: px={px:.1f} py={py:.1f} offset=({offset_x:.2f}, {offset_y:.2f})")
        print(f"  Target: X={target_x:.2f} Y={target_y:.2f}")

        klipper.move_and_wait(f"G0 X{target_x:.2f} Y{target_y:.2f} F{MOVE_FEEDRATE}")
        move_complete_time = time.time()
        time.sleep(STEP_SETTLE_TIME)

        confirmed, data = get_confirmed_detection(move_complete_time)
        if not confirmed:
            print("  No detection after alignment move -- aborting.")
            klipper.close()
            return

        detection = data
        px = detection["px"]
        py = detection["py"]

        ofst_x = abs(px - PICKUP_CX)
        ofst_y = abs(py - PICKUP_CY)
        print(f"  Residual: dx={ofst_x:.1f} dy={ofst_y:.1f} (tolerance {ALIGN_THRESH_X}/{ALIGN_THRESH_Y})")

        if ofst_x < ALIGN_THRESH_X and ofst_y < ALIGN_THRESH_Y:
            aligned = True

    # Pick sequence
    print("\nPicking up cylinder...")
    klipper.move_and_wait(f"G0 Z{Z_BED_UP} F{BED_FEEDRATE}")
    klipper.gcode(GRIPPER_CLOSE)
    time.sleep(1)
    klipper.move_and_wait(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")

    # Move to drop position
    print(f"\nMoving to drop position X={DROP_X} Y={DROP_Y}...")
    klipper.move_and_wait(f"G0 X{DROP_X} Y{DROP_Y} F{MOVE_FEEDRATE}")

    # Drop
    print("Dropping cylinder.")
    klipper.gcode(GRIPPER_OPEN)
    time.sleep(0.5)

    print("\nDone.")
    klipper.close()


if __name__ == "__main__":
    main()
