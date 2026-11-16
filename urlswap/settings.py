# -*- coding: utf-8 -*-
"""设置与任务持久化。

settings.json —— 界面偏好（项目路径、线程数、开关等）
tasks.json    —— 下载任务列表（程序关闭后重新打开可断点续传）
"""
import json
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # PyInstaller 打包运行：配置保存在 exe 同目录
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = APP_DIR / "settings.json"
TASKS_FILE = APP_DIR / "tasks.json"

DEFAULTS = {
    "projects": [],          # 手动/历史添加过的项目路径
    "last_project": "",      # 上次使用的项目
    "workers": 4,            # 下载线程数
    "skip_existing": True,   # 目标文件已存在则跳过
    "auto_mirror": True,     # huggingface.co -> hf-mirror.com
}


def load_settings():
    data = dict(DEFAULTS)
    try:
        if SETTINGS_FILE.exists():
            loaded = json.loads(SETTINGS_FILE.read_text("utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
    except Exception:
        pass
    return data


def save_settings(data):
    try:
        SETTINGS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), "utf-8"
        )
    except OSError:
        pass
