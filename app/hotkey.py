"""全局热键：键盘按键或鼠标侧键，支持 Ctrl/Alt/Shift/Win 组合。"""

from __future__ import annotations

import threading
from typing import Callable

from pynput import keyboard, mouse

MODS = {"ctrl", "alt", "shift", "win", "cmd"}

def _mod_keys() -> set:
    keys = set()
    for name in (
        "ctrl", "ctrl_l", "ctrl_r",
        "alt", "alt_l", "alt_r", "alt_gr",
        "shift", "shift_l", "shift_r",
        "cmd", "cmd_l", "cmd_r",
    ):
        key = getattr(keyboard.Key, name, None)
        if key is not None:
            keys.add(key)
    return keys


_MOD_KEYS = _mod_keys()

_KEY_ALIASES = {
    "esc": "esc",
    "escape": "esc",
    "return": "enter",
    "spacebar": "space",
    "control": "ctrl",
    "windows": "cmd",
    "win": "cmd",
    "meta": "cmd",
    "mouse4": "x1",
    "mouse5": "x2",
    "mouse_middle": "middle",
    "capslock": "caps_lock",
    "pagedown": "page_down",
    "pageup": "page_up",
}


def _normalize(token: str) -> str:
    token = token.strip().lower()
    return _KEY_ALIASES.get(token, token)


def _is_mod(key) -> bool:  # noqa: ANN001
    return key in _MOD_KEYS


def _key_name(key) -> str:  # noqa: ANN001
    if isinstance(key, keyboard.Key):
        return _normalize(key.name)
    if isinstance(key, keyboard.KeyCode):
        if key.char:
            return _normalize(key.char)
        if key.vk:
            return f"vk{key.vk}"
    return ""


def describe_key(key) -> str:  # noqa: ANN001
    name = _key_name(key)
    return name or "?"


def _char_vk(char: str) -> int | None:
    """字符对应的 Windows 虚拟键码（用于匹配真实按键事件）。"""
    try:
        import ctypes

        user32 = ctypes.WinDLL("user32")
        user32.VkKeyScanW.argtypes = (ctypes.c_wchar,)
        user32.VkKeyScanW.restype = ctypes.c_short
        scan = user32.VkKeyScanW(char)
        if scan == -1:
            return None
        return scan & 0xFF
    except Exception:
        return None


class HotkeyManager:
    def __init__(
        self,
        spec: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        self.on_press = on_press
        self.on_release = on_release
        self.spec = (spec or "").strip().lower()
        self._mods: set[str] = set()
        self._keyboard_listener: keyboard.Listener | None = None
        self._mouse_listener: mouse.Listener | None = None
        self._active = False
        self._pressed: set[str] = set()
        self._lock = threading.Lock()
        self._parse()

    # ---------- 解析快捷键 ----------
    def _parse(self) -> None:
        tokens = [t for t in self.spec.replace(" ", "").split("+") if t]
        self.is_mouse = False
        self.mouse_button = None
        self.main_char: str | None = None
        self.main_key = None
        self._main_vk: int | None = None
        self.modifiers: set[str] = set()
        if not tokens:
            tokens = ["f8"]
        main = _normalize(tokens[-1])
        for mod in tokens[:-1]:
            mod = _normalize(mod)
            if mod in MODS:
                self.modifiers.add("cmd" if mod == "win" else mod)
        if main in ("left", "right", "middle", "x1", "x2"):
            self.is_mouse = True
            self.mouse_button = {
                "left": mouse.Button.left,
                "right": mouse.Button.right,
                "middle": mouse.Button.middle,
                "x1": mouse.Button.x1,
                "x2": mouse.Button.x2,
            }[main]
        elif main.startswith("vk") and main[2:].isdigit():
            self.main_key = keyboard.KeyCode.from_vk(int(main[2:]))
        elif len(main) == 1:
            self.main_char = main
            self.main_key = keyboard.KeyCode.from_char(main)
            self._main_vk = _char_vk(main)
        else:
            if hasattr(keyboard.Key, main):
                self.main_key = getattr(keyboard.Key, main)
            elif len(main) == 2 and main.startswith("f") and main[1].isdigit():
                self.main_key = getattr(keyboard.Key, main, None)
            else:
                self.main_key = keyboard.KeyCode.from_char(main[:1] or "f8")
                self.main_char = main[:1] or "f8"

    def valid(self) -> bool:
        # 单独一个修饰键（ctrl/shift/alt）不能作为触发键
        if self.main_key is not None and self.main_key in _MOD_KEYS:
            return False
        return self.main_key is not None or self.is_mouse

    # ---------- 匹配 ----------
    def _matches(self, key) -> bool:  # noqa: ANN001
        if self.main_key is None:
            return False
        name = _key_name(key)
        if self.main_char:
            if name == self.main_char:
                return True
            # 真实按键上报的是虚拟键码，字符键需要按 vk 比对
            vk = getattr(key, "vk", None)
            return bool(vk and self._main_vk and vk == self._main_vk)
        return key == self.main_key or name == _key_name(self.main_key)

    def _fire_press(self) -> None:
        with self._lock:
            if self._active:
                return
            if not self.modifiers.issubset(self._mods):
                return
            self._active = True
        try:
            self.on_press()
        except Exception:
            pass

    def _fire_release(self) -> None:
        with self._lock:
            if not self._active:
                return
            self._active = False
        try:
            self.on_release()
        except Exception:
            pass

    # ---------- 监听 ----------
    def _kb_press(self, key) -> None:  # noqa: ANN001
        if _is_mod(key):
            with self._lock:
                self._mods.add(_normalize(key.name).split("_")[0])
            return
        if self._matches(key):
            self._fire_press()

    def _kb_release(self, key) -> None:  # noqa: ANN001
        if _is_mod(key):
            with self._lock:
                mod = _normalize(key.name).split("_")[0]
                self._mods.discard(mod)
            if self._active:
                self._fire_release()
            return
        if self._matches(key):
            self._fire_release()

    def _mouse_click(self, x, y, button, pressed) -> None:  # noqa: ANN001
        if not self.is_mouse or button != self.mouse_button:
            return
        if pressed:
            self._fire_press()
        else:
            self._fire_release()

    def start(self) -> None:
        if not self.valid():
            return
        self._keyboard_listener = keyboard.Listener(
            on_press=self._kb_press, on_release=self._kb_release
        )
        self._keyboard_listener.daemon = True
        self._keyboard_listener.start()
        if self.is_mouse:
            self._mouse_listener = mouse.Listener(on_click=self._mouse_click)
            self._mouse_listener.daemon = True
            self._mouse_listener.start()

    def stop(self) -> None:
        for listener in (self._keyboard_listener, self._mouse_listener):
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
        self._keyboard_listener = None
        self._mouse_listener = None


def capture_once(timeout: float = 30.0) -> str:
    """阻塞等待用户按下一个键/鼠标键，返回其名称（供界面“录制按键”用）。"""
    result: list[str] = []
    done = threading.Event()

    def finish(name: str) -> None:
        if not done.is_set():
            result.append(name)
            done.set()

    kbl = keyboard.Listener(
        on_press=lambda key: finish(describe_key(key))
        if not _is_mod(key)
        else None
    )
    msl = mouse.Listener(
        on_click=lambda x, y, b, pressed: finish(str(b).split(".")[-1]) if pressed else None
    )
    kbl.start()
    msl.start()
    done.wait(timeout)
    kbl.stop()
    msl.stop()
    name = result[0] if result else ""
    return "" if name in ("", "?") else name
