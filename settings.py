# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Ai Studio"
APP_VERSION = "3.6.0"

# Theme (managed by launcher.py)
# "dark" = Apple dark theme (default), "light" = Apple light theme
THEME_MODE = "dark"
THEME_FILE_NAME = "theme.json"

# === 已修改: 硬编码到本地, 绕过远程验证 ===
PUBLIC_LICENSE_SERVER_URL = "http://127.0.0.1:5000"
LOCAL_LICENSE_SERVER_URL = "http://127.0.0.1:5000"
BUILTIN_LICENSE_SERVER_URL = "http://127.0.0.1:5000"
LICENSE_SERVER_CANDIDATES = ["http://127.0.0.1:5000"]
UPDATE_INFO_URL = "http://127.0.0.1:5000/api/app/version"

CONTACT_TEXT = "问题咨询：QQ1483151744\n备注：AI原创"
VERIFY_SECRET = os.getenv("AUDIOFLOW_VERIFY_SECRET", "change-this-signing-secret")
SUPPORTED_AUDIO_EXTS = {".mp3", ".wav"}
DEFAULT_OUTPUT_DIR = str(Path.home() / "Desktop" / "AudioFlow_Output")


def app_data_dir() -> Path:
    if sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    elif sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    else:
        base = str(Path.home() / ".local" / "share")
    path = Path(base) / os.getenv("AUDIOFLOW_APP_DATA_NAME", "AudioFlowStudio")
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(relative: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).resolve().parent / relative
