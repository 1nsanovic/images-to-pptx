from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from images_to_pptx.hotkey import Hotkey, default_hotkey

Region = dict[str, int]
DEFAULT_UI_SCALE = 1.5
MIN_UI_SCALE = 1.0
MAX_UI_SCALE = 2.0


def config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "images-to-pptx" / "config.json"


def default_save_dir() -> Path:
    pictures = Path.home() / "Pictures"
    if pictures.is_dir():
        return pictures / "slides"
    return Path.home() / "slides"


def _parse_region(raw: object) -> Region | None:
    if not isinstance(raw, dict):
        return None
    try:
        region = {
            "left": int(raw["left"]),
            "top": int(raw["top"]),
            "width": int(raw["width"]),
            "height": int(raw["height"]),
        }
    except (KeyError, TypeError, ValueError):
        return None
    if region["width"] < 10 or region["height"] < 10:
        return None
    return region


def _parse_ui_scale(raw: object) -> float:
    try:
        scale = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_UI_SCALE
    scale = round(scale * 4) / 4
    return min(MAX_UI_SCALE, max(MIN_UI_SCALE, scale))


@dataclass
class Config:
    save_dir: Path
    region: Region | None = None
    ui_scale: float = DEFAULT_UI_SCALE
    hotkey: Hotkey = field(default_factory=default_hotkey)

    @classmethod
    def load(cls) -> Config:
        path = config_path()
        if not path.is_file():
            return cls(save_dir=default_save_dir())
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(save_dir=default_save_dir())
        save_dir = Path(data["save_dir"]) if data.get("save_dir") else default_save_dir()
        ui_scale = (
            _parse_ui_scale(data["ui_scale"])
            if "ui_scale" in data
            else DEFAULT_UI_SCALE
        )
        return cls(
            save_dir=save_dir,
            region=_parse_region(data.get("region")),
            ui_scale=ui_scale,
            hotkey=Hotkey.from_dict(data.get("hotkey")),
        )

    def save(self) -> None:
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "save_dir": str(self.save_dir),
            "region": self.region,
            "ui_scale": self.ui_scale,
            "hotkey": self.hotkey.to_dict(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
