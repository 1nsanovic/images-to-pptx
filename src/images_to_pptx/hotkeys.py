from __future__ import annotations

from collections.abc import Callable

from pynput.keyboard import GlobalHotKeys

from images_to_pptx.hotkey import Hotkey


class HotkeyListener:
    def __init__(self, hotkey: Hotkey, on_press: Callable[[], None]) -> None:
        self._hotkey = hotkey
        self._on_press = on_press
        self._listener: GlobalHotKeys | None = None

    def start(self) -> None:
        self.stop()
        self._listener = GlobalHotKeys({self._hotkey.pynput_spec(): self._on_press})
        self._listener.start()

    def stop(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None
