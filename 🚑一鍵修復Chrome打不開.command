#!/bin/bash
# 🚑 一鍵修復 Mac 上 Google Chrome 打不開 / 被外掛或背景殭屍程序卡死的問題
echo "=================================================================="
echo "🚑 正在為您清理卡住的 Google Chrome 背景程序與鎖定檔 (SingletonLock)..."
echo "=================================================================="

# 1. 關閉所有殘留在背景卡住的 Chrome 程序
killall -9 "Google Chrome" 2>/dev/null || true
killall -9 "Google Chrome Helper" 2>/dev/null || true
killall -9 "Google Chrome Helper (Renderer)" 2>/dev/null || true
sleep 1

# 2. 移除導致 Chrome 點了沒反應的 Profile 鎖定檔
rm -f "$HOME/Library/Application Support/Google/Chrome/SingletonLock" 2>/dev/null || true
rm -f "$HOME/Library/Application Support/Google/Chrome/SingletonCookie" 2>/dev/null || true
rm -f "$HOME/Library/Application Support/Google/Chrome/SingletonSocket" 2>/dev/null || true

echo "✅ 已解除鎖定！正在為您重新打開 Google Chrome 並直接進入新網站..."
open -a "Google Chrome" "https://hemanjj.github.io/grace-shop/"
