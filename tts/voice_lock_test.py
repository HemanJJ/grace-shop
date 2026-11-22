#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""聲音鎖定測試：同一條聲線，比「沒有參考音」與「有參考音」的差別。

流程：
  1. 用 Ryan 唸一段參考稿 → ref.wav（聲音樣本）
  2. 同一句測試稿，兩種生法：
       A 只給 voice=ryan
       B 給 ref_audio + ref_text（聲音克隆）
  3. 再一句不同內容，也用 B 的方式 → C，驗證跨句穩定度

輸出：audio_demo/聲音測試/*.mp3
"""
import pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL_DIR = pathlib.Path("/Users/defi/Documents/Codex/2026-10-29/users-defi-ai-md-users-defi-3/work/tts_qwen/models/Qwen3-TTS-1.7B")
OUT = ROOT / "audio_demo" / "聲音測試"

REF_TEXT = "各位聽眾朋友，晚上好，我是光碼電台的主持人阿光。今天要說一個，關於一杯熱咖啡的故事。"
TEST_TEXT = "他每天早上六點半，都會泡一杯熱咖啡，放在對面那張空著的藤椅前。這是他跟師母，五十年來的約定。"
TEST_TEXT2 = "那天清晨下著雨，他在整理師母留下的大字聖經，翻到一張夾在詩篇裡的字條。"

INSTRUCT = "像台灣的電台主持人，口語自然、親切，語速偏慢，句尾放鬆，不要播報腔"


def to_mp3(wav: pathlib.Path, mp3: pathlib.Path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                    "-ar", "44100", "-ac", "2", "-b:a", "192k", str(mp3)], check=True)


def main():
    from mlx_audio.tts import load_model
    from mlx_audio.tts.generate import generate_audio

    OUT.mkdir(parents=True, exist_ok=True)
    work = OUT / "_wav"
    work.mkdir(exist_ok=True)

    print("載入模型…")
    t0 = time.time()
    model = load_model(MODEL_DIR)
    print(f"模型就緒（{time.time()-t0:.0f}s）")

    def gen(text, prefix, **kw):
        t = time.time()
        generate_audio(text, model=model, lang_code="zh", instruct=INSTRUCT,
                       output_path=str(work), file_prefix=prefix,
                       audio_format="wav", join_audio=True, verbose=False, ddpm_steps=50, **kw)
        files = sorted(work.glob(f"{prefix}*.wav"))
        if not files:
            raise RuntimeError(f"{prefix} 沒有產出")
        print(f"  {prefix}: {time.time()-t:.0f}s → {files[-1].name}")
        return files[-1]

    print("① 參考音（Ryan 唸 40 字）")
    ref = gen(REF_TEXT, "ref", voice="ryan")

    print("② A：只用 voice，不給參考音")
    a = gen(TEST_TEXT, "A_no_ref", voice="ryan")

    print("③ B：給參考音（聲音克隆）")
    b = gen(TEST_TEXT, "B_ref", ref_audio=str(ref), ref_text=REF_TEXT)

    print("④ C：換一句，同樣用參考音")
    c = gen(TEST_TEXT2, "C_ref2", ref_audio=str(ref), ref_text=REF_TEXT)

    for src, name in [(ref, "00_參考音"), (a, "01_A_無參考"), (b, "02_B_有參考"), (c, "03_C_換句有參考")]:
        to_mp3(src, OUT / f"{name}.mp3")
        print("輸出", name)

    print("完成 →", OUT)


if __name__ == "__main__":
    sys.exit(main())
