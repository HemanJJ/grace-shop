#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""9 條聲線同句試聽（每條約 15 秒），用來挑台灣腔的主持人聲。

用法：python3 tts/make_voice_samples.py
前置：控制台在 http://127.0.0.1:8766
輸出：audio_demo/9聲線/<n>_<voice>.mp3
"""
import json, pathlib, sys, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:8766"
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "audio_demo" / "9聲線"

TEXT = ("各位聽眾朋友，晚上好，我是阿光。今天要說的，是一位七十六歲的老牧師，"
        "他每天早上六點半，都會泡一杯熱咖啡，放在對面那張空著的藤椅前。")

VOICES = [
    ("vivian",   "Vivian｜溫暖自然女聲"),
    ("uncle_fu", "Uncle Fu｜低沉厚實男聲"),
    ("serena",   "Serena｜清澈溫柔女聲"),
    ("ryan",     "Ryan｜明亮穩重男聲"),
    ("aiden",    "Aiden｜年輕自然男聲"),
    ("ono_anna", "Ono Anna｜輕柔女聲"),
    ("sohee",    "Sohee｜甜淨女聲"),
    ("eric",     "Eric｜成熟男聲"),
    ("dylan",    "Dylan｜低沉男聲"),
]

TONE = "口語自然，像台灣的電台主持人對長輩說話，語速偏慢，句尾放鬆"


def post(path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode("utf-8", "replace")}


def gen(voice):
    res = post("/api/generate", {
        "mode": "single",
        "text": TEXT,
        "speakers": {"旁白": {"voice": voice, "age": 50, "tone": TONE, "speed": 0.9, "pause_ms": 600}},
        "paragraph_pause_ms": 700,
        "sentence_pause_ms": 150,
    })
    if "id" not in res:
        return None, res
    tid = res["id"]
    while True:
        with urllib.request.urlopen(f"{BASE}/api/status?id={tid}", timeout=30) as r:
            st = json.loads(r.read().decode())
        if st.get("state") == "done":
            return st.get("filename"), None
        if st.get("state") == "error":
            return None, st
        time.sleep(3)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (vid, label) in enumerate(VOICES, 1):
        fn, err = gen(vid)
        if not fn:
            print(f"!! {vid} 失敗：{err}")
            continue
        with urllib.request.urlopen(f"{BASE}/api/audio/{fn}", timeout=60) as r:
            blob = r.read()
        p = OUT / f"{i:02d}_{vid}.mp3"
        p.write_bytes(blob)
        print(f"{i:02d} {vid:<9} {len(blob)/1024:.0f} KB  {p.name}")
    print("完成")


if __name__ == "__main__":
    sys.exit(main())
