"""
VisionGrabber Button Handler
============================
Runs as a separate process, started/stopped by udev when the button
controller is plugged in or unplugged.

Responsibilities:
  - Opens the button serial port
  - Polls Flask API for sequence state every POLL_INTERVAL seconds
  - Lights LED when state is 'ready' or 'awaiting_operator'
  - On button press: sends START or RESET to Flask depending on state
  - Notifies Flask of connection/disconnection for health indicator

Run:
    python -m machine.button_handler

udev rule should start this on plug and kill it on unplug.
"""

import signal
import sys
import time

import requests
import serial

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# Import from config relative to backend/ root
sys.path.insert(0, __file__.rsplit("/machine", 1)[0])
from config import BUTTON_PORT, BUTTON_BAUDRATE, FLASK_URL

POLL_INTERVAL   = 0.5    # seconds between state polls
CONNECT_TIMEOUT = 3.0    # seconds for HTTP requests
RECONNECT_DELAY = 2.0    # seconds before retrying serial open

LED_STATES = {"ready", "awaiting_operator"}


# ---------------------------------------------------------------------------
# Flask API helpers
# ---------------------------------------------------------------------------

def api_get(path: str) -> dict | None:
    try:
        r = requests.get(f"{FLASK_URL}{path}", timeout=CONNECT_TIMEOUT)
        return r.json()
    except Exception:
        return None


def api_post(path: str, body: dict = None) -> dict | None:
    try:
        r = requests.post(f"{FLASK_URL}{path}",
                          json=body or {},
                          timeout=CONNECT_TIMEOUT)
        return r.json()
    except Exception:
        return None


def get_sequence_state() -> str | None:
    data = api_get("/api/sequence/state")
    if data:
        return data.get("state")
    return None


def notify_connected():
    """Notify Flask the button is connected - retries until Flask is available."""
    for _ in range(20):  # retry for up to 20 seconds
        try:
            r = requests.post(f"{FLASK_URL}/api/button/connected",
                              timeout=CONNECT_TIMEOUT)
            if r.ok:
                print("[Button] Notified Flask: connected", flush=True)
                return
        except Exception:
            pass
        time.sleep(1)
    print("[Button] Could not notify Flask of connection", flush=True)


def notify_disconnected():
    try:
        requests.post(f"{FLASK_URL}/api/button/disconnected",
                      timeout=CONNECT_TIMEOUT)
        print("[Button] Notified Flask: disconnected", flush=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def set_led(ser: serial.Serial, on: bool):
    try:
        ser.write(b"LED_ON\n" if on else b"LED_OFF\n")
    except Exception:
        pass


def handle_button_press(state: str):
    """Send the appropriate command to Flask based on current sequence state."""
    if state == "ready":
        print("[Button] Press → START", flush=True)
        api_post("/api/sequence/start")
    elif state == "awaiting_operator":
        print("[Button] Press → RESET", flush=True)
        api_post("/api/sequence/operator", {"action": "reset"})
    else:
        print(f"[Button] Press ignored (state={state})", flush=True)


def main():
    print(f"[Button] Opening {BUTTON_PORT} at {BUTTON_BAUDRATE}", flush=True)

    # Handle clean shutdown
    def _shutdown(signum, frame):
        print("[Button] Shutting down", flush=True)
        notify_disconnected()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT,  _shutdown)

    # Open serial port - retry until available
    ser = None
    while ser is None:
        try:
            ser = serial.Serial(BUTTON_PORT, BUTTON_BAUDRATE,
                                timeout=POLL_INTERVAL, dsrdtr=True)
            time.sleep(2)
            ser.reset_input_buffer()
            print("[Button] Serial port open", flush=True)
            # Notify Flask only after serial is confirmed open
            notify_connected()
        except Exception as exc:
            print(f"[Button] Could not open port: {exc} - retrying", flush=True)
            time.sleep(RECONNECT_DELAY)

    led_on = False
    set_led(ser, False)

    try:
        while True:
            # Poll sequence state
            state = get_sequence_state()

            # Update LED
            should_be_on = state in LED_STATES
            if should_be_on != led_on:
                set_led(ser, should_be_on)
                led_on = should_be_on
                print(f"[Button] LED {'ON' if led_on else 'OFF'} "
                      f"(state={state})", flush=True)

            # Check for button press (non-blocking - timeout set on Serial)
            try:
                line = ser.readline().decode(errors="replace").strip()
                if line == "BTN" and state:
                    handle_button_press(state)
                elif line:
                    print(f"[Button] Serial: {line!r}", flush=True)
            except Exception as exc:
                print(f"[Button] Serial read error: {exc}", flush=True)
                break

    finally:
        set_led(ser, False)
        try:
            ser.close()
        except Exception:
            pass
        notify_disconnected()
        print("[Button] Exited", flush=True)


if __name__ == "__main__":
    main()
