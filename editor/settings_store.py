# -*- coding: utf-8 -*-
"""设置持久化（data/settings.json）"""
import json
import os
import shutil

from .paths import PROJECT_ROOT, get_data_dir

# 设置文件统一存放在 data 目录
SETTINGS_FILE = os.path.join(get_data_dir(), "settings.json")


def _migrate_legacy_settings():
    """将旧位置（项目根目录）的 settings.json 迁移到 data 目录"""
    legacy = os.path.join(PROJECT_ROOT, "settings.json")
    if os.path.exists(legacy) and not os.path.exists(SETTINGS_FILE):
        try:
            shutil.move(legacy, SETTINGS_FILE)
        except OSError:
            pass


_migrate_legacy_settings()


def load_settings():
    """读取设置，缺失项使用默认值"""
    defaults = {"auto_save_enabled": True, "auto_save_interval": 30}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return defaults


def save_settings(data):
    """保存设置到磁盘（覆盖写入）"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
