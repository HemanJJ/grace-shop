#!/bin/bash
# 一鍵合成 10 首 MP3 ＋ 打開 Cloudflare Pages 拖曳部署頁面（免費合法商用、0.2 秒極速串流）
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1

# 若還沒生齊 10 首 MP3，先自動呼叫合成腳本
if [ ! -f "$DIR/mp3/10_回家篇_陳媽媽熬了四十年的禱告湯.mp3" ]; then
  bash "$DIR/一鍵合成MP3並預覽.command"
fi

echo "=================================================================="
echo "🚀 準備將【咖啡時光廊・歲月恩典館】發布至 Cloudflare Pages 正式營業站"
echo "✅ 已內建 _headers（MP3 極速分段串流 + 首頁防快取 no-store）"
echo "=================================================================="
echo ""
echo "👉 步驟 1：即將為您打開 Cloudflare Pages 建立專案頁面（免費商用、無限流量）"
echo "👉 步驟 2：點選「Upload assets (直接上傳資料夾)」，專案名稱輸入：grace-coffee"
echo "👉 步驟 3：把旁邊跳出來的【DEMO_light_shop】整個資料夾拖進去，點 Deploy 即完成！"
echo "=================================================================="

open "https://dash.cloudflare.com/?to=/:account/workers-and-pages/create/pages"
open -R "$DIR/index.html"
