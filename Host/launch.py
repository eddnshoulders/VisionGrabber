import serial
import time
from scan_and_grab import scan_and_grab
from machineAPI import MachineAPI
from config import *

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

def wait_BTN(ser):
    print("Waiting for button")
    ser.write(("LED_ON\n").encode())
    line = ''
    while not line == "BTN":
        line = ser.readline().decode().strip()
        if line:
            print(f"line: ", line)
    ser.write(("LED_OFF\n").encode())
    time.sleep(0.1)
    ser.reset_input_buffer()

def main():
    print(f"{time.time():.3f} [SerialManager] opening {BUTTON_PORT}", flush=True)
    ser = serial.Serial(BUTTON_PORT, BUTTON_BAUDRATE, timeout=0.2, dsrdtr = True)

    # Avoid immediate traffic while the MCU reboots/settles
    time.sleep(0.5)

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    print("Connecting to MCU...")
    machine = MachineAPI()
    print("Connected.")
    
    # check machine is in home position
    homed, x, y, z = machine.get_position()

    # if unhomed, send G28
    if not homed:
        wait_BTN(ser)
        home(machine)
    # if not at home, position but homed, move to home position
    if homed and (x != SCAN_X_START) and (y != SCAN_Y_START) and (z != Z_BED_DOWN):
        wait_BTN(ser)
        home(machine)

    # if in home position, do nothing
    
    while(1):
        # Wait for user
        print("Place cylinder on bed")
        wait_BTN(ser)
        scan_and_grab(machine)
        home(machine)           

    machine.close()

if __name__ == "__main__":
    main()