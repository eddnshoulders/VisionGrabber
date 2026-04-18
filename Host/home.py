MOVE_FEEDRATE     = 10000
BED_FEEDRATE      = 3000

SCAN_X_START      = 120
SCAN_Y_START      = 120

Z_BED_DOWN        = 40

GRIPPER_OPEN      = "M280 S30"

def home(machine):
    # Try moving to home position
    machine._send(f"G0 X{SCAN_X_START} Y{SCAN_Y_START} F{MOVE_FEEDRATE}")
    line = machine.ser.readline().decode().strip()
    if line == "error: not homed":
        print("\nHoming...")
        machine.gcode("G28")

    # Bed down, gripper open
    machine.gcode(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
    machine.gcode(GRIPPER_OPEN)