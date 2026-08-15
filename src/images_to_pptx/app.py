from __future__ import annotations

import os
import signal
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import ImageTk

from images_to_pptx.capture import grab_image, save_slide, select_region
from images_to_pptx.config import Config
from images_to_pptx.gnome_shortcut import install_gnome_shortcut
from images_to_pptx.hotkey import Hotkey
from images_to_pptx.hotkeys import HotkeyListener
from images_to_pptx.ipc import CaptureIpc
from images_to_pptx.notify import notify as os_notify
from images_to_pptx.pptx_export import export_pptx
from images_to_pptx.resources import load_icon_image
from images_to_pptx.slides import list_slide_images
from images_to_pptx.tray import TrayIcon

SCALE_LABELS = ["100%", "125%", "150%", "175%", "200%"]


def _apply_ui_scale(scale: float) -> None:
    ctk.set_widget_scaling(scale)
    ctk.set_window_scaling(scale)


class App(ctk.CTk):
    def __init__(self) -> None:
        self.cfg = Config.load()
        _apply_ui_scale(self.cfg.ui_scale)
        super().__init__()
        self.title("Images to PPTX")
        self.geometry("560x560")
        self.minsize(500, 500)
        self._tray: TrayIcon | None = None
        self._hotkeys: HotkeyListener | None = None
        self._ipc: CaptureIpc | None = None
        self._quitting = False
        self._capturing = False
        self._recording_hotkey = False
        self._last_capture_at = 0.0
        self._build_ui()
        self._set_window_icon()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._start_background)
        self._refresh_count()
        self._refresh_region_label()

    def _build_ui(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="Images to PPTX", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )
        ctk.CTkLabel(frame, text="Папка сохранения").grid(row=1, column=0, columnspan=2, sticky="w")
        self._dir_var = ctk.StringVar(value=str(self.cfg.save_dir))
        ctk.CTkEntry(frame, textvariable=self._dir_var).grid(
            row=2, column=0, sticky="ew", padx=(0, 8), pady=(0, 8)
        )
        ctk.CTkButton(frame, text="Обзор", width=110, command=self._choose_dir).grid(
            row=2, column=1, pady=(0, 8)
        )
        self._count_label = ctk.CTkLabel(frame, text="Снимков: 0")
        self._count_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self._region_label = ctk.CTkLabel(frame, text="")
        self._region_label.grid(row=4, column=0, columnspan=2, sticky="w")
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ctk.CTkButton(btns, text="Выбрать область", command=self._choose_region).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(btns, text="Сбросить область", command=self._reset_region).pack(side="left")
        ctk.CTkLabel(frame, text="Масштаб интерфейса").grid(
            row=6, column=0, columnspan=2, sticky="w"
        )
        self._scale_menu = ctk.CTkOptionMenu(
            frame,
            values=SCALE_LABELS,
            command=self._change_ui_scale,
            width=110,
        )
        self._scale_menu.set(f"{int(self.cfg.ui_scale * 100)}%")
        self._scale_menu.grid(row=7, column=0, sticky="w", pady=(0, 12))
        ctk.CTkLabel(frame, text="Горячая клавиша").grid(row=8, column=0, sticky="w")
        self._hotkey_value = ctk.CTkLabel(frame, text=self.cfg.hotkey.label())
        self._hotkey_value.grid(row=9, column=0, sticky="w", pady=(0, 8))
        self._hotkey_btn = ctk.CTkButton(
            frame, text="Изменить", width=110, command=self._start_record_hotkey
        )
        self._hotkey_btn.grid(row=9, column=1, pady=(0, 8))
        ctk.CTkButton(frame, text="Сделать снимок", command=self.capture_slide).grid(
            row=10, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )
        ctk.CTkButton(frame, text="Собрать презентацию", command=self.export_presentation).grid(
            row=11, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )
        ctk.CTkButton(frame, text="Выход", fg_color="gray", command=self.quit_app).grid(
            row=12, column=0, columnspan=2, sticky="ew"
        )
        self._status = ctk.CTkLabel(frame, text="", text_color="gray")
        self._status.grid(row=13, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _set_window_icon(self) -> None:
        try:
            icon = load_icon_image()
            photo = ImageTk.PhotoImage(icon)
            self.iconphoto(True, photo)
            self._icon_photo = photo
        except OSError:
            self._icon_photo = None

    def _start_background(self) -> None:
        try:
            icon = load_icon_image()
            self._tray = TrayIcon(
                icon,
                on_show=lambda: self.after(0, self.show_window),
                on_capture=lambda: self.after(0, self.capture_slide),
                on_export=lambda: self.after(0, self.export_presentation),
                on_quit=lambda: self.after(0, self.quit_app),
            )
            self._tray.start()
        except Exception:
            self._tray = None
            self._set_status("Трей недоступен, закрытие окна завершит программу")
        try:
            self._ipc = CaptureIpc(lambda: self.after(0, self.capture_slide))
            self._ipc.start()
        except Exception:
            self._ipc = None
        self._apply_hotkey(self.cfg.hotkey, persist=False)

    def _choose_dir(self) -> None:
        chosen = filedialog.askdirectory(
            title="Папка для слайдов",
            initialdir=str(self.cfg.save_dir) if self.cfg.save_dir.exists() else str(Path.home()),
        )
        if not chosen:
            return
        self.cfg.save_dir = Path(chosen)
        self._dir_var.set(chosen)
        self.cfg.save()
        self._refresh_count()

    def _sync_save_dir(self) -> Path:
        raw = self._dir_var.get().strip()
        path = Path(raw).expanduser() if raw else self.cfg.save_dir
        self.cfg.save_dir = path
        self.cfg.save()
        return path

    def _choose_region(self) -> None:
        region = select_region(self)
        if region is None:
            self._set_status("Выбор области отменён")
            return
        self.cfg.region = region
        self.cfg.save()
        self._refresh_region_label()
        self._set_status("Область сохранена")

    def _reset_region(self) -> None:
        self.cfg.region = None
        self.cfg.save()
        self._refresh_region_label()
        self._set_status("Область сброшена, снимается весь экран")

    def _change_ui_scale(self, value: str) -> None:
        scale = int(value.rstrip("%")) / 100
        self.cfg.ui_scale = scale
        self.cfg.save()
        _apply_ui_scale(scale)
        self._set_status(f"Масштаб: {value}")

    def _start_record_hotkey(self) -> None:
        if self._recording_hotkey:
            self._stop_record_hotkey()
            self._refresh_hotkey_label()
            self._set_status("Смена клавиши отменена")
            return
        self._recording_hotkey = True
        self._hotkey_btn.configure(text="Отмена")
        self._hotkey_value.configure(text="Нажмите клавишу…")
        self.bind("<KeyPress>", self._on_record_key)
        self.grab_set()
        self.focus_force()

    def _stop_record_hotkey(self) -> None:
        self._recording_hotkey = False
        self.unbind("<KeyPress>")
        try:
            self.grab_release()
        except Exception:
            pass
        self._hotkey_btn.configure(text="Изменить")

    def _on_record_key(self, event: object) -> str:
        keysym = str(getattr(event, "keysym", ""))
        if keysym == "Escape":
            self._stop_record_hotkey()
            self._refresh_hotkey_label()
            self._set_status("Смена клавиши отменена")
            return "break"
        hotkey = Hotkey.from_tk_event(event)
        if hotkey is None:
            return "break"
        self._stop_record_hotkey()
        self._apply_hotkey(hotkey, persist=True)
        return "break"

    def _apply_hotkey(self, hotkey: Hotkey, persist: bool) -> None:
        self.cfg.hotkey = hotkey
        if persist:
            self.cfg.save()
        gnome_ok = False
        if sys.platform != "win32":
            gnome_ok = install_gnome_shortcut(hotkey)
        if self._hotkeys is not None:
            try:
                self._hotkeys.stop()
            except Exception:
                pass
            self._hotkeys = None
        try:
            listener = HotkeyListener(hotkey, lambda: self.after(0, self.capture_slide))
            listener.start()
            self._hotkeys = listener
        except Exception:
            self._hotkeys = None
        self._refresh_hotkey_label()
        if persist:
            self._set_status(f"Горячая клавиша: {hotkey.label()}")
        elif not gnome_ok and self._hotkeys is None:
            self._set_status("Горячая клавиша недоступна. Задайте её или используйте кнопку")

    def _refresh_hotkey_label(self) -> None:
        self._hotkey_value.configure(text=self.cfg.hotkey.label())

    def _refresh_region_label(self) -> None:
        region = self.cfg.region
        if region is None:
            text = "Область: весь экран"
        else:
            text = (
                f"Область: {region['width']}×{region['height']} "
                f"@ ({region['left']}, {region['top']})"
            )
        self._region_label.configure(text=text)

    def _refresh_count(self) -> None:
        count = len(list_slide_images(self.cfg.save_dir))
        self._count_label.configure(text=f"Снимков: {count}")

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _notify_saved(self, path: Path) -> None:
        os_notify("Images to PPTX", f"Сохранено: {path.name}")

    def capture_slide(self) -> None:
        if self._capturing:
            return
        now = time.monotonic()
        if now - self._last_capture_at < 1.0:
            return
        self._last_capture_at = now
        self._capturing = True
        try:
            if self.winfo_ismapped():
                self.withdraw()
                self.update()
                time.sleep(0.2)
            image = grab_image(self.cfg.region)
            path = save_slide(self._sync_save_dir(), image)
            self._refresh_count()
            self._set_status(f"Сохранено: {path.name}")
            self._notify_saved(path)
        except Exception as exc:
            if self._tray is None:
                self.show_window()
                messagebox.showerror("Ошибка снимка", str(exc))
            else:
                os_notify("Images to PPTX", f"Ошибка снимка: {exc}")
        finally:
            self._capturing = False

    def export_presentation(self) -> None:
        directory = self._sync_save_dir()
        images = list_slide_images(directory)
        if not images:
            messagebox.showwarning("Нет слайдов", "В папке нет файлов slide-N.png")
            self.show_window()
            return
        self.show_window()
        output = filedialog.asksaveasfilename(
            title="Сохранить презентацию",
            defaultextension=".pptx",
            filetypes=[("PowerPoint", "*.pptx")],
            initialfile="slides.pptx",
            initialdir=str(directory),
        )
        if not output:
            return
        try:
            count = export_pptx(directory, Path(output))
        except Exception as exc:
            messagebox.showerror("Ошибка сборки", str(exc))
            return
        self._set_status(f"Сохранено: {output}")
        messagebox.showinfo("Готово", f"Презентация из {count} слайдов сохранена")

    def show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_close(self) -> None:
        if self._tray is None:
            self.quit_app()
            return
        self.withdraw()
        self._set_status("Свёрнуто в трей")

    def quit_app(self) -> None:
        if self._quitting:
            return
        self._quitting = True

        def _stop_background() -> None:
            if self._hotkeys is not None:
                try:
                    self._hotkeys.stop()
                except Exception:
                    pass
                self._hotkeys = None
            if self._ipc is not None:
                try:
                    self._ipc.stop()
                except Exception:
                    pass
                self._ipc = None
            if self._tray is not None:
                try:
                    self._tray.stop()
                except Exception:
                    pass
                self._tray = None

        worker = threading.Thread(target=_stop_background, daemon=True)
        worker.start()
        worker.join(timeout=2.0)
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)


def _enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def run() -> None:
    _enable_dpi_awareness()
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    app = App()

    def _on_signal(_signum: int, _frame: object) -> None:
        app.after(0, app.quit_app)

    try:
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
    except ValueError:
        pass
    app.mainloop()
