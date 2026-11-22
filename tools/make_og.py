#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生每集的分享卡（1200×630 OG 圖）＋ LINE 轉傳用的靜態分享頁。

用法：
    python3 tools/make_og.py --base https://grace-shop-radio.netlify.app
輸出：
    images/og/<n>.png      1200×630，LINE／FB 預覽圖
    s/<n>.html             有 OG meta 的靜態頁，自動跳轉到 App 深連結
"""
import argparse, base64, json, pathlib, shutil, subprocess, tempfile
from string import Template

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

TPL = Template("""<!doctype html><html lang="zh-Hant-TW"><head><meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1200px;height:630px;overflow:hidden;font-family:"Noto Serif TC","PingFang TC",serif;
 background:radial-gradient(900px 500px at 50% -10%,#4a2b19 0%,#241408 55%,#150c07 100%);color:#f6eedd;position:relative}
.frame{position:absolute;inset:26px;border:1px solid rgba(201,162,39,.35);border-radius:10px}
.inner{position:absolute;left:64px;top:58px;right:250px}
.onair{display:flex;align-items:center;gap:12px;font-size:22px;letter-spacing:.22em;color:#e0c79c;font-weight:700}
.lamp{width:16px;height:16px;border-radius:50%;background:radial-gradient(circle at 35% 32%,#ffb9a8,#c0392b 45%,#5c1108);box-shadow:0 0 16px rgba(255,80,50,.75)}
.station{font-size:30px;letter-spacing:.2em;color:#f6e3bd;font-weight:900;margin-left:6px}
.meta{margin-top:34px;display:flex;align-items:center;gap:16px}
.no{background:#b23a2b;color:#fff6e6;font-size:30px;font-weight:900;padding:6px 18px;border-radius:4px;letter-spacing:.06em}
.cat{font-size:24px;color:#c8a97c;letter-spacing:.1em}
h1{margin-top:26px;font-size:52px;line-height:1.34;font-weight:900;letter-spacing:.02em;
 display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;max-width:820px}
.ex{margin-top:22px;font-size:24px;line-height:1.6;color:#cdb894;max-width:760px;
 display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.qr{position:absolute;right:64px;bottom:74px;width:210px;text-align:center}
.qr img{width:210px;height:210px;background:#fff;padding:12px;border-radius:8px;display:block}
.qr span{display:block;margin-top:12px;font-size:19px;color:#c8a97c;letter-spacing:.14em}
.foot{position:absolute;left:64px;bottom:56px;font-size:20px;color:#8f7350;letter-spacing:.18em}
</style></head><body>
<div class="frame"></div>
<div class="inner">
  <div class="onair"><span class="lamp"></span>ON AIR<span class="station">光碼電台</span></div>
  <div class="meta"><span class="no">#$no</span><span class="cat">$cat</span></div>
  <h1>$title</h1>
  <div class="ex">$excerpt</div>
</div>
<div class="qr"><img src="data:image/png;base64,$qr"><span>掃我聽故事</span></div>
<div class="foot">歲月恩典館 ・ AM 1080</div>
</body></html>""")

SHARE = Template("""<!doctype html><html lang="zh-Hant-TW"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>#$no $cat｜$title</title>
<meta property="og:type" content="article">
<meta property="og:site_name" content="光碼電台・歲月恩典館">
<meta property="og:title" content="#$no $title">
<meta property="og:description" content="$excerpt">
<meta property="og:image" content="$base/images/og/$n.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="$base/s/$n.html">
<meta name="twitter:card" content="summary_large_image">
<script>location.replace("$base/#/story/$sid");</script>
</head>
<body style="background:#1b0f09;color:#f0dcb4;font-family:system-ui,sans-serif;margin:0;padding:40px 24px;text-align:center">
<p style="font-size:18px;line-height:1.8">正在打開「#$no $title」…</p>
<p><a href="$base/#/story/$sid" style="color:#e8ce7a">沒有自動跳轉，點這裡</a></p>
</body></html>""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://grace-shop-radio.netlify.app")
    a = ap.parse_args()

    stories = json.load(open(ROOT / "stories.json", encoding="utf-8"))
    stories.sort(key=lambda s: s.get("sort", 1))
    (ROOT / "images" / "og").mkdir(parents=True, exist_ok=True)
    (ROOT / "s").mkdir(exist_ok=True)

    tmp = pathlib.Path(tempfile.mkdtemp())
    for s in stories:
        n = int(s["sort"])
        qr_path = ROOT / "images" / "qr" / f"{n:02d}_qr.png"
        qr_b64 = base64.b64encode(qr_path.read_bytes()).decode() if qr_path.exists() else ""
        html = TPL.substitute(
            no=f"{n:03d}",
            cat=s.get("categoryName", ""),
            title=s.get("title", ""),
            excerpt=s.get("excerpt", ""),
            qr=qr_b64,
        )
        page = tmp / f"{n}.html"
        page.write_text(html, encoding="utf-8")
        out_png = ROOT / "images" / "og" / f"{n}.png"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        f"--user-data-dir={tmp}/prof{n}", "--window-size=1200,630",
                        "--virtual-time-budget=5000", f"--screenshot={out_png}", page.as_uri()],
                       check=True, capture_output=True)
        (ROOT / "s" / f"{n}.html").write_text(SHARE.substitute(
            no=f"{n:03d}", cat=s.get("categoryName", ""), title=s.get("title", ""),
            excerpt=s.get("excerpt", ""), base=a.base, n=n, sid=s["id"]), encoding="utf-8")
        print(f"#{n:03d}  {out_png.name}  s/{n}.html")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(stories)} 張分享卡 + {len(stories)} 個分享頁完成")


if __name__ == "__main__":
    main()
