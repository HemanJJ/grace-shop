#!/bin/bash
cd "/Users/defi/一號/projects/DEMO_light_shop"

echo "=================================================="
echo "⚡ 正在啟動《咖啡時光廊・歲月恩典館》本機秒開站與視覺化後台..."
echo "=================================================="

# 若 8920 port 尚未啟動，在背景啟動 admin_cms.py
if ! lsof -i :8920 >/dev/null 2>&1; then
    nohup python3 admin_cms.py >/tmp/grace_shop_cms.log 2>&1 &
    sleep 1
fi

# 同時打開本機秒開預覽 (100% 不受路由器擋 GitHub 影響) 與後台
open "http://127.0.0.1:8920/"
open "http://127.0.0.1:8920/admin"

echo "✅ 已為您打開："
echo "👉 前台網站：http://127.0.0.1:8920/"
echo "👉 維護後台：http://127.0.0.1:8920/admin"
