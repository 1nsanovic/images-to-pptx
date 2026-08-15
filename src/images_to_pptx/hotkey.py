from __future__ import annotations

from dataclasses import dataclass

MODIFIER_KEYSYMS = {
    "Control_L",
    "Control_R",
    "Alt_L",
    "Alt_R",
    "Shift_L",
    "Shift_R",
    "Super_L",
    "Super_R",
    "Meta_L",
    "Meta_R",
    "ISO_Level3_Shift",
    "Caps_Lock",
    "Num_Lock",
}

_PYNPUT_KEYS = {
    "Print": "<print_screen>",
    "Sys_Req": "<print_screen>",
    "Return": "<enter>",
    "KP_Enter": "<enter>",
    "Escape": "<esc>",
    "space": "<space>",
    "Tab": "<tab>",
    "BackSpace": "<backspace>",
    "Delete": "<delete>",
    "Insert": "<insert>",
    "Home": "<home>",
    "End": "<end>",
    "Prior": "<page_up>",
    "Page_Up": "<page_up>",
    "Next": "<page_down>",
    "Page_Down": "<page_down>",
    "Left": "<left>",
    "Right": "<right>",
    "Up": "<up>",
    "Down": "<down>",
}

_GNOME_KEYS = {
    "Print": "Print",
    "Sys_Req": "Print",
    "Return": "Return",
    "space": "space",
    "Prior": "Page_Up",
    "Next": "Page_Down",
}


@dataclass(frozen=True)
class Hotkey:
    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    super: bool = False

    def label(self) -> str:
        parts: list[str] = []
        if self.ctrl:
            parts.append("Ctrl")
        if self.alt:
            parts.append("Alt")
        if self.shift:
            parts.append("Shift")
        if self.super:
            parts.append("Super")
        parts.append(_display_key(self.key))
        return "+".join(parts)

    def pynput_spec(self) -> str:
        parts: list[str] = []
        if self.ctrl:
            parts.append("<ctrl>")
        if self.alt:
            parts.append("<alt>")
        if self.shift:
            parts.append("<shift>")
        if self.super:
            parts.append("<cmd>")
        parts.append(_pynput_key(self.key))
        return "+".join(parts)

    def gnome_binding(self) -> str:
        mods = ""
        if self.ctrl:
            mods += "<Control>"
        if self.alt:
            mods += "<Alt>"
        if self.shift:
            mods += "<Shift>"
        if self.super:
            mods += "<Super>"
        return f"{mods}{_gnome_key(self.key)}"

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "ctrl": self.ctrl,
            "alt": self.alt,
            "shift": self.shift,
            "super": self.super,
        }

    @classmethod
    def from_dict(cls, raw: object) -> Hotkey:
        if isinstance(raw, str):
            return cls.from_label(raw)
        if not isinstance(raw, dict):
            return default_hotkey()
        key = str(raw.get("key") or "F9")
        if not key or key in MODIFIER_KEYSYMS:
            return default_hotkey()
        return cls(
            key=key,
            ctrl=bool(raw.get("ctrl")),
            alt=bool(raw.get("alt")),
            shift=bool(raw.get("shift")),
            super=bool(raw.get("super")),
        )

    @classmethod
    def from_label(cls, label: str) -> Hotkey:
        parts = [part.strip() for part in label.split("+") if part.strip()]
        if not parts:
            return default_hotkey()
        flags = {part.lower() for part in parts[:-1]}
        return cls(
            key=parts[-1],
            ctrl="ctrl" in flags or "control" in flags,
            alt="alt" in flags,
            shift="shift" in flags,
            super="super" in flags or "win" in flags or "cmd" in flags,
        )

    @classmethod
    def from_tk_event(cls, event: object) -> Hotkey | None:
        keysym = str(getattr(event, "keysym", ""))
        if not keysym or keysym in MODIFIER_KEYSYMS:
            return None
        state = int(getattr(event, "state", 0))
        return cls(
            key=_canonical_key(keysym),
            ctrl=bool(state & 0x4),
            alt=bool(state & 0x8),
            shift=bool(state & 0x1),
            super=bool(state & 0x40),
        )


def default_hotkey() -> Hotkey:
    return Hotkey(key="F9")


def _canonical_key(keysym: str) -> str:
    if len(keysym) == 1:
        return keysym.lower()
    return _GNOME_KEYS.get(keysym, keysym)


def _display_key(key: str) -> str:
    if len(key) == 1:
        return key.upper()
    return key.replace("_", " ")


def _pynput_key(key: str) -> str:
    if key in _PYNPUT_KEYS:
        return _PYNPUT_KEYS[key]
    if key.startswith("F") and key[1:].isdigit():
        return f"<{key.lower()}>"
    if len(key) == 1:
        return key.lower()
    return f"<{key.lower()}>"


def _gnome_key(key: str) -> str:
    if key in _GNOME_KEYS:
        return _GNOME_KEYS[key]
    if len(key) == 1:
        return key.lower()
    return key
