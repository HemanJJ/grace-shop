#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
古早收音機版音檔產生器（edge-tts zh-TW 神經語音）
用法：
  python3 tts/build_radio.py --ep 05 --voice YunJheNeural
  python3 tts/build_radio.py --ep all --voice YunJheNeural
輸出：mp3/<編號>_<篇名>.mp3（檔名與 stories.json 的 mp3File 完全一致）
"""
import argparse, json, os, re, subprocess, sys, tempfile, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MP3DIR = ROOT / "mp3"
TTSDIR = ROOT / "tts"

VOICES = {
    "YunJheNeural": "zh-TW-YunJheNeural",     # 男聲・說書人
    "HsiaoChenNeural": "zh-TW-HsiaoChenNeural",  # 女聲・曉臻
    "HsiaoYuNeural": "zh-TW-HsiaoYuNeural",   # 女聲・曉雨
}

# ---- 10 集電台腳本 ----
# intro：開場（主持人）；scripture 會自動從 tts/NN.txt 第 5 行抓；
# pitch：工商服務（把第 4 行產品段落改寫成主持人語氣）；outro：結尾 CTA。
RADIO = {
    "01": dict(name="愛篇_林伯伯熱芝麻拿鐵", kind="ad", extra=False,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道。今天要講的，是一對結縭五十年的老夫婦。老先生有一點失智，連今天是星期幾都記不得，但是他每天早上七點，還是會站在廚房，幫太太溫一杯牛奶。",
        pitch="聽眾朋友，想要對老伴好一點，這組很實在。無糖黑芝麻粉，配半低因的濾掛咖啡，沖進熱牛奶，又香又濃。一組八百八十元，有芝麻粉一罐、濾掛十包，還有一張雙人祝福卡。買給自己，還是囡仔買來送爸媽，都很體面。加我們的 LINE，用 LINE Pay 就能帶回家。"),
    "02": dict(name="饒恕篇_李長老父子破冰咖啡", kind="bless", extra=True,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道。今天要講的，是一對冷戰十年的父子。兩個人住得不遠，卻十年沒有坐下來好好吃一頓飯。",
        pitch="故事講到這裡。這集，我們沒有要賣東西。如果你家裡也有一個，十年沒有好好講話的人，今天，先傳一個貼圖給他。想聽更多故事，加我們的 LINE 好友，新的一集上架，我們用電台通知你。咱，後一集，再會。"),
    "03": dict(name="等候篇_吳師母洋甘菊博士茶", kind="ad", extra=False,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道。今天要講的，是加護病房外面，十四個睡不著的夜晚。",
        pitch="睡不著的聽眾朋友，這壺可以參考。南非博士茶加洋甘菊，零咖啡因，泡起來有一股淡淡的草本香。睡前一個小時，泡一杯熱的，坐下來，讀一段詩篇，讓自己安靜。一盒二十包，四百六十元，買兩盒，送大字版的平安經文卡。加 LINE，用 LINE Pay。"),
    "04": dict(name="盼望篇_82歲王奶奶長青詩班", kind="bless", extra=False,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道。今天要講的，是一位八十二歲的奶奶。她說自己五音不全，這輩子不敢開口唱歌。",
        pitch="故事講到這裡。這集沒有要賣東西。如果你身邊也有一個，說自己老了、學不會的長輩，跟他說一句：天父聽詩歌，不是聽技巧，是聽你喜樂的心。想聽更多故事，加我們的 LINE。咱，後一集，再會。"),
    "05": dict(name="平安篇_林牧師清晨六點半的熱咖啡", kind="ad", extra=False,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道，現在時間，暗時九點。今天要講的，是一位七十六歲的老牧師。師母走了三年，但是他每天早上六點半，還是會泡一杯熱咖啡，放在對面那張空著的藤椅前。",
        pitch="聽眾朋友，你也想要每天早上，有一杯熱咖啡，陪你好好跟天父說說話嗎？這組「牧者的晨更陪伴」，是半低因的濾掛咖啡。我們特別把林牧師這段見證，錄成一段語音，印在每一包十乘十二公分的外袋上。手機一掃，就有林牧師的聲音，陪你過一個平安的早晨。一盒十包，四百九十元。教會團購五盒，另外有優惠。買給自己，或是送給獨居的老朋友，都很合適。"),
    "06": dict(name="恩典篇_張長老不灑農藥的黃金苦茶油", kind="ad", extra=False,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道。今天要講的，是海拔一千公尺的山上，一位被笑是傻瓜的泰雅族長老。",
        pitch="這瓶油，是山上的長老，一粒一粒顧出來的。冷壓初榨，開瓶有一股淡淡的堅果香。拌麵線、拌青菜，還是早上溫溫喝一小匙，都很合。五百毫升，一千兩百八十元，附一張有聲見證吊牌。孝親雙瓶禮盒，兩千三百八十元，免運。加 LINE，用 LINE Pay。"),
    "07": dict(name="陪伴篇_美玲姊週三下午手沖約定", kind="bless", extra=False,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道。今天要講的，是每禮拜三下午三點，那一聲敲門。",
        pitch="故事講到這裡。這集沒有要賣東西。下禮拜三下午三點，換你去敲一次門，帶兩包濾掛咖啡就好。想聽更多故事，加我們的 LINE。咱，後一集，再會。"),
    "08": dict(name="感恩篇_許長老紅藜麥豐收感恩", kind="ad", extra=False,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道。今天要講的，是屏東一位長老，差一點就保不住的那一隻腳。",
        pitch="煮飯的時候，加一小匙紅藜麥，軟糯好咀嚼，牙口不好的長輩也吃得下。台灣高山種的，脫殼免洗，拆開就能煮。一組七百九十元，紅藜兩包，加一罐無糖堅果穀粉。加 LINE，用 LINE Pay。"),
    "09": dict(name="重新開始篇_76歲周伯伯背吉他唱詩歌", kind="ad", extra=False,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道。今天要講的，是一位七十六歲的阿伯，背著一把吉他，走進病房。",
        pitch="天氣一冷，膝蓋就先知道。這組護膝，遠紅外線布料，不緊繃、不捲邊，穿去聚會、去菜市場，一整天也不會滑下來。配兩罐無糖高鈣黑芝麻粉，早上沖一杯，暖暖的。一組一千一百八十元。加 LINE，用 LINE Pay。"),
    "10": dict(name="回家篇_陳媽媽熬了四十年的禱告湯", kind="ad", extra=False,
        intro="各位聽眾朋友，大家好，我是阿光，歡迎轉到恩典頻道。今天要講的，是一鍋熬了四十年的湯。",
        pitch="陳媽媽那鍋湯，我們把它做成常溫包。不用冷凍、不用開瓦斯，長輩早上放進馬克杯，泡熱水三分鐘，就有一碗熱湯。一盒十包，一千五百八十元，免費幫你代寫孝親小卡。買一盒寄回老家，就像你每天陪爸媽吃早餐。加 LINE，用 LINE Pay。"),
}


def read_lines(num):
    p = TTSDIR / f"{num}.txt"
    lines = [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return lines


def say(text, voice, out, rate="-6%", pitch_hz="-2Hz"):
    subprocess.run([
        "edge-tts", "--voice", VOICES[voice], f"--rate={rate}", f"--pitch={pitch_hz}",
        "--text", text, "--write-media", str(out),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def build_one(num, voice, dry=False):
    cfg = RADIO[num]
    lines = read_lines(num)      # [0]=篇名 [1]=第1段 [2]=第2段 [3]=產品段/故事段 [4]=經文
    story = lines[1] + "\n" + lines[2]
    if cfg.get("extra") and len(lines) > 4:
        story += "\n" + lines[3]
    scripture = lines[4]

    if cfg["kind"] == "ad":
        segments = [
            ("opening", cfg["intro"]),
            ("story", story),
            ("scripture", scripture),
            ("adbreak", "故事講到這裡。接下來，是今天的工商服務時間。"),
            ("pitch", cfg["pitch"]),
        ]
    else:
        segments = [
            ("opening", cfg["intro"]),
            ("story", story),
            ("scripture", scripture),
            ("pitch", cfg["pitch"]),
        ]

    out = MP3DIR / f"{num}_{cfg['name']}.mp3"
    print(f"[{num}] {out.name}  voice={voice}  segs={len(segments)}")
    if dry:
        for k, tx in segments:
            print(f"   - {k}: {len(tx)} 字")
        return out

    MP3DIR.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        parts = []
        for i, (key, text) in enumerate(segments):
            f = td / f"{i:02d}_{key}.mp3"
            say(text, voice, f)
            parts.append(f)
        sil = td / "sil.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", "anullsrc=r=24000:cl=mono", "-t", "0.35", str(sil)], check=True)
        lst = td / "list.txt"
        rows = []
        for i, fp in enumerate(parts):
            rows.append("file '%s'" % fp)
            if i < len(parts) - 1:
                rows.append("file '%s'" % sil)
                if segments[i + 1][0] == "adbreak":
                    rows.append("file '%s'" % sil)
        lst.write_text("\n".join(rows) + "\n", encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-codec:a", "libmp3lame", "-q:a", "3", "-ar", "24000",
                        str(out)], check=True)
    size = out.stat().st_size
    dur = subprocess.run(["afinfo", str(out)], capture_output=True, text=True).stdout
    m = re.search(r"estimated duration: ([0-9.]+)", dur)
    print("   -> %.0f KB, %.0f 秒" % (size/1024, float(m.group(1)) if m else 0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", default="all")
    ap.add_argument("--voice", default="YunJheNeural")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    nums = sorted(RADIO) if a.ep == "all" else [a.ep.zfill(2)]
    for n in nums:
        build_one(n, a.voice, a.dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
