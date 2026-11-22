#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B 式配音：整段生成，但「每 ~2 分鐘強迫分段」，接縫做交叉淡入淡出。

為什麼這樣做：
  · 一次生完最穩（B 版），但太長會退化 / 截斷 → 每段約 2 分鐘切一次。
  · 切點只在句號後，不會切斷句子。
  · 接縫處做 0.25 秒 crossfade ＋ 去頭尾靜音，把音色跳動藏起來。

用法：
  python3 tts/qwen_blocks.py --ep 05          # 只做一集
  python3 tts/qwen_blocks.py --all            # 十集
"""
import argparse, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL_DIR = pathlib.Path("/Users/defi/Documents/Codex/2026-10-29/users-defi-ai-md-users-defi-3/work/tts_qwen/models/Qwen3-TTS-1.7B")
SRC = ROOT / "tts" / "播稿_口語"
MP3 = ROOT / "mp3"
WORKROOT = ROOT / "audio_demo" / "_blocks"

TARGET_CHARS = 380          # 約 2 分鐘
INSTRUCT = "像台灣的電台主持人，口語自然、親切，語速偏慢，句尾放鬆，不要播報腔"
SEAM_GAP = 1.0            # 接縫留白（秒），不用淡接
GAP = 0.45                  # 接縫後補的停頓（秒）


def split_blocks(text: str, target: int = TARGET_CHARS) -> list[str]:
    text = text.replace("\n", "").strip()
    sentences = re.findall(r"[^。！？!?]+[。！？!?]?", text)
    blocks, buf = [], ""
    for s in sentences:
        if not s.strip():
            continue
        if buf and len(buf) + len(s) > target:
            blocks.append(buf.strip())
            buf = ""
        buf += s
    if buf.strip():
        blocks.append(buf.strip())
    return blocks


def trim(src: pathlib.Path, dst: pathlib.Path):
    """去掉頭尾靜音，前後各留 0.08 秒。"""
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
        "-af", ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,"
                "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,areverse"),
        "-ar", "24000", "-ac", "2", str(dst)
    ], check=True)


def stitch(parts: list[pathlib.Path], out_mp3: pathlib.Path):
    """段與段之間不做淡接：讓每段平穩收尾，留 1 秒空白，再接下一段。"""
    if len(parts) == 1:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(parts[0]),
                        "-af", "apad=pad_dur=0.6", "-ar", "44100", "-ac", "2",
                        "-b:a", "192k", str(out_mp3)], check=True)
        return

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p in parts:
        cmd += ["-i", str(p)]
    # 產生 1 秒靜音
    cmd += ["-f", "lavfi", "-t", f"{SEAM_GAP}", "-i", "anullsrc=r=44100:cl=stereo"]
    n = len(parts)
    sil = f"{n}:a"
    order = []
    for i in range(n):
        order.append(f"[{i}:a]")
        if i < n - 1:
            order.append(f"[{sil}]")
    fc = "".join(order) + f"concat=n={len(order)}:v=0:a=1[joined];[joined]apad=pad_dur=0.6[out]"
    cmd += ["-filter_complex", fc, "-map", "[out]", "-ar", "44100", "-ac", "2",
            "-b:a", "192k", str(out_mp3)]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", default="05")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--target", type=int, default=TARGET_CHARS, help="每段目標字數；設大一點就是整篇一次")
    a = ap.parse_args()

    nums = [f"{i:02d}" for i in range(1, 11)] if a.all else [a.ep.zfill(2)]
    plan = {}
    for n in nums:
        src = SRC / f"ep{n}.txt"
        if not src.exists():
            continue
        blocks = split_blocks(src.read_text(encoding="utf-8"), a.target)
        plan[n] = blocks
        print(f"ep{n}: {sum(len(b) for b in blocks)} 字 → {len(blocks)} 段 {[len(b) for b in blocks]}")
    if a.dry:
        return 0

    from mlx_audio.tts import load_model
    from mlx_audio.tts.generate import generate_audio

    model = load_model(MODEL_DIR)
    print("模型就緒", flush=True)

    for n, blocks in plan.items():
        work = WORKROOT / f"ep{n}"
        work.mkdir(parents=True, exist_ok=True)
        parts = []
        for i, text in enumerate(blocks, 1):
            t = time.time()
            generate_audio(text, model=model, voice="ryan", lang_code="zh", instruct=INSTRUCT,
                           output_path=str(work), file_prefix=f"b{i:02d}", audio_format="wav",
                           join_audio=True, verbose=False, ddpm_steps=50, max_tokens=9000)
            got = sorted(work.glob(f"b{i:02d}*.wav"))
            if not got:
                print(f"!! ep{n} 第 {i} 段沒產出"); return 1
            clean = work / f"clean{i:02d}.wav"
            trim(got[-1], clean)
            parts.append(clean)
            print(f"  ep{n} 段{i}/{len(blocks)} {len(text)}字 {time.time()-t:.0f}s", flush=True)
        out = MP3 / f"ep{n}.mp3"
        stitch(parts, out)
        dur = subprocess.run(["afinfo", str(out)], capture_output=True, text=True).stdout
        m = re.search(r"estimated duration: ([\d.]+)", dur)
        print(f"✓ ep{n} → {out.name} {float(m.group(1)) if m else 0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
