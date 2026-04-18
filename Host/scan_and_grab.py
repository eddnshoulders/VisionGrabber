import serial
import time
import requests
from config import *

# ── Vision ────────────────────────────────────────────────────────────────────

def capture():
    positive_px = []
    positive_py = []

    for i in range(N_FRAMES):
        try:
            r = requests.get(f"{FLASK_URL}/capture", timeout=2.0)
            data = r.json()
        except Exception as e:
            continue

        if data.get("detected"):
            positive_px.append(data["px"])
            positive_py.append(data["py"])

    if len(positive_px) >= Y_DETECTIONS:
        avg_px = sum(positive_px) / len(positive_px)
        avg_py = sum(positive_py) / len(positive_py)
        return True, {"px": avg_px, "py": avg_py}

    return False, None

# ── Main sequence ─────────────────────────────────────────────────────────────

def scan_and_grab(machine):    # Scan -- snake pattern
    print("\nScanning...")
    found = False
    detection = None

    y = SCAN_Y_START
    row = 0

    while y >= SCAN_Y_END and not found:
        if row % 2 == 0:
            x_start = SCAN_X_START
            x_end = SCAN_X_END
        else:
            x_start = SCAN_X_END
            x_end = SCAN_X_START

        print(f"  Sweeping Y={y} X={x_start} -> {x_end}")
        machine._send(f"G0 X{x_end} Y{y} F{SCAN_FEEDRATE}")

        while True:
            confirmed, data = capture()
            if confirmed:
                machine._send("STOP")
                machine._wait_ok()
                homed, tx, ty, tz = machine.get_position()
                if row % 2 == 0:
                    machine._send(f"G0 X{tx + DET_STEPBACK} Y{y} F{MOVE_FEEDRATE}")
                else:
                    machine._send(f"G0 X{tx - DET_STEPBACK} Y{y} F{MOVE_FEEDRATE}")
                found = True
                detection = data
                break

            line = machine.ser.readline().decode().strip() if machine.ser.in_waiting else None
            if line == "ok":
                break
            elif line and line.startswith("error"):
                raise RuntimeError(f"Machine error: {line}")

        if not found:
            y -= SCAN_Y_STEP
            row += 1
            machine.move_and_wait(f"G0 X{x_end} Y{y} F{SCAN_FEEDRATE}")

    if not found:
        print("\nScan complete -- cylinder not found. Aborting.")
        return

    # Iterative alignment loop
    aligned = False

    while not aligned:
        time.sleep(0.5)
        confirmed, data = capture()
        px = data["px"]
        py = data["py"]

        homed, tx, ty, tz = machine.get_position()

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