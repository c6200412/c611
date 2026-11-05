# -*- coding: utf-8 -*-
"""
把 JPG/PNG 照片转成屏幕可直接显示的 RGB565 裸文件 (photo.raw)
用法:
    python convert.py 你的照片.jpg          # 默认 240x320
    python convert.py 你的照片.jpg 320 240  # 自定义宽高
输出: data/photo.raw (小端 uint16, 每像素2字节)
"""
import os
import sys

from PIL import Image
import numpy as np


def convert(src, dst, w, h):
    img = Image.open(src).convert("RGB")

    # 等比缩放后居中裁剪，避免拉伸变形
    img.thumbnail((w, h))
    canvas = Image.new("RGB", (w, h), (0, 0, 0))
    canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2))

    a = np.array(canvas, dtype=np.uint8)
    r = (a[..., 0] >> 3) & 0x1F          # 5 bit 红
    g = (a[..., 1] >> 2) & 0x3F          # 6 bit 绿
    b = (a[..., 2] >> 3) & 0x1F          # 5 bit 蓝
    rgb565 = (r.astype(np.uint16) << 11) | (g.astype(np.uint16) << 5) | b.astype(np.uint16)

    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)  # 自动建 data/ 目录
    rgb565.astype('<u2').tofile(dst)     # '<u2' = 小端 uint16，关键，别改
    print(f"OK: {src} -> {dst}  ({w}x{h}, {w*h*2} bytes)")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "photo.jpg"
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 240
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 320
    convert(src, "data/photo.raw", w, h)
