#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
☕ 咖啡時光廊・歲月恩典館 — 本機視覺化 CMS 維護後台 & GitHub Pages 一鍵發布伺服器
完全免 Google 試算表、免雲端轉檔、純 Python 標準庫零依賴。
"""

import base64
import json
import mimetypes
import os
import re
import subprocess
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parent
INDEX_HTML = ROOT_DIR / "index.html"
STORIES_JSON = ROOT_DIR / "stories.json"
IMAGES_DIR = ROOT_DIR / "images"
MP3_DIR = ROOT_DIR / "mp3"

IMAGES_DIR.mkdir(exist_ok=True)
MP3_DIR.mkdir(exist_ok=True)


def extract_stories_from_index() -> list:
    """若 stories.json 尚未建立，直接從 index.html 解析預設 10 篇故事"""
    if STORIES_JSON.exists():
        try:
            data = json.loads(STORIES_JSON.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception:
            pass

    if not INDEX_HTML.exists():
        return []

    html = INDEX_HTML.read_text(encoding="utf-8")
    m = re.search(r"const\s+STORIES_DB\s*=\s*(\[[\s\S]*?\])\s*;\s*\n\s*let\s+activeCategory", html)
    if not m:
        return []

    js_array = m.group(1)
    # 利用 node 或 python 轉換 JS object literal 為 JSON
    try:
        res = subprocess.run(
            ["node", "-e", f"const arr = {js_array}; console.log(JSON.stringify(arr));"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.strip())
            for idx, item in enumerate(data):
                item.setdefault("status", "published")
                item.setdefault("sort", idx + 1)
                item.setdefault("externalLink", "")
            STORIES_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
    except Exception:
        pass
    return []


def save_stories_everywhere(stories: list) -> None:
    """同時寫入 stories.json 與 index.html 的 STORIES_DB，確保線上與離線預覽 100% 同步"""
    json_str = json.dumps(stories, ensure_ascii=False, indent=4)
    STORIES_JSON.write_text(json_str, encoding="utf-8")

    if INDEX_HTML.exists():
        html = INDEX_HTML.read_text(encoding="utf-8")
        pattern = r"(const\s+STORIES_DB\s*=\s*)\[[\s\S]*?\](\s*;\s*\n\s*let\s+activeCategory)"
        if re.search(pattern, html):
            new_html = re.sub(pattern, lambda m: m.group(1) + json_str + m.group(2), html, count=1)
            INDEX_HTML.write_text(new_html, encoding="utf-8")


def get_git_info() -> dict:
    try:
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
        )
        remote_url = remote.stdout.strip() if remote.returncode == 0 else ""
        return {"hasGit": (ROOT_DIR / ".git").exists(), "remoteUrl": remote_url}
    except Exception:
        return {"hasGit": False, "remoteUrl": ""}


def publish_to_github(remote_url: str = "") -> dict:
    try:
        if not (ROOT_DIR / ".git").exists():
            subprocess.run(["git", "init"], cwd=str(ROOT_DIR), check=True)
            subprocess.run(["git", "branch", "-M", "main"], cwd=str(ROOT_DIR), check=True)

        if remote_url:
            has_origin = subprocess.run(
                ["git", "remote", "get-url", "origin"], cwd=str(ROOT_DIR), capture_output=True
            )
            if has_origin.returncode == 0:
                subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=str(ROOT_DIR), check=True)
            else:
                subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=str(ROOT_DIR), check=True)

        info = get_git_info()
        if not info.get("remoteUrl"):
            return {
                "success": False,
                "needRemote": True,
                "message": "尚未綁定新 GitHub 倉庫網址，請先輸入您的新 GitHub 倉庫網址（例如 https://github.com/HemanJJ/grace-shop.git）",
            }

        subprocess.run(["git", "add", "-A"], cwd=str(ROOT_DIR), check=True)
        commit_msg = f"CMS 更新故事與商品 ({time.strftime('%Y-%m-%d %H:%M:%S')})"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(ROOT_DIR), capture_output=True)
        push_res = subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if push_res.returncode != 0:
            return {"success": False, "message": "Git 推送失敗：" + (push_res.stderr or push_res.stdout)}

        return {"success": True, "message": "✅ 已成功儲存並推送到 GitHub Pages！約 30 秒後全球生效。"}
    except Exception as e:
        return {"success": False, "message": str(e)}


ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🛠️ 咖啡時光廊・歲月恩典館 — 本機視覺化 CMS 後台（免雲端轉檔・秒播版）</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #fff8ee;
      --bg-secondary: #f4e3cc;
      --text-primary: #2a1810;
      --text-secondary: #735b4a;
      --accent: #a45f38;
      --accent-hover: #7e4425;
      --card-bg: #fffcf6;
      --border-color: rgba(126, 68, 37, 0.2);
      --success: #2e7d32;
      --danger: #c0392b;
      --line-green: #06C755;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Noto Sans TC', system-ui, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
      padding-bottom: 60px;
    }
    .header {
      background: linear-gradient(135deg, #2c1910, #5c341f);
      color: #fff8ee;
      padding: 20px 28px;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 6px 20px rgba(0,0,0,0.18);
    }
    .header-inner {
      max-width: 1240px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
    }
    .header h1 {
      font-family: 'Noto Serif TC', serif;
      font-size: 1.45rem;
    }
    .header-sub {
      font-size: 0.82rem;
      color: #ffd89b;
    }
    .header-btns {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .btn {
      padding: 9px 18px;
      border-radius: 10px;
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
      border: none;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .btn-outline-light {
      background: rgba(255,255,255,0.12);
      color: #fff;
      border: 1px solid rgba(255,255,255,0.3);
    }
    .btn-publish {
      background: linear-gradient(135deg, #06C755, #04963f);
      color: #fff;
      box-shadow: 0 4px 14px rgba(6, 199, 85, 0.35);
    }
    .container {
      max-width: 1240px;
      margin: 24px auto;
      padding: 0 20px;
    }
    .stats-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 20px;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 16px 20px;
    }
    .stat-label { font-size: 0.82rem; color: var(--text-secondary); }
    .stat-value { font-family: 'Noto Serif TC', serif; font-size: 1.7rem; font-weight: 700; }
    .toolbar {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 18px;
      align-items: center;
    }
    .btn-add {
      background: var(--accent);
      color: #fff;
      padding: 11px 22px;
      border-radius: 10px;
      font-weight: 700;
      border: none;
      cursor: pointer;
      font-size: 0.95rem;
    }
    .search-input, .filter-select {
      padding: 10px 14px;
      border-radius: 10px;
      border: 1px solid var(--border-color);
      background: #fff;
      font-size: 0.9rem;
    }
    .search-input { flex: 1; min-width: 220px; }
    .table-wrap {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      overflow-x: auto;
    }
    table { width: 100%; border-collapse: collapse; }
    th {
      background: var(--bg-secondary);
      padding: 13px 16px;
      text-align: left;
      font-size: 0.82rem;
      color: var(--text-secondary);
    }
    td {
      padding: 14px 16px;
      border-bottom: 1px solid rgba(126, 68, 37, 0.1);
      vertical-align: middle;
      font-size: 0.9rem;
    }
    tr:hover { background: rgba(244, 227, 204, 0.3); }
    .badge {
      padding: 4px 11px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      border: none;
    }
    .badge-pub { background: #e6f9ee; color: #166534; border: 1px solid #86efac; }
    .badge-draft { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
    .badge-shop { background: #e0f2fe; color: #075985; border: 1px solid #7dd3fc; }
    .badge-pure { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
    .btn-sm {
      padding: 6px 12px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
      background: #fff;
      cursor: pointer;
      font-size: 0.82rem;
      font-weight: 600;
      margin-left: 6px;
    }
    .btn-sm.del { color: var(--danger); border-color: #f5b7b1; }
    /* 編輯彈窗：嚴格遵守 27 號人設鐵律（任何螢幕高度都可捲動，底部按鈕永遠按得到） */
    dialog#editModal {
      margin: auto;
      border: none;
      border-radius: 20px;
      max-width: 920px;
      width: calc(100% - 28px);
      max-height: 90vh;
      background: var(--card-bg);
      box-shadow: 0 25px 70px rgba(0,0,0,0.45);
      padding: 0;
      overflow: hidden;
    }
    dialog#editModal::backdrop {
      background: rgba(25, 14, 9, 0.65);
      backdrop-filter: blur(4px);
    }
    .modal-inner {
      display: flex;
      flex-direction: column;
      max-height: 90vh;
    }
    .modal-head {
      background: #2c1910;
      color: #fff8ee;
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
    .modal-body {
      padding: 22px 24px;
      overflow-y: auto;
      flex: 1;
    }
    .modal-foot {
      padding: 14px 24px;
      background: var(--bg-secondary);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
      border-top: 1px solid var(--border-color);
    }
    .two-col {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 22px;
    }
    @media (max-width: 820px) {
      .two-col { grid-template-columns: 1fr; }
    }
    .panel-box {
      background: #fff;
      border: 1.5px solid var(--border-color);
      border-radius: 14px;
      padding: 18px;
    }
    .panel-box h3 {
      font-family: 'Noto Serif TC', serif;
      font-size: 1.08rem;
      margin-bottom: 14px;
      padding-bottom: 8px;
      border-bottom: 1px dashed var(--border-color);
      color: #2c1910;
    }
    .field { margin-bottom: 14px; }
    .field label {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.84rem;
      font-weight: 700;
      margin-bottom: 5px;
      color: var(--text-primary);
    }
    .field input[type="text"],
    .field input[type="number"],
    .field select,
    .field textarea {
      width: 100%;
      padding: 9px 12px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
      font-size: 0.9rem;
      font-family: inherit;
    }
    .upload-btn-wrap {
      position: relative;
      display: inline-block;
    }
    .btn-upload {
      background: #2c1910;
      color: #ffd89b;
      padding: 4px 11px;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      border: none;
    }
    .upload-btn-wrap input[type="file"] {
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
    }
    .preview-thumb {
      width: 100%;
      max-height: 140px;
      object-fit: cover;
      border-radius: 10px;
      margin-top: 8px;
      border: 1px solid var(--border-color);
      display: none;
    }
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #2c1910;
      color: #fff8ee;
      padding: 14px 22px;
      border-radius: 12px;
      border-left: 5px solid #06C755;
      font-weight: 700;
      z-index: 9999;
      display: none;
      box-shadow: 0 12px 32px rgba(0,0,0,0.3);
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <div>
        <h1>☕ 咖啡時光廊・歲月恩典館 — 視覺化維護後台 (CMS)</h1>
        <div class="header-sub" id="gitRemoteStatus">🟢 本機高速直連模式（圖片與新技術 MP3 直接存入網站資料夾，0 秒完成不卡頓）</div>
      </div>
      <div class="header-btns">
        <a href="/" target="_blank" class="btn btn-outline-light">👀 打開前台看實際畫面</a>
        <button class="btn btn-outline-light" onclick="setGitHubRemote()">🔗 設定新 GitHub 倉庫網址</button>
        <button class="btn btn-publish" onclick="publishToGitHub()">🚀 儲存並一鍵推上 GitHub Pages</button>
      </div>
    </div>
  </header>

  <main class="container">
    <div class="stats-bar">
      <div class="stat-card">
        <div class="stat-label">📚 全部故事</div>
        <div class="stat-value" id="statTotal">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">🟢 已上架顯示</div>
        <div class="stat-value" id="statPub" style="color:var(--success);">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">🎁 附帶貨商品卡</div>
        <div class="stat-value" id="statShop" style="color:#075985;">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">💌 純故事 (加 LINE)</div>
        <div class="stat-value" id="statPure" style="color:#92400e;">0</div>
      </div>
    </div>

    <div class="toolbar">
      <button class="btn-add" onclick="openAddModal()">＋ 新增一篇故事與商品</button>
      <input type="text" id="searchBox" class="search-input" placeholder="🔍 搜尋故事標題、分類、商品名稱..." oninput="renderTable()">
      <select id="catFilter" class="filter-select" onchange="renderTable()">
        <option value="">全部 10 大主題</option>
        <option value="love">01. 愛</option>
        <option value="forgiveness">02. 饒恕</option>
        <option value="waiting">03. 等候</option>
        <option value="hope">04. 盼望</option>
        <option value="peace">05. 平安</option>
        <option value="grace">06. 恩典</option>
        <option value="companionship">07. 陪伴</option>
        <option value="gratitude">08. 感恩</option>
        <option value="restart">09. 重新開始</option>
        <option value="home">10. 回家</option>
      </select>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width:50px;">#</th>
            <th style="width:95px;">上下架</th>
            <th style="width:140px;">10 大分類</th>
            <th>故事標題 ＆ 試聽綁定 MP3</th>
            <th style="width:165px;">右欄帶貨狀態 (點此切換)</th>
            <th style="width:160px; text-align:right;">維護操作</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </main>

  <!-- 新增 / 編輯彈窗 -->
  <dialog id="editModal">
    <div class="modal-inner">
      <div class="modal-head">
        <h2 id="modalTitle" style="font-size:1.2rem;">✏️ 編輯故事與右欄商品</h2>
        <button onclick="closeModal()" style="background:none;border:none;color:#fff;font-size:1.4rem;cursor:pointer;">✕</button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="editIndex">
        <div class="two-col">
          <!-- 左欄：故事文案、封面圖上傳、新技術 MP3 上傳 -->
          <div class="panel-box">
            <h3>📖 左邊：故事文案 ＆ 封面圖 ＆ 新技術 MP3</h3>
            <div style="display:grid; grid-template-columns:1fr 1fr 1.2fr; gap:10px;">
              <div class="field">
                <label>狀態</label>
                <select id="fStatus">
                  <option value="published">🟢 已上架</option>
                  <option value="draft">🔴 草稿 (隱藏)</option>
                </select>
              </div>
              <div class="field">
                <label>排序數字</label>
                <input type="number" id="fSort" value="1">
              </div>
              <div class="field">
                <label>10 大主題分類</label>
                <select id="fCatKey" onchange="syncCatName()">
                  <option value="love">❤️ 01. 愛 ｜ 夫妻相守</option>
                  <option value="forgiveness">🤝 02. 饒恕 ｜ 父子和解</option>
                  <option value="waiting">⏳ 03. 等候 ｜ 守候黎明</option>
                  <option value="hope">🌅 04. 盼望 ｜ 樂齡綻放</option>
                  <option value="peace">🕊️ 05. 平安 ｜ 晨更與好眠</option>
                  <option value="grace">🌿 06. 恩典 ｜ 土地與養生</option>
                  <option value="companionship">☕ 07. 陪伴 ｜ 探訪關懷</option>
                  <option value="gratitude">🌾 08. 感恩 ｜ 走過幽谷</option>
                  <option value="restart">🚶‍♂️ 09. 重新開始 ｜ 慢老活力</option>
                  <option value="home">🍲 10. 回家 ｜ 餐桌與補養</option>
                </select>
              </div>
            </div>

            <div class="field">
              <label>
                <span>顯示分類標籤</span>
                <small style="color:var(--text-secondary);">代號 ID: <input type="text" id="fId" style="width:130px;padding:2px 6px;font-size:0.78rem;"></small>
              </label>
              <input type="text" id="fCatName" placeholder="例如：🕊️ 05. 平安 ｜ 晨更與好眠">
            </div>

            <div class="field">
              <label>故事主標題</label>
              <input type="text" id="fTitle" placeholder="請輸入打動人心的故事標題...">
            </div>

            <div class="field">
              <label>故事卡片摘要（2 行簡短引言）</label>
              <textarea id="fExcerpt" rows="2"></textarea>
            </div>

            <div class="field">
              <label>
                <span>🖼️ 故事封面圖（網址或從電腦上傳）</span>
                <span class="upload-btn-wrap">
                  <button type="button" class="btn-upload">📎 從電腦上傳封面圖</button>
                  <input type="file" accept="image/*" onchange="uploadFile(this, 'image', 'fCover', 'coverPreview')">
                </span>
              </label>
              <input type="text" id="fCover" oninput="updatePreview('fCover', 'coverPreview')" placeholder="./images/xxx.jpg 或 https://...">
              <img id="coverPreview" class="preview-thumb">
            </div>

            <div class="field" style="background:#fcf1dd; padding:12px; border-radius:10px; border:1px solid #e2be82;">
              <label>
                <span>🎧 語音 MP3（直接選取您新技術做好的 .mp3 檔案）</span>
                <span class="upload-btn-wrap">
                  <button type="button" class="btn-upload" style="background:#a3572c;color:#fff;">📎 選取新技術 .mp3 上傳</button>
                  <input type="file" accept="audio/*,.mp3,.m4a,.wav" onchange="uploadFile(this, 'audio', 'fMp3', 'mp3Preview')">
                </span>
              </label>
              <input type="text" id="fMp3" oninput="updateAudioPreview()" placeholder="./mp3/您的新技術語音.mp3">
              <audio id="mp3Preview" controls style="width:100%; height:36px; margin-top:8px;"></audio>
            </div>

            <div class="field">
              <label>
                <span>🥪 三明治上層：真實的歲月風浪與孤單（共鳴）</span>
                <button type="button" class="btn-sm" onclick="pasteFullTextAndSplit()">🪄 貼上整篇文字自動切 3 段</button>
              </label>
              <textarea id="fLayer1" rows="3"></textarea>
            </div>

            <div class="field">
              <label>🥪 三明治夾心：信仰的轉折與清晨的亮光（見證）</label>
              <textarea id="fLayer2" rows="3"></textarea>
            </div>

            <div class="field">
              <label>🥪 三明治下層：把這份陪伴帶進日常（溫暖延伸）</label>
              <textarea id="fLayer3" rows="3"></textarea>
            </div>

            <div class="field">
              <label>📖 經文祝福 ＆ 結尾禱告</label>
              <textarea id="fScripture" rows="2"></textarea>
            </div>

            <div class="field">
              <label>🌍 故事主人的家（外部 FB / 網站 / 影片連結，選填）</label>
              <input type="text" id="fExtLink" placeholder="https://www.facebook.com/...（有填才會顯示按鈕）">
            </div>
          </div>

          <!-- 右欄：同款商品與 LINE Pay 帶貨卡設定 -->
          <div class="panel-box">
            <h3>🎁 右手邊：順手帶貨商品卡設定</h3>
            <div class="field" style="background:#e6f9ee; padding:12px; border-radius:10px; border:1px solid #86efac;">
              <label style="font-size:0.92rem; color:#166534;">這篇故事右邊要不要順手賣商品？</label>
              <select id="fHasProduct" style="font-weight:700; margin-top:4px;">
                <option value="true">🎁 有賣商品（顯示同款商品卡 ＋ LINE Pay 結帳）</option>
                <option value="false">💌 先上純故事（顯示零壓力代禱 ＋ 加 LINE 好友卡）</option>
              </select>
            </div>

            <div class="field">
              <label>商品頂部小標籤</label>
              <input type="text" id="fProdTag" placeholder="例如：🎁 探訪病患／長輩晨更首選">
            </div>

            <div class="field">
              <label>商品完整名稱</label>
              <input type="text" id="fProdTitle" placeholder="例如：【牧者的晨更陪伴】有聲故事半低因濾掛禮盒">
            </div>

            <div class="field">
              <label>商品價格顯示文字（支援優惠說明）</label>
              <input type="text" id="fProdPrice" placeholder="例如：NT$ 490 <small>/ 盒（團購 5 盒 NT$ 2,200）</small>">
            </div>

            <div class="field">
              <label>
                <span>🖼️ 商品照片（從電腦上傳或點右鍵同封面）</span>
                <span>
                  <button type="button" class="btn-sm" onclick="copyCoverToProd()">同故事封面</button>
                  <span class="upload-btn-wrap">
                    <button type="button" class="btn-upload">📎 上傳商品圖</button>
                    <input type="file" accept="image/*" onchange="uploadFile(this, 'image', 'fProdImg', 'prodPreview')">
                  </span>
                </span>
              </label>
              <input type="text" id="fProdImg" oninput="updatePreview('fProdImg', 'prodPreview')" placeholder="./images/product.jpg">
              <img id="prodPreview" class="preview-thumb">
            </div>

            <div class="field">
              <label>商品溫暖簡介</label>
              <textarea id="fProdDesc" rows="3"></textarea>
            </div>

            <div class="field">
              <label>商品打勾亮點（一行寫一點，前台自動打 ✓）</label>
              <textarea id="fProdFeatures" rows="5" placeholder="銀髮族友善：低酸度、不心悸&#10;每包外袋獨立印製 10×12cm 溫暖插畫&#10;手機掃碼即可聽見 95 秒故事"></textarea>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-foot">
        <span style="font-size:0.84rem; color:var(--text-secondary);">💡 提示：按「儲存變更」會立刻寫入本機網站，點右上「🚀 推上 GitHub」即對外更新。</span>
        <div>
          <button class="btn" style="background:#e2d5c4;" onclick="closeModal()">取消</button>
          <button class="btn" style="background:var(--accent);color:#fff;" onclick="saveModalStory()">💾 儲存這篇故事與商品</button>
        </div>
      </div>
    </div>
  </dialog>

  <div id="toast" class="toast"></div>

  <script>
    let stories = [];
    let gitRemoteUrl = '';

    async function loadAll() {
      const res = await fetch('/api/stories?t=' + Date.now(), { cache: 'no-store' });
      const data = await res.json();
      stories = data.stories || [];
      gitRemoteUrl = (data.git && data.git.remoteUrl) || '';
      document.getElementById('gitRemoteStatus').textContent = gitRemoteUrl
        ? `🟢 已連線 GitHub 倉庫：${gitRemoteUrl}`
        : `🟡 本機高速模式（尚未綁定新 GitHub 倉庫，點右上「🔗 設定新 GitHub 倉庫網址」即可綁定）`;
      updateStats();
      renderTable();
    }

    function updateStats() {
      const total = stories.length;
      const pub = stories.filter(s => (s.status || 'published') === 'published').length;
      const shop = stories.filter(s => s.hasProduct).length;
      document.getElementById('statTotal').textContent = total;
      document.getElementById('statPub').textContent = pub;
      document.getElementById('statShop').textContent = shop;
      document.getElementById('statPure').textContent = total - shop;
    }

    function renderTable() {
      const q = document.getElementById('searchBox').value.trim().toLowerCase();
      const cat = document.getElementById('catFilter').value;
      const tbody = document.getElementById('tableBody');

      const rows = stories.map((s, idx) => ({ s, idx })).filter(({ s }) => {
        if (cat && s.categoryKey !== cat) return false;
        if (!q) return true;
        return [s.title, s.categoryName, s.excerpt, (s.product && s.product.title) || ''].join(' ').toLowerCase().includes(q);
      });

      tbody.innerHTML = rows.map(({ s, idx }) => {
        const isPub = (s.status || 'published') === 'published';
        return `
          <tr>
            <td><strong>${idx + 1}</strong></td>
            <td>
              <button class="badge ${isPub ? 'badge-pub' : 'badge-draft'}" onclick="quickTogglePub(${idx})">
                ${isPub ? '🟢 已上架' : '🔴 草稿'}
              </button>
            </td>
            <td><span style="font-size:0.84rem;font-weight:700;">${s.categoryName || ''}</span></td>
            <td>
              <div style="font-weight:700; margin-bottom:4px;">${s.title || ''}</div>
              <div style="display:flex; align-items:center; gap:8px; font-size:0.78rem; color:var(--text-secondary);">
                <span>🎧 ${s.mp3File || '未設定'}</span>
                ${s.mp3File ? `<audio src="${s.mp3File}" controls preload="none" style="height:26px; width:180px;"></audio>` : ''}
              </div>
            </td>
            <td>
              <button class="badge ${s.hasProduct ? 'badge-shop' : 'badge-pure'}" onclick="quickToggleShop(${idx})">
                ${s.hasProduct ? '🎁 有賣商品 (點此切)' : '💌 純故事 (點此切)'}
              </button>
            </td>
            <td style="text-align:right; white-space:nowrap;">
              <button class="btn-sm" onclick="openEditModal(${idx})">✏️ 編輯文字/傳圖/MP3</button>
              <button class="btn-sm del" onclick="deleteStory(${idx})">🗑️</button>
            </td>
          </tr>
        `;
      }).join('');
    }

    async function persistStories(toastMsg) {
      const res = await fetch('/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stories })
      });
      const out = await res.json();
      if (out.success) {
        updateStats();
        renderTable();
        showToast(toastMsg || '✅ 已儲存並同步更新前台網站！');
      }
    }

    function quickTogglePub(idx) {
      const cur = stories[idx].status || 'published';
      stories[idx].status = cur === 'published' ? 'draft' : 'published';
      persistStories(stories[idx].status === 'published' ? '🟢 已切換為上架狀態' : '🔴 已切換為草稿隱藏');
    }

    function quickToggleShop(idx) {
      stories[idx].hasProduct = !stories[idx].hasProduct;
      persistStories(stories[idx].hasProduct ? '🎁 已開啟右欄商品帶貨卡' : '💌 已切換為純故事加 LINE 模式');
    }

    function deleteStory(idx) {
      if (!confirm(`確定要刪除「${stories[idx].title}」嗎？`)) return;
      stories.splice(idx, 1);
      persistStories('🗑️ 已刪除該篇故事');
    }

    function syncCatName() {
      const sel = document.getElementById('fCatKey');
      document.getElementById('fCatName').value = sel.options[sel.selectedIndex].text;
    }

    function openAddModal() {
      document.getElementById('modalTitle').textContent = '✨ 新增故事與同款商品';
      document.getElementById('editIndex').value = '-1';
      document.getElementById('fStatus').value = 'published';
      document.getElementById('fSort').value = stories.length + 1;
      document.getElementById('fCatKey').value = 'peace';
      syncCatName();
      document.getElementById('fId').value = 'story-' + Date.now();
      document.getElementById('fTitle').value = '';
      document.getElementById('fExcerpt').value = '';
      document.getElementById('fCover').value = '';
      updatePreview('fCover', 'coverPreview');
      document.getElementById('fMp3').value = '';
      updateAudioPreview();
      document.getElementById('fLayer1').value = '';
      document.getElementById('fLayer2').value = '';
      document.getElementById('fLayer3').value = '';
      document.getElementById('fScripture').value = '📖 經文祝福：';
      document.getElementById('fExtLink').value = '';
      document.getElementById('fHasProduct').value = 'false';
      document.getElementById('fProdTag').value = '🎁 恩典同款好物';
      document.getElementById('fProdTitle').value = '';
      document.getElementById('fProdPrice').value = 'NT$ 490 <small>/ 盒</small>';
      document.getElementById('fProdImg').value = '';
      updatePreview('fProdImg', 'prodPreview');
      document.getElementById('fProdDesc').value = '';
      document.getElementById('fProdFeatures').value = '';
      document.getElementById('editModal').showModal();
    }

    function openEditModal(idx) {
      const s = stories[idx];
      const p = s.product || {};
      document.getElementById('modalTitle').textContent = '✏️ 編輯：' + s.title;
      document.getElementById('editIndex').value = String(idx);
      document.getElementById('fStatus').value = s.status || 'published';
      document.getElementById('fSort').value = s.sort || (idx + 1);
      document.getElementById('fCatKey').value = s.categoryKey || 'peace';
      document.getElementById('fCatName').value = s.categoryName || '';
      document.getElementById('fId').value = s.id || ('story-' + (idx + 1));
      document.getElementById('fTitle').value = s.title || '';
      document.getElementById('fExcerpt').value = s.excerpt || '';
      document.getElementById('fCover').value = s.cover || '';
      updatePreview('fCover', 'coverPreview');
      document.getElementById('fMp3').value = s.mp3File || '';
      updateAudioPreview();
      document.getElementById('fLayer1').value = s.layer1 || '';
      document.getElementById('fLayer2').value = s.layer2 || '';
      document.getElementById('fLayer3').value = s.layer3 || '';
      document.getElementById('fScripture').value = s.scripture || '';
      document.getElementById('fExtLink').value = s.externalLink || '';
      document.getElementById('fHasProduct').value = s.hasProduct ? 'true' : 'false';
      document.getElementById('fProdTag').value = p.tag || '';
      document.getElementById('fProdTitle').value = p.title || '';
      document.getElementById('fProdPrice').value = p.price || '';
      document.getElementById('fProdImg').value = p.img || '';
      updatePreview('fProdImg', 'prodPreview');
      document.getElementById('fProdDesc').value = p.desc || '';
      document.getElementById('fProdFeatures').value = (p.features || []).join('\n');
      document.getElementById('editModal').showModal();
    }

    function closeModal() {
      document.getElementById('editModal').close();
    }

    function updatePreview(inputId, imgId) {
      const url = document.getElementById(inputId).value.trim();
      const img = document.getElementById(imgId);
      if (url) {
        img.src = url;
        img.style.display = 'block';
      } else {
        img.style.display = 'none';
      }
    }

    function updateAudioPreview() {
      const url = document.getElementById('fMp3').value.trim();
      const audio = document.getElementById('mp3Preview');
      audio.src = url || '';
    }

    function copyCoverToProd() {
      document.getElementById('fProdImg').value = document.getElementById('fCover').value;
      updatePreview('fProdImg', 'prodPreview');
    }

    function pasteFullTextAndSplit() {
      const raw = prompt('請貼上整篇故事內文（系統會自動按段落幫您切進三明治上、中、下三層）：');
      if (!raw || !raw.trim()) return;
      const paras = raw.split(/\n+/).map(p => p.trim()).filter(Boolean);
      if (paras.length === 1) {
        document.getElementById('fLayer1').value = paras[0];
      } else if (paras.length === 2) {
        document.getElementById('fLayer1').value = paras[0];
        document.getElementById('fLayer2').value = paras[1];
      } else {
        document.getElementById('fLayer1').value = paras[0];
        document.getElementById('fLayer2').value = paras[1];
        document.getElementById('fLayer3').value = paras.slice(2).join('\n');
      }
      showToast('🪄 已自動幫您切入三明治三層段落！');
    }

    function uploadFile(inputEl, fileKind, targetInputId, previewId) {
      if (!inputEl.files || !inputEl.files[0]) return;
      const file = inputEl.files[0];
      const reader = new FileReader();
      showToast(`⏳ 正在寫入 ${file.name}...`);
      reader.onload = async (e) => {
        const res = await fetch('/api/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            kind: fileKind,
            filename: file.name,
            dataUrl: e.target.result
          })
        });
        const out = await res.json();
        inputEl.value = '';
        if (out.success) {
          document.getElementById(targetInputId).value = out.path;
          if (fileKind === 'audio') {
            updateAudioPreview();
            showToast(`🎧 音檔已存入 ${out.path}（0.2 秒極速秒播就緒！）`);
          } else {
            updatePreview(targetInputId, previewId);
            showToast(`🖼️ 圖片已存入 ${out.path}！`);
          }
        } else {
          alert('上傳失敗：' + out.error);
        }
      };
      reader.readAsDataURL(file);
    }

    function saveModalStory() {
      const idx = parseInt(document.getElementById('editIndex').value, 10);
      const item = {
        id: document.getElementById('fId').value.trim() || ('story-' + Date.now()),
        status: document.getElementById('fStatus').value,
        sort: parseInt(document.getElementById('fSort').value, 10) || 1,
        categoryKey: document.getElementById('fCatKey').value,
        categoryName: document.getElementById('fCatName').value.trim(),
        mp3File: document.getElementById('fMp3').value.trim(),
        title: document.getElementById('fTitle').value.trim(),
        excerpt: document.getElementById('fExcerpt').value.trim(),
        cover: document.getElementById('fCover').value.trim(),
        layer1: document.getElementById('fLayer1').value.trim(),
        layer2: document.getElementById('fLayer2').value.trim(),
        layer3: document.getElementById('fLayer3').value.trim(),
        scripture: document.getElementById('fScripture').value.trim(),
        externalLink: document.getElementById('fExtLink').value.trim(),
        hasProduct: document.getElementById('fHasProduct').value === 'true',
        product: {
          tag: document.getElementById('fProdTag').value.trim(),
          title: document.getElementById('fProdTitle').value.trim(),
          price: document.getElementById('fProdPrice').value.trim(),
          img: document.getElementById('fProdImg').value.trim() || document.getElementById('fCover').value.trim(),
          desc: document.getElementById('fProdDesc').value.trim(),
          features: document.getElementById('fProdFeatures').value.split('\n').map(s => s.trim()).filter(Boolean)
        }
      };

      if (!item.title) {
        alert('請填寫故事標題！');
        return;
      }

      if (idx >= 0 && idx < stories.length) {
        stories[idx] = item;
      } else {
        stories.unshift(item);
      }
      stories.sort((a, b) => (a.sort || 999) - (b.sort || 999));
      closeModal();
      persistStories('💾 已儲存！前台網站與 MP3 已同步更新');
    }

    async function setGitHubRemote() {
      const input = prompt(
        '請貼上您為新營業站建立的 GitHub 倉庫網址（與舊站 -coffee-stories 完全分開）：\n例如：https://github.com/HemanJJ/grace-shop.git',
        gitRemoteUrl || 'https://github.com/HemanJJ/grace-shop.git'
      );
      if (!input || !input.trim()) return;
      const res = await fetch('/api/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ remoteUrl: input.trim(), onlySetRemote: true })
      });
      const out = await res.json();
      loadAll();
      showToast(out.message || '🔗 已綁定 GitHub 倉庫網址');
    }

    async function publishToGitHub() {
      showToast('🚀 正在打包文字、圖片與 MP3 推送至 GitHub Pages...');
      const res = await fetch('/api/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const out = await res.json();
      if (out.needRemote) {
        setGitHubRemote();
        return;
      }
      if (out.success) {
        showToast(out.message);
      } else {
        alert(out.message);
      }
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.style.display = 'block';
      clearTimeout(window._toastTimer);
      window._toastTimer = setTimeout(() => { t.style.display = 'none'; }, 4000);
    }

    loadAll();
  </script>
</body>
</html>
"""


class CMSRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/admin", "/admin/"):
            data = ADMIN_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if parsed.path == "/api/stories":
            stories = extract_stories_from_index()
            payload = json.dumps({"stories": stories, "git": get_git_info()}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        body = json.loads(raw_body.decode("utf-8"))

        if parsed.path == "/api/stories":
            stories = body.get("stories", [])
            save_stories_everywhere(stories)
            self._send_json({"success": True})
            return

        if parsed.path == "/api/upload":
            try:
                kind = body.get("kind", "image")
                filename = os.path.basename(body.get("filename", "file"))
                safe_name = re.sub(r"[^\w\u4e00-\u9fa5\.\-]+", "_", filename)
                data_url = body.get("dataUrl", "")
                if "," in data_url:
                    data_url = data_url.split(",", 1)[1]
                binary = base64.b64decode(data_url)

                target_dir = MP3_DIR if kind == "audio" else IMAGES_DIR
                folder_name = "mp3" if kind == "audio" else "images"
                dest = target_dir / safe_name
                dest.write_bytes(binary)
                rel_path = f"./{folder_name}/{safe_name}"
                self._send_json({"success": True, "path": rel_path})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)})
            return

        if parsed.path == "/api/publish":
            remote_url = body.get("remoteUrl", "").strip()
            if body.get("onlySetRemote") and remote_url:
                if not (ROOT_DIR / ".git").exists():
                    subprocess.run(["git", "init"], cwd=str(ROOT_DIR))
                    subprocess.run(["git", "branch", "-M", "main"], cwd=str(ROOT_DIR))
                has_origin = subprocess.run(
                    ["git", "remote", "get-url", "origin"], cwd=str(ROOT_DIR), capture_output=True
                )
                if has_origin.returncode == 0:
                    subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=str(ROOT_DIR))
                else:
                    subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=str(ROOT_DIR))
                self._send_json({"success": True, "message": f"✅ 已綁定新倉庫：{remote_url}"})
                return

            res = publish_to_github(remote_url)
            self._send_json(res)
            return

        self._send_json({"success": False, "error": "Unknown endpoint"}, status=404)

    def _send_json(self, obj: dict, status: int = 200):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    PORT = int(os.environ.get("CMS_PORT", "8920"))
    extract_stories_from_index()
    print(f"☕ 咖啡時光廊 CMS 後台已啟動：http://127.0.0.1:{PORT}/admin")
    print(f"👀 前台網站預覽：http://127.0.0.1:{PORT}/")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), CMSRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
