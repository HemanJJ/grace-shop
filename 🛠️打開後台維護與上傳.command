#!/bin/bash
# 雙擊直接打開【咖啡時光廊・歲月恩典館】視覺化維護後台 (CMS)
# 支援：改文案、上傳封面圖、上傳您新技術做好的 .mp3、設定右欄商品、一鍵推上 GitHub Pages
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1
PORT=8920

# 若 8920 port 已有舊程序則先重啟
OLD=$(lsof -tiTCP:$PORT -sTCP:LISTEN 2>/dev/null || true)
[ -n "$OLD" ] && kill $OLD 2>/dev/null || true
sleep 0.3

nohup python3 "$DIR/admin_cms.py" > "$DIR/cms_server.log" 2>&1 &
sleep 0.8

echo "=================================================================="
echo "🛠️ 已啟動【咖啡時光廊・歲月恩典館】本機視覺化維護後台！"
echo "👉 後台維護網址：http://127.0.0.1:$PORT/admin"
echo "👉 前台預覽網址：http://127.0.0.1:$PORT/"
echo "=================================================================="

open "http://127.0.0.1:$PORT/admin"
