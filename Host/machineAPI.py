import serial
import time
from config import *

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
            elif line == "not homed":
                print(f"  << {line}")
                return
            elif line:
                print(f"  << {line}")

    def gcode(self, cmd):
        self._send(cmd)
        self._wait_ok()

    def move_and_wait(self, cmd):
        #print(f"  Before move: {time.time():.3f}")
        self.gcode(cmd)
        #print(f"  After move:  {time.time():.3f}")

    def get_position(self):
        x = 0; y = 0; z = 0
        homed = False
        self._send("M114")
        line = "ok"
        while line == "ok":
            line = self.ser.readline().decode().strip()
        
        # return unhomed = True if not homed
        if line == "error: not homed":
            return homed, x, y, z
        
        # otherwise, process returned position
        parts = line.split()
        x = float(parts[0].split(":")[1])
        y = float(parts[1].split(":")[1])
        z = float(parts[2].split(":")[1])
        homed = True;
        return homed, x, y, z

    def close(self):
        self.ser.close()