from __future__ import annotations

import threading
from collections.abc import Callable

import pystray
from PIL import Image
from pystray import Menu, MenuItem


class TrayIcon:
    def __init__(
        self,
        image: Image.Image,
        on_show: Callable[[], None],
        on_capture: Callable[[], None],
        on_export: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._icon = pystray.Icon(
            "images-to-pptx",
            image,
            "Images to PPTX",
            Menu(
                MenuItem("Показать", lambda: on_show(), default=True),
                MenuItem("Сделать снимок", lambda: on_capture()),
                MenuItem("Собрать презентацию", lambda: on_export()),
                Menu.SEPARATOR,
                MenuItem("Выход", lambda: on_quit()),
            ),
        )
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        try:
            self._icon.stop()
        except Exception:
            pass
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    def notify(self, title: str, message: str) -> None:
        self._icon.notify(message, title)
