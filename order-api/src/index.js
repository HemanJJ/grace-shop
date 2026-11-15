/**
 * grace-order-api — 光碼電台團購收單 API
 *
 * 只做三件事：
 *   1) POST /api/orders   收單：用 D1 裡的售價＋量價階梯重算金額（不信前端送來的錢）
 *   2) GET  /api/orders   看單：要 ADMIN_TOKEN，順便算成本、毛利、叫貨量
 *   3) GET  /api/health   活著沒
 *
 * 金額單位一律「元」。
 */

const SHIP_FEE = 80;        // 運費 80 元
const FREE_SHIP_OVER = 1000; // 滿 1000 免運

const ALLOWED_ORIGINS = [
  'https://grace-coffee.pages.dev',
  'http://localhost:8788',
  'http://127.0.0.1:8788',
];

class HttpError extends Error {
  constructor(status, code, detail) {
    super(code);
    this.status = status;
    this.code = code;
    this.detail = detail || null;
  }
}

function corsHeaders(req) {
  const origin = req.headers.get('Origin') || '';
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allow,
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

function json(data, headers, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...headers },
  });
}

/* 台灣時間（UTC+8） */
function taipeiParts(ms = Date.now()) {
  const d = new Date(ms + 8 * 3600 * 1000);
  const p = (n) => String(n).padStart(2, '0');
  const ymd = `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}`;
  const ymdDash = `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}`;
  const hms = `${p(d.getUTCHours())}${p(d.getUTCMinutes())}${p(d.getUTCSeconds())}`;
  return { ymd, ymdDash, hms, iso: `${ymdDash}T${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}+08:00` };
}

function normalizeItems(raw) {
  if (!Array.isArray(raw) || raw.length === 0) throw new HttpError(400, 'empty_cart', '購物車是空的');
  if (raw.length > 30) throw new HttpError(400, 'too_many_items', '一次最多 30 樣');
  const merged = new Map();
  for (const it of raw) {
    const id = String((it && it.id) || '').trim();
    const qty = Math.floor(Number(it && it.qty));
    if (!id || !/^[A-Za-z0-9_-]{1,32}$/.test(id)) throw new HttpError(400, 'bad_item', '商品編號不正確');
    if (!Number.isFinite(qty) || qty < 1 || qty > 999) throw new HttpError(400, 'bad_qty', '數量要在 1～999 之間');
    merged.set(id, (merged.get(id) || 0) + qty);
  }
  return [...merged.entries()].map(([id, qty]) => ({ id, qty }));
}

function pickTier(tiers, productId, qty) {
  let best = null;
  for (const t of tiers) {
    if (t.product_id !== productId && t.product_id !== '*') continue;
    if (t.min_qty > qty) continue;
    if (!best || t.min_qty > best.min_qty || (t.min_qty === best.min_qty && t.product_id === productId)) best = t;
  }
  return best;
}

async function createOrder(req, env, cors) {
  const body = await req.json().catch(() => { throw new HttpError(400, 'bad_json'); });
  const items = normalizeItems(body.items);

  const ids = items.map((i) => i.id);
  const ph = ids.map(() => '?').join(',');

  const { results: prods } = await env.DB
    .prepare(`SELECT id, name, unit, price, cost, box_qty FROM products WHERE active = 1 AND id IN (${ph})`)
    .bind(...ids).all();
  const byId = new Map(prods.map((p) => [p.id, p]));
  for (const i of items) {
    if (!byId.has(i.id)) throw new HttpError(400, 'unknown_product', `找不到商品 ${i.id}`);
  }

  const { results: tiers } = await env.DB
    .prepare(`SELECT product_id, min_qty, percent, unit_price FROM price_tiers WHERE product_id = '*' OR product_id IN (${ph})`)
    .bind(...ids).all();

  const lines = [];
  let subtotal = 0, net = 0, costTotal = 0, hasCost = false;

  for (const it of items) {
    const p = byId.get(it.id);
    const tier = pickTier(tiers, p.id, it.qty);
    const unitPrice = tier
      ? (tier.percent ? Math.round((p.price * tier.percent) / 100) : tier.unit_price)
      : p.price;

    // 護欄：折後單價低於進價 → 擋單（進價沒填就不擋）
    if (p.cost && unitPrice < p.cost) {
      throw new HttpError(409, 'below_cost',
        `${p.name} 折後 ${unitPrice} 元低於進價 ${p.cost} 元，這階梯會賠錢`);
    }

    const amount = unitPrice * it.qty;
    subtotal += p.price * it.qty;
    net += amount;
    if (p.cost != null) { hasCost = true; costTotal += p.cost * it.qty; }

    lines.push({
      product_id: p.id, name: p.name, qty: it.qty,
      list_price: p.price, unit_price: unitPrice, amount,
      cost: p.cost, tier_percent: tier ? (tier.percent || null) : null,
    });
  }

  const discount = subtotal - net;
  const shipping = net >= FREE_SHIP_OVER ? 0 : SHIP_FEE;
  const total = net + shipping;

  const t = taipeiParts();
  const rand = String(Math.floor(Math.random() * 90) + 10);
  const orderId = `GC${t.ymd}-${t.hms}${rand}`;

  const buyerName = String(body.buyer_name || '').slice(0, 40);
  const buyerPhone = String(body.buyer_phone || '').replace(/[^\d+\-() ]/g, '').slice(0, 20);
  const note = String(body.note || '').slice(0, 300);

  const stmts = [
    env.DB.prepare(
      `INSERT INTO orders (id, created_at, buyer_name, buyer_phone, note, subtotal, discount, shipping, total, cost_total, status, source)
       VALUES (?,?,?,?,?,?,?,?,?,?, 'new', 'web')`
    ).bind(orderId, t.iso, buyerName, buyerPhone, note, subtotal, discount, shipping, total, hasCost ? costTotal : null),
    ...lines.map((l) =>
      env.DB.prepare(
        `INSERT INTO order_items (order_id, product_id, name, qty, list_price, unit_price, amount, cost, tier_percent)
         VALUES (?,?,?,?,?,?,?,?,?)`
      ).bind(orderId, l.product_id, l.name, l.qty, l.list_price, l.unit_price, l.amount, l.cost, l.tier_percent)
    ),
  ];
  await env.DB.batch(stmts);

  return json({
    ok: true,
    order: { id: orderId, created_at: t.iso, subtotal, discount, shipping, total, items: lines },
  }, cors);
}

function requireToken(req, env, url) {
  const token = req.headers.get('Authorization')?.replace(/^Bearer\s+/i, '') || url.searchParams.get('token');
  if (!env.ADMIN_TOKEN || token !== env.ADMIN_TOKEN) throw new HttpError(401, 'unauthorized', '要看單要先給密碼');
}

async function listOrders(req, env, url, cors) {
  requireToken(req, env, url);

  const date = url.searchParams.get('date') || taipeiParts().ymdDash;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new HttpError(400, 'bad_date');

  const { results: orders } = await env.DB
    .prepare(`SELECT * FROM orders WHERE created_at LIKE ? ORDER BY created_at DESC`)
    .bind(`${date}%`).all();

  const { results: items } = await env.DB
    .prepare(`SELECT * FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE created_at LIKE ?)`)
    .bind(`${date}%`).all();

  const byOrder = new Map();
  for (const it of items) {
    if (!byOrder.has(it.order_id)) byOrder.set(it.order_id, []);
    byOrder.get(it.order_id).push(it);
  }

  // 叫貨彙總：同一商品今天總共幾件
  const need = new Map();
  for (const it of items) {
    if (!need.has(it.product_id)) {
      need.set(it.product_id, { product_id: it.product_id, name: it.name, qty: 0, amount: 0 });
    }
    const n = need.get(it.product_id);
    n.qty += it.qty; n.amount += it.amount;
  }

  const sum = (k) => orders.reduce((s, o) => s + (o[k] || 0), 0);

  return json({
    ok: true,
    date,
    count: orders.length,
    totals: {
      revenue: sum('total'),
      subtotal: sum('subtotal'),
      discount: sum('discount'),
      shipping: sum('shipping'),
      cost: sum('cost_total'),
      profit: sum('total') - sum('cost_total') - sum('shipping'),
      pieces: items.reduce((s, i) => s + i.qty, 0),
    },
    need: [...need.values()].sort((a, b) => b.qty - a.qty),
    orders: orders.map((o) => ({ ...o, items: byOrder.get(o.id) || [] })),
  }, cors);
}

/**
 * 把本機後台的商品主檔＋量價階梯整批灌進來。
 * 不動訂單，只動商品與階梯。
 */
async function syncCatalog(req, env, url, cors) {
  requireToken(req, env, url);
  const body = await req.json().catch(() => { throw new HttpError(400, 'bad_json'); });
  if (!Array.isArray(body.products)) throw new HttpError(400, 'bad_products', '少了 products');

  const now = taipeiParts().iso;
  const ids = [];
  const stmts = [];

  for (const p of body.products) {
    const id = String((p && p.id) || '').trim();
    if (!/^[A-Za-z0-9_-]{1,32}$/.test(id)) continue;
    const price = Math.round(Number(p.priceNum != null ? p.priceNum : p.price) || 0);
    if (!price) continue;
    ids.push(id);
    stmts.push(env.DB.prepare(
      `INSERT INTO products (id, name, unit, price, cost, box_qty, active, updated_at)
       VALUES (?,?,?,?,?,?,?,?)
       ON CONFLICT(id) DO UPDATE SET
         name = excluded.name, unit = excluded.unit, price = excluded.price,
         cost = excluded.cost, box_qty = excluded.box_qty,
         active = excluded.active, updated_at = excluded.updated_at`
    ).bind(
      id,
      String(p.title || p.name || '').slice(0, 120),
      String(p.unit || '份').slice(0, 8),
      price,
      p.cost == null || p.cost === '' ? null : Math.round(Number(p.cost)),
      p.boxQty == null || p.boxQty === '' ? null : Math.round(Number(p.boxQty)),
      p.active === false ? 0 : 1,
      now
    ));
  }

  if (!ids.length) throw new HttpError(400, 'no_valid_products', '一筆有效的商品都沒有');

  // 下架不在名單裡的商品（不刪，訂單紀錄還要對）
  stmts.push(env.DB.prepare(`UPDATE products SET active = 0 WHERE id NOT IN (${ids.map(() => '?').join(',')})`).bind(...ids));

  // 階梯整批換掉
  stmts.push(env.DB.prepare('DELETE FROM price_tiers'));
  let tierCount = 0;
  for (const t of Array.isArray(body.tiers) ? body.tiers : []) {
    const minQty = Math.round(Number(t && t.min_qty));
    if (!minQty || minQty < 1) continue;
    const percent = t.percent == null || t.percent === '' ? null : Number(t.percent);
    const unitPrice = t.unit_price == null || t.unit_price === '' ? null : Math.round(Number(t.unit_price));
    if (!percent && !unitPrice) continue;
    tierCount++;
    stmts.push(env.DB.prepare(
      `INSERT INTO price_tiers (product_id, min_qty, percent, unit_price) VALUES (?,?,?,?)`
    ).bind(String(t.product_id || '*').slice(0, 32), minQty, percent, unitPrice));
  }

  await env.DB.batch(stmts);
  return json({ ok: true, products: ids.length, tiers: tierCount, at: now }, cors);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const cors = corsHeaders(req);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });

    try {
      if (url.pathname === '/api/health') return json({ ok: true, at: taipeiParts().iso }, cors);
      if (url.pathname === '/api/orders' && req.method === 'POST') return await createOrder(req, env, cors);
      if (url.pathname === '/api/orders' && req.method === 'GET') return await listOrders(req, env, url, cors);
      if (url.pathname === '/api/admin/sync' && req.method === 'POST') return await syncCatalog(req, env, url, cors);
      return json({ ok: false, error: 'not_found' }, cors, 404);
    } catch (e) {
      if (e instanceof HttpError) {
        return json({ ok: false, error: e.code, message: e.detail }, cors, e.status);
      }
      return json({ ok: false, error: 'server_error', message: String(e && e.message || e) }, cors, 500);
    }
  },
};
