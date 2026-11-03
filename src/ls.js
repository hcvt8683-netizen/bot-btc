// ===== LONG/SHORT START =====
// Chế độ riêng cho hợp đồng vĩnh cửu BTCUSDT. build.py nhúng hai bộ số liệu:
//  LT = data/results/perp_trade.json (bot/models/perp_trade.py): công thức vào lệnh có giá vào, cắt lỗ, chốt lời; chọn lại mỗi
//       tháng chỉ bằng lệnh đã đóng trước đó, chấm đi tới. Đây là phần chính.
//  LS = data/results/perp.json (bot/models/perp_signal.py): giữ đúng kỳ hạn, không cắt lỗ (phần "Xem thêm"); quy tắc kết luận
//       giống hệt perp_signal.decide.
// Không đọc, không ghi gì của bên mua / bên bán (KN, st, các thẻ): bấm "Long/Short" chỉ thêm lớp body.ls-view để CSS ẩn
// các thẻ mua / bán; bấm "Bên mua" / "Bên bán" thì bỏ lớp đó. Trạng thái thị trường tính lúc bấm Chạy từ fapi.binance.com,
// ngưỡng phân vị và bảng lịch sử lấy từ lần chạy Daily.
(() => {
  const LS = /*LS_JSON*/null;
  const LT = /*LT_JSON*/null;
  const { tx, vnTime } = I18N;
  const $ = (id) => document.getElementById(id);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  const nf = (d) => new Intl.NumberFormat('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d });
  const nk = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 });
  const ok = (x) => x != null && isFinite(x);
  const pc = (x, d = 0) => (ok(x) ? nf(d).format(x * 100) + '%' : '—');
  const signed = (v, d, unit) => { const r = Math.round(v * 10 ** d) / 10 ** d; return (r > 0 ? '+' : r < 0 ? '−' : '') + nf(d).format(Math.abs(r)) + unit; };
  const spc = (x, d = 2) => (ok(x) ? signed(x * 100, d, '%') : '—');
  const sR = (x, d = 2) => (ok(x) ? signed(x, d, 'R') : '—');
  const usd = (x) => (ok(x) ? nf(0).format(x) + ' $' : '—');
  const susd = (x) => (ok(x) ? (x > 0 ? '+' : x < 0 ? '−' : '') + nf(2).format(Math.abs(x)) + ' $' : '—');
  const fund = (x) => (ok(x) ? (x < 0 ? '−' : '') + nf(4).format(Math.abs(x * 100)) + '%' : '—');
  const vnDate = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`;
  const vnMonth = (s) => `${s.slice(5, 7)}/${s.slice(0, 4)}`;
  const utcIso = (s) => s.replace(' ', 'T') + 'Z';  // '2026-11-02 09:00' (UTC) → ISO
  const tone = (x) => (x > 0 ? 'good' : x < 0 ? 'bad' : 'muted');
  const parseNum = (v) => {  // như parseAmount của src/ui.js: "1.5" = 1,5; "1.000" = 1000
    const t = String(v || '').replace(/\s/g, ''), m = t.match(/^(.*?)[.,](\d{1,2})$/), int = (m ? m[1] : t).replace(/[.,]/g, ''), dec = m ? m[2] : '';
    const x = /^\d*$/.test(int) && (int || dec) ? Number((int || '0') + (dec ? '.' + dec : '')) : NaN;
    return isFinite(x) && x > 0 ? x : null;
  };
  const LOCAL = location.protocol.startsWith('http') && ['localhost', '127.0.0.1'].includes(location.hostname);
  const FAPI = 'https://fapi.binance.com/fapi/v1/';

  async function getJSON(url, timeout = 15000) {
    const once = async (u) => {
      const ctl = new AbortController(), tm = setTimeout(() => ctl.abort(), timeout);
      try { const r = await fetch(u, { signal: ctl.signal }); if (!r.ok) throw new Error('HTTP ' + r.status); return await r.json(); } finally { clearTimeout(tm); }
    };
    if (LOCAL) { try { return await once('/proxy?url=' + encodeURIComponent(url)); } catch (e) { /* thử trực tiếp */ } }
    return once(url);
  }

  const view = { unit: 'h', h: 4, raw: {}, err: null, rule: null, side: null, hold: null };

  // ----- dữ liệu trực tiếp: nến giờ (500), nến ngày (40), funding (12 mốc gần nhất) -----
  const f24At = (fr, t) => {  // trung bình funding có mốc trong (t − 24 giờ, t]
    const f = (fr || []).map((x) => [Math.floor(Number(x.fundingTime) / 3600000) * 3600000, Number(x.fundingRate)]).filter(([ft]) => ft > t - 86400000 && ft <= t);
    return f.length ? f.reduce((a, [, v]) => a + v, 0) / f.length : null;
  };
  async function loadLive() {
    const [kh, kd, fr] = await Promise.all([getJSON(`${FAPI}klines?symbol=BTCUSDT&interval=1h&limit=500`),
      getJSON(`${FAPI}klines?symbol=BTCUSDT&interval=1d&limit=40`).catch(() => null), getJSON(`${FAPI}fundingRate?symbol=BTCUSDT&limit=12`)]);
    const now = Date.now(), price = Number(kh[kh.length - 1][4]), raw = {};
    for (const [unit, k] of [['h', kh], ['d', kd]]) {
      const closed = (k || []).filter((r) => Number(r[6]) < now);
      if (closed.length < 32) { if (unit === 'h') throw new Error('klines'); continue; }
      const t = Number(closed[closed.length - 1][6]) + 1;  // giờ đóng của nến cuối đã đóng
      raw[unit] = { c: closed.map((r) => Number(r[4])), hi: closed.map((r) => Number(r[2])), lo: closed.map((r) => Number(r[3])), t, price, f24: f24At(fr, t) };
    }
    view.raw = raw;
  }

  // =====================================================================================================================
  // Phần chính: công thức có giá vào, cắt lỗ, chốt lời (LT)
  // =====================================================================================================================
  const ruleOf = (id) => (LT && LT.rules[id]) || null;
  const sigName = (r) => tx('web.lt.s_' + r.sig + '_' + r.side);
  const holdText = (h) => (h >= 48 && h % 24 === 0 ? tx('web.lt.h_days', h / 24) : tx('web.lt.h_hours', h));
  const avgHold = (h) => (h >= 48 ? tx('web.lt.h_days', nf(1).format(h / 24)) : tx('web.lt.h_hours', nf(0).format(h)));
  const entryText = (r) => (r.entry === 'cho' ? tx('web.lt.entry_cho', nk.format(LT.limit_atr)) : tx('web.lt.entry_ngay'));
  const ruleLine = (r) => tx('web.lt.rule_line', sigName(r), entryText(r), nk.format(r.k), nk.format(r.r), holdText(r.h));
  const ruleShort = (r) => tx('web.lt.rule_short', entryText(r), nk.format(r.k), nk.format(r.r), holdText(r.h));

  // Trạng thái ở nến giờ đóng cuối, cùng cách tính với perp_trade.features (ATR 14 × 24 giờ, trung bình 480 nến, cao/thấp 480 nến trước)
  function tradeState() {
    const r = view.raw.h;
    if (r && r.c.length >= 481) {
      const { c, hi, lo } = r, n = c.length, last = c[n - 1];
      let s = 0;
      for (let k = 0; k < 14; k++) { const i = n - 1 - 24 * k; s += Math.max(...hi.slice(i - 23, i + 1)) - Math.min(...lo.slice(i - 23, i + 1)); }
      const ma = c.slice(n - 480).reduce((a, b) => a + b, 0) / 480;
      return { close: last, atr: s / 14 / last, ma, hh: Math.max(...hi.slice(n - 481, n - 1)), ll: Math.min(...lo.slice(n - 481, n - 1)),
        c24: c[n - 25], r24: last / c[n - 25] - 1, f24: r.f24, price: r.price, at: r.t, live: true };
    }
    const w = LT.now;
    return { ...w, c24: w.close / (1 + w.r24), price: w.close, at: Date.parse(utcIso(w.anchor)), live: false };
  }
  function fires(r, s) {  // = perp_trade.signals (lúc chưa bấm Chạy dùng đúng kết quả của Daily)
    if (!s.live) { const v = LT.now.signals[`${r.sig}|${r.side}`]; return v == null ? null : v; }
    const q = LT.thresholds.r24, fq = LT.thresholds.f24, L = r.side === 'long';
    switch (r.sig) {
      case 'moc': return true;
      case 'xu_huong': return L ? s.close > s.ma : s.close <= s.ma;
      case 'pha_vo': return L ? s.close > s.hh : s.close < s.ll;
      case 'qua_da': return L ? s.r24 <= q.q10 : s.r24 >= q.q90;
      case 'funding_nguoc': return s.f24 == null ? null : L ? s.f24 <= fq.q20 : s.f24 >= fq.q80;
      case 'hoi_xu_huong': return L ? s.close > s.ma && s.r24 <= q.q20 : s.close <= s.ma && s.r24 >= q.q80;
      default: return null;
    }
  }
  // Mức giá làm tín hiệu bật (để tính lệnh khi tín hiệu chưa bật); funding không đổi ra giá được thì dùng giá lúc này
  function trigger(r, s) {
    const q = LT.thresholds.r24, fq = LT.thresholds.f24, L = r.side === 'long';
    switch (r.sig) {
      case 'xu_huong': return { text: tx(L ? 'web.lt.trig_above' : 'web.lt.trig_below', usd(s.ma), tx('web.lt.why_ma')), px: s.ma };
      case 'pha_vo': return L ? { text: tx('web.lt.trig_above', usd(s.hh), tx('web.lt.why_hh')), px: s.hh } : { text: tx('web.lt.trig_below', usd(s.ll), tx('web.lt.why_ll')), px: s.ll };
      case 'qua_da': {
        const px = s.c24 * (1 + (L ? q.q10 : q.q90));
        return { text: tx(L ? 'web.lt.trig_below' : 'web.lt.trig_above', usd(px), tx(L ? 'web.lt.why_drop' : 'web.lt.why_rise')), px };
      }
      case 'hoi_xu_huong': {
        const px = s.c24 * (1 + (L ? q.q20 : q.q80));
        return { text: tx('web.lt.trig_band', usd(Math.min(px, s.ma)), usd(Math.max(px, s.ma)), tx(L ? 'web.lt.why_dip' : 'web.lt.why_pop')), px };
      }
      case 'funding_nguoc':
        return { text: tx(L ? 'web.lt.trig_funding_low' : 'web.lt.trig_funding_high', fund(L ? fq.q20 : fq.q80), fund(s.f24)), px: s.price };
      default: return { text: '', px: s.price };
    }
  }
  function levels(r, base, atr) {
    const g = r.side === 'long' ? 1 : -1, E = r.entry === 'cho' ? base * (1 - g * LT.limit_atr * atr) : base, s = r.k * atr;
    return { E, SL: E * (1 - g * s), TP: E * (1 + g * r.r * s), s };
  }

  // ----- thang giá: chốt lời, giá vào, giá lúc này, cắt lỗ, thanh lý -----
  function ladder(lv, now, liq, L) {
    const box = el('div', 'ladder'), H = 230, pad = 16;
    const pts = [lv.TP, lv.E, lv.SL, now];
    let lo = Math.min(...pts), hi = Math.max(...pts);
    const span = hi - lo || hi * 0.01, far = liq != null && (liq < lo - span * 0.6 || liq > hi + span * 0.6);
    if (liq != null && !far) { lo = Math.min(lo, liq); hi = Math.max(hi, liq); }
    lo -= (hi - lo) * 0.04; hi += (hi - lo) * 0.04;
    const y = (p) => pad + (hi - p) / (hi - lo) * (H - 2 * pad);
    const zone = (a, b, c) => { const z = el('i', 'zone ' + c); z.style.top = Math.min(y(a), y(b)) + 'px'; z.style.height = Math.abs(y(a) - y(b)) + 'px'; box.append(z); };
    zone(lv.E, lv.TP, 'win'); zone(lv.E, lv.SL, 'loss');
    const rows = [['tp', lv.TP, tx('web.lt.p_target')], ['en', lv.E, tx('web.lt.p_entry')], ['sl', lv.SL, tx('web.lt.p_stop')]];
    if (Math.abs(now - lv.E) / lv.E > 1e-4) rows.push(['now', now, tx('web.lt.lad_now')]);
    if (liq != null && !far) rows.push(['liq', liq, tx('web.lt.lad_liq', nk.format(L))]);
    const labs = rows.map(([c, p, name]) => ({ c, p, y: y(p), name })).sort((a, b) => a.y - b.y);
    for (let i = 1; i < labs.length; i++) labs[i].ly = Math.max(labs[i].y, (labs[i - 1].ly ?? labs[i - 1].y) + 17);
    labs[0].ly = labs[0].y;
    const over = labs[labs.length - 1].ly - (H - 8);
    if (over > 0) labs.forEach((a) => { a.ly -= over; });
    for (const a of labs) {
      const line = el('div', 'lv ' + a.c); line.style.top = a.y + 'px'; box.append(line);
      const t = el('div', 'lv ' + a.c); t.style.top = a.ly + 'px'; t.style.borderTop = '0';
      const sp = el('span'); sp.append(el('b', null, a.name + ' '), document.createTextNode(`${usd(a.p)} ${a.c === 'en' ? '' : '(' + spc(a.p / lv.E - 1, 1) + ')'}`));
      t.append(sp); box.append(t);
    }
    if (far) { const t = el('p', 'muted', tx('web.lt.lad_liq_far', nk.format(L), usd(liq))); t.style.margin = '4px 0 0'; t.style.fontSize = '12.5px'; return [box, t]; }
    return [box];
  }

  function cell(cls, lab, val, sub) {
    const c = el('div', 'lt-cell ' + cls);
    c.append(el('div', 'lab', lab), el('div', 'val', val), el('div', 'sub', sub));
    return c;
  }

  // ----- đề xuất lúc kiểm tra: 6 tiêu chí mỗi phía (mục checklist), chỉ đề xuất phía đạt đủ -----
  const sideName = (sd) => tx('web.ls.side_' + sd);
  function sidePick(sd) {
    const c = LT.sides[sd].current, id = (c.rule || c.best || {}).id;
    return { r: ruleOf(id), picked: !!c.rule, cur: c };
  }
  function checks(sd, s, L) {
    const S = LT.sides[sd], c = S.current, st = S.check, { r } = sidePick(sd), out = [];
    out.push([st.c1, st.c1 ? tx('web.lt.c1_ok', nf(2).format(c.t), nf(0).format(c.n_train), nk.format(LT.gate_t))
      : tx('web.lt.c1_no', ok(c.t) ? nf(2).format(c.t) : '—', nk.format(LT.gate_t), nf(0).format(S.stand_aside), nf(0).format(LT.wf.months))]);
    out.push([st.c2, tx('web.lt.c2', nf(0).format(S.n))]);
    out.push([st.c3, S.n ? tx('web.lt.c3', sR(S.boot[0])) : tx('web.lt.c3_none')]);
    out.push([st.c4, S.n ? tx('web.lt.c4', sR(S.halves[0].meanR), sR(S.halves[1].meanR)) : tx('web.lt.c4_none')]);
    const on = r ? fires(r, s) : null;
    out.push([on === true, on === true ? tx('web.lt.c5_on') : on === false ? tx('web.lt.c5_off') : tx('web.lt.c5_na')]);
    const stop = r ? r.k * s.atr : 0, m = 1 / L - LT.mmr;
    out.push(L <= 1 ? [true, tx('web.lt.c6_1x')] : [m > stop, tx(m > stop ? 'web.lt.c6_ok' : 'web.lt.c6_no', nk.format(L), pc(Math.max(m, 0), 1), pc(stop, 1))]);
    return out;
  }
  function atHold(r, H) {  // số của cùng công thức với thời gian giữ H (mục hold_view); H = thời gian của công thức thì đúng là số của nó
    const h = r.holds, i = h ? h.h.indexOf(H) : -1;
    if (H === r.h || i < 0) return { n: r.n, p: r.p, ci: r.ci, p_tp: r.p_tp, p_sl: r.p_sl, p_tw: r.p_time_win, mean: r.mean, meanR: r.meanR, hours: r.hours };
    return { n: h.n[i], p: h.p[i], ci: [h.lo[i], h.hi[i]], p_tp: h.p_tp[i], p_sl: h.p_sl[i], p_tw: h.p_tw[i], mean: h.mean[i], meanR: h.meanR[i], hours: h.hours[i] };
  }
  function fillHold(r) {
    const sel = $('lt-hold'), hs = LT.hold_hours || [];
    const opts = [['', tx('web.lt.hold_rule', holdText(r.h))], ...hs.map((h) => [String(h), holdText(h === 24 ? 24 : h)])];
    if (sel.options.length !== opts.length || sel.options[0].textContent !== opts[0][1]) {
      sel.replaceChildren(...opts.map(([v, t]) => { const o = el('option', null, t); o.value = v; return o; }));
    }
    sel.value = view.hold == null ? '' : String(view.hold);
  }

  // đường xác suất thắng / chạm chốt lời / chạm cắt lỗ theo thời gian giữ; bấm để chọn
  function drawHold(box, r, H) {
    const W = box.clientWidth, h = r.holds;
    if (!W || !h) return;
    const HH = 170, m = { l: 36, r: 8, t: 8, b: 22 }, n = h.h.length;
    const X = (i) => m.l + i / (n - 1) * (W - m.l - m.r), Y = (v) => m.t + (1 - v) * (HH - m.t - m.b);
    const NS = 'http://www.w3.org/2000/svg', sv = (t, at) => { const e = document.createElementNS(NS, t); for (const k in at) e.setAttribute(k, at[k]); return e; };
    const svg = sv('svg', { width: W, height: HH, viewBox: `0 0 ${W} ${HH}`, role: 'img', 'aria-label': tx('web.lt.hc_title') });
    for (const v of [0, 0.25, 0.5, 0.75, 1]) {
      svg.append(sv('line', { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: v === 0.5 ? 'half' : 'grid' }));
      const t = sv('text', { x: m.l - 5, y: Y(v) + 4, 'text-anchor': 'end', class: 'ax' }); t.textContent = Math.round(v * 100) + '%'; svg.append(t);
    }
    h.h.forEach((x, i) => {
      if (![1, 6, 12, 24, 168].includes(x)) return;
      const t = sv('text', { x: X(i), y: HH - 6, 'text-anchor': i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle', class: 'ax' });
      t.textContent = x === 24 ? tx('web.lt.h_days', 1) : holdText(x); svg.append(t);
    });
    const line = (arr) => arr.map((v, i) => (ok(v) ? `${i && ok(arr[i - 1]) ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)}` : '')).join('');
    svg.append(sv('path', { d: line(h.p_sl), class: 'hsl' }), sv('path', { d: line(h.p_tp), class: 'htp' }), sv('path', { d: line(h.p), class: 'hw' }));
    const k = h.h.indexOf(H);
    if (k >= 0) svg.append(sv('line', { x1: X(k), x2: X(k), y1: m.t, y2: HH - m.b, class: 'sel' }));
    svg.addEventListener('click', (ev) => {
      const rect = svg.getBoundingClientRect(), i = Math.max(0, Math.min(n - 1, Math.round((ev.clientX - rect.left - m.l) / (W - m.l - m.r) * (n - 1))));
      view.hold = h.h[i] === r.h ? null : h.h[i]; renderPlan();
    });
    box.replaceChildren(svg);
  }

  function renderPlan() {
    const s = tradeState(), L = parseNum($('ls-lev').value) || 1, amt = parseNum($('ls-amt').value), N = LT.checklist.length;
    const ck = { long: checks('long', s, L), short: checks('short', s, L) };
    const score = (sd) => ck[sd].filter(([x]) => x).length;
    const pass = { long: score('long') === N, short: score('short') === N };
    const near = (sd) => ck[sd].every(([x], i) => x || i === 4);   // mọi tiêu chí trừ tín hiệu
    const verdict = pass.long && !pass.short ? 'nen_long' : pass.short && !pass.long ? 'nen_short' : 'khong';
    publish({ verdict, long: score('long'), short: score('short'), N, live: !!s.live });
    const vtone = { nen_long: 'good', nen_short: 'bad', khong: 'muted' }[verdict];
    const planSide = view.side || (verdict === 'nen_short' ? 'short' : verdict === 'nen_long' ? 'long' : score('short') > score('long') ? 'short' : 'long');
    const ans = $('lt-answer'), parts = [];
    parts.push(el('p', 'kicker', tx('web.lt.check_kicker', vnTime(new Date(s.at).toISOString()))), el('div', 'verdict ' + vtone, tx('web.lt.v_' + verdict)));
    parts.push(el('p', 'muted', tx('web.lt.check_rule', N, score('long'), score('short'))));
    if (pass.long && pass.short) parts.push(el('p', 'warn', tx('web.lt.check_both')));
    for (const sd of ['long', 'short']) if (!pass[sd] && near(sd)) parts.push(el('p', 'warn', tx('web.lt.v_cho_side', sideName(sd))));
    const cards = el('div', 'lt-sides');
    for (const sd of ['long', 'short']) {
      const c = el('div', 'lt-side' + (pass[sd] ? ' pass' : '') + (sd === planSide && !view.rule ? ' sel' : '')), hd = el('div', 'hd');
      hd.append(el('b', sd === 'long' ? 'good' : 'bad', sideName(sd)), el('span', pass[sd] ? 'good' : 'muted', tx('web.lt.side_score', score(sd), N)));
      const dots = el('div', 'lt-dots'), ul = el('ul');
      for (const [x, t] of ck[sd]) { dots.append(el('i', x ? 'on' : null)); ul.append(el('li', x ? 'ok' : null, t)); }
      const b = el('button', 'btn', sd === planSide && !view.rule ? tx('web.lt.showing_plan', sideName(sd)) : tx('web.lt.show_plan', sideName(sd)));
      b.type = 'button';
      b.addEventListener('click', () => { view.side = sd; view.rule = null; renderLT(); });
      c.append(hd, dots, ul, b);
      cards.append(c);
    }
    parts.push(cards);
    if (LT.sides.long.past && LT.sides.short.past && !LT.sides.long.past.full) parts.push(el('p', 'muted', tx('web.lt.past_link', LT.sides.long.past.max, LT.sides.short.past.max)));

    // lệnh của phía đang xem (hoặc công thức chọn trong bảng)
    const sp = sidePick(planSide), r = view.rule ? ruleOf(view.rule) : sp.r;
    if (!r) { ans.replaceChildren(...parts); return; }
    const head = el('div', 'lt-head');
    head.append(el('p', 'kicker', view.rule ? tx('web.lt.kicker_pick') : tx('web.lt.side_rule', vnMonth(LT.current.month), sideName(r.side))));
    if (view.rule) { const b = el('button', 'lt-back', tx('web.lt.back')); b.type = 'button'; b.addEventListener('click', () => { view.rule = null; renderLT(); }); head.append(b); }
    const on = fires(r, s);
    const rl = el('div', 'lt-rule');
    rl.append(el('span', null, ruleLine(r)), el('span', 'pill ' + (on === true ? 'good' : on === false ? 'muted' : 'mid'),
      on === true ? tx('web.lt.sig_on') : on === false ? tx('web.lt.sig_off') : tx('web.lt.sig_na')));
    const top = el('div', 'lt-plan'); top.style.display = 'block';
    top.append(head, rl);
    if (!view.rule && !sp.picked) top.append(el('p', 'lt-trig', tx('web.lt.side_rule_ref', sideName(r.side), nk.format(LT.gate_t))));
    const trig = on === true || r.sig === 'moc' ? null : trigger(r, s);
    if (trig && trig.text) top.append(el('p', 'lt-trig', trig.text));
    parts.push(top);

    fillHold(r);
    const H = view.hold || r.h, st = atHold(r, H);
    const sideOk = !view.rule && pass[r.side];
    const base = trig && trig.px ? trig.px : s.price, lv = levels(r, base, s.atr), g = r.side === 'long' ? 1 : -1;
    window.LT_PLAN = { side: r.side, E: lv.E, SL: lv.SL, TP: lv.TP };  // mục Price action (src/pact.js) lấy giá từ đây
    const m = 1 / L - LT.mmr, liq = L > 1 ? lv.E * (1 - g * m) : null;
    const plan = el('div', 'lt-plan');
    plan.append(el('h3', null, tx(!sideOk ? 'web.lt.plan_if' : trig ? 'web.lt.plan_wait' : 'web.lt.plan_now', sideName(r.side))));
    const cells = el('div', 'lt-cells');
    cells.append(cell('entry', tx('web.lt.p_entry'), usd(lv.E), r.entry === 'cho' ? tx('web.lt.p_entry_limit', LT.limit_bars) : tx('web.lt.p_entry_now')),
      cell('stop', tx('web.lt.p_stop'), usd(lv.SL), spc(lv.SL / lv.E - 1, 2)),
      cell('target', tx('web.lt.p_target'), usd(lv.TP), spc(lv.TP / lv.E - 1, 2)),
      cell('hold', tx('web.lt.p_hold'), holdText(H), H === r.h ? tx('web.lt.p_hold_sub') : tx('web.lt.p_hold_rule', holdText(r.h))));
    plan.append(cells, el('div', null));
    plan.lastChild.append(...ladder(lv, s.price, liq, L));
    parts.push(plan);

    // xác suất thắng trong thời gian giữ đã chọn
    const prob = el('div', 'lt-prob'), big = el('div', 'big');
    big.append(el('span', 'kicker', tx('web.lt.win_title', holdText(H))), el('b', st.p >= 0.5 ? 'good' : 'mid', st.n ? pc(st.p, 0) : '—'));
    prob.append(big);
    if (H !== r.h) prob.append(el('p', 'warn', tx('web.lt.hold_diff', holdText(H), holdText(r.h), nf(0).format(st.n))));
    if (!st.n) prob.append(el('p', 'muted', tx('web.lt.hold_none')));
    else {
      prob.append(el('p', 'muted', tx('web.lt.win_sub', nf(0).format(st.n), pc(st.ci[0], 0), pc(st.ci[1], 0))));
      const bar = el('div', 'lt-split'), leg = el('div', 'legend');
      for (const [c, v, k] of [['tp', st.p_tp, 'web.lt.sp_tp'], ['tw', st.p_tw, 'web.lt.sp_time_win'], ['tl', 1 - st.p_tp - st.p_sl - st.p_tw, 'web.lt.sp_time_loss'], ['sl', st.p_sl, 'web.lt.sp_sl']]) {
        const i = el('i', c); i.style.width = (100 * Math.max(0, v)) + '%'; i.title = `${tx(k)}: ${pc(v, 0)}`; bar.append(i);
        const x = el('span'); x.append(el('i', c), document.createTextNode(`${tx(k)} ${pc(Math.max(0, v), 0)}`)); leg.append(x);
      }
      prob.append(bar, leg);
      const cost = 2 * (LT.costs.fee + LT.costs.slippage), be = (lv.s + cost) / (lv.s * (1 + r.r));
      prob.append(el('p', null, tx('web.lt.exp_line', spc(st.mean, 2), sR(st.meanR), avgHold(st.hours))),
        el('p', null, tx('web.lt.be_line', pc(lv.s, 1), pc(lv.s * r.r, 1), pc(be, 0))));
    }
    const o = r.oos || { n: 0 };
    prob.append(el('p', 'muted', tx('web.lt.win_bias', nf(0).format(LT.rules_n)) + ' ' + (H !== r.h ? '' : o.n ? tx('web.lt.win_oos', nf(0).format(o.n), pc(o.p, 0), sR(o.meanR)) : tx('web.lt.win_oos_none'))
      + ' ' + tx('web.lt.win_oos_all', nf(0).format(LT.wf.n), pc(LT.wf.p, 0))));
    const hc = el('div', 'lt-hc'), hcBox = el('div');
    const hleg = el('div', 'legend');
    for (const [c, k] of [['hw', 'web.lt.hc_win'], ['htp', 'web.lt.hc_tp'], ['hsl', 'web.lt.hc_sl']]) { const x = el('span'); x.append(el('i', c), document.createTextNode(tx(k))); hleg.append(x); }
    if (r.holds) { hc.append(el('p', 'sm', tx('web.lt.hc_title')), hcBox, hleg); prob.append(hc); }
    parts.push(prob);

    // tiền và đòn bẩy
    const money = el('div', 'lt-money');
    money.append(el('p', 'sm', tx('web.lt.money_title', nk.format(L))));
    money.append(el('p', 'muted', amt ? tx('web.lt.money_size', usd(amt), nk.format(L), usd(amt * L)) : tx('web.lt.money_hint')));
    const before = L > 1 && m <= lv.s, $amt = (x) => (amt ? tx('web.lt.money_amt', susd(amt * x)) : '');
    const cost = 2 * (LT.costs.fee + LT.costs.slippage);
    const loss = before ? -1 : -L * (lv.s + cost), gain = L * (r.r * lv.s - cost), exp = st.n ? L * st.mean : null;
    money.append(el('p', 'bad', tx('web.lt.money_sl', spc(loss, 1), $amt(loss))), el('p', 'good', tx('web.lt.money_tp', spc(gain, 1), $amt(gain))));
    if (ok(exp)) money.append(el('p', 'muted', tx('web.lt.money_exp', spc(exp, 1), $amt(exp))));
    if (L <= 1) money.append(el('p', 'muted', tx('web.lt.money_1x')));
    else {
      const lmax = nf(1).format(Math.floor(10 / (lv.s + LT.mmr)) / 10);
      money.append(el('p', null, tx('web.lt.money_liq', usd(liq), pc(Math.max(m, 0), 1))),
        el('p', before ? 'warn' : 'muted', before ? tx('web.lt.money_liq_before', lmax) : tx('web.lt.money_liq_ok', lmax)));
    }
    money.append(el('p', 'muted', tx('web.lt.money_warn')));
    parts.push(money);
    ans.replaceChildren(...parts);
    if (r.holds) drawHold(hcBox, r, H);

    $('ls-status').textContent = view.err ? tx('web.lt.status_fail', view.err, vnTime(utcIso(LT.now.anchor)))
      : s.live ? tx('web.lt.status_live', vnTime(new Date(s.at).toISOString()), usd(s.price)) : tx('web.lt.status_first', vnTime(utcIso(LT.now.anchor)));
  }

  // ----- kiểm tra trên dữ liệu cũ -----
  function kpi(cls, lab, val, sub) {
    const k = el('div', 'kpi ' + cls);
    k.append(el('div', 'lab', lab), el('div', 'val', val), el('div', 'sub', sub));
    return k;
  }
  function renderBacktest() {
    const wf = LT.wf, b = LT.base;
    $('lt-lead').textContent = tx('web.lt.lead', nf(0).format(LT.rules_n));
    $('lt-bt-lead').textContent = tx('web.lt.bt_lead', vnMonth(wf.from), nf(0).format(LT.rules_n), nk.format(LT.gate_t), nf(0).format(LT.min_trades), nf(0).format(wf.months));
    $('lt-kpis').replaceChildren(
      kpi('info', tx('web.lt.k_trades'), nf(0).format(wf.n), tx('web.lt.k_trades_sub', nf(0).format(wf.months), nf(0).format(wf.stand_aside))),
      kpi(wf.p >= 0.5 ? 'good' : 'mid', tx('web.lt.k_win'), pc(wf.p, 1), tx('web.lt.k_win_sub', pc(wf.ci[0], 0), pc(wf.ci[1], 0))),
      kpi(tone(wf.meanR), tx('web.lt.k_mean'), sR(wf.meanR), tx('web.lt.k_mean_sub', sR(wf.boot[0]), sR(wf.boot[1]))),
      kpi(tone(wf.sumR), tx('web.lt.k_sum'), sR(wf.sumR, 1), tx('web.lt.k_sum_sub', sR(-wf.maxdd, 1))),
      kpi(wf.edge ? 'good' : 'bad', tx('web.lt.k_verdict'), wf.edge ? tx('web.lt.k_edge') : tx('web.lt.k_noedge'),
        tx('web.lt.k_verdict_sub', sR(wf.halves[0].meanR), sR(wf.halves[1].meanR))));
    const lg = $('lt-legend');
    lg.replaceChildren(...[['wf', tx('web.lt.lg_wf', nf(0).format(LT.rules_n))], ['base', tx('web.lt.lg_base', nf(0).format(LT.base_n))]].map(([c, t]) => {
      const sp = el('span'); sp.append(el('i', c), document.createTextNode(t)); return sp;
    }));
    $('lt-base-note').textContent = tx('web.lt.base_note', nf(0).format(b.n), pc(b.p, 0), sR(b.meanR), sR(b.boot[0]), sR(b.boot[1]), nf(0).format(b.stand_aside));
    drawCurve();
    const sh = el('tr');
    for (const t of [tx('web.lt.th_scope'), tx('web.lt.th_n'), tx('web.lt.th_win'), tx('web.lt.th_mean'), tx('web.lt.th_ci'), tx('web.lt.th_h1'), tx('web.lt.th_h2'), tx('web.lt.th_aside'), tx('web.lt.th_verdict')]) sh.append(el('th', null, t));
    const sth = el('thead'), stb = el('tbody'); sth.append(sh);
    for (const [k, x] of [['web.lt.sc_tat_ca', LT.wf], ['web.lt.sc_long', LT.sides.long], ['web.lt.sc_short', LT.sides.short], ['web.lt.sc_base', LT.base]]) {
      const tr = el('tr', k === 'web.lt.sc_base' ? 'base' : null), has = x.n > 0;
      tr.append(el('td', null, tx(k)), el('td', 'r', nf(0).format(x.n)), el('td', 'r', has ? pc(x.p, 0) : '—'), el('td', 'r ' + (has ? tone(x.meanR) : ''), has ? sR(x.meanR) : '—'),
        el('td', 'r', has ? `${sR(x.boot[0])} … ${sR(x.boot[1])}` : '—'), el('td', 'r', has && x.halves[0].n ? sR(x.halves[0].meanR) : '—'),
        el('td', 'r', has && x.halves[1].n ? sR(x.halves[1].meanR) : '—'), el('td', 'r', nf(0).format(x.stand_aside)),
        el('td', x.edge ? 'good' : 'muted', x.edge ? tx('web.lt.k_edge') : tx('web.lt.k_noedge')));
      stb.append(tr);
    }
    $('t-lt-sides').replaceChildren(sth, stb);
    // 6 tiêu chí áp ở từng tháng trong quá khứ
    $('lt-past-lead').textContent = tx('web.lt.past_lead', vnMonth(wf.from));
    const ph = el('tr');
    for (const t of [tx('web.lt.th_side'), tx('web.lt.th_score'), tx('web.lt.th_months'), tx('web.lt.th_n'), tx('web.lt.th_win'), tx('web.lt.th_ci'), tx('web.lt.th_mean')]) ph.append(el('th', null, t));
    const pth = el('thead'), ptb = el('tbody'), pnotes = []; pth.append(ph);
    for (const sd of ['long', 'short']) {
      const P = LT.sides[sd].past;
      if (!P) continue;
      for (const x of [...P.by_score].sort((a, b2) => b2.score - a.score)) {
        const tr = el('tr', x.score === 6 ? 'here' : null);
        tr.append(el('td', null, sideName(sd)), el('td', 'r', tx('web.lt.past_score', x.score)), el('td', 'r', nf(0).format(x.months)), el('td', 'r', nf(0).format(x.n)),
          el('td', 'r', x.n ? pc(x.p, 0) : '—'), el('td', 'r', x.n ? `${pc(x.ci[0], 0)}–${pc(x.ci[1], 0)}` : '—'), el('td', 'r ' + (x.n ? tone(x.meanR) : ''), x.n ? sR(x.meanR) : '—'));
        ptb.append(tr);
      }
      pnotes.push(P.full ? tx('web.lt.past_full', sideName(sd), nf(0).format(P.full)) : tx('web.lt.past_none', sideName(sd), P.max));
    }
    $('t-lt-past').replaceChildren(pth, ptb);
    $('lt-past-notes').replaceChildren(...[...pnotes, tx('web.lt.past_honest')].map((t) => el('li', null, t)));
    // mỗi kiểu tín hiệu: công thức tốt nhất trên toàn bộ lịch sử
    const shown = view.rule || (sidePick(view.side || 'long').r || {}).id;
    const head = el('tr');
    for (const t of [tx('web.lt.th_sig'), tx('web.lt.th_rule'), tx('web.lt.th_n'), tx('web.lt.th_win'), tx('web.lt.th_tp'), tx('web.lt.th_mean'), tx('web.lt.th_t'), tx('web.lt.th_view')]) head.append(el('th', null, t));
    const thead = el('thead'), tbody = el('tbody'); thead.append(head);
    const ids = [...LT.per_signal].sort((a, b2) => (LT.rules[b2].t ?? -99) - (LT.rules[a].t ?? -99));
    for (const id of ids) {
      const r = LT.rules[id], tr = el('tr', id === shown ? 'here' : null);
      const btn = el('button', 'lt-view', id === shown ? tx('web.lt.viewing') : tx('web.lt.view'));
      btn.type = 'button'; btn.setAttribute('aria-pressed', String(id === shown));
      btn.addEventListener('click', () => { view.rule = id; renderLT(); $('lt-sec').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
      const tdb = el('td'); tdb.append(btn);
      tr.append(el('td', null, sigName(r)), el('td', null, ruleShort(r)), el('td', 'r', nf(0).format(r.n)), el('td', 'r', pc(r.p, 0)), el('td', 'r', pc(r.p_tp, 0)),
        el('td', 'r ' + tone(r.meanR), sR(r.meanR)), el('td', 'r', ok(r.t) ? nf(2).format(r.t) : '—'), tdb);
      tbody.append(tr);
    }
    $('t-lt').replaceChildren(thead, tbody);
    $('lt-notes').replaceChildren(el('li', null, tx('web.lt.sig_note', nf(0).format(LT.rules_n))), el('li', null, tx('web.lt.r_note')));
    // từng tháng (mới nhất trước)
    const hh = el('tr');
    for (const t of [tx('web.lt.th_month'), tx('web.lt.th_pick'), tx('web.lt.th_tstat'), tx('web.lt.th_trades'), tx('web.lt.th_sumR')]) hh.append(el('th', null, t));
    const th2 = el('thead'), tb2 = el('tbody'); th2.append(hh);
    for (const h of [...LT.history].reverse()) {
      const r = h.rule ? ruleOf(h.rule) || parseRule(h.rule) : null;
      const tr = el('tr');
      tr.append(el('td', null, vnMonth(h.month)), el('td', r ? null : 'muted', r ? `${sigName(r)} · ${ruleShort(r)}` : tx('web.lt.tip_none')),
        el('td', 'r', ok(h.t) ? nf(2).format(h.t) : '—'), el('td', 'r', nf(0).format(h.n)), el('td', 'r ' + tone(h.sumR), h.n ? sR(h.sumR, 1) : '—'));
      tb2.append(tr);
    }
    $('t-lt-hist').replaceChildren(th2, tb2);
  }
  const parseRule = (id) => { const [sig, side, entry, k, r, h] = id.split('|'); return { id, sig, side, entry, k: Number(k), r: Number(r), h: Number(h) }; };

  // đường lãi lũy kế theo tháng (SVG theo đúng bề rộng khung; khung đang ẩn thì bỏ qua, vẽ lại khi hiện)
  function drawCurve() {
    const box = $('lt-curve'), W = box.clientWidth;
    if (!LT || !W) return;
    const H = 240, m = { l: 44, r: 12, t: 12, b: 26 }, ms = LT.curve.months, a = [0, ...LT.curve.wf], b = [0, ...LT.curve.base], n = a.length;
    const lo = Math.min(0, ...a, ...b), hi = Math.max(0, ...a, ...b), span = hi - lo || 1;
    const step = [1, 2, 5, 10, 20, 50].find((s) => span / s <= 6) || 100;
    const y0 = Math.floor(lo / step) * step, y1 = Math.ceil(hi / step) * step;
    const X = (i) => m.l + i / (n - 1) * (W - m.l - m.r), Y = (v) => m.t + (y1 - v) / (y1 - y0) * (H - m.t - m.b);
    const NS = 'http://www.w3.org/2000/svg', sv = (t, at) => { const e = document.createElementNS(NS, t); for (const k in at) e.setAttribute(k, at[k]); return e; };
    const svg = sv('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': tx('web.lt.chart_title') });
    for (let v = y0; v <= y1 + 1e-9; v += step) {
      svg.append(sv('line', { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: v === 0 ? 'zero' : 'grid' }));
      const t = sv('text', { x: m.l - 6, y: Y(v) + 4, 'text-anchor': 'end', class: 'ax' }); t.textContent = (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v) + 'R'; svg.append(t);
    }
    const every = W < 520 ? 2 : 1;
    ms.forEach((mo, i) => {
      if (mo.slice(5) !== '01' || Number(mo.slice(0, 4)) % every) return;
      const t = sv('text', { x: X(i + 1), y: H - 8, 'text-anchor': 'middle', class: 'ax' }); t.textContent = mo.slice(0, 4); svg.append(t);
    });
    const path = (arr) => arr.map((v, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join('');
    svg.append(sv('path', { d: path(b), class: 'base' }), sv('path', { d: path(a), class: 'wf' }));
    const cross = sv('line', { y1: m.t, y2: H - m.b, class: 'cross', visibility: 'hidden' }), dot = sv('circle', { r: 4.5, class: 'dot', visibility: 'hidden' });
    svg.append(cross, dot);
    const tip = el('div', 'tip');
    svg.addEventListener('pointermove', (ev) => {
      const rect = svg.getBoundingClientRect(), i = Math.max(1, Math.min(n - 1, Math.round((ev.clientX - rect.left - m.l) / (W - m.l - m.r) * (n - 1))));
      const h = LT.history[i - 1], r = h.rule ? ruleOf(h.rule) || parseRule(h.rule) : null;
      for (const [k, v] of [['x1', X(i)], ['x2', X(i)]]) cross.setAttribute(k, v);
      dot.setAttribute('cx', X(i)); dot.setAttribute('cy', Y(a[i])); cross.setAttribute('visibility', 'visible'); dot.setAttribute('visibility', 'visible');
      tip.replaceChildren(el('b', null, `${vnMonth(ms[i - 1])}: ${sR(a[i], 1)}`), el('span', 'muted', `${tx('web.lt.lg_base', nf(0).format(LT.base_n)).split(' (')[0]}: ${sR(b[i], 1)}`),
        el('div', null, tx('web.lt.tip_rule', r ? `${sigName(r)} · ${ruleShort(r)}` : tx('web.lt.tip_none'))), el('div', 'muted', `${tx('web.lt.th_trades')}: ${h.n} · ${sR(h.sumR, 1)}`));
      tip.style.display = 'block';
      const left = X(i) + 12, w = tip.offsetWidth;
      tip.style.left = (left + w > W ? X(i) - w - 12 : left) + 'px'; tip.style.top = '8px';
    });
    svg.addEventListener('pointerleave', () => { tip.style.display = 'none'; cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); });
    tip.style.whiteSpace = 'normal'; tip.style.maxWidth = '280px';
    box.replaceChildren(svg, tip);
  }

  function renderMethodLT() {
    const items = [tx('web.lt.m1'), tx('web.lt.m2'), tx('web.lt.m3'), tx('web.lt.m4', pc(LT.costs.fee, 2), pc(LT.costs.slippage, 2)), tx('web.lt.m5'), tx('web.lt.m7'), tx('web.lt.m6'),
      tx('web.lt.updated', vnTime(utcIso(LT.data.to)), LT.version)];
    $('lt-method-list').replaceChildren(...items.map((t) => el('li', null, t)));
    const lg = LT.log || {};
    const lt = lg.tat_ca || lg;
    $('lt-log').textContent = lt.n ? tx('web.lt.log_some', nf(0).format(lt.months), nf(0).format(lt.n), pc(lt.p, 0), sR(lt.sumR, 1)) : tx('web.lt.log_none');
  }
  function renderLT() {
    if (!LT) { $('lt-none').hidden = false; ['lt-sec', 'lt-bt-sec'].forEach((id) => { $(id).hidden = true; }); $('lt-method-list').replaceChildren(); return; }
    renderPlan();
    renderBacktest();
  }

  // =====================================================================================================================
  // Xem thêm: giữ đúng kỳ hạn, không cắt lỗ (LS, nghiên cứu 02/11/2026)
  // =====================================================================================================================
  const CELLS = ['moc', 'trend_tren', 'trend_duoi', 'funding_cao', 'funding_thap', 'stretch_tang_manh', 'stretch_giam_manh', 'vol_cao', 'vol_binh_thuong'];
  const COND = { trend_tren: ['trend', 'tren'], trend_duoi: ['trend', 'duoi'], funding_cao: ['funding', 'cao'], funding_thap: ['funding', 'thap'],
    stretch_tang_manh: ['stretch', 'tang_manh'], stretch_giam_manh: ['stretch', 'giam_manh'], vol_cao: ['vol', 'cao'], vol_binh_thuong: ['vol', 'binh_thuong'] };
  const STATE_TEXT = {
    trend: { tren: 'web.ls.st_trend_tren', duoi: 'web.ls.st_trend_duoi' },
    funding: { cao: 'web.ls.st_funding_cao', thap: 'web.ls.st_funding_thap', giua: 'web.ls.st_funding_giua' },
    stretch: { tang_manh: 'web.ls.st_stretch_tang_manh', giam_manh: 'web.ls.st_stretch_giam_manh', giua: 'web.ls.st_stretch_giua' },
    vol: { cao: 'web.ls.st_vol_cao', binh_thuong: 'web.ls.st_vol_binh_thuong' },
  };
  const VERDICT = { nen_long: ['web.ls.v_nen_long', 'good'], nen_short: ['web.ls.v_nen_short', 'bad'], khong: ['web.ls.v_khong', 'muted'] };
  const SIDE = { long: 'web.ls.side_long', short: 'web.ls.side_short' };
  const cellName = (c) => tx('web.ls.c_' + c);
  const hz = (unit, h) => (LS ? LS.horizons.find((x) => x.unit === unit && x.h === h) : null);
  const hsOf = (unit) => (LS ? LS.horizons.filter((x) => x.unit === unit).map((x) => x.h) : []);

  // trạng thái lúc này: cùng cách tính với perp_signal (20 nến, phân vị của 365 ngày trước, funding 24 giờ)
  function liveState(unit, H) {
    const r = view.raw[unit], th = LS.thresholds[unit], c = r.c, n = c.length, w = 20;
    const last = c[n - 1], mean = c.slice(n - w).reduce((a, b) => a + b, 0) / w;
    const lr = []; for (let i = n - w; i < n; i++) lr.push(Math.log(c[i] / c[i - 1]));
    const m = lr.reduce((a, b) => a + b, 0) / w, vol = Math.sqrt(lr.reduce((a, b) => a + (b - m) ** 2, 0) / (w - 1));
    const past = last / c[n - 1 - H] - 1, [q10, q90] = th.stretch[String(H)], [f20, f80] = th.funding;
    return {
      trend: last > mean ? 'tren' : 'duoi', vol: vol >= th.vol80 ? 'cao' : 'binh_thuong',
      stretch: past >= q90 ? 'tang_manh' : past <= q10 ? 'giam_manh' : 'giua',
      funding: r.f24 == null ? null : r.f24 >= f80 ? 'cao' : r.f24 <= f20 ? 'thap' : 'giua',
    };
  }
  const matched = (s) => ['moc', ...CELLS.slice(1).filter((c) => s[COND[c][0]] === COND[c][1])];
  function decide(cells, names) {  // = perp_signal.decide
    const out = { cells: names };
    for (const side of ['long', 'short']) {
      const cand = names.filter((c) => cells[c] && cells[c][side].n).map((c) => [cells[c][side].lb_bonf || 0, c]);
      cand.sort((a, b) => b[0] - a[0] || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0));
      const best = cand.length ? cand[0][1] : null;
      out[side] = { cell: best, s: best ? cells[best][side] : null, edge: names.filter((c) => cells[c] && cells[c][side].edge) };
    }
    const lo = out.long.edge.length > 0, sh = out.short.edge.length > 0;
    out.verdict = lo && !sh ? 'nen_long' : sh && !lo ? 'nen_short' : 'khong';
    return out;
  }

  // đòn bẩy: nội suy tuyến tính theo ngưỡng thanh lý m = 1/L − mmr trên lưới đã đăng ký
  function lev(s, L) {
    if (!(L > 1)) return { kind: 'none' };
    const m = 1 / L - LS.mmr, g = LS.grid_pct, mp = m * 100, cur = s.lev;
    if (mp < g[0]) return { kind: 'high', m };
    const at = (arr) => {
      if (mp >= g[g.length - 1]) return arr[arr.length - 1];
      let i = 0; while (g[i + 1] <= mp) i++;
      const a = (mp - g[i]) / (g[i + 1] - g[i]);
      return arr[i] + a * (arr[i + 1] - arr[i]);
    };
    const liq = at(cur.liq), win = at(cur.win), mean = at(cur.mean);
    return { kind: mp >= g[g.length - 1] ? 'low' : 'ok', m, liq, win, ret: L * mean - liq };
  }

  function fillHorizons() {
    const sel = $('ls-h'), hs = hsOf(view.unit);
    if (!hs.includes(view.h)) view.h = hs.includes(4) ? 4 : hs[0];
    sel.replaceChildren(...hs.map((h) => { const o = el('option', null, tx(view.unit === 'h' ? 'web.ls.h_opt_h' : 'web.ls.h_opt_d', h)); o.value = String(h); o.selected = h === view.h; return o; }));
    document.querySelectorAll('#ls-unit button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.u === view.unit)));
  }
  function current() {
    const H = view.h, unit = view.unit, e = hz(unit, H), now = LS.now[unit];
    if (view.raw[unit]) return { e, state: liveState(unit, H), price: view.raw[unit].price };
    return { e, state: now.states[String(H)].state, price: now.close };
  }
  function renderOld() {
    if (!LS) { $('ls-none').hidden = false; ['ls-run', 'ls-table-sec', 'ls-method'].forEach((id) => { $(id).hidden = true; }); return; }
    fillHorizons();
    const { e, state, price } = current(), names = matched(state), d = decide(e.cells, names);
    const ans = $('ls-answer'), [vk, vtone] = VERDICT[d.verdict];
    const parts = [el('p', 'kicker', tx('web.ls.state_title')), el('div', 'verdict ' + vtone, tx(vk))];
    const best = d.verdict === 'khong' ? null : d[d.verdict === 'nen_long' ? 'long' : 'short'];
    parts.push(el('p', 'muted', best ? tx('web.ls.v_edge_sub', cellName(best.edge[0]), pc(e.cells[best.edge[0]][d.verdict === 'nen_long' ? 'long' : 'short'].lb_bonf, 1)) : tx('web.ls.v_khong_sub')));
    const chips = el('div', 'chips');
    for (const k of ['trend', 'funding', 'stretch', 'vol']) chips.append(el('span', 'pill muted', state[k] == null ? tx('web.ls.st_funding_na') : tx(STATE_TEXT[k][state[k]])));
    parts.push(chips);
    for (const side of ['long', 'short']) {
      const x = d[side];
      if (!x.s) continue;
      parts.push(el('p', null, tx('web.ls.side_line', tx(SIDE[side]), pc(x.s.p, 1), pc(x.s.ci[0], 1), pc(x.s.ci[1], 1), spc(x.s.mean), spc(x.s.p10), cellName(x.cell), nf(0).format(x.s.n_eff))));
    }
    const L = parseNum($('ls-lev').value) || 1, amt = parseNum($('ls-amt').value), box = el('div', 'lev');
    box.append(el('p', 'sm', tx('web.ls.lev_title', nf(L % 1 ? 1 : 0).format(L))));
    const l0 = d.long.s ? lev(d.long.s, L) : null;
    if (!l0 || l0.kind === 'none') box.append(el('p', null, tx('web.ls.lev_none')));
    else if (l0.kind === 'high') box.append(el('p', 'bad', tx('web.ls.lev_out_high', pc(Math.max(l0.m, 0), 2))));
    else {
      box.append(el('p', null, tx('web.ls.lev_price', usd(price * (1 - l0.m)), usd(price * (1 + l0.m)), pc(l0.m, 1))));
      if (l0.kind === 'low') box.append(el('p', 'muted', tx('web.ls.lev_out_low')));
      for (const side of ['long', 'short']) {
        const x = d[side]; if (!x.s) continue;
        const r = lev(x.s, L);
        box.append(el('p', null, tx('web.ls.lev_line', tx(SIDE[side]), pc(r.liq, 1), pc(r.win, 1), spc(r.ret, 1)) + (amt ? tx('web.ls.lev_amt', usd(amt), susd(amt * r.ret)) : '')));
      }
    }
    box.append(el('p', 'muted', tx('web.ls.lev_warn')));
    parts.push(box);
    ans.replaceChildren(...parts);
    renderTable(e, names);
  }
  function renderTable(e, names) {
    const lab = tx(view.unit === 'h' ? 'web.ls.h_opt_h' : 'web.ls.h_opt_d', view.h);
    $('ls-table-title').textContent = tx('web.ls.table_title', lab);
    $('ls-table-lead').textContent = tx('web.ls.table_lead', vnDate(e.from), vnDate(e.to), nf(0).format(e.n), vnDate(e.split), pc(LS.costs.fee, 2), pc(LS.costs.slippage, 2));
    const head = el('tr');
    for (const k of ['th_cell', 'th_now', 'th_long_p', 'th_long_m', 'th_short_p', 'th_short_m', 'th_n', 'th_verdict']) head.append(el('th', null, tx('web.ls.' + k)));
    const thead = el('thead'), tbody = el('tbody'); thead.append(head);
    for (const c of CELLS) {
      const v = e.cells[c]; if (!v) continue;
      const tr = el('tr'), on = names.includes(c);
      tr.append(el('td', null, cellName(c)), el('td', on ? 'good' : 'muted', on ? tx('web.ls.now_mark') : ''));
      for (const side of ['long', 'short']) {
        const s = v[side];
        const p = el('td', null, pc(s.p, 1)); p.title = `${pc(s.ci[0], 1)}–${pc(s.ci[1], 1)}`;
        tr.append(p, el('td', s.mean > 0 ? 'good' : 'bad', spc(s.mean)));
      }
      tr.append(el('td', null, nf(0).format(v.long.n_eff)));
      const verdict = v.long.edge ? tx('web.ls.cell_edge_long') : v.short.edge ? tx('web.ls.cell_edge_short') : tx('web.ls.cell_none');
      tr.append(el('td', v.long.edge || v.short.edge ? 'good' : 'muted', verdict));
      tbody.append(tr);
    }
    $('t-ls').replaceChildren(thead, tbody);
    const notes = [], all = [];
    for (const c of CELLS) for (const side of ['long', 'short']) if (e.cells[c] && e.cells[c][side].n) all.push([e.cells[c][side].p, c, side]);
    all.sort((a, b) => b[0] - a[0]);
    if (all.length) {
      const [, c, side] = all[0], s = e.cells[c][side];
      notes.push(tx('web.ls.note_best', tx(SIDE[side]), cellName(c), pc(s.p, 1), pc(s.ci[0], 1), pc(s.ci[1], 1), nf(0).format(s.n_eff), nf(0).format(LS.tests), pc(s.lb_bonf, 1)));
      notes.push(tx('web.ls.note_halves', pc(s.halves[0].p, 1), pc(s.halves[1].p, 1)));
    }
    notes.push(tx('web.ls.note_cost', pc(2 * (LS.costs.fee + LS.costs.slippage), 2)));
    $('ls-notes').replaceChildren(...notes.map((t) => el('li', null, t)));
  }
  function renderMethodOld() {
    if (!LS) return;
    const edges = LS.horizons.reduce((a, h) => a + Object.values(h.cells).reduce((b, v) => b + (v.long.edge ? 1 : 0) + (v.short.edge ? 1 : 0), 0), 0);
    const items = [tx('web.ls.m1'), tx('web.ls.m2', pc(LS.costs.fee, 2), pc(LS.costs.slippage, 2)), tx('web.ls.m3'),
      tx('web.ls.m4', nf(0).format(LS.tests), nf(2).format(LS.z_bonf), nf(0).format(edges)), tx('web.ls.m5'), tx('web.ls.m6'),
      tx('web.ls.updated', vnTime(utcIso(LS.now.h.anchor)), LS.version)];
    $('ls-method-list').replaceChildren(...items.map((t) => el('li', null, t)));
    const lg = LS.log || {}, v = lg.versions && lg.versions[LS.version];
    $('ls-log').textContent = v && v.matured ? tx('web.ls.log_some', nf(0).format(v.matured), pc(v.long_win, 0), pc(v.short_win, 0), nf(0).format(v.called), nf(0).format(v.called_hit)) : tx('web.ls.log_none');
  }

  function render() {
    renderLT();
    renderOld();
    if (!LT) $('ls-status').textContent = '';
  }

  // ----- chuyển chế độ: chỉ thêm / bỏ lớp body.ls-view, không gọi gì của bên mua / bán -----
  const KEY = 'btc-bot3-view';
  function setView(on) {
    document.body.classList.toggle('ls-view', on);
    $('mode-ls').setAttribute('aria-pressed', String(on));
    if (on) { $('mode-buy').setAttribute('aria-pressed', 'false'); $('mode-sell').setAttribute('aria-pressed', 'false'); render(); }
    try { if (on) localStorage.setItem(KEY, 'ls'); else localStorage.removeItem(KEY); } catch (e) { /* bỏ qua */ }
  }
  $('mode-ls').addEventListener('click', () => setView(true));
  for (const id of ['mode-buy', 'mode-sell']) $(id).addEventListener('click', () => setView(false));
  document.querySelectorAll('#ls-unit button').forEach((b) => b.addEventListener('click', () => { view.unit = b.dataset.u; renderOld(); }));
  $('ls-h').addEventListener('change', () => { view.h = Number($('ls-h').value); renderOld(); });
  for (const id of ['ls-lev', 'ls-amt']) $(id).addEventListener('input', () => { if (LT) renderPlan(); if (LS) renderOld(); });
  $('lt-hold').addEventListener('change', () => { const v = $('lt-hold').value; view.hold = v ? Number(v) : null; if (LT) renderPlan(); });
  $('ls-go').addEventListener('click', async () => {
    if (!LT && !LS) return;
    const b = $('ls-go'); b.disabled = true; $('ls-status').textContent = tx('web.ls.loading');
    try { await loadLive(); view.err = null; } catch (e) { view.raw = {}; view.err = e.message || String(e); }
    b.disabled = false; render();
  });
  if (window.ResizeObserver) {
    let w = 0;
    new ResizeObserver(() => { const x = $('lt-curve').clientWidth; if (x && x !== w) { w = x; drawCurve(); } }).observe($('lt-curve'));
  }
  // kết luận 6 tiêu chí cho nút Hold của bảng Kiểm tra điểm vào (src/pact.js, mục pa_hold): trạng thái của Daily, 1x, cho tới khi bấm Chạy
  function publish(v) { window.LS_VERDICT = v; window.dispatchEvent(new Event('ls-verdict')); }
  if (LT) {
    const s0 = tradeState(), N0 = LT.checklist.length, sc = (sd) => checks(sd, s0, 1).filter(([x]) => x).length;
    const l0 = sc('long'), h0 = sc('short');
    publish({ verdict: l0 === N0 && h0 !== N0 ? 'nen_long' : h0 === N0 && l0 !== N0 ? 'nen_short' : 'khong', long: l0, short: h0, N: N0, live: false });
  }
  if (LT) renderMethodLT();
  renderMethodOld();
  let start = false;
  try { start = localStorage.getItem(KEY) === 'ls'; } catch (e) { /* bỏ qua */ }
  if (start) setView(true);
})();
// ===== LONG/SHORT END =====
