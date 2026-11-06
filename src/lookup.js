// ===== LOOKUP VIEW START =====
// Chế độ Tra cứu (nút #mode-lk, khu #lk-app, lớp body.lk-view): mục lookup và analog của config/candidates.yaml (đăng ký 06/11/2026).
// build.py nhúng LK = data/results/lookup.json (python -m bot.cli lookup): giá đóng ngày Coin Metrics, cao / thấp Bitstamp và kết quả
// nghiên cứu Tình huống tương tự. Mọi con số tại ngày t tính trong trình duyệt chỉ từ giá đến hết ngày t, bằng LOOKUP_CORE dưới đây;
// LOOKUP_CORE phải cho cùng kết quả với bot/models/lookup.py (tests/test_lookup.py). Tách riêng như pa.js: chỉ bật lớp body.lk-view.
const LOOKUP_CORE = (() => {
  const DAY = 86400000;
  const fin = (x) => x != null && Number.isFinite(x);
  const rnd = (x) => Math.floor(x + 0.5);   // làm tròn nửa lên, như lookup.rnd
  const FEATS = ['r7', 'r30', 'ma200', 'dd', 'vol'];
  const NB = { r7: 5, r30: 5, ma200: 2, dd: 3, vol: 3 };
  function wilson(k, n, z = 1.96) {
    if (!n) return [null, null];
    const p = k / n, d = 1 + z * z / n, c = p + z * z / (2 * n), m = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n));
    return [Math.max(0, (c - m) / d), Math.min(1, (c + m) / d)];
  }
  function quantile(s, q) {   // s đã sắp xếp; nội suy tuyến tính như numpy.quantile
    const pos = q * (s.length - 1), lo = Math.floor(pos), hi = Math.min(lo + 1, s.length - 1);
    return s[lo] + (s[hi] - s[lo]) * (pos - lo);
  }
  const sorted = (a) => Float64Array.from(a).sort();
  function rollStd(x, n) {
    const out = new Float64Array(x.length).fill(NaN);
    for (let t = n - 1; t < x.length; t++) {
      let s = 0, ok = true;
      for (let i = t - n + 1; i <= t; i++) { if (!fin(x[i])) { ok = false; break; } s += x[i]; }
      if (!ok) continue;
      const m = s / n;
      let v = 0;
      for (let i = t - n + 1; i <= t; i++) { const d = x[i] - m; v += d * d; }
      out[t] = Math.sqrt(v / (n - 1));
    }
    return out;
  }
  const iso = (ms) => new Date(ms).toISOString().slice(0, 10);

  // ----- chuẩn bị một lần: chuỗi giá, độ dao động, nhóm của 5 đặc trưng mọi ngày (chỉ dùng giá đến ngày đó) -----
  function prepare(L) {
    const C = L.cfg, n = L.close.length, num = (a) => Float64Array.from(a, (v) => (v == null ? NaN : v));
    const p = num(L.close), hi = num(L.high), lo = num(L.low);
    const lr = new Float64Array(n).fill(NaN);
    for (let t = 1; t < n; t++) lr[t] = Math.log(p[t] / p[t - 1]);
    const s30 = rollStd(lr, C.vol_days);
    let mix = s30;
    if (C.vol_long_days) { const sl = rollStd(lr, C.vol_long_days); mix = s30.map((v, i) => Math.sqrt((v * v + sl[i] * sl[i]) / 2)); }
    const r7 = new Float64Array(n).fill(NaN), r30 = new Float64Array(n).fill(NaN), ma = new Float64Array(n).fill(NaN), dd = new Float64Array(n).fill(NaN), rank = new Float64Array(n).fill(NaN);
    let ath = -Infinity;
    for (let t = 0; t < n; t++) {
      if (t >= 7) r7[t] = p[t] / p[t - 7] - 1;
      if (t >= 30) r30[t] = p[t] / p[t - 30] - 1;
      if (t >= 199) { let s = 0, ok = true; for (let i = t - 199; i <= t; i++) { if (!fin(p[i])) { ok = false; break; } s += p[i]; } if (ok) ma[t] = s / 200; }
      if (fin(p[t])) { ath = Math.max(ath, p[t]); dd[t] = 1 - p[t] / ath; }
      if (fin(s30[t])) {
        let c = 0, le = 0;
        for (let i = Math.max(0, t - C.rank_days + 1); i <= t; i++) if (fin(s30[i])) { c++; if (s30[i] <= s30[t]) le++; }
        if (c >= C.rank_min) rank[t] = le / c;
      }
    }
    const cut5 = (x, c) => Int8Array.from(x, (v) => (!fin(v) ? -1 : v <= c[0] ? 0 : v <= c[1] ? 1 : v < c[2] ? 2 : v < c[3] ? 3 : 4));
    const g = {
      r7: cut5(r7, C.cuts.r7), r30: cut5(r30, C.cuts.r30),
      ma200: Int8Array.from(ma, (m, i) => (!fin(m) || !fin(p[i]) ? -1 : p[i] > m ? 0 : 1)),
      dd: Int8Array.from(dd, (v) => (!fin(v) ? -1 : v < C.cuts.dd[0] ? 0 : v < C.cuts.dd[1] ? 1 : 2)),
      vol: Int8Array.from(rank, (v) => (!fin(v) ? -1 : v <= 1 / 3 ? 0 : v <= 2 / 3 ? 1 : 2)),
    };
    let last = n - 1;
    while (last > 0 && !fin(p[last])) last--;
    return { n, last, start: Date.parse(L.start + 'T00:00:00Z'), C, p, hi, lo, s30, mix, r7, r30, ma, dd, rank, g };
  }
  const dayOf = (P, i) => iso(P.start + i * DAY);
  const indexOf = (P, s) => Math.round((Date.parse(s + 'T00:00:00Z') - P.start) / DAY);

  // ----- từng phần tại t (= lookup.py) -----
  function stateAt(P, t) {
    const v = (a) => (fin(a[t]) ? a[t] : null);
    return { date: dayOf(P, t), close: v(P.p), dd: v(P.dd), ma200: v(P.ma), vs_ma: fin(P.ma[t]) ? P.p[t] / P.ma[t] - 1 : null, r7: v(P.r7), r30: v(P.r30),
      vol: fin(P.s30[t]) ? P.s30[t] * Math.sqrt(365) : null, vol_rank: v(P.rank), groups: Object.fromEntries(FEATS.map((f) => [f, P.g[f][t]])) };
  }
  function bandAt(P, t, h) {
    const { p, mix, C } = P, M = Math.max(C.window_days - h, C.min_obs), hiI = t - h;
    if (hiI < 0 || !fin(p[t]) || !fin(mix[t])) return null;
    const z = [], sq = Math.sqrt(h);
    for (let i = Math.max(0, hiI - M + 1); i <= hiI; i++) { const v = Math.log(p[i + h] / p[i]) / (mix[i] * sq); if (fin(v)) z.push(v); }
    if (z.length < C.min_obs) return null;
    const s = sorted(z), sc = mix[t] * sq, out = { n: z.length };
    for (const q of C.quantiles) out['q' + rnd(q * 100)] = p[t] * Math.exp(quantile(s, q) * sc);
    return out;
  }
  function holdAt(P, t, h) {
    const { p, C } = P, c = C.costs, hiI = t - h;
    if (hiI < 0) return null;
    const g = [];
    for (let i = Math.max(0, hiI - C.hold_days + 1); i <= hiI; i++) { const v = p[i + h] * (1 - c) / (p[i] * (1 + c)) - 1; if (fin(v)) g.push(v); }
    const n = g.length;
    if (n < C.min_hold) return null;
    const win = g.filter((v) => v > 0).length / n, eff = Math.max(1, rnd(n / h)), s = sorted(g);
    return { n, n_eff: eff, p: win, ci: wilson(rnd(win * eff), eff), median: quantile(s, 0.5), p10: quantile(s, 0.1), p90: quantile(s, 0.9) };
  }
  function levelsAt(P, t) {
    return P.C.level_days.map((W, k) => {
      let R = -Infinity, S = Infinity, ok = t - W + 1 >= 0;
      for (let i = Math.max(0, t - W + 1); ok && i <= t; i++) { if (!fin(P.hi[i]) || !fin(P.lo[i])) { ok = false; break; } R = Math.max(R, P.hi[i]); S = Math.min(S, P.lo[i]); }
      return { frame: P.C.level_frames[k], days: W, R: ok ? R : null, S: ok ? S : null };
    });
  }
  function outcomeAt(P, t, h, band) {
    const { p, C } = P;
    if (t + h >= P.n || !fin(p[t]) || !fin(p[t + h])) return null;
    const a = p[t + h];
    let H = -Infinity, L = Infinity;
    for (let i = t + 1; i <= t + h; i++) { if (fin(P.hi[i])) H = Math.max(H, P.hi[i]); if (fin(P.lo[i])) L = Math.min(L, P.lo[i]); }
    return { date: dayOf(P, t + h), close: a, ret: a / p[t] - 1, gain: a * (1 - C.costs) / (p[t] * (1 + C.costs)) - 1,
      in80: band ? band.q10 <= a && a <= band.q90 : null, in50: band ? band.q25 <= a && a <= band.q75 : null,
      high: H > -Infinity ? H : null, low: L < Infinity ? L : null };
  }
  function desc(ids, P, h) {
    const n = ids.length;
    if (!n) return { n: 0, n_eff: 0, p: null, ci: [null, null], median: null };
    let up = 0;
    const r = new Float64Array(n);
    ids.forEach((i, k) => { if (P.p[i + h] > P.p[i]) up++; r[k] = Math.log(P.p[i + h] / P.p[i]); });
    const pp = up / n, eff = Math.max(1, rnd(n / h));
    return { n, n_eff: eff, p: pp, ci: wilson(rnd(pp * eff), eff), median: quantile(r.sort(), 0.5) };
  }
  function analogAt(P, t, h) {
    const start = Math.max(0, indexOf(P, P.C.period_from)), valid = [];
    for (let i = start; i <= t - h && i + h < P.n; i++) if (fin(P.p[i]) && fin(P.p[i + h])) valid.push(i);
    const out = { all: desc(valid, P, h), features: {} };
    let same = valid;
    for (const f of FEATS) {
      const g = P.g[f][t];
      if (g < 0) { out.features[f] = null; same = []; continue; }
      out.features[f] = { group: g, ...desc(valid.filter((i) => P.g[f][i] === g), P, h) };
      same = same.filter((i) => P.g[f][i] === g);
    }
    out.combo = desc(same, P, h);
    return out;
  }
  function lookup(P, t, h) {
    const band = bandAt(P, t, h);
    return { t: dayOf(P, t), h, target: dayOf(P, t + h), state: stateAt(P, t), band, hold: holdAt(P, t, h), levels: levelsAt(P, t), analog: analogAt(P, t, h),
      outcome: outcomeAt(P, t, h, band) };
  }
  // ----- kiểm chứng quá khứ cho đúng h: ngày gốc từ check_from, cách nhau h ngày (= lookup.check) -----
  function check(P, h) {
    const { p, C } = P, t0 = Math.max(0, indexOf(P, C.check_from)), rows = [], years = {};
    for (let t = t0; t < P.n - h; t += h) {
      if (!fin(p[t]) || !fin(p[t + h])) continue;
      const b = bandAt(P, t, h), ho = holdAt(P, t, h), a = p[t + h];
      const r = { t, in80: b ? b.q10 <= a && a <= b.q90 : null, in50: b ? b.q25 <= a && a <= b.q75 : null, said: ho ? ho.p : null,
        win: a * (1 - C.costs) / (p[t] * (1 + C.costs)) - 1 > 0 };
      rows.push(r);
      (years[dayOf(P, t).slice(0, 4)] = years[dayOf(P, t).slice(0, 4)] || []).push(r);
    }
    const cover = (rs, key) => { const x = rs.filter((r) => r[key] != null), k = x.filter((r) => r[key]).length; return { n: x.length, k, p: x.length ? k / x.length : null, ci: wilson(k, x.length) }; };
    const said = rows.filter((r) => r.said != null), mean = (a) => (a.length ? a.reduce((s, v) => s + v, 0) / a.length : null);
    const groups = [[0, 0.5], [0.5, 0.7], [0.7, 0.9], [0.9, 1.01]].map(([a, b]) => {
      const g = said.filter((r) => r.said >= a && r.said < b), k = g.filter((r) => r.win).length;
      return { from: a, to: Math.min(b, 1), n: g.length, said: mean(g.map((r) => r.said)), k, p: g.length ? k / g.length : null, ci: wilson(k, g.length) };
    });
    const k = said.filter((r) => r.win).length;
    const hold = { n: said.length, said: mean(said.map((r) => r.said)), k, p: said.length ? k / said.length : null, ci: wilson(k, said.length),
      brier: mean(said.map((r) => (r.said - (r.win ? 1 : 0)) ** 2)), brier50: mean(said.map((r) => (0.5 - (r.win ? 1 : 0)) ** 2)), groups };
    return { h, from: rows.length ? dayOf(P, rows[0].t) : null, to: rows.length ? dayOf(P, rows[rows.length - 1].t) : null, anchors: rows.length,
      in80: cover(rows, 'in80'), in50: cover(rows, 'in50'), years: Object.keys(years).sort().map((y) => ({ year: y, in80: cover(years[y], 'in80'), in50: cover(years[y], 'in50') })), hold };
  }
  return { FEATS, NB, prepare, dayOf, indexOf, stateAt, bandAt, holdAt, levelsAt, outcomeAt, analogAt, lookup, check, wilson };
})();
if (typeof module !== 'undefined') module.exports = LOOKUP_CORE;

(() => {
  if (typeof document === 'undefined' || !document.getElementById('lk-app')) return;
  const LK = /*LK_JSON*/null;
  const K = LOOKUP_CORE;
  const { tx } = I18N;
  const $ = (id) => document.getElementById(id);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  const nf = (d) => new Intl.NumberFormat('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d });
  const ok = (x) => x != null && isFinite(x);
  const pc = (x, d = 0) => (ok(x) ? nf(d).format(x * 100) + '%' : '—');
  const spc = (x, d = 1) => { if (!ok(x)) return '—'; const r = Math.round(x * 100 * 10 ** d) / 10 ** d; return (r > 0 ? '+' : r < 0 ? '−' : '') + nf(d).format(Math.abs(r)) + '%'; };
  const usd = (x) => (ok(x) ? nf(x < 10 ? 2 : 0).format(x) + ' $' : '—');
  const dmy = (s) => (s ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : '—');
  const n3 = (x) => (ok(x) ? nf(3).format(x) : '—');
  const VIEWS = ['mode-buy', 'mode-sell', 'mode-ls', 'mode-tr', 'mode-pa'];
  const KEY = 'btc-bot3-view';
  const view = { P: null, t: null, h: 30, hn: 1, hu: 30, ck: null, ckKey: null, timer: null };

  function hName(h) {   // tên kỳ hạn: theo đơn vị người dùng chọn
    if (h % 365 === 0) return tx('web.lk.h_years', h / 365);
    if (h % 30 === 0) return tx('web.lk.h_months', h / 30);
    return tx('web.lk.h_days', h);
  }
  function msg(t) { $('lk-msg').textContent = t || ''; $('lk-msg').hidden = !t; }
  function readInputs() {
    const P = view.P, d = $('lk-t').value, hn = Math.floor(Number($('lk-hn').value)), hu = Number($('lk-hu').value);
    const t = d ? K.indexOf(P, d) : P.last, h = hn * hu, t0 = K.indexOf(P, LK.cfg.t_from);
    if (!(t >= t0 && t <= P.last)) { msg(tx('web.lk.msg_range', dmy(LK.cfg.t_from), dmy(LK.last))); return false; }
    if (!(hn >= 1 && h >= 1 && h <= LK.cfg.max_h)) { msg(tx('web.lk.msg_h')); return false; }
    view.t = t; view.h = h; view.hn = hn; view.hu = hu;
    msg('');
    return true;
  }

  // ----- tình trạng giá tại t -----
  function kpi(lab, val, sub) { const k = el('div', 'kpi'); k.append(el('span', 'lab', lab), el('span', 'val num', val)); if (sub) k.append(el('span', 'sub', sub)); return k; }
  function renderState(x) {
    const s = x.state;
    $('lk-price').textContent = usd(s.close);
    $('lk-price-sub').textContent = tx('web.lk.price_sub', dmy(s.date));
    $('lk-state').replaceChildren(
      kpi(tx('web.lk.st_dd'), ok(s.dd) ? (s.dd < 0.0005 ? tx('web.lk.st_ath') : '−' + pc(s.dd, 1)) : '—', tx('web.lk.st_dd_sub', usd(s.close / (1 - s.dd)))),
      kpi(tx('web.lk.st_ma'), spc(s.vs_ma), tx('web.lk.st_ma_sub', usd(s.ma200))),
      kpi(tx('web.lk.st_r7'), spc(s.r7), tx('web.lk.g_r7_' + s.groups.r7)),
      kpi(tx('web.lk.st_r30'), spc(s.r30), tx('web.lk.g_r30_' + s.groups.r30)),
      kpi(tx('web.lk.st_vol'), pc(s.vol, 0), ok(s.vol_rank) ? tx('web.lk.st_vol_sub', pc(s.vol_rank, 0)) : ''));
  }

  // ----- đồ thị: giá đóng quanh t, dải ngày t + h, giá thật sau đó -----
  const NS = 'http://www.w3.org/2000/svg';
  const sv = (t, at) => { const e = document.createElementNS(NS, t); for (const k in at) e.setAttribute(k, at[k]); return e; };
  function drawChart(x) {
    const box = $('lk-chart'), W = box.clientWidth;
    if (!W) return;
    const P = view.P, t = view.t, h = view.h, b = x.band, back = Math.max(60, Math.min(2 * h, 730)), a0 = Math.max(0, t - back), end = t + h, a1 = Math.min(end, P.last);
    const H = 300, m = { l: 8, r: 112, t: 14, b: 26 };
    const vals = [];
    for (let i = a0; i <= a1; i++) if (ok(P.p[i])) vals.push(P.p[i]);
    if (b) vals.push(b.q10, b.q90);
    let lo = Math.min(...vals), hi = Math.max(...vals);
    const pad = (hi - lo) * 0.05 || hi * 0.02; lo -= pad; hi += pad;
    const X = (i) => m.l + (i - a0) / Math.max(1, end - a0) * (W - m.l - m.r), Y = (v) => m.t + (hi - v) / (hi - lo) * (H - m.t - m.b);
    const svg = sv('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, class: 'pa-svg lk-svg', role: 'img', 'aria-label': tx('web.lk.ch_label') });
    const raw = (hi - lo) / 5, mag = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 2.5, 5, 10].map((v) => v * mag).find((v) => v >= raw);
    for (let v = Math.ceil(lo / step) * step; v < hi; v += step) {
      svg.append(sv('line', { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: 'grid' }));
      const tt = sv('text', { x: m.l + 4, y: Y(v) - 3, class: 'ax' }); tt.textContent = nf(v < 10 ? 2 : 0).format(v); svg.append(tt);
    }
    if (b) {
      const pt = P.p[t];
      svg.append(sv('polygon', { points: `${X(t)},${Y(pt)} ${X(end)},${Y(b.q90)} ${X(end)},${Y(b.q10)}`, class: 'cone80' }));
      svg.append(sv('polygon', { points: `${X(t)},${Y(pt)} ${X(end)},${Y(b.q75)} ${X(end)},${Y(b.q25)}`, class: 'cone50' }));
    }
    const path = (i0, i1, cls) => {
      let d = '';
      for (let i = i0; i <= i1; i++) if (ok(P.p[i])) d += (d ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(P.p[i]).toFixed(1);
      if (d) svg.append(sv('path', { d, class: cls }));
    };
    path(a0, t, 'ln');
    if (a1 > t) path(t, a1, 'ln after');
    svg.append(sv('line', { x1: X(t), x2: X(t), y1: m.t, y2: H - m.b, class: 'tline' }));
    const labs = [];
    if (b) labs.push({ y: b.q90, cls: 'r', t: tx('web.lk.ch_q90') }, { y: b.q50, cls: 'p', t: tx('web.lk.ch_q50') }, { y: b.q10, cls: 's', t: tx('web.lk.ch_q10') });
    if (x.outcome) labs.push({ y: x.outcome.close, cls: 'e', t: tx('web.lk.ch_real') });
    labs.forEach((l) => { l.yy = Y(l.y); });
    labs.sort((u, v) => u.yy - v.yy).forEach((l, i, arr) => { l.ly = i ? Math.max(l.yy, arr[i - 1].ly + 18) : Math.max(l.yy, m.t + 8); });
    for (const l of labs) {
      const g = sv('g', { class: 'pt ' + l.cls });
      g.append(sv('rect', { x: W - m.r + 4, y: l.ly - 8, width: m.r - 6, height: 16, rx: 6 }));
      const tt = sv('text', { x: W - m.r + 9, y: l.ly + 4 }); tt.textContent = `${l.t} ${nf(l.y < 10 ? 2 : 0).format(l.y)}`; g.append(tt);
      svg.append(g);
    }
    const ticks = [[a0, dmy(K.dayOf(P, a0))], [t, tx('web.lk.ch_t', dmy(K.dayOf(P, t)))], [end, dmy(K.dayOf(P, end))]]
      .filter(([i], k, arr) => k !== 1 && Math.abs(X(i) - X(arr[1][0])) < 120 ? false : true);   // nhãn sát nhãn ngày t thì bỏ (ngày đích đã ở tiêu đề)
    for (const [i, s] of ticks) {
      const tt = sv('text', { x: Math.min(W - m.r - 4, Math.max(m.l + 30, X(i))), y: H - 8, 'text-anchor': i === a0 ? 'start' : i === end ? 'end' : 'middle', class: 'ax' });
      tt.textContent = s; svg.append(tt);
    }
    box.replaceChildren(svg);
  }

  // ----- dải giá ngày t + h -----
  function renderBand(x, ck) {
    const b = x.band, box = $('lk-band'), reg = [1, 2, 3, 4, 5, 6, 7, 30].includes(view.h);
    $('lk-band-title').textContent = tx('web.lk.band_title', dmy(x.target), hName(view.h));
    const out = [];
    if (!b) out.push(el('p', 'warn', tx('web.lk.band_none')));
    else {
      const p0 = x.state.close, rel = (v) => spc(v / p0 - 1);
      const t = el('div', 'lk-bandrow');
      t.append(kpi(tx('web.lk.band_80'), `${usd(b.q10)} – ${usd(b.q90)}`, `${rel(b.q10)} … ${rel(b.q90)}`),
        kpi(tx('web.lk.band_50'), `${usd(b.q25)} – ${usd(b.q75)}`, `${rel(b.q25)} … ${rel(b.q75)}`),
        kpi(tx('web.lk.band_mid'), usd(b.q50), rel(b.q50)));
      out.push(t, el('p', 'sm muted', tx('web.lk.band_n', nf(0).format(b.n))));
    }
    out.push(el('p', 'sm', tx(reg ? 'web.lk.band_reg' : 'web.lk.band_new')));
    if (ck && ck.in80.n) out.push(el('p', null, tx('web.lk.band_check', hName(view.h), nf(0).format(ck.anchors), dmy(ck.from), pc(ck.in80.p), pc(ck.in80.ci[0]), pc(ck.in80.ci[1]), pc(ck.in50.p))));
    else if (ck) out.push(el('p', 'muted', tx('web.lk.check_none')));
    const o = x.outcome, ob = el('div', 'lk-out');
    ob.append(el('b', null, tx('web.lk.out_title')));
    if (!o) ob.append(el('p', null, tx('web.lk.out_none', dmy(x.target))));
    else {
      ob.append(el('p', null, tx('web.lk.out_close', dmy(o.date), usd(o.close), spc(o.ret))));
      if (o.in80 != null) ob.append(el('p', o.in80 ? 'good' : 'bad', tx('web.lk.out_in', tx(o.in80 ? 'web.lk.co' : 'web.lk.khong'), tx(o.in50 ? 'web.lk.co' : 'web.lk.khong'))));
      ob.append(el('p', 'sm muted', tx('web.lk.out_range', usd(o.high), usd(o.low))));
    }
    out.push(ob);
    box.replaceChildren(...out);
  }

  // ----- mua tại t, giữ h -----
  function renderHold(x, ck) {
    const ho = x.hold, box = $('lk-hold'), out = [];
    $('lk-hold-title').textContent = tx('web.lk.hold_title', hName(view.h));
    if (!ho) out.push(el('p', 'warn', tx('web.lk.hold_none')));
    else {
      const row = el('div', 'lk-bandrow');
      row.append(kpi(tx('web.lk.hold_p'), pc(ho.p), tx('web.lk.hold_ci', pc(ho.ci[0]), pc(ho.ci[1]), nf(0).format(ho.n_eff))),
        kpi(tx('web.lk.hold_ret'), spc(ho.median), tx('web.lk.hold_ret_sub', spc(ho.p10), spc(ho.p90))));
      out.push(row, el('p', 'sm muted', tx('web.lk.hold_sub', nf(0).format(ho.n), dmy(K.dayOf(view.P, view.t - view.h)))));
    }
    if (ck && ck.hold.n) {
      const H = ck.hold;
      out.push(el('p', null, tx('web.lk.hold_check', nf(0).format(H.n), dmy(ck.from), pc(H.said), pc(H.p), pc(H.ci[0]), pc(H.ci[1]), n3(H.brier), n3(H.brier50))),
        el('p', H.brier < H.brier50 ? 'muted' : 'warn', tx(H.brier < H.brier50 ? 'web.lk.hold_skill_low' : 'web.lk.hold_skill_no')));
    }
    if (x.outcome) { const o = x.outcome; out.push(el('p', o.gain > 0 ? 'good' : 'bad', tx('web.lk.hold_out', dmy(o.date), spc(o.gain), tx(o.gain > 0 ? 'web.lk.w_gain' : 'web.lk.w_loss')))); }
    const adv = el('div', 'pa-honest');
    adv.append(el('p', null, tx('web.lk.advice', x.band ? usd(x.band.q10) : '—')));
    out.push(adv);
    box.replaceChildren(...out);
  }

  // ----- hỗ trợ / kháng cự tại t -----
  function renderLevels(x) {
    const t = $('t-lk-lv'), head = el('tr'), body = el('tbody'), thead = el('thead'), p0 = x.state.close, SRV = (LK.sr && LK.sr.frames) || {};
    for (const k of ['th_frame', 'th_r', 'th_rd', 'th_s', 'th_sd', 'th_v']) head.append(el('th', null, tx('web.lk.' + k)));
    thead.append(head);
    for (const L of x.levels) {
      const tr = el('tr'), v = SRV[L.frame] || {};
      const vt = ['R', 'S'].map((s) => (v[s] ? tx('web.pa.v_' + v[s].verdict) : '—'));
      tr.append(el('td', null, tx('web.lk.f_' + L.days)), el('td', 'r', usd(L.R)), el('td', 'r', ok(L.R) ? spc(L.R / p0 - 1) : '—'),
        el('td', 'r', usd(L.S)), el('td', 'r', ok(L.S) ? spc(L.S / p0 - 1) : '—'), el('td', null, vt[0] === vt[1] ? vt[0] : `${vt[0]} / ${vt[1]}`));
      body.append(tr);
    }
    t.replaceChildren(thead, body);
  }

  // ----- tình huống tương tự -----
  const VERD = { hon: 'v_hon', kem: 'v_kem', nhu_bat_ky: 'v_nhu', it_du_lieu: 'v_it' };
  function renderAnalog(x) {
    const A = x.analog, R = LK.research, hs = LK.cfg.horizons;
    $('lk-an-lead').textContent = tx('web.lk.an_lead', hName(view.h), nf(0).format(R.tests), dmy(R.from));
    const t = $('t-lk-an'), head = el('tr'), body = el('tbody'), thead = el('thead');
    for (const s of [tx('web.lk.th_feat'), tx('web.lk.th_group'), tx('web.lk.th_up', hName(view.h)), tx('web.lk.th_all'), tx('web.lk.th_tests', hs.join(' / '))]) head.append(el('th', null, s));
    thead.append(head);
    for (const f of K.FEATS) {
      const a = A.features[f], tr = el('tr');
      if (!a) { tr.append(el('td', null, tx('web.lk.f_' + f)), el('td', null, '—'), el('td', null, '—'), el('td', 'r', '—'), el('td', null, '—')); body.append(tr); continue; }
      const vs = hs.map((h) => { const r = R.rows.find((y) => y.feature === f && y.group === a.group && y.h === h); return r ? tx('web.lk.' + VERD[r.verdict]) : '—'; });
      const up = el('td', 'r');
      up.append(document.createTextNode(`${pc(a.p)} `), el('span', 'muted', tx('web.lk.an_n', nf(0).format(a.n), nf(0).format(a.n_eff), pc(a.ci[0]), pc(a.ci[1]))));
      tr.append(el('td', null, tx('web.lk.f_' + f)), el('td', null, tx(`web.lk.g_${f}_${a.group}`)), up, el('td', 'r', pc(A.all.p)), el('td', null, vs.join(' · ')));
      body.append(tr);
    }
    t.replaceChildren(thead, body);
    const c = A.combo, s = R.summary;
    $('lk-an').replaceChildren(
      el('p', null, c.n ? tx('web.lk.an_combo', nf(0).format(c.n), hName(view.h), pc(c.p), nf(0).format(c.n_eff), pc(c.ci[0]), pc(c.ci[1]), pc(A.all.p)) : tx('web.lk.an_combo_none')),
      el('p', 'sm muted', tx('web.lk.an_desc_note', hName(view.h))),
      el('p', s.hon + s.kem ? 'warn' : 'muted', tx('web.lk.an_summary', nf(0).format(R.tests), nf(0).format(s.hon), nf(0).format(s.kem), nf(0).format(s.nhu_bat_ky), nf(0).format(s.it_du_lieu))));
  }

  // ----- kiểm chứng quá khứ theo năm -----
  function renderCheck(ck) {
    $('lk-ck-title').textContent = tx('web.lk.ck_title', hName(view.h));
    $('lk-ck-lead').textContent = tx('web.lk.ck_lead', hName(view.h), dmy(LK.cfg.check_from));
    const t = $('t-lk-ck'), thead = el('thead'), head = el('tr'), body = el('tbody');
    for (const k of ['th_year', 'th_anchors', 'th_in80', 'th_in50']) head.append(el('th', null, tx('web.lk.' + k)));
    thead.append(head);
    const cell = (c) => (c.n ? `${pc(c.p)} (${nf(0).format(c.k)}/${nf(0).format(c.n)})` : '—');
    for (const y of ck.years) { const tr = el('tr'); tr.append(el('td', null, y.year), el('td', 'r', nf(0).format(y.in80.n)), el('td', 'r', cell(y.in80)), el('td', 'r', cell(y.in50))); body.append(tr); }
    const all = el('tr', 'here');
    all.append(el('td', null, tx('web.lk.all_years')), el('td', 'r', nf(0).format(ck.anchors)), el('td', 'r', cell(ck.in80)), el('td', 'r', cell(ck.in50)));
    body.append(all);
    t.replaceChildren(thead, body);
    const notes = [];
    if (ck.anchors < 30) notes.push(el('p', 'warn', tx('web.lk.ck_few', nf(0).format(ck.anchors))));
    const H = ck.hold;
    if (H.n) {
      const ht = el('table'), hh = el('thead'), hr = el('tr'), hb = el('tbody');
      for (const k of ['th_said', 'th_anchors', 'th_said_avg', 'th_real']) hr.append(el('th', null, tx('web.lk.' + k)));
      hh.append(hr);
      for (const g of H.groups) {
        if (!g.n) continue;
        const tr = el('tr');
        tr.append(el('td', null, g.to >= 1 ? tx('web.lk.said_ge', pc(g.from)) : `${pc(g.from)} – ${pc(g.to)}`), el('td', 'r', nf(0).format(g.n)), el('td', 'r', pc(g.said)),
          el('td', 'r', `${pc(g.p)} (${pc(g.ci[0])}–${pc(g.ci[1])})`));
        hb.append(tr);
      }
      ht.append(hh, hb);
      const sc = el('div', 'scroll'); sc.append(ht);
      notes.push(el('h3', 'sm', tx('web.lk.hg_title', hName(view.h))), sc);
    }
    $('lk-ck').replaceChildren(...notes);
  }
  function renderNotes() {
    $('lk-notes').replaceChildren(...[tx('web.lk.n_data', dmy(LK.start), dmy(LK.last)), tx('web.lk.n_method'), tx('web.lk.n_sources'), tx('web.lk.n_reg', LK.version), tx('web.lk.n_ref')]
      .map((s) => el('li', null, s)));
  }

  function render() {
    if (!LK) { $('lk-none').hidden = false; ['lk-sec', 'lk-band-sec', 'lk-hold-sec', 'lk-lv-sec', 'lk-an-sec', 'lk-ck-sec', 'lk-notes-sec'].forEach((id) => { $(id).hidden = true; }); return; }
    if (!document.body.classList.contains('lk-view')) return;
    if (!view.P) {
      view.P = K.prepare(LK);
      const inp = $('lk-t');
      inp.min = LK.cfg.t_from; inp.max = LK.last;
      if (!inp.value) inp.value = LK.last;
      view.t = view.P.last;
    }
    if (view.t == null && !readInputs()) return;
    const x = K.lookup(view.P, view.t, view.h), key = `${view.h}`;
    if (view.ckKey !== key) { view.ck = K.check(view.P, view.h); view.ckKey = key; }   // kiểm chứng chỉ phụ thuộc h
    const s = LK.research.summary;
    $('lk-honest').replaceChildren(el('p', null, tx('web.lk.honest1', nf(0).format(LK.research.tests), nf(0).format(s.hon), nf(0).format(s.kem))), el('p', 'muted', tx('web.lk.honest2')));
    renderState(x); renderBand(x, view.ck); drawChart(x); renderHold(x, view.ck); renderLevels(x); renderAnalog(x); renderCheck(view.ck); renderNotes();
  }
  function go() { if (view.P && readInputs()) render(); }

  // ----- chuyển chế độ: chỉ thêm / bỏ lớp body.lk-view (và bỏ ls-view, tr-view, pa-view), không gọi gì của các phần khác -----
  function setView(on) {
    document.body.classList.toggle('lk-view', on);
    $('mode-lk').setAttribute('aria-pressed', String(on));
    if (!on) return;
    document.body.classList.remove('ls-view', 'tr-view', 'pa-view');
    for (const id of VIEWS) $(id).setAttribute('aria-pressed', 'false');
    try { localStorage.setItem(KEY, 'lk'); } catch (e) { /* bỏ qua */ }
    render();
  }
  $('mode-lk').addEventListener('click', () => setView(true));
  for (const id of VIEWS) $(id).addEventListener('click', () => setView(false));
  $('lk-go').addEventListener('click', go);
  for (const id of ['lk-t', 'lk-hn']) $(id).addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
  $('lk-hu').addEventListener('change', go);
  $('lk-t').addEventListener('change', go);
  document.querySelectorAll('#lk-quick button').forEach((b) => b.addEventListener('click', () => {
    $('lk-hn').value = b.dataset.n; $('lk-hu').value = b.dataset.u; go();
  }));
  $('lk-latest').addEventListener('click', () => { if (LK) { $('lk-t').value = LK.last; go(); } });
  if (window.ResizeObserver) {
    let w = 0;
    new ResizeObserver(() => { const x = $('lk-chart').clientWidth; if (x && x !== w) { w = x; if (view.P && document.body.classList.contains('lk-view')) drawChart(K.lookup(view.P, view.t, view.h)); } }).observe($('lk-chart'));
  }
  let start = false;
  try { start = localStorage.getItem(KEY) === 'lk'; } catch (e) { /* bỏ qua */ }
  if (start) setView(true);
})();
// ===== LOOKUP VIEW END =====
