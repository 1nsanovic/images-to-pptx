from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "images_to_pptx" / "assets"
    return Path(__file__).resolve().parent / "assets"


def icon_png_path() -> Path:
    return assets_dir() / "icon.png"


def load_icon_image() -> Image.Image:
    return Image.open(icon_png_path()).convert("RGBA")
