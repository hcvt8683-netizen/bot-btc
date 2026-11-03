// ===== TREND START =====
// Chế độ "Xu hướng" (nút thứ 4 ở đầu trang). Số liệu: data/results/trend.json từ bot/models/trend.py, build.py nhúng vào (TR).
// Tách riêng như ls.js: không đọc, không ghi gì của bên mua / bán hay Long/Short; chỉ bật lớp body.tr-view để CSS ẩn phần khác.
// Giá lúc này lấy từ Binance (REST) khi mở chế độ và mỗi phút; xu hướng, phân vị, độ dao động lấy từ lần chạy Daily.
(() => {
  const TR = /*TR_JSON*/null;
  const { tx, vnTime } = I18N;
  const $ = (id) => document.getElementById(id);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  const nf = (d) => new Intl.NumberFormat('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d });
  const ok = (x) => x != null && isFinite(x);
  const pc = (x, d = 0) => (ok(x) ? nf(d).format(x * 100) + '%' : '—');
  const signed = (v, d, unit) => { const r = Math.round(v * 10 ** d) / 10 ** d; return (r > 0 ? '+' : r < 0 ? '−' : '') + nf(d).format(Math.abs(r)) + unit; };
  const spc = (x, d = 1) => (ok(x) ? signed(x * 100, d, '%') : '—');
  const usd = (x) => (ok(x) ? nf(0).format(x) + ' $' : '—');
  const vnDate = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`;
  const shortDate = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}`;
  const LOCAL = location.protocol.startsWith('http') && ['localhost', '127.0.0.1'].includes(location.hostname);
  const GROUPS = { day: [1, 2, 3, 4, 5, 6, 7], week: [7, 14, 21, 28], month: [30, 60, 90, 120, 150, 180] };
  const MODELS = ['goc', 'dong_luong', 'ma200', 'dinh_gia', 'dao_chieu', 'ket_hop', 'hoc_may'];
  const TESTED = ['dong_luong', 'ma200', 'dinh_gia', 'dao_chieu', 'ket_hop'];   // 5 mô hình chấm chung một họ Holm (học máy chấm riêng)
  const view = { group: 'day', price: null, at: null, timer: null };
  const row = (k) => (TR ? TR.now.find((r) => r.k === k) : null);
  const hLabel = (k, group) => (group === 'week' || (!group && [14, 21, 28].includes(k)) ? tx('web.tr.h_week', k / 7)
    : k >= 30 ? tx('web.tr.h_month', k / 30) : tx('web.tr.h_day', k));
  const tone = (lab) => (lab === 'tang' ? 'up' : lab === 'giam' ? 'down' : 'flat');
  const ARROW = { tang: '↑', giam: '↓', khong_ro: '→' };
  const base = () => view.price || (TR ? TR.close : null);
  const modelName = (m) => tx('web.tr.m_' + m);

  async function getJSON(url, timeout = 12000) {
    const once = async (u) => {
      const ctl = new AbortController(), tm = setTimeout(() => ctl.abort(), timeout);
      try { const r = await fetch(u, { signal: ctl.signal }); if (!r.ok) throw new Error('HTTP ' + r.status); return await r.json(); } finally { clearTimeout(tm); }
    };
    if (LOCAL) { try { return await once('/proxy?url=' + encodeURIComponent(url)); } catch (e) { /* thử trực tiếp */ } }
    return once(url);
  }
  async function loadPrice() {
    if (window.BOT_NO_WS) return;
    try {
      const j = await getJSON('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT');
      const p = Number(j.price);
      if (p > 0) { view.price = p; view.at = Date.now(); render(); }
    } catch (e) { /* giữ giá đóng ngày */ }
  }

  // ----- phần đầu: giá, trạng thái, kết luận trung thực -----
  function renderHead() {
    $('tr-price').textContent = usd(base());
    $('tr-price-sub').textContent = view.at ? tx('web.tr.now_live', vnTime(new Date(view.at).toISOString())) : tx('web.tr.now_close', vnDate(TR.anchor));
    const chips = $('tr-states');
    chips.replaceChildren(...['dong_luong', 'ma200', 'dinh_gia', 'dao_chieu'].filter((m) => TR.states[m]).map((m) => el('span', 'pill muted', tx(`web.tr.st_${m}_${TR.states[m]}`))));
    const dirEdge = TR.now.filter((r) => r.dir_model !== 'goc'), magEdge = TR.now.filter((r) => r.mag_model !== 'goc');
    const lines = [dirEdge.length ? tx('web.tr.honest_some', dirEdge.map((r) => `${hLabel(r.k)} (${modelName(r.dir_model)})`).join(', '))
      : tx('web.tr.honest_none', nf(0).format(TR.tests))];
    if (magEdge.length) lines.push(tx('web.tr.honest_mag', magEdge.map((r) => `${hLabel(r.k)} (${modelName(r.mag_model)})`).join(', ')));
    $('tr-honest').replaceChildren(...lines.map((t) => el('p', null, t)));
    // điều nói chắc được: khoảng 9/10 lần, kèm độ phủ thật khi chấm đi tới
    const P = base(), sure = [el('span', 't', tx('web.tr.sure_title'))];
    for (const k of [1, 7, 30]) {
      const r = row(k), e = TR.eval[String(k)];
      if (!r || !ok(r.q5) || !e || !e.models) continue;
      const p = el('p');
      p.append(document.createTextNode(tx('web.tr.sure_line', hLabel(k), '\u0000', '\u0001', pc(e.models[e.mag_model].cover90, 0)).split('\u0000')[0]),
        el('b', null, usd(P * (1 + r.q5))), document.createTextNode(' – '), el('b', null, usd(P * (1 + r.q95))),
        document.createTextNode(tx('web.tr.sure_line', hLabel(k), '\u0000', '\u0001', pc(e.models[e.mag_model].cover90, 0)).split('\u0001')[1]));
      sure.push(p);
    }
    sure.push(el('p', 'no', tx('web.tr.sure_basis', usd(P), vnDate(TR.anchor))), el('p', 'no', tx('web.tr.sure_no')));
    $('tr-sure').replaceChildren(...sure);
    document.querySelectorAll('#tr-groups button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.g === view.group)));
  }

  // ----- biểu đồ hình quạt: khoảng 8/10 lần và giữa, theo kỳ hạn của nhóm đang chọn -----
  const NS = 'http://www.w3.org/2000/svg';
  const sv = (t, at) => { const e = document.createElementNS(NS, t); for (const k in at) e.setAttribute(k, at[k]); return e; };
  function drawFan() {
    const box = $('tr-fan'), W = box.clientWidth;
    if (!TR || !W) return;
    const ks = GROUPS[view.group], P = base(), H = 260, m = { l: 64, r: 16, t: 16, b: 30 };
    const pts = [{ k: 0, lo: P, mid: P, hi: P, lo9: P, hi9: P }, ...ks.map((k) => { const r = row(k);
      return { k, lo: P * (1 + r.q10), mid: P * (1 + r.q50), hi: P * (1 + r.q90), lo9: P * (1 + (ok(r.q5) ? r.q5 : r.q10)), hi9: P * (1 + (ok(r.q95) ? r.q95 : r.q90)), r }; })];
    let lo = Math.min(...pts.map((p) => p.lo9)), hi = Math.max(...pts.map((p) => p.hi9));
    const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
    const X = (i) => m.l + i / (pts.length - 1) * (W - m.l - m.r), Y = (v) => m.t + (hi - v) / (hi - lo) * (H - m.t - m.b);
    const svg = sv('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': tx('web.tr.fan_title') });
    const defs = sv('defs', {}), grad = sv('linearGradient', { id: 'tr-fan-g', x1: 0, y1: 0, x2: 0, y2: 1 });
    grad.append(sv('stop', { offset: '0%', class: 'g-up' }), sv('stop', { offset: '100%', class: 'g-down' }));
    defs.append(grad); svg.append(defs);
    const step = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000].find((s) => (hi - lo) / s <= 6) || 100000;
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) {
      svg.append(sv('line', { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: 'grid' }));
      const t = sv('text', { x: m.l - 8, y: Y(v) + 4, 'text-anchor': 'end', class: 'ax' }); t.textContent = nf(0).format(v); svg.append(t);
    }
    const area = pts.map((p, i) => `${X(i).toFixed(1)},${Y(p.hi).toFixed(1)}`).concat(pts.slice().reverse().map((p, j) => `${X(pts.length - 1 - j).toFixed(1)},${Y(p.lo).toFixed(1)}`));
    const area9 = pts.map((p, i) => `${X(i).toFixed(1)},${Y(p.hi9).toFixed(1)}`).concat(pts.slice().reverse().map((p, j) => `${X(pts.length - 1 - j).toFixed(1)},${Y(p.lo9).toFixed(1)}`));
    svg.append(sv('polygon', { points: area9.join(' '), class: 'band90' }), sv('polygon', { points: area.join(' '), class: 'band' }));
    svg.append(sv('line', { x1: m.l, x2: W - m.r, y1: Y(P), y2: Y(P), class: 'now' }));
    svg.append(sv('polyline', { points: pts.map((p, i) => `${X(i).toFixed(1)},${Y(p.mid).toFixed(1)}`).join(' '), class: 'midline' }));
    const compact = (W - m.l - m.r) / (pts.length - 1) < 64;   // khung hẹp: nhãn chỉ ghi số của nhóm đang chọn
    const unit = { day: 1, week: 7, month: 30 }[view.group];
    pts.forEach((p, i) => {
      svg.append(sv('circle', { cx: X(i), cy: Y(p.mid), r: i ? 4 : 5, class: i ? 'pt ' + (p.mid >= P ? 'up' : 'down') : 'pt0' }));
      const t = sv('text', { x: X(i), y: H - 9, 'text-anchor': i === 0 ? 'start' : i === pts.length - 1 ? 'end' : 'middle', class: 'ax' });
      t.textContent = i ? (compact ? String(p.k / unit) : hLabel(p.k, view.group)) : tx(compact ? 'web.tr.fan_now_short' : 'web.tr.fan_now'); svg.append(t);
    });
    const tip = el('div', 'tip');
    svg.addEventListener('pointermove', (ev) => {
      const rect = svg.getBoundingClientRect(), i = Math.max(0, Math.min(pts.length - 1, Math.round((ev.clientX - rect.left - m.l) / (W - m.l - m.r) * (pts.length - 1))));
      const p = pts[i];
      if (!i) { tip.style.display = 'none'; return; }
      tip.replaceChildren(el('b', null, `${hLabel(p.k, view.group)} · ${tx('web.tr.by_date', shortDate(p.r.target))}`),
        el('div', null, tx('web.tr.mid', usd(p.mid), spc(p.r.q50))), el('div', null, tx('web.tr.band90', usd(p.lo9), usd(p.hi9))), el('div', 'muted', tx('web.tr.band80', usd(p.lo), usd(p.hi))));
      tip.style.display = 'block';
      const left = X(i) + 12, w = tip.offsetWidth;
      tip.style.left = (left + w > W ? X(i) - w - 12 : left) + 'px'; tip.style.top = (Math.max(4, Y(p.hi) - 10)) + 'px';
    });
    svg.addEventListener('pointerleave', () => { tip.style.display = 'none'; });
    box.replaceChildren(svg, tip);
  }

  // ----- thẻ từng kỳ hạn -----
  function renderCards() {
    const ks = GROUPS[view.group], P = base();
    const lo9 = (r) => (ok(r.q5) ? r.q5 : r.q10), hi9 = (r) => (ok(r.q95) ? r.q95 : r.q90);
    const M = Math.max(...ks.map((k) => Math.max(Math.abs(lo9(row(k))), Math.abs(hi9(row(k)))))) * 1.05;
    const pos = (x) => 50 + 50 * x / M;
    $('tr-cards').replaceChildren(...ks.map((k) => {
      const r = row(k), t = tone(r.label), c = el('article', 'tr-card ' + t);
      const hd = el('div', 'hd');
      hd.append(el('b', null, hLabel(k, view.group)), el('span', 'muted', tx('web.tr.by_date', shortDate(r.target))));
      const dir = el('div', 'dir');
      dir.append(el('span', 'arrow', ARROW[r.label]), el('span', null, tx('web.tr.lab_' + r.label)));
      const pu = el('div', 'pu');
      pu.append(el('b', null, pc(r.p, 0)), el('span', 'muted', tx('web.tr.p_up', '').trim()));
      const meter = el('div', 'meter'), fill = el('i'); fill.style.width = (100 * (r.p || 0)) + '%'; meter.append(fill, el('s'));
      const mid = el('div', 'med', tx('web.tr.mid', usd(P * (1 + r.q50)), spc(r.q50)));
      const rb = el('div', 'rbar'), seg = el('i'), zero = el('s'), mk = el('b');
      seg.style.left = pos(lo9(r)) + '%'; seg.style.width = (pos(hi9(r)) - pos(lo9(r))) + '%';
      zero.style.left = '50%'; mk.style.left = pos(r.q50) + '%';
      rb.append(seg, zero, mk);
      const band = el('div', 'band');
      band.append(el('div', 'b90', tx('web.tr.band90', usd(P * (1 + lo9(r))), usd(P * (1 + hi9(r))))), el('div', 'muted', tx('web.tr.band80', usd(P * (1 + r.q10)), usd(P * (1 + r.q90)))));
      const src = el('div', 'src', r.dir_model === 'goc' ? tx('web.tr.src_goc') : tx('web.tr.src_model', modelName(r.dir_model)));
      const dots = el('div', 'dots');
      dots.title = tx('web.tr.agree', r.agree_up, r.agree_down);
      for (const m of TESTED) { const p = r.models[m].p, d = el('i', p > 0.5 ? 'up' : p < 0.5 ? 'down' : null); d.title = `${modelName(m)}: ${pc(p, 0)}`; dots.append(d); }
      c.append(hd, dir, pu, meter, mid, rb, band, dots, src);
      return c;
    }));
  }

  // ----- bảng nhiệt: các mô hình nói gì -----
  function renderModels() {
    const head = el('tr');
    head.append(el('th', null, tx('web.tr.th_h')));
    for (const m of MODELS) { const th = el('th', null, modelName(m)); th.title = tx('web.tr.md_' + m); head.append(th); }
    const tb = el('tbody');
    for (const r of TR.now) {
      const tr = el('tr');
      tr.append(el('td', null, hLabel(r.k)));
      for (const m of MODELS) {
        const p = r.models[m].p, td = el('td', (p >= 0.55 ? 'hi-up' : p <= 0.45 ? 'hi-down' : '') + (m === r.dir_model ? ' use' : ''), pc(p, 0));
        tr.append(td);
      }
      tb.append(tr);
    }
    const th = el('thead'); th.append(head);
    $('t-tr-models').replaceChildren(th, tb);
  }

  // ----- đối chiếu với các thẻ khác -----
  function renderCross() {
    const C = TR.cross || {}, head = el('tr'), tb = el('tbody');
    for (const k of ['th_what', 'th_other', 'th_this', 'th_match']) head.append(el('th', null, tx('web.tr.' + k)));
    const add = (what, other, mine, match) => {
      const tr = el('tr');
      tr.append(el('td', null, what), el('td', 'num', other), el('td', 'num', mine),
        el('td', match == null ? 'muted' : match ? 'good' : 'bad', match == null ? tx('web.tr.cx_na') : tx(match ? 'web.tr.cx_yes' : 'web.tr.cx_no')));
      tb.append(tr);
    };
    const fmtBand = (x) => `${spc(x.q50)} (${spc(x.q10)} … ${spc(x.q90)})`;
    for (const k of [1, 7, 30]) {
      const f = C.forecast && C.forecast.rows.find((x) => x.k === k), r = row(k);
      if (!f || !r) continue;
      const wa = f.q90 - f.q10, wb = r.q90 - r.q10;
      add(tx('web.tr.cx_band', hLabel(k)), fmtBand(f), fmtBand(r), Math.abs(f.q50 - r.q50) <= 0.01 && Math.abs(wa - wb) <= 0.25 * wa);
    }
    for (const [w, k] of [[4, 28], [13, 90], [26, 180]]) {
      const c = (C.calib || []).find((x) => x.weeks === w), r = row(k);
      if (!c || !r) continue;
      add(tx('web.tr.cx_calib', w, k), pc(c.p, 0), pc(r.p, 0), Math.abs(c.p - r.p) <= 0.05);
    }
    if (C.long_short && C.long_short.score) {
      const s = C.long_short.score, r1 = row(1), lsTrade = (s.long || 0) >= 6 || (s.short || 0) >= 6;
      add(tx('web.tr.cx_ls'), tx('web.tr.cx_ls_val', s.long ?? '—', s.short ?? '—', tx(lsTrade ? 'web.tr.ls_yes' : 'web.tr.ls_no')),
        tx('web.tr.cx_ls_this', tx('web.tr.lab_' + r1.label)), !lsTrade === (r1.label === 'khong_ro'));
    }
    const th = el('thead'); th.append(head);
    $('t-tr-cross').replaceChildren(th, tb);
  }

  // ----- kiểm tra trên dữ liệu cũ: biểu đồ cột đúng hướng và bảng -----
  const bestOf = (e) => TESTED.reduce((a, m) => (e.models[m].dir_gain > e.models[a].dir_gain ? m : a), TESTED[0]);
  function drawHits() {
    const box = $('tr-hits'), W = box.clientWidth;
    if (!TR || !W) return;
    const rows = TR.now.map((r) => ({ k: r.k, e: TR.eval[String(r.k)] })).filter((x) => x.e && x.e.models);
    const H = 210, m = { l: 40, r: 8, t: 10, b: 26 }, lo = 0.4, hi = 0.75, n = rows.length, gw = (W - m.l - m.r) / n, bw = Math.max(3, Math.min(14, gw * 0.32));
    const Y = (v) => m.t + (hi - Math.max(lo, Math.min(hi, v))) / (hi - lo) * (H - m.t - m.b);
    const svg = sv('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': tx('web.tr.bt_chart') });
    for (const v of [0.4, 0.5, 0.6, 0.7]) {
      svg.append(sv('line', { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: v === 0.5 ? 'half' : 'grid' }));
      const t = sv('text', { x: m.l - 6, y: Y(v) + 4, 'text-anchor': 'end', class: 'ax' }); t.textContent = Math.round(v * 100) + '%'; svg.append(t);
    }
    rows.forEach((x, i) => {
      const cx = m.l + gw * (i + 0.5), g = x.e.models.goc.hit, b = x.e.models[bestOf(x.e)].hit;
      const r1 = sv('rect', { x: cx - bw - 1, y: Y(g), width: bw, height: Y(lo) - Y(g), rx: 2, class: 'b-goc' });
      const r2 = sv('rect', { x: cx + 1, y: Y(b), width: bw, height: Y(lo) - Y(b), rx: 2, class: 'b-best' });
      const tt = sv('title', {}); tt.textContent = `${hLabel(x.k)}: ${tx('web.tr.lg_goc')} ${pc(g, 1)} · ${modelName(bestOf(x.e))} ${pc(b, 1)}`;
      r1.append(tt.cloneNode(true)); r2.append(tt);
      svg.append(r1, r2);
      const t = sv('text', { x: cx, y: H - 8, 'text-anchor': 'middle', class: 'ax' }); t.textContent = String(x.k); svg.append(t);
    });
    box.replaceChildren(svg);
  }
  function renderBacktest() {
    const first = TR.eval['1'];
    $('tr-bt-lead').textContent = tx('web.tr.bt_lead', first && first.from ? vnDate(first.from) : '—');
    const head = el('tr');
    for (const k of ['th_h', 'th_n', 'th_win', 'th_goc_hit', 'th_best', 'th_ml', 'th_gain', 'th_holm', 'th_cover', 'th_cover90', 'th_verdict']) head.append(el('th', null, tx('web.tr.' + k)));
    const ML = TR.ml || {};
    const tb = el('tbody');
    for (const r of TR.now) {
      const e = TR.eval[String(r.k)];
      if (!e || !e.models) continue;
      const b = bestOf(e), x = e.models[b], edge = e.dir_model !== 'goc', tr = el('tr', edge ? 'here' : null);
      const v = el('td', edge ? 'good' : 'muted', tx(edge ? 'web.tr.v_edge' : 'web.tr.v_none'));
      if (!edge && x.dir_gain > 0 && !x.dir_halves) v.append(el('span', 'sub', tx('web.tr.halves_bad')));
      tr.append(el('td', null, hLabel(r.k)), el('td', 'r num', nf(0).format(e.n)), el('td', 'r num', nf(0).format(e.windows)), el('td', 'r num', pc(e.models.goc.hit, 1)),
        el('td', 'r num', tx('web.tr.best_cell', modelName(b), pc(x.hit, 1))),
        (() => { const m = ML[String(r.k)]; return el('td', 'r num ' + (m && m.hit != null ? (m.dir_edge ? 'good' : m.hit < m.hit_goc ? 'bad' : 'muted') : 'muted'), m && m.hit != null ? pc(m.hit, 1) : '—'); })(),
        el('td', 'r num ' + (edge ? 'good' : x.dir_gain < 0 ? 'bad' : 'muted'), tx('web.tr.gain_cell', nf(4).format(x.dir_gain), nf(4).format(x.dir_ci[0]), nf(4).format(x.dir_ci[1]))),
        el('td', 'r num', nf(2).format(x.dir_holm)), el('td', 'r num', pc(e.models[e.mag_model].cover80, 0)), el('td', 'r num', pc(e.models[e.mag_model].cover90, 0)), v);
      tb.append(tr);
    }
    const th = el('thead'); th.append(head);
    $('t-tr-bt').replaceChildren(th, tb);
    const notes = [], mls = Object.values(ML).filter((m) => m && m.hit != null);
    if (mls.length) notes.push(tx('web.tr.ml_note', mls.filter((m) => m.hit < m.hit_goc).length, mls.length));
    const B = Object.entries(TR.bitstamp || {});
    if (B.length) {
      const same = B.filter(([k, b]) => b.dir_model === (TR.eval[k] || {}).dir_model).length, c9 = B.map(([, b]) => b.cover90).filter(ok);
      notes.push(tx('web.tr.robust', same, B.length, pc(Math.min(...c9), 0), pc(Math.max(...c9), 0)));
    }
    $('tr-bt-notes').replaceChildren(...notes.map((t) => el('li', null, t)));
    drawHits();
  }
  // ----- mô hình nến: hôm nay có mẫu nào, mỗi mẫu đúng hướng bao nhiêu so với một ngày bất kỳ -----
  function renderCandles() {
    const CD = TR.candles;
    if (!CD) { $('tr-cd-sec').hidden = true; return; }
    $('tr-cd-lead').textContent = tx('web.tr.cd_lead', vnDate(String(CD.from)));
    const name = (n) => tx('web.tr.c_' + n);
    $('tr-cd-today').replaceChildren(CD.today.length
      ? el('span', 'pill mid', tx('web.tr.cd_today', vnDate(CD.anchor), CD.today.map(name).join(', ')))
      : el('span', 'pill muted', tx('web.tr.cd_today_none', vnDate(CD.anchor))));
    const ks = ['1', '3', '7'], head = el('tr');
    head.append(el('th', null, tx('web.tr.th_cd')), el('th', null, tx('web.tr.th_cd_n')));
    for (const k of ks) head.append(el('th', null, tx('web.tr.th_cd_k', k)));
    head.append(el('th', null, tx('web.tr.th_cd_v')));
    const tb = el('tbody');
    for (const [n, x] of Object.entries(CD.patterns)) {
      const tr = el('tr', CD.today.includes(n) ? 'here' : null), c0 = el('td');
      c0.append(el('b', null, name(n)), el('span', 'sub', tx(x.dir > 0 ? 'web.tr.cd_up' : 'web.tr.cd_down')));
      tr.append(c0, el('td', 'r num', nf(0).format(x.count)));
      const cells = ks.map((k) => x.per_k[k]);
      for (const v of cells) {
        const better = v && v.rate != null && v.rate > v.base;
        tr.append(el('td', 'r num ' + (v && v.edge ? (x.dir > 0 ? 'hit-up' : 'hit-down') : better ? '' : 'muted'), v && v.n ? tx('web.tr.cd_cell', pc(v.rate, 0), pc(v.base, 0)) : '—'));
      }
      const edge = cells.some((v) => v && v.edge), few = cells.every((v) => !v || v.few);
      tr.append(el('td', edge ? 'good' : 'muted', tx(edge ? 'web.tr.cd_edge' : few ? 'web.tr.cd_few' : 'web.tr.cd_none')));
      tb.append(tr);
    }
    const th = el('thead'); th.append(head);
    $('t-tr-cd').replaceChildren(th, tb);
    $('tr-cd-notes').replaceChildren(el('li', null, tx('web.tr.cd_note', nf(0).format(CD.tests))));
  }

  function renderMethod() {
    const items = [tx('web.tr.m1'), tx('web.tr.m2'), tx('web.tr.m3', nf(0).format(TR.tests)), tx('web.tr.m4'), tx('web.tr.m5'), tx('web.tr.updated', vnDate(TR.anchor), TR.version)];
    $('tr-method-list').replaceChildren(...items.map((t) => el('li', null, t)));
    const lg = TR.log || {};
    $('tr-log').textContent = lg.matured ? tx('web.tr.log_some', nf(0).format(lg.matured), pc(lg.hit && lg.hit.goc, 0), pc(lg.cover80, 0)) : tx('web.tr.log_none');
  }

  function render() {
    if (!TR) { $('tr-none').hidden = false; ['tr-sec', 'tr-models-sec', 'tr-bt-sec'].forEach((id) => { $(id).hidden = true; }); return; }
    if (!document.body.classList.contains('tr-view')) return;
    renderHead(); renderCards(); drawFan();
  }
  function renderAll() {
    if (!TR) { render(); return; }
    render(); renderModels(); renderCross(); renderCandles(); renderBacktest(); renderMethod();
  }

  // ----- chuyển chế độ: chỉ thêm / bỏ lớp body.tr-view (và bỏ ls-view), không gọi gì của các phần khác -----
  const KEY = 'btc-bot3-view';
  function setView(on) {
    document.body.classList.toggle('tr-view', on);
    $('mode-tr').setAttribute('aria-pressed', String(on));
    if (on) {
      document.body.classList.remove('ls-view');
      for (const id of ['mode-buy', 'mode-sell', 'mode-ls']) $(id).setAttribute('aria-pressed', 'false');
      try { localStorage.setItem(KEY, 'tr'); } catch (e) { /* bỏ qua */ }
      renderAll();
      loadPrice();
      if (!view.timer) view.timer = setInterval(() => { if (document.body.classList.contains('tr-view') && !document.hidden) loadPrice(); }, 60000);
    }
  }
  $('mode-tr').addEventListener('click', () => setView(true));
  for (const id of ['mode-buy', 'mode-sell', 'mode-ls']) $(id).addEventListener('click', () => setView(false));
  document.querySelectorAll('#tr-groups button').forEach((b) => b.addEventListener('click', () => { view.group = b.dataset.g; render(); }));
  if (window.ResizeObserver) {
    const seen = new WeakMap();
    const ro = new ResizeObserver((es) => { for (const e of es) { const w = e.target.clientWidth; if (w && w !== seen.get(e.target)) { seen.set(e.target, w); if (e.target.id === 'tr-fan') drawFan(); else drawHits(); } } });
    ro.observe($('tr-fan')); ro.observe($('tr-hits'));
  }
  // bảng Tóm tắt quyết định (Tổng quan, src/ui.js) đọc nhãn 7 và 30 ngày từ đây
  if (TR) {
    const at = (k) => TR.now.find((x) => x.k === k);
    window.BOT_SUMMARY = Object.assign(window.BOT_SUMMARY || {}, { trend: { r7: at(7), r30: at(30) } });
    window.dispatchEvent(new Event('bot-summary'));
  }
  let start = false;
  try { start = localStorage.getItem(KEY) === 'tr'; } catch (e) { /* bỏ qua */ }
  if (start) setView(true);
})();
// ===== TREND END =====
