from __future__ import annotations

import os
import socket
import sys
import threading
from collections.abc import Callable
from pathlib import Path


def ipc_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        folder = base / "images-to-pptx"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / "capture.sock"
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
    return runtime / "images-to-pptx.sock"


class CaptureIpc:
    def __init__(self, on_capture: Callable[[], None]) -> None:
        self._on_capture = on_capture
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        path = ipc_path()
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(path))
        sock.listen(4)
        sock.settimeout(0.5)
        self._sock = sock
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        try:
            ipc_path().unlink()
        except FileNotFoundError:
            pass

    def _loop(self) -> None:
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            with conn:
                try:
                    data = conn.recv(64).decode("utf-8", errors="ignore")
                except OSError:
                    continue
            if "capture" in data:
                self._on_capture()


def request_capture() -> bool:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(str(ipc_path()))
        sock.sendall(b"capture\n")
        sock.close()
        return True
    except OSError:
        return False
