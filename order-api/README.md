# 收單系統（團購用）

## 這是什麼

客人按「結帳」→ 訂單真的寫進資料庫（Cloudflare D1）→ 你打開看板就看到的單。
不再是「客人傳一則 LINE 訊息，你在那邊對」。

## 兩個網址

| 用途 | 網址 |
|---|---|
| 客人買東西 | https://grace-coffee.pages.dev |
| 你看今天的單 | https://grace-coffee.pages.dev/orders |
| 收單後台（程式用） | https://grace-order-api.difly.workers.dev |

看單密碼存在 `order-api/看單密碼.txt`（這個檔不進版控）。

## 量價階梯怎麼算

同一樣商品自己湊件數，**不同商品不合併**（成本不同，併起來會賠）。

| 滿幾件 | 折扣 |
|---|---|
| 50 | 9 折 |
| 100 | 8 折 |
| 200 | 7 折 |

要改數字：改 `tiers.json` → 重新灌資料庫 → 重新部署（下面「改東西之後」）。

## 你要填的兩個欄位

`products.json` 每樣商品有兩個欄位現在是空的：

- `cost`：進價（元）。沒填 → 毛利算不準，折扣低於成本也擋不住。
- `boxQty`：箱入數。沒填 → 叫貨只能看件數。

填好跟我說，我重新灌一次就會生效。

## 改東西之後（不用打指令）

打開本機後台（桌面 `🧾 網站後台`）→「發布」頁：

- 按 **🔄 同步價錢到收單系統**：把 products.json 的價錢、進價、箱入數＋tiers.json 的階梯，一次灌進收單資料庫。
- 按 **🚀 發布上線**：會先自動同步，再把網站推上線。

> 為什麼不能只發布：網站（前台）讀 JSON、結帳（收單）讀資料庫，兩個都要更新，價錢才會一致。

## 工程用（我要自己跑的時候）

```bash
cd ~/一號/projects/DEMO_light_shop/order-api
curl -sS -X POST https://grace-order-api.difly.workers.dev/api/admin/sync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(cat 看單密碼.txt)" \
  -d "{\"products\": [], \"tiers\": []}"   # 空的不會刪東西，只是示意
```

真正灌資料用後台按鈕就好。

## 出事了怎麼看

- 客人說「沒收到單」→ 先看看板那天有沒有；沒有就是他的網路斷在送出前。
- 系統連不上（極少）→ 網站會自己退回「只產生訂單文字」，客人仍可傳 LINE，不會卡死。
