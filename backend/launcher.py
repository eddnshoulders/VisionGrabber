"""
VisionGrabber Launcher
======================
Runs as VisionGrabberLauncher.service (systemd).

Responsibilities:
  - Owns the machine UART (MachineAPI)
  - Owns the button serial port (if connected)
  - Exposes a Unix socket IPC server for the Flask backend
  - Forwards button presses and IPC START commands as the same event
  - Maintains machine state string readable via STATE command

The Flask backend is the sequence coordinator - the launcher is purely
a hardware abstraction layer. It executes commands and reports state.
It does not make sequencing decisions.

IPC protocol (line-oriented UTF-8):
  Client sends:   "<COMMAND>\n"
  Server replies: "<response>\n"

Special commands:
  STATE           -> current machine state string (no UART traffic)
  START           -> trigger sequence (queued, same as button press)
  HOME            -> home the machine
  MOVE <x> <y>   -> G0 move
  GRIPPER OPEN <val> / GRIPPER CLOSE <val>
  <anything else> -> forwarded verbatim to machine as gcode
"""

import os
import queue
import socket
import threading
import time

import serial

from machine.machine_api import MachineAPI
from config import (
    BUTTON_PORT, BUTTON_BAUDRATE,
    MACHINE_UART, MACHINE_BAUDRATE,
    SCAN_X_START, SCAN_Y_START,
    Z_BED_DOWN, BED_FEEDRATE, MOVE_FEEDRATE,
    GRIPPER_OPEN, GRIPPER_CLOSE,
    IPC_SOCKET_PATH,
)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
_state_lock = threading.Lock()
_state_str  = "initialising"


def set_state(s: str):
    global _state_str
    with _state_lock:
        _state_str = s
    print(f"[state] {s}", flush=True)


def get_state() -> str:
    with _state_lock:
        return _state_str


# Command queue shared between IPC server thread and main loop
# Each item: {"cmd": str, "result": queue.Queue(1)}
cmd_queue: queue.Queue = queue.Queue()

# Event set when a START trigger arrives (button or IPC)
start_event = threading.Event()


# ---------------------------------------------------------------------------
# Machine helpers
# ---------------------------------------------------------------------------

def home(machine: MachineAPI):
    set_state("homing")
    machine._send(f"G0 X{SCAN_X_START} Y{SCAN_Y_START} F{MOVE_FEEDRATE}")
    line = machine.ser.readline().decode().strip()
    if line == "error: not homed":
        print("\nHoming...")
        machine.gcode("G28")
    machine.gcode(f"G0 X120 Y120 Z{Z_BED_DOWN} F{BED_FEEDRATE}")
    machine.gcode(f"M280 S{GRIPPER_OPEN}")
    set_state("IDLE")


def execute_command(machine: MachineAPI, cmd: str) -> str:
    """Dispatch a single IPC command with exclusive UART access."""
    parts = cmd.strip().split()
    verb  = parts[0].upper() if parts else ""

    try:
        if verb == "STATE":
            return get_state()

        elif verb == "M114":
            machine._send("M114")
            # Read the position line directly, don't use _wait_ok()
            line = machine.ser.readline().decode().strip()
            return line

        elif verb == "HOME":
            home(machine)
            return "ok"

        elif verb == "MOVE" and len(parts) >= 3:
            x, y = parts[1], parts[2]
            z = parts[3] if len(parts) >= 4 else None
            cmd_str = f"G0 X{x} Y{y}"
            if z is not None:
                cmd_str += f" Z{z}"
            cmd_str += f" F{MOVE_FEEDRATE}"
            machine.gcode(cmd_str)
            return "ok"

        elif verb == "GRIPPER" and len(parts) >= 3:
            val = parts[2]
            machine.gcode(f"M280 S{val}")
            return f"ok gripper {parts[1].lower()} {val}"

        elif verb == "START":
            start_event.set()
            return "ok"

        else:
            machine.gcode(cmd)
            return "ok"

    except Exception as exc:
        return f"ERROR: {exc}"


# ---------------------------------------------------------------------------
# IPC server
# ---------------------------------------------------------------------------

def _ipc_handle(conn: socket.socket, machine: MachineAPI):
    try:
        data = b""
        conn.settimeout(5.0)
        while b"\n" not in data:
            chunk = conn.recv(256)
            if not chunk:
                break
            data += chunk

        cmd = data.decode(errors="replace").strip()
        if not cmd:
            conn.sendall(b"ERROR: empty command\n")
            return

        print(f"[IPC] recv: {cmd!r}", flush=True)

        # STATE answered immediately - no queue needed
        if cmd.strip().upper() == "STATE":
            conn.sendall((get_state() + "\n").encode())
            return

        # START sets the event immediately
        if cmd.strip().upper() == "START":
            start_event.set()
            conn.sendall(b"ok\n")
            return

        # All other commands go through the queue for serialised UART access
        result_q: queue.Queue = queue.Queue(maxsize=1)
        cmd_queue.put({"cmd": cmd, "result": result_q})

        try:
            result = result_q.get(timeout=35)
        except queue.Empty:
            result = "ERROR: timeout waiting for machine"

        conn.sendall((result + "\n").encode())

    except Exception as exc:
        try:
            conn.sendall(f"ERROR: {exc}\n".encode())
        except Exception:
            pass
    finally:
        conn.close()


def _ipc_server(machine: MachineAPI):
    if os.path.exists(IPC_SOCKET_PATH):
        os.unlink(IPC_SOCKET_PATH)

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(IPC_SOCKET_PATH)
    srv.listen(8)
    os.chmod(IPC_SOCKET_PATH, 0o660)
    print(f"[IPC] Listening on {IPC_SOCKET_PATH}", flush=True)

    while True:
        try:
            conn, _ = srv.accept()
            threading.Thread(
                target=_ipc_handle,
                args=(conn, machine),
                daemon=True,
            ).start()
        except Exception as exc:
            print(f"[IPC] accept error: {exc}", flush=True)
            time.sleep(0.5)


# ---------------------------------------------------------------------------
# Button handler (runs only when button serial port is available)
# ---------------------------------------------------------------------------

def _button_handler():
    """
    Attempts to open the button serial port. If unavailable, exits silently.
    When connected, forwards button presses as START events and mirrors
    the LED state from IPC messages.
    """
    try:
        ser = serial.Serial(BUTTON_PORT, BUTTON_BAUDRATE,
                            timeout=0.2, dsrdtr=True)
        time.sleep(2)
        ser.reset_input_buffer()
        print("[Button] Connected", flush=True)
        set_state_led(ser, False)
    except Exception as exc:
        print(f"[Button] Not available: {exc}", flush=True)
        return

    while True:
        try:
            line = ser.readline().decode().strip()
            if line == "BTN":
                print("[Button] Press received", flush=True)
                start_event.set()
            elif line:
                print(f"[Button] {line}", flush=True)
        except Exception as exc:
            print(f"[Button] Error: {exc}", flush=True)
            break

    print("[Button] Disconnected", flush=True)


def set_state_led(ser, on: bool):
    try:
        ser.write(b"LED_ON\n" if on else b"LED_OFF\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Idle loop - drains command queue while waiting for START
# ---------------------------------------------------------------------------

def wait_for_start(machine: MachineAPI):
    """
    Block until a START trigger arrives, executing any queued commands
    in the meantime.
    """
    set_state("IDLE")
    print("Waiting for start trigger...", flush=True)

    while True:
        # Drain command queue
        try:
            item   = cmd_queue.get_nowait()
            cmd    = item["cmd"]
            set_state(f"executing: {cmd}")
            result = execute_command(machine, cmd)
            item["result"].put(result)
            set_state("IDLE")
        except queue.Empty:
            pass

        if start_event.is_set():
            start_event.clear()
            return

        time.sleep(0.05)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Connecting to machine...", flush=True)
    machine = MachineAPI()
    print("Connected.", flush=True)

    # Start IPC server
    threading.Thread(
        target=_ipc_server,
        args=(machine,),
        daemon=True,
    ).start()

    # Start button handler (optional - exits gracefully if not connected)
    threading.Thread(target=_button_handler, daemon=True).start()

    # Initial home
    homed, x, y, z = machine.get_position()
    if not homed:
        wait_for_start(machine)
        home(machine)
    elif (x != SCAN_X_START) or (y != SCAN_Y_START) or (z != Z_BED_DOWN):
        wait_for_start(machine)
        home(machine)
    else:
        set_state("IDLE")

    # Main loop
    while True:
        wait_for_start(machine)
        # Sequence is driven by the Flask coordinator via IPC from here.
        # The launcher just executes commands as they arrive.
        # wait_for_start returns immediately when START fires, then we
        # loop back to draining the command queue.


if __name__ == "__main__":
    main()
