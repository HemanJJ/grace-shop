#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""播稿口語化：進 TTS 前把「不像人話」的東西清掉。

規則（保守，不動意思）：
 1. 台語字詞換成國語（TTS 會唸錯）
 2. 去掉引號，保留內容（避免模型在引號處換語氣）
 3. 省略號換逗號
 4. 括號整段移除（含內容），例如「（或作…）」
 5. 超過 55 字又含逗號的長句，在最靠近中間的逗號斷成兩句
 6. 阿拉伯數字轉中文（1–9999）
用法：
  python3 tools/colloquial.py --ep 05        # 預覽
  python3 tools/colloquial.py --all --write  # 寫回 tts/播稿_口語/
"""
import argparse, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "tts" / "播稿"
DST = ROOT / "tts" / "播稿_口語"

# 1) 台語詞 → 國語
WORDS = {
    "暗時": "晚上", "恁": "你們", "咱": "我們", "厝": "家", "囡仔": "孩子",
    "攏": "都", "袂": "不會", "抑是": "還是", "佇": "在", "真濟": "很多",
    "遮": "這裡", "遐": "那裡", "予": "給", "伊": "他",
}

DIGIT = "零一二三四五六七八九"


def zh_num(n: int) -> str:
    if n < 10:
        return DIGIT[n]
    if n < 20:
        return "十" + (DIGIT[n % 10] if n % 10 else "")
    if n < 100:
        return DIGIT[n // 10] + "十" + (DIGIT[n % 10] if n % 10 else "")
    if n < 1000:
        tail = n % 100
        s = DIGIT[n // 100] + "百"
        if tail == 0:
            return s
        if tail < 10:
            return s + "零" + DIGIT[tail]
        return s + (zh_num(tail) if tail >= 20 else "一" + zh_num(tail))
    if n < 10000:
        s = DIGIT[n // 1000] + "千"
        tail = n % 1000
        if tail == 0:
            return s
        if tail < 100:
            return s + "零" + zh_num(tail)
        return s + zh_num(tail)
    return str(n)


def colloquial(text: str) -> str:
    for k, v in WORDS.items():
        text = text.replace(k, v)

    # 4) 括號整段移除（先做，避免裡面的逗號被當斷句點）
    text = re.sub(r"（[^）]*）|\([^)]*\)", "", text)

    # 2) 引號去殼
    text = re.sub(r"[「」『』“”\"]", "", text)

    # 3) 省略號
    text = text.replace("…", "，").replace("⋯", "，")

    # 6) 數字
    def _num(m):
        n = int(m.group(0))
        return zh_num(n) if n <= 9999 else m.group(0)
    text = re.sub(r"(?<![0-9A-Za-z])\d+(?![0-9A-Za-z])", _num, text)

    # 5) 長句斷句
    out = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            out.append("")
            continue
        sentences = re.findall(r"[^。！？!?]+[。！？!?]?", para)
        fixed = []
        for s in sentences:
            s = s.strip()
            while len(s) > 55:
                commas = [m.start() for m in re.finditer("，", s)]
                if not commas:
                    break
                target = min(commas, key=lambda i: abs(i - len(s) // 2))
                fixed.append(s[: target + 1].strip())
                s = s[target + 1 :].strip()
            if s:
                fixed.append(s)
        out.append("".join(fixed))
    text = "\n".join(out)

    # 收尾整理：標點與空白
    text = text.replace("\u3000", " ")                      # 全形空白
    text = "\n".join(l.lstrip(" \t") for l in text.split("\n"))  # 行首縮排
    text = re.sub(r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])", r"\1\2", text)  # 中文之間空格
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"，{2,}", "，", text)
    text = re.sub(r"，。", "。", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", default="05")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    nums = [f"{i:02d}" for i in range(1, 11)] if a.all else [a.ep.zfill(2)]
    DST.mkdir(parents=True, exist_ok=True)
    for n in nums:
        src = SRC / f"ep{n}.txt"
        if not src.exists():
            print("跳過", src.name); continue
        raw = src.read_text(encoding="utf-8")
        clean = colloquial(raw)
        before = len(raw.replace("\n", ""))
        after = len(clean.replace("\n", ""))
        print(f"ep{n}: {before} → {after} 字")
        if a.write:
            (DST / f"ep{n}.txt").write_text(clean, encoding="utf-8")
        else:
            print(clean[:400], "\n---")
    if a.write:
        print("已寫入", DST)


if __name__ == "__main__":
    sys.exit(main())
