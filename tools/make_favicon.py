#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用品牌 Logo 產生 favicon 全組。

輸出（都在根目錄）：
    favicon.ico            16/32/48 多尺寸
    favicon-32.png
    apple-touch-icon.png   180×180（iPhone 加到主畫面）
    icon-192.png / icon-512.png  （PWA / Android）
"""
import pathlib
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGO = ROOT / "images" / "logo_mark.png"

# 深木色底（透明 favicon 在白色分頁上會看不見）
BG_TOP = (58, 34, 19)
BG_BOT = (32, 18, 10)


def plate(size, radius_ratio=0.22):
    """圓角方形底，帶一點木色漸層。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size))
    gd = grad.load()
    for y in range(size):
        t = y / max(1, size - 1)
        col = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(size):
            gd[x, y] = col + (255,)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=255)
    img.paste(grad, (0, 0), mask)
    # 金色細邊
    ImageDraw.Draw(img).rounded_rectangle(
        [1, 1, size - 2, size - 2], radius=int(size * radius_ratio),
        outline=(201, 162, 39, 220), width=max(1, size // 32))
    return img


def make(size, pad_ratio=0.16):
    base = plate(size)
    logo = Image.open(LOGO).convert("RGBA")
    inner = int(size * (1 - pad_ratio * 2))
    logo = logo.resize((inner, inner), Image.LANCZOS)
    base.paste(logo, ((size - inner) // 2, (size - inner) // 2), logo)
    return base


def main():
    sizes = [16, 32, 48, 180, 192, 512]
    imgs = {s: make(s) for s in sizes}

    imgs[32].save(ROOT / "favicon-32.png")
    imgs[180].save(ROOT / "apple-touch-icon.png")
    imgs[192].save(ROOT / "icon-192.png")
    imgs[512].save(ROOT / "icon-512.png")
    imgs[48].save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("favicon 完成：ico + 32 + apple-touch 180 + 192 + 512")

    # 預覽一張
    prev = Image.new("RGB", (size_ := 560, 160), (240, 236, 228))
    x = 10
    for s in (16, 32, 48, 180):
        prev.paste(imgs[s].resize((s, s)) if s < 60 else imgs[s], (x, 80 - s // 2), imgs[s].resize((s, s)))
        x += s + 24
    prev.save(ROOT / "樣張" / "favicon預覽.png")
    print("預覽：樣張/favicon預覽.png")


if __name__ == "__main__":
    main()
