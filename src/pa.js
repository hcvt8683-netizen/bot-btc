// ===== PRICE ACTION VIEW START =====
// Chế độ Price action (nút #mode-pa, khu #pa-app, lớp body.pa-view). build.py nhúng SR = data/results/sr.json
// (bot/models/sr_levels.py): kháng cự / hỗ trợ của từng khung, bật lại hay xuyên qua khi chạm so với mức giả, khả năng chạm.
// Mức lúc này tính từ nến BTCUSDT vĩnh cửu (fapi.binance.com) cùng cách với sr_levels.levels (W nến đã đóng, ATR 14).
// Tách riêng như ls.js / trend.js: không đọc, không ghi gì của phần khác; bảng Kiểm tra điểm vào (src/pact.js) nằm trong khu này.
(() => {
  const SR = /*SR_JSON*/null;
  const { tx, vnTime } = I18N;
  const $ = (id) => document.getElementById(id);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  const nf = (d) => new Intl.NumberFormat('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d });
  const ok = (x) => x != null && isFinite(x);
  const pc = (x, d = 0) => (ok(x) ? nf(d).format(x * 100) + '%' : '—');
  const usd = (x) => (ok(x) ? nf(0).format(x) + ' $' : '—');
  const spc = (x, d = 1) => { if (!ok(x)) return '—'; const r = Math.round(x * 100 * 10 ** d) / 10 ** d; return (r > 0 ? '+' : r < 0 ? '−' : '') + nf(d).format(Math.abs(r)) + '%'; };
  const sp = (x, d) => (ok(x) ? (x < 0 ? '−' : '') + nf(d).format(Math.abs(x)) : '—');
  const utcIso = (s) => s.replace(' ', 'T') + 'Z';
  const LOCAL = location.protocol.startsWith('http') && ['localhost', '127.0.0.1'].includes(location.hostname);
  const FAPI = 'https://fapi.binance.com/fapi/v1/';
  const ATR_N = SR ? SR.atr_n : 14;
  const VIEWS = ['mode-buy', 'mode-sell', 'mode-ls', 'mode-tr'];
  const KEY = 'btc-bot3-view';

  async function getJSON(url, timeout = 15000) {
    const once = async (u) => {
      const ctl = new AbortController(), tm = setTimeout(() => ctl.abort(), timeout);
      try { const r = await fetch(u, { signal: ctl.signal }); if (!r.ok) throw new Error('HTTP ' + r.status); return await r.json(); } finally { clearTimeout(tm); }
    };
    if (LOCAL) { try { return await once('/proxy?url=' + encodeURIComponent(url)); } catch (e) { /* thử trực tiếp */ } }
    return once(url);
  }

  const view = { unit: 'ngay', n: 1, live: null, err: null, timer: null, busy: false };
  const row = (u, n, side) => (SR ? SR.frames.find((r) => r.unit === u && r.n === n && r.side === side) : null);
  const nsOf = (u) => (SR ? [...new Set(SR.frames.filter((r) => r.unit === u).map((r) => r.n))] : []);
  const frameName = (u, n) => tx('web.pa.f_' + u, n);
  const horizon = (r) => (r.candles === '1h' && r.H >= 24 && r.H % 24 === 0 ? tx('web.pa.h_days', r.H / 24) : r.candles === '1h' ? tx('web.pa.h_hours', r.H) : tx('web.pa.h_days', r.H));

  // ----- nến trực tiếp: 520 nến giờ, 1100 nến ngày (mức của 7 ngày / 12 tháng cộng ATR 14; đồ thị 21 nến ngày gộp, 36 nến tháng gộp) -----
  async function loadLive() {
    const [kh, kd] = await Promise.all([getJSON(`${FAPI}klines?symbol=BTCUSDT&interval=1h&limit=520`), getJSON(`${FAPI}klines?symbol=BTCUSDT&interval=1d&limit=1100`)]);
    const now = Date.now();
    const closed = (k) => k.filter((r) => Number(r[6]) < now).map((r) => ({ o: Number(r[1]), h: Number(r[2]), l: Number(r[3]), c: Number(r[4]), t: Number(r[6]) + 1 }));
    const h = closed(kh), d = closed(kd);
    if (h.length < 200 || d.length < 30) throw new Error('klines');
    view.live = { '1h': h, '1d': d, price: Number(kh[kh.length - 1][4]), at: h[h.length - 1].t };
  }
  // = sr_levels.levels: kháng cự / hỗ trợ của W nến đã đóng cuối, ATR = trung bình biên thật 14 nến
  function levelsNow(r) {
    const L = view.live && view.live[r.candles];
    if (L && L.length >= Math.max(r.W, ATR_N + 1)) {
      const w = L.slice(-r.W);
      let s = 0;
      for (let i = L.length - ATR_N; i < L.length; i++) { const p = L[i - 1].c; s += Math.max(L[i].h - L[i].l, Math.abs(L[i].h - p), Math.abs(L[i].l - p)); }
      return { R: Math.max(...w.map((x) => x.h)), S: Math.min(...w.map((x) => x.l)), atr: s / ATR_N, price: view.live.price, live: true };
    }
    const nw = SR.now[r.candles], lv = nw.levels[`${r.unit}|${r.n}`] || {};
    return { ...lv, price: view.live ? view.live.price : nw.close, live: false };
  }
  function reachOf(r, dist) {
    if (!(dist >= 0)) return null;
    return r.reach.find((b) => dist >= b.from && (b.to == null || dist < b.to)) || null;
  }

  // ----- đồ thị nến của khung (mục sr_view; hàm vẽ dùng chung PA_CHART của src/pact.js) -----
  // Mỗi nến vẽ = 1 đơn vị của khung (giờ: 1 nến giờ; ngày: 24 nến giờ; tuần: 7 nến ngày; tháng: 30 nến ngày), gộp từ nến
  // đã đóng gần nhất lùi về trước, nên n nến gộp cuối đúng là W nến của khung n: đỉnh / đáy của chúng là R / S.
  const two = (x) => String(x).padStart(2, '0');
  const PER = { gio: 1, ngay: 24, tuan: 7, thang: 30 }, MIN_BARS = { gio: 24, ngay: 10, tuan: 12, thang: 12 };
  function baseCandles(r) {   // nến gốc đã đóng, t = giờ mở nến (ms UTC)
    const hourly = r.candles === '1h', L = view.live && view.live[r.candles];
    return L ? L.map((k) => ({ t: k.t - (hourly ? 3600000 : 86400000), o: k.o, h: k.h, l: k.l, c: k.c }))
      : (SR.now[r.candles].candles || []).map(([x, o, h, l, c]) => ({ t: Date.parse(utcIso(x)) - (hourly ? 3600000 : 0), o, h, l, c }));
  }
  function group(base, per) {
    const out = [];
    for (let end = base.length; end - per >= 0; end -= per) {
      const g = base.slice(end - per, end), hs = g.map((k) => k.h).filter(ok), ls = g.map((k) => k.l).filter(ok);
      const o = g.find((k) => ok(k.o)), c = [...g].reverse().find((k) => ok(k.c));
      out.unshift({ t: g[0].t, t1: g[g.length - 1].t, o: o ? o.o : null, h: hs.length ? Math.max(...hs) : null, l: ls.length ? Math.min(...ls) : null, c: c ? c.c : null });
    }
    return out;
  }
  function candlesOf(r) {
    const hourly = r.candles === '1h', per = PER[r.unit], step = hourly ? 3600000 : 86400000;
    const all = group(baseCandles(r), per), cand = all.slice(-Math.max(MIN_BARS[r.unit], 3 * r.n));
    const vn = (t) => new Date(t + (hourly ? 7 * 3600000 : 0));   // nến giờ theo giờ Việt Nam, nến ngày theo ngày UTC
    const day = (v) => `${two(v.getUTCDate())}/${two(v.getUTCMonth() + 1)}/${v.getUTCFullYear()}`;
    const at = (v) => (hourly ? `${two(v.getUTCHours())}:00 ` : '') + day(v);
    return cand.map((k) => {
      const v = vn(k.t), e = vn(k.t1 + step), dd = two(v.getUTCDate()), mm = two(v.getUTCMonth() + 1);
      return { ...k, d: r.unit === 'gio' ? `${dd}/${mm} ${two(v.getUTCHours())}h` : r.unit === 'thang' ? `${mm}/${String(v.getUTCFullYear()).slice(2)}` : `${dd}/${mm}`,
        full: per === 1 ? at(v) : `${at(v)} → ${at(e)}` };
    });
  }
  function chart(r, lv) {
    const box = $('sr-chart');
    if (!window.PA_CHART) return;
    const cand = candlesOf(r), a = lv.atr, w = SR.params.zone_atr * a, b = SR.params.bounce_atr * a, inWin = Math.min(r.n, cand.length);
    $('sr-chart-title').textContent = tx(view.live ? 'web.pa.ch_title' : 'web.pa.ch_title_old', nf(0).format(cand.length), tx('web.pa.ch_c_' + r.unit), frameName(r.unit, r.n), nf(0).format(inWin));
    window.PA_CHART(box, cand, {
      height: 320, label: frameName(r.unit, r.n), span: { from: cand.length - inWin, label: frameName(r.unit, r.n) },
      zones: [{ lo: lv.R - w, hi: lv.R + w, cls: 'r' }, { lo: lv.S - w, hi: lv.S + w, cls: 's' }],
      lines: [{ y: lv.R, cls: 'r', label: tx('web.pa.ch_r') }, { y: lv.S, cls: 's', label: tx('web.pa.ch_s') }, { y: lv.price, cls: 'p', label: tx('web.pa.ch_now') },
        { y: lv.R - b, cls: 't' }, { y: lv.S + b, cls: 't' }],
      tip: (k) => tx('web.pact.ch_tip', k.full, usd(k.o), usd(k.h), usd(k.l), usd(k.c)),
    });
  }

  // ----- thẻ kháng cự / hỗ trợ -----
  function card(side, r, lv) {
    const R = side === 'R', L = R ? lv.R : lv.S, a = lv.atr, w = SR.params.zone_atr * a;
    const dist = R ? (L - lv.price) / a : (lv.price - L) / a, pct = L / lv.price - 1;
    const c = el('div', 'pa-card ' + (R ? 'r' : 's')), hd = el('div', 'hd');
    hd.append(el('b', null, tx(R ? 'web.pa.r_title' : 'web.pa.s_title', frameName(r.unit, r.n))), el('span', null, tx('web.pa.dist', spc(pct), sp(dist, 1))));
    c.append(hd, el('div', 'px', usd(L)), el('div', 'def', tx('web.pa.zone_line', usd(w))));
    if (dist < SR.params.zone_atr) c.append(el('div', 'inz', tx(R ? 'web.pa.inside_r' : 'web.pa.inside_s')));
    else {
      const b = reachOf(r, dist), rc = el('div', 'reach');
      rc.append(el('span', null, tx('web.pa.reach', horizon(r))), el('b', null, b ? pc(b.p, 0) : '—'));
      c.append(rc);
      if (b) c.append(el('div', 'def', b.to == null ? tx('web.pa.reach_sub_far', nf(0).format(b.n), nf(0).format(b.from), pc(b.ci[0], 0), pc(b.ci[1], 0))
        : tx('web.pa.reach_sub', nf(0).format(b.n), sp(b.from, 1), sp(b.to, 1), pc(b.ci[0], 0), pc(b.ci[1], 0))));
    }
    c.append(el('div', 'kick', tx('web.pa.react')));
    const re = r.real, fk = r.fake;
    if (!re.n) { c.append(el('div', 'def', tx('web.pa.no_touch'))); return c; }
    const bx = el('div', 'rx'), bo = el('i', 'bo', `${tx(R ? 'web.pa.r_bounce' : 'web.pa.s_bounce')} ${pc(re.p, 0)}`), bk = el('i', 'bk', `${tx(R ? 'web.pa.r_break' : 'web.pa.s_break')} ${pc(1 - re.p, 0)}`);
    bo.style.width = (100 * re.p) + '%'; bk.style.width = (100 * (1 - re.p)) + '%'; bx.append(bo, bk);
    c.append(bx);
    const vs = el('div', 'vs'), mk = el('div', 'mk');
    if (ok(re.ci[0])) { const s = el('s'); s.style.left = (100 * re.ci[0]) + '%'; s.style.width = (100 * (re.ci[1] - re.ci[0])) + '%'; mk.append(s); }
    const iR = el('i', 'real'); iR.style.left = (100 * re.p) + '%'; iR.title = tx('web.pa.real_mark'); mk.append(iR);
    if (ok(fk.p)) { const iF = el('i', 'fake'); iF.style.left = (100 * fk.p) + '%'; iF.title = tx('web.pa.fake_mark'); mk.append(iF); }
    vs.append(document.createTextNode(tx('web.pa.fake_line', tx(R ? 'web.pa.r_bounce' : 'web.pa.s_bounce').toLowerCase(), pc(fk.p, 0))), mk);
    c.append(vs);
    const badge = el('span', 'badge ' + r.verdict, tx('web.pa.v_' + r.verdict));
    if (ok(r.p_holm)) badge.title = tx('web.pa.v_sub', nf(3).format(r.p_holm), pc(r.halves[0].diff, 0), pc(r.halves[1].diff, 0));
    c.append(badge, el('div', 'def', tx('web.pa.n_line', nf(0).format(re.episodes), nf(0).format(re.n), nf(0).format(re.open), horizon(r), pc(re.ci[0], 0), pc(re.ci[1], 0))),
      el('div', 'def', tx(R ? 'web.pa.def_r' : 'web.pa.def_s', usd(SR.params.bounce_atr * a), usd(R ? L + SR.params.break_atr * a : L - SR.params.break_atr * a))));
    return c;
  }

  function renderPick() {
    document.querySelectorAll('#sr-unit button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.u === view.unit)));
    const ns = nsOf(view.unit);
    if (!ns.includes(view.n)) view.n = ns[0];
    $('sr-ns').replaceChildren(...ns.map((n) => {
      const b = el('button', null, String(n)); b.type = 'button'; b.title = frameName(view.unit, n);
      b.setAttribute('aria-pressed', String(n === view.n));
      b.addEventListener('click', () => { view.n = n; render(); });
      return b;
    }));
  }
  function renderHead() {
    const s = SR.summary, base = view.live;
    $('sr-price').textContent = usd(base ? base.price : SR.now['1h'].close);
    $('sr-price-sub').textContent = base ? tx('web.pa.now_sub', vnTime(new Date(base.at).toISOString())) : tx('web.pa.now_sub_old', vnTime(utcIso(SR.now['1h'].anchor)));
    const h = $('sr-honest');
    h.replaceChildren(el('p', null, tx('web.pa.honest', nf(0).format(SR.tests), nf(0).format(s.manh_hon), nf(0).format(s.yeu_hon), nf(0).format(s.nhu_bat_ky), nf(0).format(s.it_du_lieu))),
      el('p', 'muted', tx('web.pa.honest_why')));
    $('sr-status').textContent = view.err ? tx('web.pa.status_fail', view.err, vnTime(utcIso(SR.now['1h'].anchor)))
      : base ? tx('web.pa.status_live', vnTime(new Date(base.at).toISOString())) : tx('web.pa.status_first', vnTime(utcIso(SR.now['1h'].anchor)));
  }
  function renderMain() {
    const rR = row(view.unit, view.n, 'R'), rS = row(view.unit, view.n, 'S');
    if (!rR || !rS) return;
    const lv = levelsNow(rR);
    if (!ok(lv.R) || !ok(lv.S) || !ok(lv.atr)) { $('sr-cards').replaceChildren(el('p', 'muted', tx('web.pa.none'))); return; }
    $('sr-cards').replaceChildren(card('R', rR, lv), card('S', rS, lv));
    chart(rR, lv);
  }
  function renderTable() {
    $('sr-all-title').textContent = tx('web.pa.all_title', tx('web.pa.unit_word_' + view.unit));
    $('sr-all-lead').textContent = tx('web.pa.all_lead');
    const head = el('tr');
    for (const t of [tx('web.pa.th_frame'), tx('web.pa.th_r'), tx('web.pa.th_rd'), tx('web.pa.th_rb'), tx('web.pa.th_s'), tx('web.pa.th_sd'), tx('web.pa.th_sb'), tx('web.pa.th_v')]) head.append(el('th', null, t));
    const thead = el('thead'), tbody = el('tbody'); thead.append(head);
    const first = { R: null, S: null }, prev = { R: null, S: null };   // mục sr_view: mức bằng đúng khung trước → ghi khung đầu tiên có mức đó
    const lvCell = (side, n, x) => {
      if (!(ok(x) && x === prev[side])) first[side] = n;
      prev[side] = x;
      const td = el('td', 'r', usd(x));
      if (first[side] !== n) td.append(el('span', 'same', tx('web.pa.same_as', frameName(view.unit, first[side]))));
      return td;
    };
    for (const n of nsOf(view.unit)) {
      const rR = row(view.unit, n, 'R'), rS = row(view.unit, n, 'S'), lv = levelsNow(rR), tr = el('tr', n === view.n ? 'here' : null);
      const vcell = el('td');
      for (const [x, nm] of [[rR, tx('web.pa.th_r')], [rS, tx('web.pa.th_s')]]) { const v = el('span', 'v ' + x.verdict, `${nm}: ${tx('web.pa.v_' + x.verdict)}`); vcell.append(v, document.createElement('br')); }
      vcell.lastChild.remove();
      const both = (x) => `${pc(x.real.p, 0)} / ${pc(x.fake.p, 0)}`;
      tr.append(el('td', null, frameName(view.unit, n)), lvCell('R', n, lv.R), el('td', 'r', spc(lv.R / lv.price - 1)), el('td', 'r', both(rR)),
        lvCell('S', n, lv.S), el('td', 'r', spc(lv.S / lv.price - 1)), el('td', 'r', both(rS)), vcell);
      tr.addEventListener('click', () => { view.n = n; render(); $('sr-sec').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
      tbody.append(tr);
    }
    $('t-sr').replaceChildren(thead, tbody);
    $('sr-notes').replaceChildren(...[tx('web.pa.note_same'), tx('web.pa.note_bars'), tx('web.pa.note_data'), tx('web.pa.note_fake'), tx('web.pa.note_long')].map((t) => el('li', null, t)));
  }
  function renderMethod() {
    const r0 = row(view.unit, view.n, 'R');
    const items = [tx('web.pa.m1'), tx('web.pa.m2', r0 ? horizon(r0) : '—'), tx('web.pa.m3'), tx('web.pa.m4', nf(0).format(SR.tests)), tx('web.pa.m5'),
      tx('web.pa.updated', vnTime(utcIso(SR.to['1h'])), SR.to['1d'].slice(8, 10) + '/' + SR.to['1d'].slice(5, 7) + '/' + SR.to['1d'].slice(0, 4), SR.version)];
    $('sr-method-list').replaceChildren(...items.map((t) => el('li', null, t)));
  }
  function render() {
    if (!SR) { $('sr-none').hidden = false; ['sr-sec', 'sr-all-sec'].forEach((id) => { $(id).hidden = true; }); return; }
    if (!document.body.classList.contains('pa-view')) return;
    renderPick(); renderHead(); renderMain(); renderTable(); renderMethod();
  }
  async function refresh() {
    if (!SR || view.busy) return;
    view.busy = true;
    try { await loadLive(); view.err = null; } catch (e) { view.err = e.message || String(e); }
    view.busy = false;
    render();
  }

  // ----- chuyển chế độ: chỉ thêm / bỏ lớp body.pa-view (và bỏ ls-view, tr-view), không gọi gì của các phần khác -----
  function setView(on) {
    document.body.classList.toggle('pa-view', on);
    $('mode-pa').setAttribute('aria-pressed', String(on));
    if (!on) return;
    document.body.classList.remove('ls-view', 'tr-view');
    for (const id of VIEWS) $(id).setAttribute('aria-pressed', 'false');
    try { localStorage.setItem(KEY, 'pa'); } catch (e) { /* bỏ qua */ }
    render();
    refresh();
    if (!view.timer) view.timer = setInterval(() => { if (document.body.classList.contains('pa-view') && !document.hidden) refresh(); }, 60000);
  }
  $('mode-pa').addEventListener('click', () => setView(true));
  for (const id of VIEWS) $(id).addEventListener('click', () => setView(false));
  document.querySelectorAll('#sr-unit button').forEach((b) => b.addEventListener('click', () => { view.unit = b.dataset.u; render(); }));
  if (window.ResizeObserver) {
    let w = 0;
    new ResizeObserver(() => { const x = $('sr-chart').clientWidth; if (x && x !== w) { w = x; if (SR && document.body.classList.contains('pa-view')) renderMain(); } }).observe($('sr-chart'));
  }
  let start = false;
  try { start = localStorage.getItem(KEY) === 'pa'; } catch (e) { /* bỏ qua */ }
  if (start) setView(true);
})();
// ===== PRICE ACTION VIEW END =====
