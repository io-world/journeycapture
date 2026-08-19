from __future__ import annotations

import threading
import time
from typing import Literal

from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button, Controller as MouseController

_mouse = MouseController()
_keyboard = KeyboardController()
_lock = threading.Lock()

_BUTTONS = {
    "left": Button.left,
    "right": Button.right,
    "middle": Button.middle,
}


def move_mouse(x: int, y: int, relative: bool = False) -> tuple[int, int]:
    with _lock:
        if relative:
            _mouse.move(x, y)
        else:
            _mouse.position = (x, y)
        pos = _mouse.position
    return int(pos[0]), int(pos[1])


def click_mouse(
    button: Literal["left", "right", "middle"] = "left",
    action: Literal["click", "down", "up"] = "click",
    clicks: int = 1,
    x: int | None = None,
    y: int | None = None,
) -> None:
    with _lock:
        if x is not None and y is not None:
            _mouse.position = (x, y)
        btn = _BUTTONS[button]
        if action == "click":
            _mouse.click(btn, clicks)
        elif action == "down":
            _mouse.press(btn)
        elif action == "up":
            _mouse.release(btn)


def scroll_mouse(dx: int = 0, dy: int = 0) -> None:
    with _lock:
        _mouse.scroll(dx, dy)


def type_text(text: str, interval: float = 0.01) -> int:
    with _lock:
        for char in text:
            _keyboard.type(char)
            time.sleep(interval)
    return len(text)


def _resolve_key(name: str) -> Key | KeyCode:
    special = getattr(Key, name, None)
    if isinstance(special, Key):
        return special
    if len(name) == 1:
        return KeyCode.from_char(name)
    raise ValueError(f"unknown key: {name!r}")


def send_keys(keys: list[str], action: Literal["press", "release", "tap"] = "tap") -> None:
    resolved = [_resolve_key(k) for k in keys]
    with _lock:
        if action == "press":
            for key in resolved:
                _keyboard.press(key)
        elif action == "release":
            for key in resolved:
                _keyboard.release(key)
        elif action == "tap":
            for key in resolved:
                _keyboard.press(key)
            for key in reversed(resolved):
                _keyboard.release(key)
