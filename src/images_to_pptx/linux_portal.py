from __future__ import annotations

import os
import subprocess
from urllib.parse import unquote, urlparse

from jeepney import DBusAddress, MatchRule, new_method_call
from jeepney.bus_messages import message_bus
from jeepney.io.blocking import open_dbus_connection
from jeepney.wrappers import unwrap_msg


def _unique_to_path_element(unique_name: str) -> str:
    return unique_name[1:].replace(".", "_")


def ensure_host_screenshot_permission() -> None:
    try:
        subprocess.run(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.freedesktop.impl.portal.PermissionStore",
                "--object-path",
                "/org/freedesktop/impl/portal/PermissionStore",
                "--method",
                "org.freedesktop.impl.portal.PermissionStore.SetPermission",
                "screenshot",
                "true",
                "screenshot",
                "",
                "['yes']",
            ],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return


def portal_screenshot(timeout: float = 20.0) -> str:
    ensure_host_screenshot_permission()
    token = f"itp{os.getpid()}{os.urandom(4).hex()}"
    with open_dbus_connection() as conn:
        unique = conn.unique_name or ""
        request_path = (
            f"/org/freedesktop/portal/desktop/request/"
            f"{_unique_to_path_element(unique)}/{token}"
        )
        rule = MatchRule(
            type="signal",
            interface="org.freedesktop.portal.Request",
            member="Response",
            path=request_path,
        )
        conn.send_and_get_reply(message_bus.AddMatch(rule), timeout=5)
        portal = DBusAddress(
            "/org/freedesktop/portal/desktop",
            bus_name="org.freedesktop.portal.Desktop",
            interface="org.freedesktop.portal.Screenshot",
        )
        call = new_method_call(
            portal,
            "Screenshot",
            "sa{sv}",
            (
                "",
                {
                    "handle_token": ("s", token),
                    "interactive": ("b", False),
                    "modal": ("b", False),
                },
            ),
        )
        with conn.filter(rule, bufsize=8) as matches:
            unwrap_msg(conn.send_and_get_reply(call, timeout=timeout))
            signal = conn.recv_until_filtered(matches, timeout=timeout)
        status, results = (_unwrap(part) for part in signal.body)
        if int(status) != 0:
            raise RuntimeError(f"Портал скриншота вернул статус {status}")
        if not isinstance(results, dict):
            raise RuntimeError("Портал скриншота вернул неожиданный ответ")
        uri = results.get("uri")
        if not uri:
            raise RuntimeError("Портал скриншота не вернул файл")
        return _uri_to_path(str(uri))


def _unwrap(value: object) -> object:
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        return _unwrap(value[1])
    if isinstance(value, dict):
        return {str(key): _unwrap(item) for key, item in value.items()}
    return value


def _uri_to_path(uri: str) -> str:
    if uri.startswith("file://"):
        return unquote(urlparse(uri).path)
    if uri.startswith("file:"):
        return unquote(uri[5:])
    return unquote(uri)
