import socket
import json
import time
from config import *

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
        resp = self._send("objects/query", {
            "objects": {
                "toolhead": ["position", "homed_axes"]
            }
        })
        status = resp["result"]["status"]["toolhead"]
        pos = status["position"]
        homed_axes = status["homed_axes"]  # e.g. "xyz" or "" or "xy"
        homed = "x" in homed_axes and "y" in homed_axes and "z" in homed_axes
        return homed, pos[0], pos[1], pos[2]

    def move_and_wait(self, gcode):
        self.gcode(gcode)
        #print(f"  Before M400: {time.time():.3f}")
        self.gcode("M400")
        #print(f"  After M400:  {time.time():.3f}")

    def close(self):
        self.sock.close()
