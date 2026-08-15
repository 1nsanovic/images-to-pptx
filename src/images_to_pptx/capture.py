from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import mss
from PIL import Image, ImageGrab, ImageTk

from images_to_pptx.config import Region
from images_to_pptx.slides import next_slide_number


def grab_image(region: Region | None = None) -> Image.Image:
    image = _grab_full()
    if region is None:
        return image
    left = max(0, int(region["left"]))
    top = max(0, int(region["top"]))
    right = min(image.width, left + int(region["width"]))
    bottom = min(image.height, top + int(region["height"]))
    if right - left < 10 or bottom - top < 10:
        raise RuntimeError("Область скриншота вне кадра")
    return image.crop((left, top, right, bottom))


def save_slide(directory: Path, image: Image.Image) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"slide-{next_slide_number(directory)}.png"
    image.save(path, format="PNG")
    return path


def select_region(parent: tk.Misc) -> Region | None:
    was_mapped = bool(parent.winfo_ismapped())
    if was_mapped:
        parent.withdraw()
        parent.update()
        time.sleep(0.25)
    try:
        screenshot = _grab_full()
        origin_left, origin_top = _screen_origin()
        return _overlay_select(parent, screenshot, origin_left, origin_top)
    finally:
        if was_mapped:
            parent.deiconify()
            parent.lift()
            parent.focus_force()


def _grab_full() -> Image.Image:
    errors: list[str] = []
    for name, grabber in _grabbers():
        try:
            image = grabber()
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            continue
        if image is not None and not _is_nearly_black(image):
            return image
        errors.append(f"{name}: чёрный кадр")
    detail = "; ".join(errors) if errors else "нет доступных способов"
    raise RuntimeError(f"Не удалось сделать скриншот ({detail})")


def _grabbers() -> list[tuple[str, Callable[[], Image.Image]]]:
    wayland = _is_wayland()
    grabbers: list[tuple[str, object]] = []
    if sys.platform == "win32":
        grabbers.append(("mss", _grab_mss))
        grabbers.append(("imagegrab", _grab_imagegrab))
        return grabbers
    if wayland:
        grabbers.append(("portal", _grab_portal))
        grabbers.append(("grim", _grab_grim))
        grabbers.append(("gnome-screenshot", _grab_gnome_screenshot))
        grabbers.append(("mss", _grab_mss))
        grabbers.append(("imagegrab", _grab_imagegrab))
        return grabbers
    grabbers.append(("mss", _grab_mss))
    grabbers.append(("imagegrab", _grab_imagegrab))
    grabbers.append(("portal", _grab_portal))
    grabbers.append(("grim", _grab_grim))
    grabbers.append(("gnome-screenshot", _grab_gnome_screenshot))
    return grabbers


def _is_wayland() -> bool:
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    return session == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))


def _is_nearly_black(image: Image.Image) -> bool:
    sample = image.convert("L").resize((64, 64))
    pixels = list(sample.getdata())
    return max(pixels) <= 12 and (sum(pixels) / len(pixels)) <= 6


def _screen_origin() -> tuple[int, int]:
    try:
        with mss.mss() as sct:
            mon = sct.monitors[0]
            return int(mon["left"]), int(mon["top"])
    except Exception:
        return 0, 0


def _grab_mss() -> Image.Image:
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[0])
    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def _grab_imagegrab() -> Image.Image:
    try:
        image = ImageGrab.grab(all_screens=True)
    except TypeError:
        image = ImageGrab.grab()
    return image.convert("RGB")


def _grab_portal() -> Image.Image:
    from images_to_pptx.linux_portal import portal_screenshot

    path = Path(portal_screenshot())
    return _load_image(path, delete=True)


def _grab_grim() -> Image.Image:
    path = _temp_png()
    try:
        subprocess.run(["grim", str(path)], check=True, timeout=15, capture_output=True)
        return _load_image(path, delete=True)
    finally:
        path.unlink(missing_ok=True)


def _grab_gnome_screenshot() -> Image.Image:
    path = _temp_png()
    try:
        subprocess.run(
            ["gnome-screenshot", "-f", str(path)],
            check=True,
            timeout=20,
            capture_output=True,
        )
        return _load_image(path, delete=True)
    finally:
        path.unlink(missing_ok=True)


def _temp_png() -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    handle.close()
    return Path(handle.name)


def _load_image(path: Path, delete: bool = False) -> Image.Image:
    with Image.open(path) as image:
        converted = image.convert("RGB")
        converted.load()
    if delete:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    return converted


def _overlay_select(
    parent: tk.Misc, screenshot: Image.Image, origin_left: int, origin_top: int
) -> Region | None:
    overlay = tk.Toplevel(parent)
    overlay.overrideredirect(True)
    overlay.attributes("-topmost", True)
    overlay.geometry(
        f"{screenshot.width}x{screenshot.height}+{origin_left}+{origin_top}"
    )
    canvas = tk.Canvas(
        overlay,
        width=screenshot.width,
        height=screenshot.height,
        highlightthickness=0,
        cursor="crosshair",
        bg="black",
    )
    canvas.pack(fill="both", expand=True)
    photo = ImageTk.PhotoImage(screenshot)
    canvas.create_image(0, 0, image=photo, anchor="nw")
    canvas.image = photo
    canvas.create_text(
        screenshot.width // 2,
        36,
        text="Выделите область. Esc или ПКМ — отмена",
        fill="white",
        font=("Helvetica", 16),
    )
    state: dict[str, object] = {"start": None, "rect": None, "result": None}

    def _to_image(x: int, y: int) -> tuple[int, int]:
        cw = max(canvas.winfo_width(), 1)
        ch = max(canvas.winfo_height(), 1)
        ix = int(x * screenshot.width / cw)
        iy = int(y * screenshot.height / ch)
        return max(0, min(screenshot.width, ix)), max(0, min(screenshot.height, iy))

    def on_press(event: tk.Event) -> None:
        state["start"] = (event.x, event.y)

    def on_move(event: tk.Event) -> None:
        start = state["start"]
        if start is None:
            return
        if state["rect"] is not None:
            canvas.delete(state["rect"])
        x0, y0 = start
        state["rect"] = canvas.create_rectangle(
            x0, y0, event.x, event.y, outline="#00bfff", width=2
        )

    def on_release(event: tk.Event) -> None:
        start = state["start"]
        if start is None:
            overlay.destroy()
            return
        x0, y0 = start
        left, top = _to_image(min(x0, event.x), min(y0, event.y))
        right, bottom = _to_image(max(x0, event.x), max(y0, event.y))
        width = right - left
        height = bottom - top
        if width >= 10 and height >= 10:
            state["result"] = {
                "left": left,
                "top": top,
                "width": width,
                "height": height,
            }
        overlay.destroy()

    def cancel(_: tk.Event | None = None) -> None:
        overlay.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_move)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<ButtonPress-3>", cancel)
    overlay.bind("<Escape>", cancel)
    canvas.bind("<Escape>", cancel)
    overlay.grab_set()
    overlay.focus_force()
    canvas.focus_set()
    overlay.wait_window()
    return state["result"] if isinstance(state["result"], dict) else None
