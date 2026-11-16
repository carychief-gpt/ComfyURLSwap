# -*- coding: utf-8 -*-
"""生成程序图标 tools/app.ico（紫色圆角方形 + 白色下载箭头）。"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "app.ico"
S = 256


def gradient_rounded(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # 垂直渐变底
    top, bottom = (124, 92, 255), (90, 60, 210)
    grad = Image.new("RGBA", (size, size))
    gd = ImageDraw.Draw(grad)
    for y in range(size):
        t = y / (size - 1)
        c = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,)
        gd.line([(0, y), (size, y)], fill=c)
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, size - 1, size - 1], radius=size * 0.22, fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    lw = size * 0.14
    cx = size * 0.5
    top_y, bot_y = size * 0.17, size * 0.50
    d.rounded_rectangle([cx - lw / 2, top_y, cx + lw / 2, bot_y],
                        radius=lw * 0.35, fill=white)
    d.polygon([(cx - size * 0.22, bot_y - 1),
               (cx + size * 22 / 100, bot_y - 1),
               (cx, size * 0.76)], fill=white)
    d.rounded_rectangle([size * 0.26, size * 0.82, size * 0.74, size * 0.89],
                        radius=size * 0.025, fill=white)
    return img


def main():
    base = gradient_rounded(S)
    base.save(OUT, format="ICO",
              sizes=[(256, 256), (128, 128), (64, 64), (48, 48),
                     (32, 32), (16, 16)])
    print("icon written:", OUT)


if __name__ == "__main__":
    main()
