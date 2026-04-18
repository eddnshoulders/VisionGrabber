import time
import serial
from scan_and_grab import scan_and_grab
from klipperAPI import KlipperAPI
from config import *
from skr_reset import SKR_Reset

def home(machine):
    # get homes status
    homed, x, y, z = machine.get_position()
    if not homed:
        print("\nHoming...")
        machine.gcode("G28")
    else:
        machine.gcode("G0 X120 Y120 F5000")

    # Bed down, gripper open
    machine.gcode(f"G0 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
    machine.gcode(GRIPPER_OPEN)

def wait_BTN(btn):
    print("Waiting for button")
    btn.write(("LED_ON\n").encode())
    line = ''
    while not line == "BTN":
        line = btn.readline().decode().strip()
        if line:
            print(f"line: ", line)
    btn.write(("LED_OFF\n").encode())
    time.sleep(0.1)
    btn.reset_input_buffer()

def reset_stm32(port, baudrate):
    with serial.Serial(port, baudrate, dsrdtr=True) as s:
        s.dtr = False
        time.sleep(0.1)
        s.dtr = True
        time.sleep(0.1)
        s.dtr = False
    time.sleep(2)  # wait for re-enumeration

def main():
    #SKR_Reset()

    print(f"{time.time():.3f} Opening {BUTTON_PORT}", flush=True)
    btn = serial.Serial(BUTTON_PORT, BUTTON_BAUDRATE, timeout=0.2, dsrdtr = True)

    # Avoid immediate traffic while the MCU reboots/settles
    time.sleep(0.5)

    btn.reset_input_buffer()
    btn.reset_output_buffer()

    print("Connecting to MCU...")
    machine = KlipperAPI()
    print("Connected.")
    
    # check machine is in home position
    homed, x, y, z = machine.get_position()

    # if unhomed, send G28
    if not homed:
        wait_BTN(btn)
        home(machine)
    # if not at home, position but homed, move to home position
    if homed and (x != SCAN_X_START) and (y != SCAN_Y_START) and (z != Z_BED_DOWN):
        wait_BTN(btn)
        home(machine)

    # if in home position, do nothing
    
    while(1):
        # Wait for user
        print("Place cylinder on bed")
        wait_BTN(btn)
        scan_and_grab(machine)
        home(machine)           

    machine.close()

if __name__ == "__main__":
    main()
