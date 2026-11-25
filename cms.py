#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故事電台・本機維護後台（歲月恩典館 CMS）
=================================
- 只有你能改：一組密碼，存在 cms_password.txt
- 管兩個檔案：stories.json（故事）、products.json（商品）
- 一鍵發布：同步到 dist/ 再推 Cloudflare Pages
- 純標準庫，零依賴

啟動：
    python3 cms.py            # http://127.0.0.1:8756
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent
STORIES = BASE / "stories.json"
PRODUCTS = BASE / "products.json"
IMAGES = BASE / "images"
MP3 = BASE / "mp3"
DIST = BASE / "dist"
PW_FILE = BASE / "cms_password.txt"
PORT = 8756
PROJECT = "grace-coffee"
SITE = "https://grace-coffee.pages.dev"

ADMIN_HTML = (BASE / "cms_ui.html")


def load_pw() -> str:
    if PW_FILE.exists():
        return PW_FILE.read_text(encoding="utf-8").strip()
    PW_FILE.write_text("grace2026\n", encoding="utf-8")
    return "grace2026"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


ORDER_API = "https://grace-order-api.difly.workers.dev"
ORDER_TOKEN_FILE = BASE / "order-api" / "看單密碼.txt"


def order_token() -> str:
    try:
        return ORDER_TOKEN_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def sync_d1() -> dict:
    """把 products.json ＋ tiers.json 灌進收單資料庫（不動訂單）。"""
    token = order_token()
    if not token:
        return {"ok": False, "log": "找不到 order-api/看單密碼.txt"}
    tiers = (read_json(BASE / "tiers.json", {}) or {}).get("tiers", [])
    payload = json.dumps({"products": read_json(PRODUCTS, []), "tiers": tiers})
    # 用 curl 送（Python 的 urllib 會被 Cloudflare 的機器人防護擋掉）
    try:
        r = subprocess.run(
            ["curl", "-sS", "--max-time", "25", "-X", "POST", ORDER_API + "/api/admin/sync",
             "-H", "Content-Type: application/json",
             "-H", "Authorization: Bearer " + token,
             "-d", "@-"],
            input=payload, capture_output=True, text=True, timeout=40,
        )
        d = json.loads(r.stdout or "{}")
        return {"ok": bool(d.get("ok")), "products": d.get("products"), "tiers": d.get("tiers"),
                "log": "" if d.get("ok") else (d.get("message") or d.get("error") or r.stderr or "未知錯誤")}
    except Exception as e:
        return {"ok": False, "log": f"{type(e).__name__}: {e}"}


def sync_dist() -> None:
    """把資料與媒體同步到 dist/，讓發布帶上去。"""
    DIST.mkdir(exist_ok=True)
    for f in (STORIES, PRODUCTS):
        if f.exists():
            shutil.copy2(f, DIST / f.name)
    for src, dst in ((MP3, DIST / "mp3"), (IMAGES, DIST / "images")):
        if src.exists():
            dst.mkdir(parents=True, exist_ok=True)
            for item in src.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(src)
                    target = dst / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists() or item.stat().st_mtime > target.stat().st_mtime:
                        shutil.copy2(item, target)


def publish() -> dict:
    synced = sync_d1()          # 先讓收單用的資料庫跟上價錢
    sync_dist()
    try:
        r = subprocess.run(
            ["npx", "--yes", "wrangler@3", "pages", "deploy", "dist",
             "--project-name", PROJECT, "--commit-dirty=true"],
            cwd=str(BASE), capture_output=True, text=True, timeout=600,
        )
        out = (r.stdout or "") + (r.stderr or "")
        url = ""
        m = re.search(r"https://[0-9a-f]+\.grace-coffee\.pages\.dev", out)
        if m:
            url = m.group(0)
        return {"ok": r.returncode == 0, "url": url, "log": out[-3000:], "sync": synced}
    except Exception as e:
        return {"ok": False, "url": "", "log": f"{type(e).__name__}: {e}", "sync": synced}


class Handler(SimpleHTTPRequestHandler):
    server_version = "GraceCMS/1.0"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(BASE), **kw)

    # ── 小工具 ──────────────────────────────────────────────
    def _authed(self) -> bool:
        cookie = self.headers.get("Cookie") or ""
        m = re.search(r"cms_auth=([a-f0-9]{32})", cookie)
        if not m:
            return False
        want = hashlib.md5(load_pw().encode()).hexdigest()
        return m.group(1) == want

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _html(self, text: str, code=200):
        data = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    # ── GET ─────────────────────────────────────────────────
    def do_GET(self):  # noqa: N802
        p = urlparse(self.path).path
        if p == "/login":
            self._html(LOGIN_HTML)
            return
        if not self._authed():
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
            return
        if p in ("/", "/index.html", "/admin"):
            self._html(ADMIN_HTML.read_text(encoding="utf-8") if ADMIN_HTML.exists() else "<h1>缺少 cms_ui.html</h1>")
            return
        if p == "/api/data":
            self._json({
                "stories": read_json(STORIES, []),
                "products": read_json(PRODUCTS, []),
                "site": SITE,
            })
            return
        if p == "/api/ping":
            self._json({"ok": True})
            return
        # 讀圖/音檔預覽
        if p.startswith("/preview/"):
            rel = p[len("/preview/"):]
            target = (BASE / rel).resolve()
            if str(target).startswith(str(BASE)) and target.is_file():
                self.path = "/" + rel
                return super().do_GET()
            self._json({"error": "not found"}, 404)
            return
        self._json({"error": "not found"}, 404)

    # ── POST ────────────────────────────────────────────────
    def do_POST(self):  # noqa: N802
        p = urlparse(self.path).path
        body = self._body()

        if p == "/api/login":
            pw = (body.get("password") or "").strip()
            if pw == load_pw():
                token = hashlib.md5(pw.encode()).hexdigest()
                data = json.dumps({"ok": True}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", f"cms_auth={token}; Path=/; Max-Age=604800; SameSite=Lax")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._json({"ok": False, "error": "密碼不對"}, 401)
            return

        if not self._authed():
            self._json({"error": "請先登入"}, 401)
            return

        if p == "/api/save":
            kind = body.get("type")
            item = body.get("item") or {}
            if kind == "story":
                data = read_json(STORIES, [])
                idx = next((i for i, s in enumerate(data) if s.get("id") == item.get("id")), -1)
                if idx >= 0:
                    data[idx] = {**data[idx], **item}
                else:
                    data.append(item)
                write_json(STORIES, data)
                self._json({"ok": True, "count": len(data)})
                return
            if kind == "product":
                data = read_json(PRODUCTS, [])
                idx = next((i for i, s in enumerate(data) if s.get("id") == item.get("id")), -1)
                if idx >= 0:
                    data[idx] = {**data[idx], **item}
                else:
                    data.append(item)
                write_json(PRODUCTS, data)
                self._json({"ok": True, "count": len(data)})
                return
            self._json({"error": "type 要 story 或 product"}, 400)
            return

        if p == "/api/reorder":
            kind = body.get("type")
            ids = [str(i) for i in (body.get("ids") or [])]
            f = STORIES if kind == "story" else PRODUCTS if kind == "product" else None
            if not f:
                self._json({"error": "type 要 story 或 product"}, 400)
                return
            data = read_json(f, [])
            before = len(data)
            pos = {x: n for n, x in enumerate(ids)}
            data.sort(key=lambda x: pos.get(str(x.get("id")), 9999))
            if len(data) != before:          # 保險：排序不該改變筆數
                self._json({"ok": False, "error": "筆數異常，已中止（未寫檔）"}, 500)
                return
            # 寫檔前留一份，出事可以還原
            try:
                (f.parent / (f.name + ".bak-last")).write_text(
                    f.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass
            for n, x in enumerate(data, 1):
                x["sort"] = n
            write_json(f, data)
            self._json({"ok": True, "count": len(data)})
            return

        if p == "/api/delete":
            kind, ident = body.get("type"), body.get("id")
            f = STORIES if kind == "story" else PRODUCTS
            data = [x for x in read_json(f, []) if x.get("id") != ident]
            write_json(f, data)
            self._json({"ok": True, "count": len(data)})
            return

        if p == "/api/upload":
            name = re.sub(r"[^\w.\-]+", "_", (body.get("name") or "file").strip())
            kind = body.get("kind") or "image"
            import base64
            raw = base64.b64decode(body.get("data") or "")
            folder = MP3 if kind == "audio" else IMAGES
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / name
            target.write_bytes(raw)
            rel = target.relative_to(BASE).as_posix()
            self._json({"ok": True, "path": "./" + rel, "bytes": len(raw)})
            return

        if p == "/api/sync-d1":
            self._json(sync_d1())
            return

        if p == "/api/publish":
            res = publish()
            self._json(res)
            return

        self._json({"error": "not found"}, 404)


LOGIN_HTML = """<!doctype html><html lang="zh-Hant-TW"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>登入｜故事電台後台（歲月恩典館）</title>
<style>body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:#14110d;color:#f3ead9;font-family:"PingFang TC",sans-serif}
.box{background:#1d1812;border:1px solid #3a3022;border-radius:14px;padding:26px;width:300px}
h1{font-size:1.05rem;margin:0 0 16px}input{width:100%;padding:11px;border-radius:9px;border:1px solid #3a3022;
background:#0f0c09;color:#fff;font-size:1rem;box-sizing:border-box}
button{width:100%;margin-top:14px;padding:12px;border:0;border-radius:9px;background:#c9a227;color:#231a09;
font-weight:800;font-size:1rem;cursor:pointer}.err{color:#f0a5a5;font-size:.85rem;margin-top:10px}</style></head>
<body><div class="box"><h1>🎙 故事電台・後台（歲月恩典館）</h1>
<input id="pw" type="password" placeholder="密碼" autofocus>
<button onclick="go()">登入</button><div class="err" id="err"></div></div>
<script>async function go(){const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({password:document.getElementById('pw').value})});
if(r.ok){location.href='/';}else{document.getElementById('err').textContent='密碼不對';}}
document.getElementById('pw').addEventListener('keydown',e=>{if(e.key==='Enter')go();});</script></body></html>"""


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"🧾 後台：http://127.0.0.1:{PORT}/   （密碼在 {PW_FILE.name}）")
    srv.serve_forever()


if __name__ == "__main__":
    main()
