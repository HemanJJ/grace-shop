#!/usr/bin/env node
/**
 * 把 products.json ＋ tiers.json 灌進 D1。
 * 用法（在專案根目錄）：
 *   node scripts/seed-d1.mjs > /tmp/seed.sql
 *   cd order-api && wrangler d1 execute grace-shop --remote --file=/tmp/seed.sql
 *   本機測試：wrangler d1 execute grace-shop --local --file=/tmp/seed.sql
 */
import { readFileSync } from 'node:fs';

const q = (v) => (v === null || v === undefined || v === '' ? 'NULL' : `'${String(v).replace(/'/g, "''")}'`);
const n = (v) => (v === null || v === undefined || v === '' ? 'NULL' : Number(v));

const products = JSON.parse(readFileSync('products.json', 'utf8'));
const tiersFile = JSON.parse(readFileSync('tiers.json', 'utf8'));
const tiers = tiersFile.tiers || [];

const out = ['PRAGMA foreign_keys=OFF;'];
out.push('DELETE FROM order_items; DELETE FROM orders; DELETE FROM price_tiers; DELETE FROM products;');

for (const p of products) {
  if (p.active === false) continue;
  out.push(
    `INSERT INTO products (id, name, unit, price, cost, box_qty, active, updated_at) VALUES (` +
      [q(p.id), q(p.title || p.name), q(p.unit || '份'), n(p.priceNum), n(p.cost), n(p.boxQty), 1, q(new Date().toISOString())].join(',') +
      ');'
  );
}

for (const t of tiers) {
  out.push(
    `INSERT INTO price_tiers (product_id, min_qty, percent, unit_price) VALUES (` +
      [q(t.product_id || '*'), n(t.min_qty), n(t.percent), n(t.unit_price)].join(',') +
      ') ON CONFLICT(product_id, min_qty) DO UPDATE SET percent=excluded.percent, unit_price=excluded.unit_price;'
  );
}

out.push(`SELECT 'products=' || count(*) FROM products;`);
out.push(`SELECT 'tiers=' || count(*) FROM price_tiers;`);
console.log(out.join('\n'));
