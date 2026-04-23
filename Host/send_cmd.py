#!/usr/bin/env python3
# send_cmd.py

import argparse
import time
import serial
from config import *

parser = argparse.ArgumentParser()
parser.add_argument(
    "--nowait",
    action="store_true",
    help="don't wait for returned strings",
)
parser.add_argument(
    "--waitinf",
    action="store_true",
    help="wait forever and print all returned strings",
)
parser.add_argument(
    "cmd",
    nargs="+",
    help="command to send",
)

args = parser.parse_args()

cmd = " ".join(args.cmd)

if cmd == "GRIPPER_OPEN":
    cmd = f"M280 S{GRIPPER_OPEN}"
elif cmd == "GRIPPER_CLOSE":
    cmd = f"M280 S{GRIPPER_CLOSE}"

ser = serial.Serial(MACHINE_UART, MACHINE_BAUDRATE, timeout=30)
time.sleep(0.1)  # let port settle

print(f">> {cmd.strip()}")
ser.write((cmd + "\n").encode())

if not args.nowait:
    if args.waitinf:
        while True:
            response = ser.readline().decode(errors="replace").strip()
            print(f"<< {response}")
    else:
        response = ser.readline().decode(errors="replace").strip()
        print(f"<< {response}")

ser.close()
