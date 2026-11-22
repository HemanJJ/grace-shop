#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生每集故事的 QR Code（PNG 印刷級 + SVG 向量），中間嵌品牌金色 Logo。

用法：
    python3 tools/make_qr.py --base https://grace-coffee.pages.dev
需求：
    pip install qrcode pillow
輸出：
    images/qr/<n>_qr.png / .svg
    images/qr/line_qr.png（購物小助理）
"""
import argparse, json, pathlib, sys

try:
    import qrcode
    from qrcode.image.svg import SvgPathImage
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("請先安裝：pip install qrcode pillow")

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGO = ROOT / "images" / "logo_gold.png"


def make_with_logo(url, px=1200, logo_ratio=0.20):
    """錯誤更正等級 H（可還原 30%），中央放 logo 仍可掃。"""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    modules = qr.modules_count + 8           # 含留白
    qr.box_size = max(8, round(px / modules))
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    if LOGO.exists():
        lw = int(img.width * logo_ratio)
        pad = int(lw * 1.16)
        cx, cy = img.width // 2, img.height // 2
        plate = Image.new("RGBA", (pad, pad), (0, 0, 0, 0))
        ImageDraw.Draw(plate).rounded_rectangle(
            [0, 0, pad - 1, pad - 1], radius=int(pad * 0.18), fill=(255, 255, 255, 255))
        img = img.convert("RGBA")
        img.paste(plate, (cx - pad // 2, cy - pad // 2), plate)
        logo = Image.open(LOGO).convert("RGBA").resize((lw, lw), Image.LANCZOS)
        img.paste(logo, (cx - lw // 2, cy - lw // 2), logo)
    return img


def verify(path):
    """用 OpenCV 解一次，確認加了 logo 還掃得到。"""
    try:
        import cv2
    except ImportError:
        return None
    img = cv2.imread(str(path))
    for det in (cv2.QRCodeDetector(), getattr(cv2, "QRCodeDetectorAruco", lambda: None)()):
        if det is None:
            continue
        data, _, _ = det.detectAndDecode(img)
        if data:
            return data
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://grace-coffee.pages.dev")
    a = ap.parse_args()

    stories = json.load(open(ROOT / "stories.json", encoding="utf-8"))
    stories.sort(key=lambda s: s.get("sort", 1))
    out = ROOT / "images" / "qr"
    out.mkdir(parents=True, exist_ok=True)

    targets = [(f"{int(s['sort']):02d}_qr", f"{a.base}/#/story/{s['id']}", f"#{int(s['sort']):03d}") for s in stories]
    targets.append(("line_qr", "https://line.me/R/ti/p/@lightcode", "購物小助理"))

    ok = fail = 0
    for name, url, label in targets:
        img = make_with_logo(url)
        png = out / f"{name}.png"
        img.convert("RGB").save(png, quality=95)
        # 掃不到就縮小 logo 重試（錯誤更正等級夠高，通常第二次就過）
        for ratio in (0.18, 0.16, 0.14):
            got0 = verify(png)
            if got0 and got0.rstrip("/") == url.rstrip("/"):
                break
            img = make_with_logo(url, logo_ratio=ratio)
            img.convert("RGB").save(png, quality=95)
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,
                           image_factory=SvgPathImage, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        qr.make_image().save(out / f"{name}.svg")

        got = verify(png)
        if got and got.rstrip("/") == url.rstrip("/"):
            ok += 1
            mark = "✓ 掃得到"
        elif got is None:
            mark = "（未驗證，缺 cv2）"
        else:
            fail += 1
            mark = f"✗ 解出不同內容：{got[:40]}"
        print(f"{label:<8} {png.name:<12} {img.width}px  {mark}")

    print(f"\n完成 {len(targets)} 組；驗證通過 {ok}、失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
