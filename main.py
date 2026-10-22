"""语音输入工具 —— 程序入口。

用法：
    runtime\\python\\pythonw.exe main.py      # 正常启动（无控制台）
    runtime\\python\\python.exe  main.py --headless
    runtime\\python\\python.exe  main.py --selftest

打包后：
    语音输入工具.exe            # 正常启动
    语音输入工具.exe --selftest # 控制台自检（配合自检.bat）
"""

from __future__ import annotations

import argparse
import ctypes
import sys
import time
import traceback
from ctypes import wintypes as wt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import paths  # noqa: E402

LOG_DIR = paths.log_dir()
APP_TITLE = paths.APP_NAME
_MUTEX = None

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wt.BOOL, wt.LPCWSTR)
kernel32.CreateMutexW.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = (wt.HANDLE,)
kernel32.CloseHandle.restype = wt.BOOL
kernel32.GetLastError.restype = wt.DWORD
kernel32.AttachConsole.argtypes = (wt.DWORD,)
kernel32.AttachConsole.restype = wt.BOOL
kernel32.AllocConsole.argtypes = ()
kernel32.AllocConsole.restype = wt.BOOL
kernel32.SetConsoleOutputCP.argtypes = (wt.UINT,)
kernel32.SetConsoleOutputCP.restype = wt.BOOL
user32.FindWindowW.argtypes = (wt.LPCWSTR, wt.LPCWSTR)
user32.FindWindowW.restype = wt.HWND
user32.ShowWindow.argtypes = (wt.HWND, ctypes.c_int)
user32.ShowWindow.restype = wt.BOOL
user32.SetForegroundWindow.argtypes = (wt.HWND,)
user32.SetForegroundWindow.restype = wt.BOOL
user32.MessageBoxW.argtypes = (wt.HWND, wt.LPCWSTR, wt.LPCWSTR, wt.UINT)
user32.MessageBoxW.restype = ctypes.c_int


def _acquire_single_instance() -> bool:
    """保证只跑一个实例；已存在时激活旧窗口并返回 False。"""
    global _MUTEX
    try:
        ctypes.set_last_error(0)
        _MUTEX = kernel32.CreateMutexW(None, False, "Local\\ValorantVoiceInput_Single")
        if not _MUTEX:
            return True  # 创建互斥体失败时不要阻止程序启动
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(_MUTEX)
            _MUTEX = None
            return False
    except Exception:
        pass
    return True


def _focus_existing() -> None:
    try:
        hwnd = user32.FindWindowW(None, APP_TITLE)
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def _write_crash(exc: BaseException) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "crash.log"
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n===== " + time.strftime("%Y-%m-%d %H:%M:%S") + " =====\n")
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=fh)
    return path


def _message_box(text: str) -> None:
    try:
        user32.MessageBoxW(None, text, APP_TITLE, 0x10)
    except Exception:
        print(text)


def _attach_console() -> None:
    """打包成窗口程序后，命令行模式没有控制台；附着到父控制台或新建一个。"""
    if not paths.is_frozen() or sys.stdout is not None:
        return
    try:
        if not kernel32.AttachConsole(0xFFFFFFFF):  # ATTACH_PARENT_PROCESS
            kernel32.AllocConsole()
        kernel32.SetConsoleOutputCP(65001)
        sys.stdout = open(  # noqa: SIM115
            "CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1
        )
        sys.stderr = open(  # noqa: SIM115
            "CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1
        )
    except Exception:
        pass


def _say(line: str = "") -> None:
    """窗口程序里 stdout 可能为 None，自检输出失败不应中断检查。"""
    try:
        print(line)
    except Exception:
        pass


# --------------------------------------------------------------------- 自检
def selftest() -> int:
    from app import audio, config as cfgmod

    lines: list[str] = []

    def report(line: str = "") -> None:
        lines.append(line)
        _say(line)

    ok = True
    report(f"== {paths.APP_NAME} {paths.APP_VERSION} · 自检 ==")
    report(f"Python      : {sys.version.split()[0]}")
    report(f"资源目录    : {paths.resource_root()}")
    report(f"数据目录    : {paths.data_root()}")
    report(f"运行方式    : {'安装版/打包版' if paths.is_frozen() else '源码'}")

    for module in ("numpy", "sounddevice", "sherpa_onnx", "pynput", "requests"):
        try:
            __import__(module)
            report(f"依赖 {module:<12}: OK")
        except Exception as exc:
            ok = False
            report(f"依赖 {module:<12}: 缺失 ({exc})")

    cfg = cfgmod.load()
    report(f"配置        : 引擎={cfg.engine} 语言={cfg.language} 快捷键={cfg.hotkey}")

    from app.config import MODEL_DIR

    model = None
    for name in ("model.int8.onnx", "model.onnx"):
        if (MODEL_DIR / name).exists():
            model = MODEL_DIR / name
            break
    if model and (MODEL_DIR / "tokens.txt").exists():
        size = model.stat().st_size / 1024 / 1024
        report(f"模型        : OK  {model.name} ({size:.0f} MB)")
    else:
        ok = False
        report(f"模型        : 缺失（{MODEL_DIR}）")

    devices = audio.list_input_devices()
    report(f"麦克风      : 共 {len(devices)} 个输入设备")
    for idx, name in devices[:6]:
        report(f"              [{idx}] {name}")

    try:
        from app.winapi import is_admin

        report(f"管理员权限  : {'是' if is_admin() else '否（若游戏内打不出字，请以管理员运行）'}")
    except Exception as exc:
        ok = False
        report(f"输入接口    : 异常 {exc}")

    if ok and model:
        report("正在加载识别模型…")
        try:
            from app.asr import build_engine

            engine = build_engine(cfg)
            report(f"模型加载    : OK  {engine.name}")
        except Exception as exc:
            ok = False
            report(f"模型加载    : 失败 {exc}")

    report("== 自检结果: " + ("通过 ==" if ok else "存在问题 =="))

    # 无论控制台是否可用，都落一份报告，安装版的「自检.bat」会显示它
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (LOG_DIR / "selftest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass
    return 0 if ok else 1


# --------------------------------------------------------------------- 命令行
def record_demo(seconds: float) -> int:
    from app import config as cfgmod
    from app.asr import build_engine, postprocess
    from app.audio import trim_silence
    from app.service import record_for

    cfg = cfgmod.load()
    print(f"请说话，录音 {seconds} 秒…")
    samples = record_for(seconds, cfg.device)
    samples = trim_silence(samples)
    if samples is None:
        print("没有检测到语音")
        return 1
    engine = build_engine(cfg)
    print("识别结果：", postprocess(engine.transcribe(samples), cfg))
    return 0


def run_headless() -> int:
    import queue

    from app.config import load
    from app.service import VoiceService

    cfg = load()
    events: "queue.Queue" = queue.Queue()
    service = VoiceService(cfg, events)
    if not service.start():
        return 1
    print("后台运行中，按 Ctrl+C 退出。")
    try:
        while True:
            try:
                kind, payload = events.get(timeout=0.3)
            except queue.Empty:
                continue
            if kind == "log":
                print(payload)
            elif kind == "text":
                print(">>", payload)
            elif kind == "error":
                print("!!", payload)
            elif kind == "state":
                sys.stdout.write({"idle": ".", "recording": "R", "busy": "*"}.get(payload, "?"))
                sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n退出")
    finally:
        service.stop()
        time.sleep(0.2)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=paths.APP_NAME)
    parser.add_argument("--selftest", action="store_true", help="检查依赖、模型、麦克风")
    parser.add_argument("--headless", action="store_true", help="不开界面，在控制台运行")
    parser.add_argument("--record", type=float, metavar="SECONDS", help="录一段并打印识别结果")
    parser.add_argument("--version", action="version", version=f"{paths.APP_NAME} {paths.APP_VERSION}")
    args = parser.parse_args()

    if args.selftest or args.record or args.headless:
        _attach_console()
    if args.selftest:
        return selftest()
    if args.record:
        return record_demo(args.record)
    if args.headless:
        return run_headless()

    try:
        from app.gui import run

        if not _acquire_single_instance():
            _focus_existing()
            return 0
        run()
    except Exception as exc:  # 界面启动失败时给出可见提示
        path = _write_crash(exc)
        _message_box(f"启动失败：{exc}\n\n详细信息见：{path}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
