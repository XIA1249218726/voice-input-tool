"""核心服务：热键 → 录音 → 识别 → 打字进游戏。"""

from __future__ import annotations

import queue
import re
import threading
import time

import numpy as np

from . import asr, audio
from .config import Config
from .hotkey import HotkeyManager
from .winapi import (
    VK_RETURN,
    foreground_exe,
    is_admin,
    set_clipboard,
    tap_key,
    type_text,
)

IDLE, RECORDING, BUSY = "idle", "recording", "busy"
_VIRTUAL_DEVICE_KEYS = (
    "mixline",
    "stereo mix",
    "立体声混音",
    "cable output",
    "voicemeeter",
    "vb-audio",
)


def _beep(freq: int, ms: int) -> None:
    def run() -> None:
        try:
            import winsound

            winsound.Beep(freq, ms)
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()


class VoiceService:
    def __init__(self, cfg: Config, events: "queue.Queue") -> None:
        self.cfg = cfg
        self.events = events
        self.state = IDLE
        self.ready = False
        self.last_text = ""
        self._engine = None
        self._recorder: audio.Recorder | None = None
        self._hotkey: HotkeyManager | None = None
        self._jobs: "queue.Queue[np.ndarray | None]" = queue.Queue()
        self._worker: threading.Thread | None = None
        self._running = False
        self._starting = False
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    # ------------------------------------------------------------------ 事件
    def _emit(self, kind: str, payload=None) -> None:
        self.events.put((kind, payload))

    def _log(self, message: str) -> None:
        self._emit("log", message)

    def _set_state(self, state: str) -> None:
        self.state = state
        self._emit("state", state)

    # ------------------------------------------------------------------ 生命周期
    def start(self) -> bool:
        """加载模型、打开麦克风、安装热键。返回是否真正就绪。"""
        with self._lock:
            if self.ready:
                return True
            if self._starting:
                return False
            self._starting = True

        self._log("正在加载识别引擎…")
        engine = None
        recorder = None
        try:
            engine = asr.build_engine(self.cfg)
            recorder = audio.Recorder(
                device=self.cfg.device, max_seconds=self.cfg.max_record_seconds
            )
            recorder.open()
        except Exception as exc:
            if recorder is not None:
                recorder.close()
            with self._lock:
                self._starting = False
            self._emit("error", f"启动失败：{exc}")
            self._log(f"启动失败：{exc}")
            self._emit("ready", False)
            return False

        hotkey = HotkeyManager(self.cfg.hotkey, self._on_press, self._on_release)
        if not hotkey.valid():
            recorder.close()
            with self._lock:
                self._starting = False
            self._emit("error", f"快捷键无效：{self.cfg.hotkey}")
            self._log(f"快捷键无效：{self.cfg.hotkey}（请重新设置）")
            self._emit("ready", False)
            return False
        try:
            hotkey.start()
        except Exception as exc:
            recorder.close()
            with self._lock:
                self._starting = False
            self._emit("error", f"热键监听失败：{exc}")
            self._emit("ready", False)
            return False

        with self._lock:
            self._engine = engine
            self._recorder = recorder
            self._hotkey = hotkey
            self._jobs = queue.Queue()
            self._worker = threading.Thread(target=self._work_loop, daemon=True)
            self._worker.start()
            self._running = True
            self._starting = False
            self.ready = True

        mode = "按住说话" if self.cfg.trigger_mode == "hold" else "按一下开始/再按结束"
        self._log(f"引擎：{engine.name}｜麦克风：{recorder.active_device or '系统默认'}")
        if recorder.device_missing:
            self._log("提醒：配置的麦克风没有找到，已改用系统默认设备，请到设置里重新选择")
        if any(key in (recorder.active_device or "").lower() for key in _VIRTUAL_DEVICE_KEYS):
            self._log("提醒：当前是虚拟声卡/混音设备，会把游戏声一起识别；建议在设置里选真实麦克风")
        self._log(f"已就绪：{mode}，快捷键 {self.cfg.hotkey.upper()}")
        if not is_admin():
            self._log("提示：若游戏内打不出字，请右键以管理员身份运行本程序")
        self._set_state(IDLE)
        self._emit("ready", True)
        return True

    def stop(self) -> None:
        with self._lock:
            if not self._running and not self.ready and not self._starting:
                return
            self._running = False
            self.ready = False
            self._cancel_timer()
            hotkey, self._hotkey = self._hotkey, None
            recorder, self._recorder = self._recorder, None
            worker, self._worker = self._worker, None
            self._jobs.put(None)

        if hotkey:
            hotkey.stop()
        if worker is not None and worker.is_alive():
            worker.join(timeout=1.5)
        self._drain_jobs()
        if recorder:
            recorder.close()
        with self._lock:
            self._engine = None
        self._set_state(IDLE)
        self._emit("ready", False)
        self._log("已停止")

    def _drain_jobs(self) -> None:
        while True:
            try:
                self._jobs.get_nowait()
            except queue.Empty:
                return

    # ------------------------------------------------------------------ 热键
    def _on_press(self) -> None:
        if not self.ready:
            return
        if self.cfg.trigger_mode == "toggle":
            if self._recorder and self._recorder.recording:
                self._finish_recording()
            else:
                self._begin_recording()
        else:
            self._begin_recording()

    def _on_release(self) -> None:
        if not self.ready or self.cfg.trigger_mode != "hold":
            return
        self._finish_recording()

    # ------------------------------------------------------------------ 录音
    def _begin_recording(self) -> None:
        with self._lock:
            if self._recorder is None or not self.ready or self.state != IDLE:
                return
            self._set_state(RECORDING)
        try:
            self._recorder.start()
        except Exception as exc:
            self._set_state(IDLE)
            self._log(f"录音启动失败：{exc}")
            return
        if self.cfg.beep:
            _beep(1046, 40)
        self._cancel_timer()
        self._timer = threading.Timer(self.cfg.max_record_seconds, self._finish_recording)
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _finish_recording(self) -> None:
        with self._lock:
            recorder = self._recorder
            if recorder is None or self.state != RECORDING:
                return
            self._cancel_timer()
            self._set_state(BUSY)
        try:
            samples = recorder.stop()
        except Exception as exc:
            self._set_state(IDLE)
            self._log(f"结束录音失败：{exc}")
            return
        if self.cfg.beep:
            _beep(784, 40)
        trimmed = audio.trim_silence(samples)
        if trimmed is None:
            self._set_state(IDLE)
            self._log("没有检测到语音（说话稍微大声一点，或检查麦克风）")
            return
        self._jobs.put(trimmed)

    # ------------------------------------------------------------------ 识别线程
    def _work_loop(self) -> None:
        while True:
            job = self._jobs.get()
            if job is None:
                return
            engine = self._engine
            if engine is None:
                continue
            try:
                started = time.time()
                raw = engine.transcribe(job)
                text = asr.postprocess(raw, self.cfg)
                cost = time.time() - started
                if not text:
                    self._log(f"没听清（{cost * 1000:.0f}ms）")
                else:
                    self.last_text = text
                    self._emit("text", text)
                    self._log(f"识别 {cost * 1000:.0f}ms：{text}")
                    self._deliver(text)
            except Exception as exc:
                self._emit("error", f"识别失败：{exc}")
                self._log(f"识别失败：{exc}")
            finally:
                if self._running:
                    self._set_state(IDLE)
                if self.cfg.beep:
                    _beep(1568, 25)

    # ------------------------------------------------------------------ 预览
    def preview(self, samples: np.ndarray) -> str:
        """只识别不输入，供界面上的录音测试使用。"""
        engine = self._engine
        if engine is None:
            raise RuntimeError("识别引擎未加载")
        return asr.postprocess(engine.transcribe(samples), self.cfg)

    def record_test(self, seconds: float = 3.0) -> np.ndarray:
        """借用已经在跑的录音流录一小段，避免重复打开麦克风。"""
        recorder = self._recorder
        if recorder is None or not self.ready:
            raise RuntimeError("服务未就绪")
        with self._lock:
            if self.state != IDLE:
                raise RuntimeError("正在录音或识别，请稍后再试")
            self._set_state(RECORDING)
        try:
            recorder.start()
            time.sleep(seconds)
            return recorder.stop()
        finally:
            self._set_state(IDLE)

    # ------------------------------------------------------------------ 输入
    def game_active(self) -> bool:
        exe = foreground_exe().lower()
        if not exe:
            return False
        names = [
            name.strip().lower()
            for name in re.split(r"[;,]", self.cfg.game_process)
            if name.strip()
        ]
        return any(name in exe for name in names)

    def _copy(self, text: str, reason: str) -> None:
        if set_clipboard(text):
            self._log(f"{reason}，已复制到剪贴板")
        else:
            self._log(f"{reason}，但复制剪贴板失败（可能被其它程序占用）")

    def _deliver(self, text: str) -> None:
        if self.cfg.only_clipboard:
            self._copy(text, "只复制模式")
            return
        if self.cfg.only_when_game and not self.game_active():
            self._copy(text, "当前不是游戏窗口")
            return
        try:
            if self.cfg.auto_enter_chat:
                tap_key(VK_RETURN)
                time.sleep(self.cfg.chat_open_delay)
            type_text(text, self.cfg.char_delay)
            time.sleep(self.cfg.send_delay)
            if self.cfg.auto_send:
                tap_key(VK_RETURN)
            self._log("已输入到聊天框")
        except Exception as exc:
            self._copy(text, f"模拟按键失败（{exc}）")


# ---------------------------------------------------------------- 一次性工具
def record_for(seconds: float, device: str = "") -> np.ndarray:
    """录固定时长（独立录音流，供命令行测试使用）。"""
    rec = audio.Recorder(device=device, max_seconds=seconds + 2, preroll_ms=0)
    rec.open()
    try:
        rec.start()
        time.sleep(seconds)
        return rec.stop()
    finally:
        rec.close()
