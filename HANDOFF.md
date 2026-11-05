# 🤝 專案交接手冊 (HANDOFF.md) — 咖啡時光廊・歲月恩典館 (`DEMO_light_shop`)

> **⚠️ 給新 Session AI 助手的【最高省 Token 鐵律】**：
> 1. **禁止未經確認就整份重寫 `index.html`**：遇到需求變更時，**必須先用簡短純文字與使用者討論定案**；確認後，只使用 `edit_file` 修改局部幾十行程式碼，嚴禁反覆全檔覆寫。
> 2. **善用本機零成本資源**：使用者 Mac 本機已安裝 Ollama (`qwen2.5:14b`, `deepseek-r1:14b`, `qwen2.5vl:7b`) 與 `ffmpeg` / macOS `Meijia` 語音。日常大量文字、圖片主體辨識、MP3 轉檔優先寫成本機腳本或串接 Google Sheet CMS，不消耗雲端額度。
> 3. **注意預設工作目錄**：若預設 workspace `/Users/hohe/Desktop/故事vlog` 不存在，請勿呼叫 `run_command`，一律使用 `read_file` / `edit_file` / `write_file` 操作 `/Users/defi/...` 絕對路徑，或寫成 `.command` 腳本讓使用者執行。

---

## 一、核心專案路徑地圖

1. **【主力開發中】基督徒樂齡有聲選物網店（咖啡時光廊・歲月恩典館）**
   - 路徑：`/Users/defi/一號/projects/DEMO_light_shop/`
   - 主網頁：`/Users/defi/一號/projects/DEMO_light_shop/index.html`
   - 一鍵離線合成 4 首 MP3 並預覽腳本：`/Users/defi/一號/projects/DEMO_light_shop/一鍵合成MP3並預覽.command`
   - Netlify 設定：`/Users/defi/一號/projects/DEMO_light_shop/netlify.toml`

2. **【已完成支線】兩姐妹「名片咖啡 Business Card Coffee」BNI 媒合平台**
   - 路徑：`/Users/defi/一號/projects/business-card-coffee/`
   - 樣站首頁：`index.html` ｜ 合作提案書 PDF：`proposal.html`

3. **【已完成支線】10×12cm 咖啡包完稿機 (`/composer` 本機 Ollama 免費版)**
   - 路徑：`/Users/defi/一號/projects/AI-IOT-coffee/studio/`
   - 對外啟動腳本：`/Users/defi/一號/projects/AI-IOT-coffee/studio/啟動對外demo.command`

---

## 二、`DEMO_light_shop/index.html` 目前已完成狀態

1. **旗艦首頁視覺 (Landing Page Hero)**：
   - 頂部導覽列採用手繪金線「咖啡杯＋十字晨光」SVG Logo，右側僅保留 `🔍 長輩大字 A+` 與 `💬 加 LINE 好友領故事`。
   - 語速控制 (`0.82x / 0.92x / 1.0x`) 收納於下方故事閱讀廳的語音播放器內。
2. **完整 10 大恩典生命主題分類 ＋ 10 篇 500 字三明治故事**：
   - `01. 愛`、`02. 饒恕`、`03. 等候`、`04. 盼望`、`05. 平安`、`06. 恩典`、`07. 陪伴`、`08. 感恩`、`09. 重新開始`、`10. 回家`。
3. **黃金左右雙欄（「左邊聽三明治故事 ＋ 右手邊順手帶貨」不跳轉設計）**：
   - **左欄**：三明治三層結構（上層歲月風浪 ➔ 夾心信仰轉折 ➔ 下層日常祝福），支援 Web Speech API 逐段發光高亮朗讀 ＋ `<audio>` MP3 播放與下載。
   - **右欄智慧切換（解決「先上故事、有賣再補商品」痛點）**：
     - 當 `hasProduct: true`：顯示對應恩典好物購買卡 ＋ **「💬 加 LINE 好友・用 LINE Pay 把祝福帶回家」** 彈窗（自動生成訂購文案＋LINE QR Code）。
     - 當 `hasProduct: false`（先上純故事）：自動顯示 **「🙏 為受訪長輩點燈代禱 ＆ 加 LINE 好友免費收聽新故事」**，並提供店長預覽切換鈕。

---

## 三、新 Session 接手後的待辦方向（先討論、後微調）

1. **UI / 文案微調確認**：先詢問使用者檢視 `DEMO_light_shop/index.html` 後，有哪些局部區塊想調整（先純文字討論，確認後再用 `edit_file` 小範圍修改）。
2. **串接 Google Sheet CMS 後台**：將 `DEMO_light_shop/index.html` 串接使用者原有的 Google Apps Script / Google Sheet CMS（含 Base64 MP3 原音中繼與商品欄位 `hasProduct`, `productTitle`, `productPrice`, `productImg`, `productDesc`），達成未來「改試算表就自動更新網站，完全不花 AI Token」。
3. **串接 ElevenLabs / 本機 TTS 量產流程**：協助建立最低成本的語音故事 `.mp3` 產出工作流。
