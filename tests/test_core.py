"""语音输入工具 —— 核心逻辑单元测试。

运行：
    runtime\\python\\python.exe -m unittest discover -s tests -v
或：
    powershell -ExecutionPolicy Bypass -File tests\\run_tests.ps1

不依赖麦克风；模型测试只在模型存在时运行。
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import asr, audio, config, hotkey  # noqa: E402


def _cfg(**kwargs) -> config.Config:
    base = dict(
        replacements={},
        strip_punct=True,
        prefix="",
        only_clipboard=False,
        chat_open_delay=0.0,
        send_delay=0.0,
    )
    base.update(kwargs)
    return config.Config(**base)


class ConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        cfg = config.Config()
        self.assertEqual(cfg.hotkey, "f8")
        self.assertEqual(cfg.engine, "local")
        self.assertEqual(cfg.trigger_mode, "hold")

    def test_bad_types_are_coerced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "hotkey": 123,
                        "chat_open_delay": "not-a-number",
                        "num_threads": "8",
                        "engine": "bogus",
                        "trigger_mode": "???",
                        "language": "xx",
                        "replacements": {"a": 1, "": "x"},
                        "beep": "false",
                    }
                ),
                encoding="utf-8",
            )
            cfg = config.load(path)
            self.assertEqual(cfg.hotkey, "123")
            self.assertEqual(cfg.chat_open_delay, 0.35)
            self.assertEqual(cfg.num_threads, 8)
            self.assertEqual(cfg.engine, "local")
            self.assertEqual(cfg.trigger_mode, "hold")
            self.assertEqual(cfg.language, "zh")
            self.assertEqual(cfg.replacements, {"a": "1"})
            self.assertFalse(cfg.beep)

    def test_clamping(self) -> None:
        cfg = config.Config(
            max_record_seconds=999,
            num_threads=0,
            char_delay=-1,
            chat_open_delay=99,
        )
        cfg = config._sanitize(cfg)
        self.assertEqual(cfg.max_record_seconds, 60.0)
        self.assertEqual(cfg.num_threads, 1)
        self.assertEqual(cfg.char_delay, 0.0)
        self.assertEqual(cfg.chat_open_delay, 5.0)

    def test_save_is_atomic_and_roundtrips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            cfg = config.Config(hotkey="ctrl+alt+v", replacements={"a大": "A大"})
            config.save(cfg, path)
            self.assertTrue(path.exists())
            self.assertFalse(list(Path(tmp).glob(".config-*.json")))
            loaded = config.load(path)
            self.assertEqual(loaded.hotkey, "ctrl+alt+v")
            self.assertEqual(loaded.replacements, {"a大": "A大"})


class TextTests(unittest.TestCase):
    def test_clean_text_removes_sensevoice_tags(self) -> None:
        raw = "<|zh|><|NEUTRAL|><|Speech|>  你好   世界 <|woitn|>"
        self.assertEqual(asr.clean_text(raw), "你好 世界")

    def test_postprocess_replacements_punct_prefix(self) -> None:
        cfg = _cfg(replacements={"哎大": "A大"}, prefix="[报点]")
        text = asr.postprocess("哎大有两个。", cfg)
        self.assertEqual(text, "[报点]A大有两个")

    def test_postprocess_keeps_punct_when_disabled(self) -> None:
        cfg = _cfg(strip_punct=False)
        self.assertEqual(asr.postprocess("你好。", cfg), "你好。")

    def test_postprocess_empty(self) -> None:
        self.assertEqual(asr.postprocess("", _cfg()), "")


class AudioTests(unittest.TestCase):
    def test_trim_silence_removes_edges(self) -> None:
        sr = audio.SAMPLE_RATE
        silence = np.zeros(int(sr * 1.0), dtype=np.float32)
        t = np.arange(int(sr * 0.4), dtype=np.float32) / sr
        speech = (0.3 * np.sin(2 * math.pi * 220 * t)).astype(np.float32)
        samples = np.concatenate([silence, speech, silence])
        out = audio.trim_silence(samples)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertLess(out.size, samples.size)
        self.assertGreater(out.size, speech.size * 0.5)

    def test_trim_silence_all_silence(self) -> None:
        self.assertIsNone(audio.trim_silence(np.zeros(16000, dtype=np.float32)))

    def test_trim_silence_too_short(self) -> None:
        sr = audio.SAMPLE_RATE
        t = np.arange(int(sr * 0.03), dtype=np.float32) / sr
        samples = (0.5 * np.sin(2 * math.pi * 300 * t)).astype(np.float32)
        self.assertIsNone(audio.trim_silence(samples))

    def test_wav_encoding(self) -> None:
        samples = np.zeros(1600, dtype=np.float32)
        data = audio.to_wav_bytes(samples)
        self.assertTrue(data.startswith(b"RIFF"))
        self.assertGreater(len(data), 44)


class HotkeyTests(unittest.TestCase):
    def test_function_key(self) -> None:
        from pynput import keyboard

        hk = hotkey.HotkeyManager("f8", lambda: None, lambda: None)
        self.assertTrue(hk.valid())
        self.assertEqual(hk.main_key, keyboard.Key.f8)

    def test_mouse_button(self) -> None:
        hk = hotkey.HotkeyManager("mouse4", lambda: None, lambda: None)
        self.assertTrue(hk.valid())
        self.assertTrue(hk.is_mouse)

    def test_combination(self) -> None:
        hk = hotkey.HotkeyManager("ctrl+alt+v", lambda: None, lambda: None)
        self.assertTrue(hk.valid())
        self.assertEqual(hk.modifiers, {"ctrl", "alt"})
        self.assertEqual(hk.main_char, "v")

    def test_modifier_only_is_invalid(self) -> None:
        hk = hotkey.HotkeyManager("ctrl", lambda: None, lambda: None)
        self.assertFalse(hk.valid())


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = config.MODEL_DIR / "model.int8.onnx"
        if not cls.model.exists():
            raise unittest.SkipTest("未找到模型，跳过识别测试")
        cls.cfg = _cfg()
        cls.engine = asr.build_engine(cls.cfg)

    def test_chinese_sample(self) -> None:
        wav = config.MODEL_DIR / "test_wavs" / "zh.wav"
        with wave.open(str(wav), "rb") as fh:
            self.assertEqual(fh.getframerate(), 16000)
            data = np.frombuffer(fh.readframes(fh.getnframes()), dtype=np.int16)
        samples = data.astype(np.float32) / 32768.0
        text = asr.clean_text(self.engine.transcribe(samples))
        self.assertTrue(text)
        self.assertNotIn("<|", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
