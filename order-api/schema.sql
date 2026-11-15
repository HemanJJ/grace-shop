-- 光碼電台・團購收單 資料表
-- 金額單位：新台幣「元」（整數）

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS price_tiers;
DROP TABLE IF EXISTS products;

-- ① 商品主檔：進價、售價、箱入數
CREATE TABLE products (
  id          TEXT PRIMARY KEY,      -- P001
  name        TEXT NOT NULL,
  unit        TEXT,                  -- 盒 / 組 / 瓶
  price       INTEGER NOT NULL,      -- 售價（元）
  cost        INTEGER,               -- 進價（元）；NULL = 還沒填
  box_qty     INTEGER,               -- 箱入數；NULL = 還沒填
  active      INTEGER NOT NULL DEFAULT 1,
  updated_at  TEXT
);

-- ② 量價階梯：同一商品湊到 min_qty，打 percent 折（90 = 9 折）
--    product_id = '*' 表示套用到全部商品
CREATE TABLE price_tiers (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id  TEXT NOT NULL,
  min_qty     INTEGER NOT NULL,      -- 滿幾件
  percent     INTEGER,               -- 折扣（90 = 9 折）
  unit_price  INTEGER,               -- 或直接指定單價（二選一）
  UNIQUE (product_id, min_qty)
);

-- ③ 訂單
CREATE TABLE orders (
  id          TEXT PRIMARY KEY,      -- GC20261115-10300012
  created_at  TEXT NOT NULL,         -- ISO（台灣時間）
  buyer_name  TEXT,
  buyer_phone TEXT,
  note        TEXT,
  subtotal    INTEGER NOT NULL,      -- 原價小計（元）
  discount    INTEGER NOT NULL,      -- 折扣（元）
  shipping    INTEGER NOT NULL,      -- 運費（元）
  total       INTEGER NOT NULL,      -- 應付（元）
  cost_total  INTEGER,               -- 這張單的成本（元）
  status      TEXT NOT NULL DEFAULT 'new',  -- new / confirmed / shipped / done / cancelled
  source      TEXT NOT NULL DEFAULT 'web'
);

-- ④ 訂單明細
CREATE TABLE order_items (
  order_id     TEXT NOT NULL,
  product_id   TEXT NOT NULL,
  name         TEXT,
  qty          INTEGER NOT NULL,
  list_price   INTEGER NOT NULL,     -- 原價單價
  unit_price   INTEGER NOT NULL,     -- 折後單價
  amount       INTEGER NOT NULL,     -- unit_price × qty
  cost         INTEGER,              -- 成本單價
  tier_percent INTEGER               -- 套用到幾折
);

CREATE INDEX idx_tiers ON price_tiers (product_id, min_qty);
CREATE INDEX idx_orders_created ON orders (created_at);
CREATE INDEX idx_items_order ON order_items (order_id);
