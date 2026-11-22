#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""破音字檢查：掃出 TTS 容易唸錯的多音字，附上下文，讓人決定要不要換字。

用法：
    python3 tools/polyphone_check.py                  # 掃十集
    python3 tools/polyphone_check.py --text "..."     # 掃一段
"""
import argparse, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "tts" / "播稿_口語"

# （字, 常見誤讀說明, 建議改寫詞）
POLY = {
    "還": ("hái / huán", "還是、還有 → hái；歸還、還錢 → huán"),
    "了": ("le / liǎo", "好了 → le；受不了、了解 → liǎo"),
    "行": ("xíng / háng", "可以 → xíng；銀行、行業 → háng"),
    "長": ("cháng / zhǎng", "很長 → cháng；長輩、長老 → zhǎng"),
    "重": ("zhòng / chóng", "重要 → zhòng；重來、重複 → chóng"),
    "發": ("fā / fà", "發現 → fā；頭髮 → fà"),
    "樂": ("lè / yuè", "快樂 → lè；音樂 → yuè"),
    "數": ("shù / shǔ", "數字 → shù；數一數 → shǔ"),
    "差": ("chā / chà / chāi", "差別 → chā；差不多 → chà"),
    "調": ("diào / tiáo", "聲調 → diào；調整 → tiáo"),
    "散": ("sàn / sǎn", "散步 → sàn；零散 → sǎn"),
    "傳": ("chuán / zhuàn", "傳福音 → chuán；自傳 → zhuàn"),
    "著": ("zhe / zháo / zhuó", "看著 → zhe；睡著 → zháo"),
    "得": ("de / dé / děi", "跑得快 → de；得到 → dé"),
    "地": ("de / dì", "慢慢地 → de；土地 → dì"),
    "角": ("jiǎo / jué", "角落 → jiǎo；角色 → jué"),
    "量": ("liàng / liáng", "力量 → liàng；量血壓 → liáng"),
    "會": ("huì / kuài", "教會 → huì（口語多讀 huì）；會計 → kuài"),
    "好": ("hǎo / hào", "好人 → hǎo；愛好 → hào"),
    "種": ("zhǒng / zhòng", "種類 → zhǒng；種田 → zhòng"),
    "空": ("kōng / kòng", "空氣 → kōng；有空 → kòng"),
    "中": ("zhōng / zhòng", "中間 → zhōng；中獎 → zhòng"),
    "便": ("biàn / pián", "方便 → biàn；便宜 → pián"),
    "沒": ("méi / mò", "沒有 → méi；淹沒 → mò"),
    "給": ("gěi / jǐ", "給你 → gěi；供給 → jǐ"),
    "血": ("xuè / xiě", "血壓 → xuè（口語 xiě）"),
    "拾": ("shí / shè", "收拾 → shi；拾荒 → shí"),
    "辦": ("bàn", "只有一讀，常見誤標"),
    "爸": ("bà", "單音"),
    "行行": ("—", "疊字最容易錯"),
}


def scan(text: str):
    hits = []
    for ch, (reading, note) in POLY.items():
        for m in re.finditer(re.escape(ch), text):
            a, b = max(0, m.start() - 8), min(len(text), m.end() + 8)
            ctx = text[a:b].replace("\n", "")
            hits.append((ch, reading, note, ctx))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="")
    ap.add_argument("--ep", default="")
    a = ap.parse_args()

    if a.text:
        files = [("輸入文字", a.text)]
    else:
        nums = [a.ep.zfill(2)] if a.ep else [f"{i:02d}" for i in range(1, 11)]
        files = [(f"ep{n}", (SRC / f"ep{n}.txt").read_text(encoding="utf-8")) for n in nums
                 if (SRC / f"ep{n}.txt").exists()]

    total = 0
    for name, text in files:
        hits = scan(text)
        if not hits:
            continue
        total += len(hits)
        print(f"\n=== {name}：{len(hits)} 處 ===")
        seen = set()
        for ch, reading, note, ctx in hits:
            key = (ch, ctx)
            if key in seen:
                continue
            seen.add(key)
            print(f"  「{ch}」{reading}　…{ctx}…")
    print(f"\n合計 {total} 處需要人看一眼（不是每個都錯，只是有風險）")


if __name__ == "__main__":
    sys.exit(main())
