"""
IPC client for VisionGrabber backend.

Communicates with the launcher process (VisionGrabberLauncher.service)
via a Unix domain socket at SOCKET_PATH.

Protocol:
    Client sends:   "<COMMAND>\n"
    Server replies: "<response>\n"

All commands are synchronous from the caller's perspective - send a command,
get a response. The launcher serialises all commands through its cmd_queue
so there is no concurrent access to the machine UART.
"""

import logging
import socket
import threading
from config import IPC_SOCKET_PATH, IPC_TIMEOUT

logger = logging.getLogger(__name__)


class IpcClient:
    """
    Thread-safe Unix socket client.

    Multiple threads (heartbeat poller, sequence coordinator, REST route
    handlers) may call send() concurrently. A lock ensures commands are
    serialised - the launcher handles one at a time anyway, but this
    prevents interleaved writes on the socket.
    """

    def __init__(self, socket_path: str = IPC_SOCKET_PATH, timeout: float = IPC_TIMEOUT):
        self._socket_path = socket_path
        self._timeout     = timeout
        self._lock        = threading.Lock()

    def send(self, cmd: str) -> str:
        """
        Send a command to the launcher and return the response.

        Returns an error string prefixed with "ERROR:" if the socket is
        unavailable or the command times out - never raises. Callers can
        check response.startswith("ERROR:") to detect failure.
        """
        with self._lock:
            return self._send(cmd)

    def is_available(self) -> bool:
        """
        Quick liveness check - attempt to connect to the socket.
        Does not send any command.
        """
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(self._socket_path)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send(self, cmd: str) -> str:
        """Send a single command and read one response line."""
        logger.debug(f"[IPC] >> {cmd!r}")
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(self._timeout)
                s.connect(self._socket_path)
                s.sendall((cmd.strip() + "\n").encode())

                # Read until newline
                resp = b""
                while b"\n" not in resp:
                    chunk = s.recv(256)
                    if not chunk:
                        break
                    resp += chunk

                result = resp.decode(errors="replace").strip()
                logger.debug(f"[IPC] << {result!r}")
                return result

        except FileNotFoundError:
            msg = "ERROR: socket not found - is VisionGrabberLauncher running?"
            logger.warning(f"[IPC] {msg}")
            return msg
        except ConnectionRefusedError:
            msg = "ERROR: connection refused - launcher not listening"
            logger.warning(f"[IPC] {msg}")
            return msg
        except socket.timeout:
            msg = f"ERROR: timeout after {self._timeout}s"
            logger.warning(f"[IPC] {msg}")
            return msg
        except Exception as exc:
            msg = f"ERROR: {exc}"
            logger.warning(f"[IPC] {msg}")
            return msg


# ---------------------------------------------------------------------------
# Singleton instance - import this everywhere
# ---------------------------------------------------------------------------
ipc_client = IpcClient()
