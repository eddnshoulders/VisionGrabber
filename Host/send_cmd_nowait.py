#!/usr/bin/env python3
# send_cmd.py
import serial
import sys
import time
from config import *

ser = serial.Serial(MACHINE_UART, MACHINE_BAUDRATE, timeout=30)
time.sleep(0.1)  # let port settle

cmd = " ".join(sys.argv[1:]) + "\n"
print(f">> {cmd.strip()}")
ser.write(cmd.encode())

ser.close()
