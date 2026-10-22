"""语音识别引擎：本地 SenseVoice（离线）与云端 OpenAI 兼容接口。"""

from __future__ import annotations

import re
import threading
from pathlib import Path

import numpy as np

from .audio import SAMPLE_RATE, to_wav_bytes

_TAG = re.compile(r"<\|[^|]*\|>")
_SPACE = re.compile(r"\s+")


class AsrError(RuntimeError):
    pass


def clean_text(text: str) -> str:
    text = _TAG.sub("", text or "")
    return _SPACE.sub(" ", text).strip()


class LocalSenseVoice:
    """sherpa-onnx + SenseVoiceSmall(int8)：中/英/日/韩/粤，CPU 上很快。"""

    name = "本地离线 (SenseVoice)"

    def __init__(
        self,
        model_dir: Path,
        num_threads: int = 4,
        language: str = "zh",
        use_itn: bool = True,
    ) -> None:
        import sherpa_onnx

        model_dir = Path(model_dir)
        model = None
        for candidate in ("model.int8.onnx", "model.onnx"):
            p = model_dir / candidate
            if p.exists():
                model = p
                break
        tokens = model_dir / "tokens.txt"
        if model is None or not tokens.exists():
            raise AsrError(f"找不到模型文件：{model_dir}（需要 model.onnx 与 tokens.txt）")

        self._lock = threading.Lock()
        self._rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(model),
            tokens=str(tokens),
            num_threads=max(1, int(num_threads)),
            language=language or "zh",
            use_itn=bool(use_itn),
            debug=False,
            provider="cpu",
        )

    def transcribe(self, samples: np.ndarray, samplerate: int = SAMPLE_RATE) -> str:
        if samples is None or samples.size < SAMPLE_RATE * 0.1:
            return ""
        samples = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        with self._lock:
            stream = self._rec.create_stream()
            stream.accept_waveform(samplerate, samples)
            self._rec.decode_stream(stream)
            result = stream.result
            return clean_text(getattr(result, "text", "") or "")


class CloudAsr:
    """任意 OpenAI 兼容的 /audio/transcriptions 接口。"""

    name = "云端接口"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        language: str = "zh",
        timeout: float = 25.0,
    ) -> None:
        if not base_url.strip():
            raise AsrError("云端接口地址为空")
        if not api_key.strip():
            raise AsrError("云端接口密钥为空")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.language = "" if language == "auto" else language
        self.timeout = timeout

    def transcribe(self, samples: np.ndarray, samplerate: int = SAMPLE_RATE) -> str:
        import requests

        wav = to_wav_bytes(samples, samplerate)
        data = {"model": self.model, "response_format": "json"}
        if self.language:
            data["language"] = self.language
        try:
            resp = requests.post(
                f"{self.base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": ("speech.wav", wav, "audio/wav")},
                data=data,
                timeout=self.timeout,
            )
        except Exception as exc:  # 网络问题
            raise AsrError(f"请求失败：{exc}") from exc
        if resp.status_code != 200:
            raise AsrError(f"接口返回 {resp.status_code}：{resp.text[:200]}")
        try:
            payload = resp.json()
        except Exception as exc:
            raise AsrError(f"返回内容无法解析：{resp.text[:200]}") from exc
        return clean_text(payload.get("text", "") or "")


def build_engine(cfg, on_log=None):
    if cfg.engine == "api":
        return CloudAsr(cfg.api_base, cfg.api_key, cfg.api_model, cfg.language)
    from .config import MODEL_DIR

    return LocalSenseVoice(
        MODEL_DIR,
        num_threads=cfg.num_threads,
        language=cfg.language,
        use_itn=cfg.use_itn,
    )


_PUNCT = "。，、！？；：,.!?;:~…"


def postprocess(text: str, cfg) -> str:
    text = clean_text(text)
    if not text:
        return ""
    for old, new in (cfg.replacements or {}).items():
        if old:
            text = text.replace(old, new)
    if cfg.strip_punct:
        text = text.strip().strip(_PUNCT).strip()
    text = _SPACE.sub(" ", text).strip()
    if text and cfg.prefix:
        text = cfg.prefix + text
    return text
