from __future__ import annotations

import subprocess
import sys

from images_to_pptx.resources import icon_png_path


def notify(title: str, message: str) -> None:
    try:
        if sys.platform == "win32":
            _notify_windows(title, message)
        else:
            _notify_linux(title, message)
    except Exception:
        return


def _notify_linux(title: str, message: str) -> None:
    cmd = ["notify-send", "-a", "Images to PPTX", title, message]
    icon = icon_png_path()
    if icon.is_file():
        cmd[2:2] = ["-i", str(icon)]
    subprocess.run(cmd, check=False, timeout=5, capture_output=True)


def _notify_windows(title: str, message: str) -> None:
    ps = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null;"
        "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
        "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
        "$text = $template.GetElementsByTagName('text');"
        f"$text.Item(0).AppendChild($template.CreateTextNode({_ps_quote(title)})) > $null;"
        f"$text.Item(1).AppendChild($template.CreateTextNode({_ps_quote(message)})) > $null;"
        "$toast = [Windows.UI.Notifications.ToastNotification]::new($template);"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Images to PPTX').Show($toast);"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        check=False,
        timeout=10,
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
