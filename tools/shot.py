# -*- coding: utf-8 -*-
"""启动界面 1.5 秒后截图保存为 screenshot.png（用于预览）。"""
import ctypes
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from PIL import ImageGrab  # noqa: E402
from urlswap.ui import App  # noqa: E402

app = App()
app.geometry("+120+60")


def shot():
    app.update_idletasks()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(
        str(ROOT / "screenshot.png"))
    app.destroy()


app.after(1600, shot)
app.mainloop()
print("screenshot saved")
