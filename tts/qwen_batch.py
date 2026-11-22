#!/usr/bin/env python3
"""把 tts/播稿/epNN.txt 送進本機 Qwen3-TTS 控制台，存成 mp3/epNN.mp3。

用法：
  python3 tts/qwen_batch.py --ep 05
  python3 tts/qwen_batch.py --ep all
前置：控制台已在 http://127.0.0.1:8766 執行。
"""
import argparse, json, pathlib, sys, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:8766"
ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "tts" / "播稿_口語"
MP3_DIR = ROOT / "mp3"

SPEAKER = {
    "旁白": {
        "voice": "ryan",
        "age": 50,
        "tone": "像台灣的電台主持人，口語自然、親切，語速偏慢，句尾放鬆，不要播報腔",
        "speed": 0.9,
        "pause_ms": 700,
    }
}


DIALOGUE_SPEAKERS = {
    "主持人": {
        "voice": "vivian", "age": 42,
        "tone": "語調溫暖親切，像電台主持人對長輩說話，句尾自然放鬆，帶一點好奇",
        "speed": 0.92, "pause_ms": 350,
    },
    "受訪者": {
        "voice": "uncle_fu", "age": 66,
        "tone": "聲音低沉厚實、沉穩、語速偏慢、溫暖可信，說話像在回想往事",
        "speed": 0.86, "pause_ms": 500,
    },
}


def post(path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode("utf-8", "replace")}


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return r.read()


def status(tid):
    return json.loads(get("/api/status?id=" + tid).decode("utf-8"))


def run_ep(num, dialogue=False):
    src = SCRIPT_DIR / (f"ep{num}_訪問稿.txt" if dialogue else f"ep{num}.txt")
    if not src.exists():
        print(f"!! 找不到 {src}")
        return False
    text = src.read_text(encoding="utf-8").strip()
    print(f"[ep{num}{'_訪談' if dialogue else ''}] {len(text)} 字 → 送單")
    res = post("/api/generate", {
        "mode": "dialogue" if dialogue else "single",
        "text": text,
        "speakers": DIALOGUE_SPEAKERS if dialogue else SPEAKER,
        "paragraph_pause_ms": 800,
    })
    if "id" not in res:
        print("!! 送單失敗", res)
        return False
    tid = res["id"]
    last = ""
    while True:
        st = status(tid)
        msg = f"{st.get('state')} {st.get('progress')}% {st.get('message','')}"
        if msg != last:
            print("   ", msg)
            last = msg
        if st.get("state") == "done":
            fn = st.get("filename")
            blob = get("/api/audio/" + fn)
            out = MP3_DIR / (f"ep{num}_訪問.mp3" if dialogue else f"ep{num}.mp3")
            out.write_bytes(blob)
            print(f"    ✓ {out.name}  {len(blob)/1024:.0f} KB")
            return True
        if st.get("state") == "error":
            print("!! 生成失敗：", st.get("error"))
            return False
        time.sleep(4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", default="all")
    ap.add_argument("--dialogue", action="store_true", help="跑雙人訪問稿 epNN_訪問稿.txt")
    a = ap.parse_args()
    nums = [f"{i:02d}" for i in range(1, 11)] if a.ep == "all" else [a.ep.zfill(2)]
    for n in nums:
        if not run_ep(n, a.dialogue):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
