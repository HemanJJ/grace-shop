#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""品牌 Logo：金色十字 ＋ 大方塊 QR 示意底。

概念：後面是「碼」（示意用的粗方塊，不是真 QR），前面是十字。
用法：python3 tools/make_logo.py
輸出：images/logo_gold.png（800×800，透明）
"""
import math, pathlib, random
from PIL import Image, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
S = 800
GOLD_LIGHT = (255, 236, 176)
GOLD_MID = (224, 176, 74)
GOLD_DARK = (168, 116, 36)


def draw_logo(path):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2

    # ---------- 1) QR 示意底：粗方塊 ----------
    rnd = random.Random(20261110)
    N = 6                                  # 6×6 大格子（大塊一點）
    field = S * 0.70
    cell = field / N
    x0 = (S - field) / 2
    y0 = (S - field) / 2

    def cell_box(col, row, inset=0):
        x = x0 + col * cell + inset
        y = y0 + row * cell + inset
        return [x, y, x + cell - inset, y + cell - inset]

    # 三個角落的定位圖形（像 QR 的尋像器）
    def finder(col, row):
        for (dc, dr, w) in [(0, 0, 3), (0.6, 0.6, 1.8), (1.15, 1.15, 0.7)]:
            box = cell_box(col, row, inset=0)
            bx = [box[0] + cell * dc, box[1] + cell * dr]
            bx += [bx[0] + cell * w, bx[1] + cell * w]
            d.rounded_rectangle(bx, radius=cell * 0.10,
                                outline=GOLD_MID + (185,), width=max(4, int(cell * 0.16)))

    finder(0, 0)
    finder(N - 3, 0)
    finder(0, N - 3)

    # 資料方塊（示意，不是真的可掃內容）
    reserved = set()
    for (fc, fr) in [(0, 0), (N - 3, 0), (0, N - 3)]:
        for dc in range(3):
            for dr in range(3):
                reserved.add((fc + dc, fr + dr))

    for row in range(N):
        for col in range(N):
            if (col, row) in reserved:
                continue
            if rnd.random() < 0.52:
                a = rnd.choice([110, 135, 160])
                d.rounded_rectangle(cell_box(col, row, inset=cell * 0.10),
                                    radius=cell * 0.08, fill=GOLD_MID + (a,))

    # ---------- 2) 外圈光芒（短、粗） ----------
    for i in range(12):
        a = 2 * math.pi * i / 12 + math.pi / 12
        r1, r2 = S * 0.415, S * 0.485
        w = max(4, int(S * 0.008))
        d.line([(c + r1 * math.cos(a), c + r1 * math.sin(a)),
                (c + r2 * math.cos(a), c + r2 * math.sin(a))],
               fill=GOLD_LIGHT + (215,), width=w)

    # ---------- 3) 金色十字（前景） ----------
    pts = [
        (c, c - S * 0.44),
        (c + S * 0.058, c - S * 0.075),
        (c + S * 0.43, c),
        (c + S * 0.058, c + S * 0.075),
        (c, c + S * 0.44),
        (c - S * 0.058, c + S * 0.075),
        (c - S * 0.43, c),
        (c - S * 0.058, c - S * 0.075),
    ]
    # 白邊讓十字從碼底跳出來
    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(halo).polygon(pts, fill=(255, 250, 235, 235))
    halo = halo.filter(ImageFilter.GaussianBlur(S * 0.012))
    img = Image.alpha_composite(img, halo)

    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    grad = Image.new("RGBA", (S, S))
    gd = grad.load()
    for y in range(S):
        t = y / S
        if t < 0.5:
            k = t / 0.5
            col = tuple(int(GOLD_LIGHT[i] + (GOLD_MID[i] - GOLD_LIGHT[i]) * k) for i in range(3))
        else:
            k = (t - 0.5) / 0.5
            col = tuple(int(GOLD_MID[i] + (GOLD_DARK[i] - GOLD_MID[i]) * k) for i in range(3))
        for x in range(S):
            gd[x, y] = col + (255,)
    img.paste(grad, (0, 0), mask)

    # 中央亮心
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([c - S * 0.12, c - S * 0.12, c + S * 0.12, c + S * 0.12],
                                 fill=GOLD_LIGHT + (120,))
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.045))
    img = Image.alpha_composite(img, glow)

    img.save(path)
    print("logo →", path)


def draw_mark(path):
    """小尺寸用：只有十字＋光芒，去掉方塊，16px 才看得懂。"""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    for i in range(16):
        a = 2 * math.pi * i / 16
        long = (i % 2 == 0)
        r1, r2 = S * (0.30 if long else 0.34), S * (0.49 if long else 0.43)
        d.line([(c + r1 * math.cos(a), c + r1 * math.sin(a)),
                (c + r2 * math.cos(a), c + r2 * math.sin(a))],
               fill=GOLD_LIGHT + (235 if long else 195,), width=max(4, int(S * (0.012 if long else 0.008))))
    pts = [(c, c - S * 0.44), (c + S * 0.058, c - S * 0.075), (c + S * 0.43, c),
           (c + S * 0.058, c + S * 0.075), (c, c + S * 0.44), (c - S * 0.058, c + S * 0.075),
           (c - S * 0.43, c), (c - S * 0.058, c - S * 0.075)]
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    grad = Image.new("RGBA", (S, S)); gd = grad.load()
    for y in range(S):
        t2 = y / S
        if t2 < 0.5:
            k = t2 / 0.5
            col = tuple(int(GOLD_LIGHT[i] + (GOLD_MID[i] - GOLD_LIGHT[i]) * k) for i in range(3))
        else:
            k = (t2 - 0.5) / 0.5
            col = tuple(int(GOLD_MID[i] + (GOLD_DARK[i] - GOLD_MID[i]) * k) for i in range(3))
        for x in range(S):
            gd[x, y] = col + (255,)
    img.paste(grad, (0, 0), mask)
    img.save(path)
    print("mark →", path)


if __name__ == "__main__":
    draw_logo(ROOT / "images" / "logo_gold.png")
    draw_mark(ROOT / "images" / "logo_mark.png")
