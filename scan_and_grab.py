import serial
import json
import time
import requests

# ── Configuration ─────────────────────────────────────────────────────────────

MACHINE_UART      = "/dev/ttyAMA0"
MACHINE_BAUDRATE  = 115200
FLASK_URL         = "http://localhost:5000"

SCAN_FEEDRATE     = 2500    # mm/min -- scan step moves
MOVE_FEEDRATE     = 8000    # mm/min -- repositioning moves
BED_FEEDRATE      = 3000    # mm/min -- Z moves

SCAN_X_STEP       = 15      # mm -- X increment between scan points
SCAN_Y_STEP       = 20      # mm -- Y increment between scan rows
SCAN_X_START      = 120     # mm
SCAN_X_END        = 0       # mm
SCAN_Y_START      = 120     # mm
SCAN_Y_END        = 0       # mm

STEP_SETTLE_TIME  = 0.1     # seconds to wait after each move before checking detection

Z_BED_DOWN        = 40      # mm -- bed lowered (safe scanning height)
Z_BED_UP          = 5       # mm -- bed raised (pick height)

GRIPPER_OPEN      = "M280 S30"
GRIPPER_CLOSE     = "M280 S145"

DROP_X            = 20      # mm -- drop position
DROP_Y            = 0       # mm

PICKUP_CX         = 318     # image X position of circle centre when aligned for pickup
PICKUP_CY         = 231     # image Y position of circle centre when aligned for pickup
IMAGE_CX          = 320     # pixels -- image centre X (half of frame width)
IMAGE_CY          = 240     # pixels -- image centre Y (half of frame height)
SCALE_X           = -6      # pixels per mm
SCALE_Y           = 6       # pixels per mm

ALIGN_THRESH_X    = 2       # pixels -- alignment tolerance in X
ALIGN_THRESH_Y    = 2       # pixels -- alignment tolerance in Y

N_FRAMES          = 2       # number of frames to capture for confirmed detection
Y_DETECTIONS      = 1       # minimum positive detections required out of N_FRAMES

DET_STEPBACK      = 6       # how far to step back after detection (reverse overshoot on stopping)


# ── Klipper API ───────────────────────────────────────────────────────────────

class MachineAPI:
    def __init__(self, port=MACHINE_UART, baud=MACHINE_BAUDRATE, timeout=30):
        self.ser = serial.Serial(port, baud, timeout=timeout)

    def _send(self, cmd):
        print(f"  >> {cmd}")
        self.ser.write((cmd + "\n").encode())

    def _wait_ok(self):
        while True:
            line = self.ser.readline().decode().strip()
            if line == "ok":
                print(f"  << {line}")
                return
            elif line.startswith("error"):
                raise RuntimeError(f"Machine error: {line}")
            elif line:
                print(f"  << {line}")  # log unexpected responses

    def gcode(self, cmd):
        self._send(cmd)
        self._wait_ok()

    def move_and_wait(self, cmd):
        print(f"  Before move: {time.time():.3f}")
        self.gcode(cmd)
        print(f"  After move:  {time.time():.3f}")

    def get_position(self):
        self._send("M114")
        line = "ok"
        while line == "ok":
            line = self.ser.readline().decode().strip()  # X:60.00 Y:60.00 Z:0.00      
        # Parse response
        parts = line.split()
        x = float(parts[0].split(":")[1])
        y = float(parts[1].split(":")[1])
        return x, y

    def close(self):
        self.ser.close()

# ── Vision ────────────────────────────────────────────────────────────────────

def capture():
    """
    Call /capture for a fresh frame captured at this exact moment.
    Returns (detected, data) where data has px, py, radius, area, circularity.
    Retries N_FRAMES times and requires Y_DETECTIONS positive results.
    """
    positive_px = []
    positive_py = []

    for i in range(N_FRAMES):
        try:
            r = requests.get(f"{FLASK_URL}/capture", timeout=2.0)
            data = r.json()
        except Exception as e:
            #print(f"  Frame {i+1}/{N_FRAMES}: request failed ({e})")
            continue

        if data.get("detected"):
            positive_px.append(data["px"])
            positive_py.append(data["py"])
            #print(f"  Frame {i+1}/{N_FRAMES}: detected px={data['px']} py={data['py']}")
        #else:
            #print(f"  Frame {i+1}/{N_FRAMES}: no detection")

    if len(positive_px) >= Y_DETECTIONS:
        avg_px = sum(positive_px) / len(positive_px)
        avg_py = sum(positive_py) / len(positive_py)
        #print(f"  Confirmed: {len(positive_px)}/{N_FRAMES} positive, avg px={avg_px:.1f} py={avg_py:.1f}")
        return True, {"px": avg_px, "py": avg_py}

    #print(f"  Not confirmed: only {len(positive_px)}/{N_FRAMES} positive")
    return False, None


# ── Main sequence ─────────────────────────────────────────────────────────────

def main():
    print("Connecting to Klipper...")
    machine = MachineAPI()
    print("Connected.")

    # Home
    print("\nHoming...")
    machine.gcode("G28")

    # Bed down, gripper open
    machine.gcode(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
    machine.gcode(GRIPPER_OPEN)

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
            x_start = SCAN_X_START
            x_end = SCAN_X_END
        else:
            x_start = SCAN_X_END
            x_end = SCAN_X_START

        print(f"  Sweeping Y={y} X={x_start} -> {x_end}")

        # Start the sweep -- non-blocking, don't wait for ok
        machine._send(f"G0 X{x_end} Y{y} F{SCAN_FEEDRATE}")

        # Sample continuously while the move is in progress
        while True:
            confirmed, data = capture()
            if confirmed:
                machine._send("STOP")
                machine._wait_ok()
                tx, ty = machine.get_position()
                # if X was decreasing, increase to step back
                if row % 2 == 0:
                    machine._send(f"G0 X{tx + DET_STEPBACK} Y{y} F{MOVE_FEEDRATE}")
                # or vice-versa
                else:
                    machine._send(f"G0 X{tx - DET_STEPBACK} Y{y} F{MOVE_FEEDRATE}")
                found = True
                detection = data
                break

            # Check if move completed
            line = machine.ser.readline().decode().strip() if machine.ser.in_waiting else None
            if line == "ok":
                break  # Row complete, no detection
            elif line and line.startswith("error"):
                raise RuntimeError(f"Machine error: {line}")

        if not found:
            y -= SCAN_Y_STEP
            row += 1
            # Move to start of next row
            machine.move_and_wait(f"G0 X{x_end} Y{y} F{SCAN_FEEDRATE}")

    if not found:
        print("\nScan complete -- cylinder not found. Aborting.")
        machine.close()
        return

    # Iterative alignment loop
    aligned = False

    while not aligned:
        # get a fresh pixel position of the circle centre (should be close to original detection point afer stepback)
        time.sleep(0.5)
        confirmed, data = capture()
        px = data["px"]
        py = data["py"]

        # get current machine position
        tx, ty = machine.get_position()

        offset_x = (px - PICKUP_CX) / SCALE_X
        offset_y = (py - PICKUP_CY) / SCALE_Y
        target_x = max(0, min(120, tx + offset_x))
        target_y = max(0, min(120, ty + offset_y))

        print(f"\n  Aligning: px={px:.1f} py={py:.1f} offset=({offset_x:.2f}, {offset_y:.2f})")
        print(f"  Target: X={target_x:.2f} Y={target_y:.2f}")

        machine.move_and_wait(f"G0 X{target_x:.2f} Y{target_y:.2f} F{MOVE_FEEDRATE}")
        time.sleep(STEP_SETTLE_TIME)

        confirmed, data = capture()
        if not confirmed:
            print("  No detection after alignment move -- aborting.")
            machine.close()
            return

        px = data["px"]
        py = data["py"]

        ofst_x = abs(px - PICKUP_CX)
        ofst_y = abs(py - PICKUP_CY)
        print(f"  Residual: dx={ofst_x:.1f} dy={ofst_y:.1f} (tolerance {ALIGN_THRESH_X}/{ALIGN_THRESH_Y})")

        if ofst_x < ALIGN_THRESH_X and ofst_y < ALIGN_THRESH_Y:
            aligned = True

    # Pick sequence
    print("\nPicking up cylinder...")
    machine.move_and_wait(f"G0 Z{Z_BED_UP} F{BED_FEEDRATE}")
    machine.gcode(GRIPPER_CLOSE)
    time.sleep(1)
    machine.move_and_wait(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")

    # Move to drop position
    print(f"\nMoving to drop position X={DROP_X} Y={DROP_Y}...")
    machine.move_and_wait(f"G0 X{DROP_X} Y{DROP_Y} F{MOVE_FEEDRATE}")

    # Drop
    print("Dropping cylinder.")
    machine.gcode(GRIPPER_OPEN)
    time.sleep(0.5)

    print("\nDone.")
    machine.close()

if __name__ == "__main__":
    main()