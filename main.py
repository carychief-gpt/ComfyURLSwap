# -*- coding: utf-8 -*-
"""ComfyURLSwap 入口: ComfyUI 模型下载器 (huggingface.co -> hf-mirror.com)."""
import sys


def _enable_high_dpi():
    """Windows 高分屏下避免界面模糊。"""
    if sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except OSError:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    _enable_high_dpi()
    from urlswap.ui import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
