from __future__ import annotations

import ast
import shlex
import subprocess
import sys

from images_to_pptx.hotkey import Hotkey

SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
BINDING_PATH = (
    "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/images-to-pptx/"
)


def capture_command() -> str:
    if getattr(sys, "frozen", False):
        return shlex.join([sys.executable, "--capture"])
    return shlex.join([sys.executable, "-m", "images_to_pptx", "--capture"])


def install_gnome_shortcut(hotkey: Hotkey) -> bool:
    try:
        raw = _gsettings("get", SCHEMA, "custom-keybindings")
        paths = _parse_paths(raw)
        if BINDING_PATH not in paths:
            paths.append(BINDING_PATH)
            _gsettings("set", SCHEMA, "custom-keybindings", _format_paths(paths))
        rel = CUSTOM_SCHEMA + ":" + BINDING_PATH
        _gsettings("set", rel, "name", _gvariant_string("Images to PPTX"))
        _gsettings("set", rel, "command", _gvariant_string(capture_command()))
        _gsettings("set", rel, "binding", _gvariant_string(hotkey.gnome_binding()))
        return True
    except (FileNotFoundError, OSError, subprocess.CalledProcessError, ValueError, SyntaxError):
        return False


def _gvariant_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _gsettings(*args: str) -> str:
    result = subprocess.run(
        ["gsettings", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.stdout.strip()


def _parse_paths(raw: str) -> list[str]:
    text = raw.strip()
    if text.startswith("@as"):
        text = text[3:].strip()
    parsed = ast.literal_eval(text)
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _format_paths(paths: list[str]) -> str:
    inner = ", ".join(f"'{path}'" for path in paths)
    return f"[{inner}]"
