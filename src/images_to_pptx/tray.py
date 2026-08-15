from __future__ import annotations

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

    def start(self) -> None:
        self._icon.run_detached()

    def stop(self) -> None:
        self._icon.stop()

    def notify(self, title: str, message: str) -> None:
        self._icon.notify(message, title)
