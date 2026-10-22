"""Windows 输入注入（SendInput）与窗口查询。

文字通过 KEYEVENTF_UNICODE 直接送入目标窗口，不依赖输入法，
因此中文、英文、符号都能原样打进游戏聊天框。

注意：这里显式声明了所有 Win32 函数的 argtypes/restype。ctypes 默认返回值是
32 位 int，在 64 位 Windows 上会把窗口句柄/进程句柄截断，导致前置窗口识别失败。
"""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_EXTENDEDKEY = 0x0001

VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_BACK = 0x08
VK_TAB = 0x09
VK_SPACE = 0x20

ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wt.LONG),
        ("dy", wt.LONG),
        ("mouseData", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wt.DWORD),
        ("wParamL", wt.WORD),
        ("wParamH", wt.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


user32.SendInput.argtypes = (wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wt.UINT
user32.GetForegroundWindow.argtypes = ()
user32.GetForegroundWindow.restype = wt.HWND
user32.GetWindowTextLengthW.argtypes = (wt.HWND,)
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = (wt.HWND, wt.LPWSTR, ctypes.c_int)
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = (wt.HWND, ctypes.POINTER(wt.DWORD))
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.OpenClipboard.argtypes = (wt.HWND,)
user32.OpenClipboard.restype = wt.BOOL
user32.EmptyClipboard.argtypes = ()
user32.EmptyClipboard.restype = wt.BOOL
user32.CloseClipboard.argtypes = ()
user32.CloseClipboard.restype = wt.BOOL
user32.SetClipboardData.argtypes = (wt.UINT, wt.HANDLE)
user32.SetClipboardData.restype = wt.HANDLE

kernel32.OpenProcess.argtypes = (wt.DWORD, wt.BOOL, wt.DWORD)
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = (
    wt.HANDLE,
    wt.DWORD,
    wt.LPWSTR,
    ctypes.POINTER(wt.DWORD),
)
kernel32.QueryFullProcessImageNameW.restype = wt.BOOL
kernel32.CloseHandle.argtypes = (wt.HANDLE,)
kernel32.CloseHandle.restype = wt.BOOL
kernel32.GlobalAlloc.argtypes = (wt.UINT, ctypes.c_size_t)
kernel32.GlobalAlloc.restype = wt.HGLOBAL
kernel32.GlobalLock.argtypes = (wt.HGLOBAL,)
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = (wt.HGLOBAL,)
kernel32.GlobalUnlock.restype = wt.BOOL
kernel32.GlobalFree.argtypes = (wt.HGLOBAL,)
kernel32.GlobalFree.restype = wt.HGLOBAL


def _key_event(vk: int, scan: int, flags: int, extra: int = 0) -> INPUT:
    ev = INPUT()
    ev.type = INPUT_KEYBOARD
    ev.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=extra)
    return ev


def _send(events: list[INPUT], chunk: int = 40) -> None:
    """分批调用 SendInput；被系统拒绝（如权限不足）时抛出 OSError。"""
    n = len(events)
    if not n:
        return
    arr = (INPUT * n)(*events)
    done = 0
    while done < n:
        part = min(chunk, n - done)
        slice_arr = ctypes.cast(
            ctypes.byref(arr, done * ctypes.sizeof(INPUT)), ctypes.POINTER(INPUT)
        )
        sent = user32.SendInput(part, slice_arr, ctypes.sizeof(INPUT))
        if sent == 0:
            raise OSError(ctypes.get_last_error(), "SendInput 被系统拒绝")
        done += sent


def key_down(vk: int, extended: bool = False) -> None:
    flags = KEYEVENTF_EXTENDEDKEY if extended else 0
    _send([_key_event(vk, 0, flags)])


def key_up(vk: int, extended: bool = False) -> None:
    flags = KEYEVENTF_KEYUP | (KEYEVENTF_EXTENDEDKEY if extended else 0)
    _send([_key_event(vk, 0, flags)])


def tap_key(vk: int, hold: float = 0.02, extended: bool = False) -> None:
    key_down(vk, extended)
    try:
        time.sleep(hold)
    finally:
        key_up(vk, extended)


def _char_events(text: str) -> list[INPUT]:
    events: list[INPUT] = []
    for ch in text:
        if ch == "\n":
            events.append(_key_event(VK_RETURN, 0, 0))
            events.append(_key_event(VK_RETURN, 0, KEYEVENTF_KEYUP))
            continue
        if ch == "\t":
            events.append(_key_event(VK_TAB, 0, 0))
            events.append(_key_event(VK_TAB, 0, KEYEVENTF_KEYUP))
            continue
        # 用 UTF-16 单元逐个发送，可覆盖 BMP 之外的字符
        raw = ch.encode("utf-16-le")
        for i in range(0, len(raw), 2):
            unit = int.from_bytes(raw[i:i + 2], "little")
            events.append(_key_event(0, unit, KEYEVENTF_UNICODE))
            events.append(_key_event(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
    return events


def type_text(text: str, char_delay: float = 0.0, chunk: int = 24) -> None:
    """把文字打进当前前台窗口。char_delay 为每字符额外停顿（秒）。"""
    if not text:
        return
    if char_delay <= 0:
        _send(_char_events(text))
        return
    for i in range(0, len(text), chunk):
        _send(_char_events(text[i:i + chunk]))
        time.sleep(max(char_delay * min(chunk, len(text) - i), 0.001))


def foreground_hwnd() -> int:
    return int(user32.GetForegroundWindow() or 0)


def window_title(hwnd: int | None = None) -> str:
    hwnd = hwnd or foreground_hwnd()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def foreground_exe() -> str:
    """返回前台窗口所属进程的完整路径，取不到时返回空串。"""
    hwnd = foreground_hwnd()
    if not hwnd:
        return ""
    pid = wt.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    handle = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return ""
    try:
        size = wt.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
    finally:
        kernel32.CloseHandle(handle)
    return ""


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def set_clipboard(text: str, retries: int = 5) -> bool:
    """写入剪贴板（不依赖第三方库）。

    剪贴板可能被其它程序短暂锁住，这里做几次重试；失败时会释放已分配的内存。
    """
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    data = (text + "\0").encode("utf-16-le")
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        return False
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        return False
    try:
        ctypes.memmove(pointer, data, len(data))
    finally:
        kernel32.GlobalUnlock(handle)

    opened = False
    for _ in range(max(1, retries)):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.03)
    if not opened:
        kernel32.GlobalFree(handle)
        return False
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            return False
        handle = None  # 所有权已交给系统，不能再释放
        return True
    finally:
        user32.CloseClipboard()
        if handle:
            kernel32.GlobalFree(handle)
