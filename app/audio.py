"""麦克风录音：常驻采集 + 预录缓冲 + 静音裁剪。"""

from __future__ import annotations

import collections
import threading
import time

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
BLOCK = 1600  # 100ms


def list_input_devices() -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    try:
        for idx, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) > 0:
                api = sd.query_hostapis(dev["hostapi"])["name"]
                result.append((idx, f"{dev['name']}  [{api}]"))
    except Exception:
        pass
    return result


def resolve_device(name: str) -> int | None:
    """按名称关键字（不区分大小写）找麦克风，返回设备索引。"""
    name = (name or "").strip().lower()
    if not name:
        return None
    devices = list_input_devices()
    for idx, label in devices:
        if name in label.lower():
            return idx
    return None


class Recorder:
    """长期保持一条输入流，正在说话时把缓冲区的音频取出。"""

    def __init__(
        self,
        device: str = "",
        preroll_ms: int = 350,
        max_seconds: float = 15.0,
    ) -> None:
        self.device_name = device
        self.max_seconds = max_seconds
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._chunks: list[np.ndarray] = []
        self._recording = False
        self._preroll = collections.deque(maxlen=max(1, preroll_ms // 100))
        self._level = 0.0
        self._max_blocks = max(1, int(max_seconds * SAMPLE_RATE / BLOCK))
        self.overflowed = False
        # 实际打开的设备和配置里的设备是否一致（配置写错时会退回系统默认）
        self.active_device = ""
        self.device_missing = False

    # ---------- 生命周期 ----------
    def open(self) -> None:
        if self._stream is not None:
            return
        device = resolve_device(self.device_name)
        self.device_missing = bool((self.device_name or "").strip()) and device is None
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK,
            channels=1,
            dtype="float32",
            device=device,
            latency="low",
            callback=self._callback,
        )
        try:
            self._stream.start()
        except Exception:
            self.close()
            raise
        try:
            index = device if device is not None else sd.default.device[0]
            info = sd.query_devices(index)
            api = sd.query_hostapis(info["hostapi"])["name"]
            self.active_device = f"{info['name']}  [{api}]"
        except Exception:
            self.active_device = self.device_name or "系统默认"

    def close(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    # ---------- 采集 ----------
    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        block = indata[:, 0].copy()
        peak = float(np.max(np.abs(block))) if block.size else 0.0
        with self._lock:
            self._level = peak
            if status:
                self.overflowed = True
            if not self._recording:
                self._preroll.append(block)
                return
            if len(self._chunks) >= self._max_blocks:
                self.overflowed = True
                return
            self._chunks.append(block)

    @property
    def level(self) -> float:
        with self._lock:
            return self._level

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def overflowing(self) -> bool:
        return self.overflowed

    def start(self) -> None:
        with self._lock:
            self._chunks = list(self._preroll)
            self._preroll.clear()
            self._recording = True
            self.overflowed = False

    def stop(self) -> np.ndarray:
        with self._lock:
            self._recording = False
            chunks = self._chunks
            self._chunks = []
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks).astype(np.float32, copy=False)


def trim_silence(
    samples: np.ndarray,
    threshold: float = 0.006,
    pad_ms: int = 180,
    min_speech_ms: int = 120,
) -> np.ndarray | None:
    """裁掉首尾静音；有效语音太短则返回 None。"""
    if samples.size == 0:
        return None
    frame = 160  # 10ms
    usable = (samples.size // frame) * frame
    if usable < frame * 3:
        return None
    frames = samples[:usable].reshape(-1, frame)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    noise = float(np.percentile(rms, 10)) if rms.size else 0.0
    gate = max(threshold, noise * 2.5)
    active = np.nonzero(rms > gate)[0]
    if active.size == 0:
        return None
    speech_frames = int(active[-1] - active[0] + 1)
    if speech_frames * 10 < min_speech_ms:
        return None
    pad = pad_ms // 10
    start = max(0, int(active[0]) - pad) * frame
    end = min(samples.size, (int(active[-1]) + 1 + pad) * frame)
    out = samples[start:end]
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if peak < 1e-5:
        return None
    if 0 < peak < 0.5:  # 音量偏小的场景做一点增益
        out = np.clip(out * min(3.0, 0.9 / peak), -1.0, 1.0)
    return out


def to_pcm16(samples: np.ndarray) -> bytes:
    return (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()


def to_wav_bytes(samples: np.ndarray, samplerate: int = SAMPLE_RATE) -> bytes:
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(to_pcm16(samples))
    return buf.getvalue()


def wait_until(predicate, timeout: float = 1.0, interval: float = 0.02) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False
