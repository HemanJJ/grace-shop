#!/bin/bash
# 一鍵把【咖啡時光廊・歲月恩典館 (DEMO_light_shop)】打包成獨立 Git 倉庫，並推上全新 GitHub Pages (grace-shop)
# 完全不碰舊的 -coffee-stories！
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1

REPO_NAME="grace-shop"
REMOTE_URL="https://github.com/HemanJJ/${REPO_NAME}.git"
LIVE_URL="https://hemanjj.github.io/${REPO_NAME}/"

echo "=================================================================="
echo "🌐 正在準備【咖啡時光廊・歲月恩典館】全新獨立 GitHub 網站 ($REPO_NAME)..."
echo "=================================================================="

# 1. 確保 stories.json 已同步生成
python3 -c "import admin_cms; admin_cms.extract_stories_from_index()" 2>/dev/null || true

# 2. 初始化 Git 並打包所有檔案
if [ ! -d "$DIR/.git" ]; then
  git init
  git branch -M main
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

git add -A
git commit -m "正式上線：咖啡時光廊・歲月恩典館 (含視覺化後台與10篇故事)" 2>/dev/null || true

echo ""
echo "👉 正在嘗試直接推送到 $REMOTE_URL ..."
if git push -u origin main 2>/dev/null; then
  echo "🎉 推送成功！"
  echo "👉 即將為您打開 GitHub Pages 開關頁，請將 Branch 選為【main】並按【Save】"
  echo "👉 1 分鐘後您的新正式營業網址就是：$LIVE_URL"
  open "https://github.com/HemanJJ/${REPO_NAME}/settings/pages"
else
  echo "=================================================================="
  echo "💡 您的 GitHub 還沒建立【$REPO_NAME】這個新倉庫！"
  echo "👉 我現在幫您打開 GitHub 新建頁面（名稱已幫您填好 $REPO_NAME）："
  echo "   1. 請在跳出的網頁直接往下滑，點綠色按鈕【Create repository】"
  echo "   2. 點完後，回到這個視窗按一下【Enter 鍵】，就會自動上傳並上線！"
  echo "=================================================================="
  open "https://github.com/new?name=${REPO_NAME}&description=%E5%92%96%E5%95%A1%E6%99%82%E5%85%89%E5%BB%8A%E3%83%BB%E6%AD%B2%E6%9C%88%E6%81%A9%E5%85%B8%E9%A4%A8&visibility=public"
  read -r -p "👉 在網頁點完【Create repository】後，請按這裡的 [Enter 鍵] 繼續上傳..."
  if git push -u origin main; then
    echo "🎉 上傳成功！正在打開 GitHub Pages 設定頁..."
    echo "👉 請在網頁中把 Branch 選成【main】➔ 點【Save】！"
    echo "✅ 您的新網站公開網址：$LIVE_URL"
    open "https://github.com/HemanJJ/${REPO_NAME}/settings/pages"
  else
    echo "💡 若需要登入權限，已為您呼叫 GitHub Desktop，請直接點【Publish repository】即可！"
    open -a "GitHub Desktop" "$DIR" 2>/dev/null || true
  fi
fi
