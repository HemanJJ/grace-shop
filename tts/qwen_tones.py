#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""依「語氣對照表」重出十集（Ryan 固定，換語氣不換人）。

對照表見 tts/語氣對照.md。
用法：python3 tts/qwen_tones.py [--ep 04] [--all]
"""
import argparse, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL_DIR = pathlib.Path("/Users/defi/Documents/Codex/2026-10-29/users-defi-ai-md-users-defi-3/work/tts_qwen/models/Qwen3-TTS-1.7B")
SRC = ROOT / "tts" / "播稿_口語"
MP3 = ROOT / "mp3"
WORKROOT = ROOT / "audio_demo" / "_tones"

# 集數 → (聲線, 年齡, 語速, 語氣描述, 講者停頓, 段落停頓, 句間停頓)
TONES = {
    # 2026-11-10 定案：全站統一「阿光・慢版」（以 #005 為基準，已由業主確認最像本人）
    "01": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
    "02": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
    "03": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
    "04": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
    "05": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
    "06": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
    "07": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
    "08": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
    "09": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
    "10": ("ryan", 50, 0.86, "低沉、語速慢、句子之間留白，像深夜電台陪長輩說話，句尾放輕", 900, 1100, 200),
}

ALT_03 = ("sohee", 58, 0.84, "輕柔、慢、氣聲多一點，像夜裡陪著人守候，不要明亮", 950, 1200, 220)


def gen_block(model, text, cfg, work, prefix):
    from mlx_audio.tts.generate import generate_audio
    # 先清掉同前綴的舊檔，避免抓到上一次的殘留（曾因此把女聲當成男聲用）
    for old in work.glob(f"{prefix}*.wav"):
        old.unlink()
    voice, age, speed, tone, pause, para, sent = cfg
    instruct = f"聲音年齡感約{age}歲。{tone}。請用繁體中文，台灣口音，自然口語。"
    generate_audio(text, model=model, voice=voice, lang_code="zh", instruct=instruct,
                   speed=speed, output_path=str(work), file_prefix=prefix,
                   audio_format="wav", join_audio=True, verbose=False,
                   ddpm_steps=50, max_tokens=12000)
    got = sorted(work.glob(f"{prefix}*.wav"))
    if not got:
        raise RuntimeError("沒有產出")
    return got[-1]


def to_mp3(src, dst, pad=0.5):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-af", ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.10,"
                            "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.30,areverse,"
                            f"apad=pad_dur={pad}"),
                    "-ar", "44100", "-ac", "2", "-b:a", "192k", str(dst)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", default="")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    nums = sorted(TONES) if a.all or not a.ep else [a.ep.zfill(2)]

    from mlx_audio.tts import load_model
    model = load_model(MODEL_DIR)
    print("模型就緒", flush=True)

    for n in nums:
        src = SRC / f"ep{n}.txt"
        if not src.exists():
            print("跳過", n); continue
        text = src.read_text(encoding="utf-8").replace("\n", "").strip()
        work = WORKROOT / f"ep{n}"; work.mkdir(parents=True, exist_ok=True)
        for old in work.glob("*.wav"):
            old.unlink()
        t = time.time()
        wav = gen_block(model, text, TONES[n], work, f"t{n}")
        out = MP3 / f"ep{n}.mp3"
        to_mp3(wav, out)
        dur = subprocess.run(["afinfo", str(out)], capture_output=True, text=True).stdout
        m = re.search(r"estimated duration: ([\d.]+)", dur)
        print(f"✓ ep{n} {TONES[n][0]} {TONES[n][2]:.2f}x → {float(m.group(1)) if m else 0:.0f}s ({time.time()-t:.0f}s)", flush=True)


    return 0


if __name__ == "__main__":
    sys.exit(main())
