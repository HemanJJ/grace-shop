/*!
 * assistant.js — 購物小助理（光碼電台／grace-coffee）
 * 規則式對話，不呼叫外部 AI。可獨立運作；若頁面已載入 cart.js，金額與購物車直接共用。
 *
 * 用法：
 *   <link rel="stylesheet" href="assistant.css">
 *   <script src="assistant.js"></script>
 *   <script>Assistant.init({ productsUrl:'./products.json', lineUrl:'./line' })</script>
 */
(function (global) {
  'use strict';

  const CFG = {
    productsUrl: './products.json',
    tiersUrl: './tiers.json',   // 量價階梯（滿幾件打幾折）
    apiBase: '',                // 收單 API；留空 = 只產生訂單文字，不入庫
    lineUrl: './line',
    shippingFee: 8000,        // 分：80 元
    freeShipOver: 100000,     // 分：滿 1,000 免運
    hideCartFab: true,        // 隱藏 cart.js 的浮動球（避免兩顆球）
    hideSelectors: ['.fab-line'],  // 要隱藏的原站按鈕（避免兩顆球重疊）
    storageKey: 'as_cart_v1',
  };

  const H = {
    esc: (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])),
    money: (cents) => 'NT$' + Math.round(cents / 100).toLocaleString('zh-TW'),
    norm: (s) => String(s || '').toLowerCase().replace(/\s+/g, ''),
  };

  let products = [];
  let tiers = [];                     // 量價階梯：[{min_qty, percent}]
  let submitting = false;
  let cart = { items: [] };           // 自有購物車（不依賴 cart.js）
  let cartWidget = null;
  let el = {};
  let chips = [];
  let lastOrder = null;

  /* ───────── 購物車 ───────── */
  function loadCart() {
    try {
      const raw = localStorage.getItem(CFG.storageKey);
      const a = raw ? JSON.parse(raw) : [];
      cart.items = Array.isArray(a) ? a : [];
    } catch (e) { cart.items = []; }
  }
  function saveCart() {
    try { localStorage.setItem(CFG.storageKey, JSON.stringify(cart.items)); } catch (e) {}
    if (cartWidget) { cartWidget.clear(); cart.items.forEach((i) => cartWidget.add(i, i.qty)); }
  }
  function addToCart(p, qty) {
    const hit = cart.items.find((x) => x.id === p.id);
    if (hit) hit.qty += qty || 1;
    else cart.items.push({ id: p.id, name: p.title || p.name, price: p.priceNum * 100, qty: qty || 1, image: p.img });
    saveCart();
    refreshDot();
  }
  /* 量價階梯：同一商品自己湊件數（不同商品不併，成本不同） */
  function tierFor(qty) {
    let best = null;
    tiers.forEach((t) => {
      if (qty >= t.min_qty && (!best || t.min_qty > best.min_qty)) best = t;
    });
    return best;
  }
  function lineCalc(i) {
    const t = tierFor(i.qty);
    const unit = t ? (t.percent ? Math.round((i.price * t.percent) / 100) : (t.unit_price || 0) * 100) : i.price;
    return { unit, amount: unit * i.qty, list: i.price * i.qty, tier: t };
  }
  function nextTier(qty) {
    let n = null;
    tiers.forEach((t) => { if (t.min_qty > qty && (!n || t.min_qty < n.min_qty)) n = t; });
    return n;
  }
  function cartCalc() {
    let sub = 0, net = 0;
    const qty = cart.items.reduce((s, i) => s + i.qty, 0);
    cart.items.forEach((i) => {
      const l = lineCalc(i);
      sub += l.list;
      net += l.amount;
    });
    const discount = sub - net;
    const ship = net === 0 ? 0 : (net >= CFG.freeShipOver ? 0 : CFG.shippingFee);
    return { sub, net, discount, qty, ship, total: net + ship };
  }
  function refreshDot() {
    const n = cartCalc().qty;
    if (!el.dot) return;
    el.dot.textContent = n;
    el.dot.hidden = n === 0;
  }

  /* ───────── 對話 ───────── */
  function say(text, who) {
    const wrap = document.createElement('div');
    wrap.className = 'as-msg' + (who === 'me' ? ' me' : '');
    wrap.innerHTML = `<div class="as-bubble">${H.esc(text)}</div>`;
    el.body.appendChild(wrap);
    scrollDown();
  }
  function showCards(list) {
    if (!list.length) return;
    const wrap = document.createElement('div');
    wrap.className = 'as-cards';
    wrap.innerHTML = list.map((p) => `
      <div class="as-card" data-pid="${H.esc(p.id)}">
        ${p.img ? `<img class="pic" src="${H.esc(p.img)}" alt="" loading="lazy">` : ''}
        <div class="in">
          <div class="t">${H.esc(p.title)}</div>
          <div class="p">${H.money(p.priceNum * 100)} / ${H.esc(p.unit || '份')}</div>
          <div class="b">
            <button class="as-add" data-act="add">加入</button>
            <button class="as-more" data-act="detail">看說明</button>
          </div>
        </div>
      </div>`).join('');
    el.body.appendChild(wrap);
    scrollDown();
  }
  function scrollDown() { el.body.scrollTop = el.body.scrollHeight; }

  function setChips(list) {
    chips = list;
    el.chips.innerHTML = list.map((c) => `<button class="as-chip" type="button">${H.esc(c)}</button>`).join('');
  }

  /* ───────── 意圖 ───────── */
  const BUDGET = /(\d{2,5})\s*(元|塊|以下|以內)?/;
  const KEYMAP = [
    ['咖啡', ['咖啡飲品', '咖啡']],
    ['茶', ['茶飲']],
    ['長輩', ['長輩', '銀髮', '孝敬', '父母', '爸']],
    ['送禮', ['禮盒', '送', '禮']],
    ['保健', ['補養', '保健', '輔具']],
    ['油', ['油品']],
    ['穀', ['穀物']],
  ];

  function search(q, budget) {
    const nq = H.norm(q);
    let list = products.filter((p) => p.active !== false);
    const cats = [];
    KEYMAP.forEach(([, keys]) => { if (keys.some((k) => nq.includes(k))) cats.push(...keys); });
    if (cats.length) list = list.filter((p) => cats.some((c) => (p.category + p.title + p.tag).includes(c)));
    // 關鍵字比對標題／描述／特點
    const words = nq.replace(/[，,。!?？、]/g, ' ').split(/\s+/).filter((w) => w.length >= 2);
    if (words.length) {
      const hit = list.filter((p) => words.some((w) => H.norm(p.title + p.desc + (p.features || []).join('')).includes(w)));
      if (hit.length) list = hit;
    }
    if (budget) list = list.filter((p) => p.priceNum <= budget);
    return list;
  }

  function handle(text) {
    const t = String(text || '').trim();
    if (!t) return;

    // 購物車
    if (/購物車|車子|買了什麼|明細/.test(t)) return showCart();
    if (/結帳|付款|怎麼付|line\s*pay/i.test(t)) return checkout();
    if (/運費|免運/.test(t)) {
      const c = cartCalc();
      return say(c.net >= CFG.freeShipOver
        ? `這單已免運。付款用 LINE Pay，按「結帳」我幫你把清單帶過去。`
        : `運費 ${H.money(CFG.shippingFee)}，滿 ${H.money(CFG.freeShipOver)} 免運。你現在 ${H.money(c.net)}，還差 ${H.money(CFG.freeShipOver - c.net)}。`);
    }

    // 打招呼
    if (/你好|哈囉|hi|嗨|在嗎/i.test(t) && t.length <= 6) {
      setChips(['送長輩', '自己喝', '500 元以下', '看購物車']);
      return say('我在。想找送人的，還是自己用的？也可以直接說預算。');
    }

    // 預算
    const bm = t.match(BUDGET);
    const budget = bm ? parseInt(bm[1], 10) : null;

    const list = search(t, budget);
    if (list.length) {
      say(budget ? `找到 ${list.length} 項在 ${budget} 元以內，這幾個最接近你的需求：` : `這幾個比較合適：`);
      showCards(list.slice(0, 3));
      setChips(['看購物車', '結帳', '換一批']);
      return;
    }
    say('我沒抓到你要的方向。可以說「送長輩」「500 以下」「想喝咖啡」，或直接看全部好物。');
    setChips(['送長輩', '自己喝', '500 元以下', '看購物車']);
  }

  function pctLabel(t) { return t.percent ? (t.percent / 10) + ' 折' : H.money((t.unit_price || 0) * 100); }

  function showCart() {
    const c = cartCalc();
    if (!c.qty) { setChips(['送長輩', '500 元以下']); return say('購物車還是空的。要我推薦嗎？'); }
    const lines = cart.items.map((i) => {
      const l = lineCalc(i);
      return `・${i.name} × ${i.qty}${l.tier ? `（${pctLabel(l.tier)}）` : ''}　${H.money(l.amount)}`;
    }).join('\n');

    // 差幾件就進下一階（挑最接近的那一項講）
    let hint = '';
    let best = null;
    cart.items.forEach((i) => {
      const n = nextTier(i.qty);
      if (!n) return;
      const gap = n.min_qty - i.qty;
      if (!best || gap < best.gap) best = { gap, name: i.name, tier: n };
    });
    if (best) hint = `\n\n再 ${best.gap} 件「${best.name.slice(0, 10)}…」就進 ${pctLabel(best.tier)}`;

    say(`你的購物車：\n${lines}\n\n小計 ${H.money(c.sub)}` +
        (c.discount ? `\n階梯折扣 −${H.money(c.discount)}` : '') +
        `\n運費 ${c.ship ? H.money(c.ship) : '免運'}\n應付 ${H.money(c.total)}` + hint);
    setChips(['結帳', '繼續逛', '清空']);
  }

  function buildOrder(server) {
    const c = cartCalc();
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const no = (server && server.id) ||
      'GC' + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + '-' +
      pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds());
    const lines = cart.items.map((i, k) => {
      const l = lineCalc(i);
      return `${k + 1}. ${i.name}  ×${i.qty}  ${l.tier ? '（' + pctLabel(l.tier) + '）' : ''} ${H.money(l.amount)}`;
    }).join('\n');

    const sub = server ? server.subtotal : c.sub;
    const disc = server ? server.discount : c.discount;
    const ship = server ? server.shipping : c.ship;
    const total = server ? server.total : c.total;

    const text =
      '【光碼電台・好物訂單】\n' +
      '訂單編號：' + no + '\n' +
      '訂單時間：' + d.toLocaleString('zh-TW', { hour12: false }) + '\n' +
      '------------------------\n' +
      lines + '\n' +
      '------------------------\n' +
      '小計：' + H.money(sub) + '\n' +
      (disc ? '階梯折扣：−' + H.money(disc) + '\n' : '') +
      '運費：' + (ship ? H.money(ship) : '免運') + '\n' +
      '應付：' + H.money(total) + '\n\n' +
      (server
        ? '（已收單，這份可傳給小編對帳）'
        : '（尚未入庫！請把這份訂單傳給小編，我們會回覆匯款或 LINE Pay 資訊）');
    return { no, text, total, qty: c.qty, saved: !!server };
  }

  function downloadTxt(filename, text) {
    try {
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      return true;
    } catch (e) { console.warn('[assistant] 下載失敗', e); return false; }
  }

  // LINE 只吃文字分享；檔案要用系統分享或下載後手動附加
  function shareToLine(text) {
    const url = 'https://line.me/R/msg/text/?' + encodeURIComponent(text.slice(0, 1800));
    location.href = url;
  }

  async function shareFile(text, filename) {
    try {
      const file = new File([text], filename, { type: 'text/plain' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: '訂單', text: '光碼電台訂單' });
        return true;
      }
    } catch (e) {}
    return false;
  }

  async function checkout() {
    const c = cartCalc();
    if (!c.qty) { return say('購物車是空的，先挑一樣吧。'); }
    if (submitting) { return say('正在送單，稍等一下。'); }

    let server = null;
    if (CFG.apiBase) {
      submitting = true;
      say('送出訂單中…');
      try {
        const res = await fetch(String(CFG.apiBase).replace(/\/+$/, '') + '/api/orders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ items: cart.items.map((i) => ({ id: i.id, qty: i.qty })) }),
        });
        const data = await res.json().catch(() => null);
        if (res.ok && data && data.ok) server = data.order;
        else if (data && data.message) say('這張單沒進資料庫：' + data.message);
      } catch (e) {
        console.warn('[assistant] 送單失敗', e);
        say('連不上收單系統，先給你訂單文字，一樣可以傳 LINE。');
      } finally { submitting = false; }
    }

    const o = buildOrder(server);
    lastOrder = o;
    say(o.text);
    setChips(['用 LINE 傳', '存成 txt', '複製']);
    if (server) { cart.items = []; saveCart(); refreshDot(); }
  }

  function copy(text) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(text); return; }
    } catch (e) {}
    const ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    ta.remove();
  }

  /* ───────── DOM ───────── */
  function build() {
    const root = document.createElement('div');
    root.className = 'as-root';
    root.innerHTML = `
      <button class="as-fab" type="button" aria-label="購物小助理">💬<span class="as-dot" hidden>0</span></button>
      <div class="as-mask" hidden></div>
      <div class="as-panel" role="dialog" aria-label="購物小助理" hidden>
        <div class="as-head">
          <div class="as-avatar">🛍️</div>
          <div><b>購物小助理</b><small>挑好物・帶你回 LINE 結帳</small></div>
          <button class="as-close" type="button" aria-label="關閉">✕</button>
        </div>
        <div class="as-body"></div>
        <div class="as-chips"></div>
        <div class="as-input">
          <input type="text" placeholder="想找什麼？例如：送長輩 500 以下" aria-label="輸入訊息">
          <button class="as-send" type="button" aria-label="送出">➤</button>
        </div>
      </div>`;
    document.body.appendChild(root);

    el = {
      root,
      fab: root.querySelector('.as-fab'),
      dot: root.querySelector('.as-dot'),
      mask: root.querySelector('.as-mask'),
      panel: root.querySelector('.as-panel'),
      body: root.querySelector('.as-body'),
      chips: root.querySelector('.as-chips'),
      input: root.querySelector('.as-input input'),
      send: root.querySelector('.as-send'),
      close: root.querySelector('.as-close'),
    };

    el.fab.onclick = open;
    el.mask.onclick = close;
    el.close.onclick = close;

    el.send.onclick = () => {
      const v = el.input.value.trim();
      if (!v) return;
      el.input.value = '';
      say(v, 'me');
      setTimeout(() => handle(v), 180);
    };
    el.input.addEventListener('keydown', (e) => { if (e.key === 'Enter') el.send.click(); });

    el.chips.addEventListener('click', (e) => {
      const b = e.target.closest('.as-chip');
      if (!b) return;
      const v = b.textContent.trim();
      say(v, 'me');
      if (v === '看購物車') return setTimeout(showCart, 120);
      if (v === '結帳') return setTimeout(checkout, 120);
      if (v === '繼續逛') { setChips(['送長輩', '自己喝', '500 元以下']); return; }
      if (v === '清空') { cart.items = []; saveCart(); refreshDot(); return say('已清空。'); }
      if (v === '用 LINE 傳') {
        if (!lastOrder) return say('先按「結帳」產生訂單。');
        shareToLine(lastOrder.text);
        return;
      }
      if (v === '存成 txt') {
        if (!lastOrder) return say('先按「結帳」產生訂單。');
        const file = 'order-' + lastOrder.no + '.txt';
        shareFile(lastOrder.text, file).then((ok) => {
          if (!ok && downloadTxt(file, lastOrder.text)) say('已下載 ' + file + '，在 LINE 裡用「+ → 檔案」附上就行。');
          else if (ok) say('已開啟分享，選 LINE 傳給小編。');
        });
        return;
      }
      if (v === '複製') {
        if (!lastOrder) return say('先按「結帳」產生訂單。');
        copy(lastOrder.text);
        return say('訂單已複製，貼到 LINE 對話就行。');
      }
      if (v === '換一批') return handle('推薦');
      setTimeout(() => handle(v), 120);
    });

    el.body.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-act]');
      if (!btn) return;
      const card = btn.closest('.as-card');
      const p = products.find((x) => x.id === card.dataset.pid);
      if (!p) return;
      if (btn.dataset.act === 'add') {
        addToCart(p);
        const c = cartCalc();
        const gap = CFG.freeShipOver - c.net;
        say(`已加入「${p.title.slice(0, 14)}…」\n目前 ${c.qty} 件，${H.money(c.total)}${gap > 0 ? `，再 ${H.money(gap)} 免運` : '，已免運'}`);
        setChips(['看購物車', '結帳', '繼續逛']);
      } else {
        say(`${p.title}\n\n${p.desc}\n\n${(p.features || []).map((f) => '・' + f).join('\n')}`);
        setChips(['加入', '看購物車']);
      }
    });
  }

  function open() {
    el.panel.hidden = false; el.mask.hidden = false;
    requestAnimationFrame(() => el.panel.classList.add('on'));
    if (!el.opened) {
      el.opened = true;
      say('嗨，我是購物小助理 👋\n說說你想找什麼，或直接點下面的選項。');
      setChips(['送長輩', '自己喝', '500 元以下', '看購物車']);
    }
  }
  function close() {
    el.panel.classList.remove('on');
    setTimeout(() => { el.panel.hidden = true; el.mask.hidden = true; }, 220);
  }

  /* ───────── init ───────── */
  async function init(opts) {
    Object.assign(CFG, opts || {});
    loadCart();
    build();
    refreshDot();

    const hide = [].concat(CFG.hideCartFab ? ['.cw-fab'] : [], CFG.hideSelectors || []);
    if (hide.length) {
      const st = document.createElement('style');
      st.textContent = hide.join(',') + '{display:none!important}';
      document.head.appendChild(st);
    }

    try {
      const res = await fetch(CFG.productsUrl, { cache: 'no-store' });
      const data = await res.json();
      products = (Array.isArray(data) ? data : data.products || []).filter((p) => p && p.id);
    } catch (e) {
      console.warn('[assistant] products.json 載入失敗', e);
    }

    try {
      const res2 = await fetch(CFG.tiersUrl, { cache: 'no-store' });
      const data2 = await res2.json();
      tiers = (data2.tiers || [])
        .filter((t) => t && Number(t.min_qty) > 0)
        .map((t) => ({ min_qty: Number(t.min_qty), percent: t.percent != null ? Number(t.percent) : null, unit_price: t.unit_price != null ? Number(t.unit_price) : null }))
        .sort((a, b) => a.min_qty - b.min_qty);
    } catch (e) {
      console.warn('[assistant] tiers.json 載入失敗', e);
      tiers = [];
    }
    return api;
  }

  const api = { init, open, close, say, orderText: () => (lastOrder ? lastOrder.text : ''), buildOrder, products: () => products.slice(), add: (id, q) => { const p = products.find((x) => x.id === id); if (p) addToCart(p, q); }, cart: () => cartCalc() };
  global.Assistant = api;
})(window);
