# -*- coding: utf-8 -*-
"""自动检测本机上的 ComfyUI 项目位置。

支持的安装形态：
  * ComfyUI Desktop:  %LOCALAPPDATA%\\Comfy-Desktop\\ComfyUI-Installs\\<实例>\\ComfyUI\\models
  * 便携包:            <盘符>\\ComfyUI(_windows_portable)\\ComfyUI\\models 或 ...\\models
  * 其它自定义目录（手动“浏览…”添加，会记住）
"""
import os
from pathlib import Path


def models_dir_of(project):
    """给定项目根目录，返回其 models 目录（不存在则返回 None）。"""
    p = Path(project)
    for cand in (p / "ComfyUI" / "models", p / "models"):
        try:
            if cand.is_dir():
                return cand
        except OSError:
            continue
    return None


def looks_like_project(p):
    return models_dir_of(p) is not None


def ensure_models_dir(project):
    """确保项目有 models 目录；没有则在 <project>/ComfyUI/models 创建。"""
    d = models_dir_of(project)
    if d:
        return d
    d = Path(project) / "ComfyUI" / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def auto_detect():
    """扫描常见位置，返回项目根目录字符串列表（去重、保序）。"""
    found = []
    seen = set()

    def add(p):
        try:
            p = Path(p)
            rp = str(p.resolve())
        except OSError:
            return
        key = rp.lower()
        if key in seen:
            return
        try:
            ok = p.is_dir() and looks_like_project(p)
        except OSError:
            ok = False
        if ok:
            seen.add(key)
            found.append(rp)

    def scan_children(base):
        base = Path(base)
        try:
            if not base.is_dir():
                return
            for child in base.iterdir():
                try:
                    if child.is_dir():
                        add(child)
                except OSError:
                    continue
        except OSError:
            pass

    la = os.environ.get("LOCALAPPDATA")
    up = os.environ.get("USERPROFILE")

    if la:
        # ComfyUI Desktop（重点支持）
        scan_children(Path(la) / "Comfy-Desktop" / "ComfyUI-Installs")
        add(Path(la) / "Programs" / "ComfyUI")
        add(Path(la) / "ComfyUI")

    if up:
        add(Path(up) / "ComfyUI")
        add(Path(up) / "Documents" / "ComfyUI")
        add(Path(up) / "Desktop" / "ComfyUI")

    # 常见盘符根目录下一层，找名字带 comfy 的目录
    for drive in ("C", "D", "E", "F", "G", "H"):
        root = Path(drive + ":/\\")
        try:
            if not root.is_dir():
                continue
            for child in root.iterdir():
                try:
                    if child.is_dir() and "comfy" in child.name.lower():
                        add(child)
                        scan_children(child)
                except OSError:
                    continue
        except OSError:
            continue

    # 当前工作目录相关
    cwd = Path.cwd()
    add(cwd)
    add(cwd / "ComfyUI")
    if cwd.parent:
        add(cwd.parent)

    return found
