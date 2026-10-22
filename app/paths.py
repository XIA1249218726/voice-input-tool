"""路径管理：区分「程序资源」与「用户数据」。

- 资源目录（只读）：源码运行时是项目根目录；打包后是 exe 所在目录。
  模型、图标等随程序安装，不写入。
- 数据目录（可写）：源码运行时仍是项目根目录（方便调试）；
  打包后默认使用 %LOCALAPPDATA%\\VoiceInputTool，避免 Program Files 只读问题。
  如果 LOCALAPPDATA 不可写，会依次回退到 exe 旁的 userdata、临时目录。
  在 exe 旁边放一个 portable.flag 文件，则数据目录改为 exe 目录（绿色版）。
- 环境变量 VOICE_DATA_DIR 可强制指定数据目录（测试/多份配置时使用）。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

APP_NAME = "语音输入工具"
APP_ID = "VoiceInputTool"
APP_VERSION = "1.0.0"

_DATA_ROOT: Path | None = None


def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包后的 exe 中。"""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """只读资源根目录（模型、图标、随包文档）。"""
    if is_frozen():
        # onedir 模式：exe 与 _internal 同级
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _local_appdata() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base)
    return Path.home() / "AppData" / "Local"


def _writable(path: Path) -> bool:
    """真正探测可写性（只读安装目录 / 受限账户时能提前发现）。"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".voice-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def data_root() -> Path:
    """可写数据根目录（config.json、logs）。"""
    global _DATA_ROOT
    if _DATA_ROOT is not None:
        return _DATA_ROOT

    root = resource_root()
    override = os.environ.get("VOICE_DATA_DIR", "").strip()
    if override:
        _DATA_ROOT = Path(override).expanduser().resolve()
        return _DATA_ROOT

    if is_frozen():
        if (root / "portable.flag").exists():
            candidates = [root]
        else:
            candidates = [
                _local_appdata() / APP_ID,
                root / "userdata",
                Path(tempfile.gettempdir()) / APP_ID,
            ]
    else:
        candidates = [root, Path(tempfile.gettempdir()) / APP_ID]

    for base in candidates:
        if _writable(base):
            _DATA_ROOT = base
            return base
    _DATA_ROOT = candidates[0]
    return _DATA_ROOT


def ensure_data_root() -> Path:
    root = data_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def config_path() -> Path:
    return data_root() / "config.json"


def log_dir() -> Path:
    return data_root() / "logs"


def model_dir() -> Path:
    return resource_root() / "models" / "sense-voice"


def icon_path() -> Path:
    return resource_root() / "app.ico"


def bundle_dir() -> Path | None:
    """PyInstaller 单文件模式的临时解包目录；仅用于定位随包数据。"""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None
