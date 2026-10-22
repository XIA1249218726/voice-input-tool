"""配置读写。

配置以 JSON 保存，存放在可写数据目录（见 app.paths）：
- 源码运行：项目根目录/config.json
- 安装版：%LOCALAPPDATA%\\VoiceInputTool\\config.json

保存采用「临时文件 + 原子替换」，避免断电/崩溃把配置写坏。
读取时做类型校验，手改配置写错类型也不会让程序崩溃。
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import paths

ROOT = paths.resource_root()
DATA_ROOT = paths.data_root()
CONFIG_PATH = paths.config_path()
MODEL_DIR = paths.model_dir()
LOG_DIR = paths.log_dir()

LANGUAGES = {
    "zh": "中文（推荐）",
    "auto": "自动识别",
    "en": "英文",
    "ja": "日文",
    "ko": "韩文",
    "yue": "粤语",
}

ENGINES = {"local", "api"}
TRIGGER_MODES = {"hold", "toggle"}


@dataclass
class Config:
    # ---- 触发 ----
    hotkey: str = "f8"
    trigger_mode: str = "hold"          # hold=按住说话 / toggle=按一下开始再按结束
    max_record_seconds: float = 15.0

    # ---- 识别 ----
    engine: str = "local"               # local=本地离线 / api=云端接口
    language: str = "zh"
    use_itn: bool = True                # 数字/日期规范化
    num_threads: int = 4
    device: str = ""                    # 麦克风名称关键字，空=系统默认

    # ---- 输入 ----
    auto_enter_chat: bool = True        # 先按回车打开游戏聊天框
    auto_send: bool = True              # 打完字再按回车发送
    chat_open_delay: float = 0.35
    char_delay: float = 0.005
    send_delay: float = 0.15
    only_when_game: bool = True         # 只在对局窗口激活时输入
    game_process: str = "VALORANT"
    prefix: str = ""                    # 每次识别结果前加的内容
    strip_punct: bool = True
    only_clipboard: bool = False        # 只复制到剪贴板，不模拟按键

    # ---- 其它 ----
    beep: bool = True
    always_on_top: bool = False
    replacements: dict = field(default_factory=dict)

    # ---- 云端接口（OpenAI 兼容 /audio/transcriptions）----
    api_base: str = "https://api.siliconflow.cn/v1"
    api_key: str = ""
    api_model: str = "FunAudioLLM/SenseVoiceSmall"


def _coerce(field_name: str, default, value):
    """按默认值类型把 JSON 里的值转成安全类型；无法转换时用默认值。"""
    if value is None:
        return default
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "是"}
        return bool(value)
    if isinstance(default, int) and not isinstance(default, bool):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default
    if isinstance(default, float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    if isinstance(default, dict):
        if not isinstance(value, dict):
            return {}
        return {str(k): str(v) for k, v in value.items() if str(k).strip()}
    if isinstance(default, str):
        return value if isinstance(value, str) else str(value)
    return value


def _sanitize(cfg: Config) -> Config:
    """把配置限制在程序真正支持的范围内。"""
    if cfg.trigger_mode not in TRIGGER_MODES:
        cfg.trigger_mode = "hold"
    if cfg.engine not in ENGINES:
        cfg.engine = "local"
    if cfg.language not in LANGUAGES:
        cfg.language = "zh"
    cfg.hotkey = (cfg.hotkey or "f8").strip().lower() or "f8"
    cfg.max_record_seconds = min(60.0, max(1.0, cfg.max_record_seconds))
    cfg.num_threads = min(16, max(1, cfg.num_threads))
    cfg.chat_open_delay = min(5.0, max(0.0, cfg.chat_open_delay))
    cfg.char_delay = min(0.2, max(0.0, cfg.char_delay))
    cfg.send_delay = min(5.0, max(0.0, cfg.send_delay))
    cfg.game_process = (cfg.game_process or "VALORANT").strip() or "VALORANT"
    cfg.api_base = (cfg.api_base or "").strip()
    cfg.api_key = (cfg.api_key or "").strip()
    cfg.api_model = (cfg.api_model or "").strip()
    return cfg


def _migrate_legacy() -> None:
    """安装版第一次启动时，把 exe 旁的 config.json 迁移到用户数据目录。"""
    if not paths.is_frozen() or CONFIG_PATH.exists():
        return
    legacy = paths.resource_root() / "config.json"
    if legacy.is_file() and legacy.resolve() != CONFIG_PATH.resolve():
        try:
            paths.ensure_data_root()
            shutil.copyfile(legacy, CONFIG_PATH)
        except Exception:
            pass


def load(path: Path | None = None) -> Config:
    path = path or CONFIG_PATH
    _migrate_legacy()
    cfg = Config()
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return cfg
        if not isinstance(raw, dict):
            return cfg
        known = {f.name: f.default for f in fields(Config)}
        defaults = Config()
        for key, value in raw.items():
            if key not in known:
                continue
            default = getattr(defaults, key)
            setattr(cfg, key, _coerce(key, default, value))
    return _sanitize(cfg)


def save(cfg: Config, path: Path | None = None) -> None:
    path = path or CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(cfg), ensure_ascii=False, indent=2)
    # 原子写入：先写同目录临时文件，再替换目标，避免半截 JSON
    fd, tmp_name = tempfile.mkstemp(prefix=".config-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass
