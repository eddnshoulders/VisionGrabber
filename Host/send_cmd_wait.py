#!/usr/bin/env python3
# send_cmd.py
import serial
import sys
import time

ser = serial.Serial("/dev/ttyAMA0", 115200, timeout=30)
time.sleep(0.1)  # let port settle

cmd = " ".join(sys.argv[1:]) + "\n"
print(f">> {cmd.strip()}")
ser.write(cmd.encode())

while(True):
	response = ser.readline().decode().strip()
	print(f"<< {response}")

ser.close()
