// ===== PRICE ACTION START =====
// Bảng "Kiểm tra điểm vào" trong chế độ Price action (#pact-sec, khu #pa-app của src/pa.js). build.py nhúng PACT = data/results/pa.json (bot/models/pa_sheet.py):
// hành động giá ở nến ngày Bitstamp cuối đã đóng (tiêu chí của mục price_action, đỉnh / đáy cục bộ đã biết, ATR, cấu trúc)
// và bảng đếm số lần giá chạm mức lên / xuống trước (theo ATR, mọi ngày từ 2016). Hàm check dưới đây phải giống hệt
// pa_sheet.check (có test). Không phát tín hiệu hướng: price action chưa có lợi thế (0/48), kết luận Long/Short không đổi.
(() => {
  const PACT = /*PACT_JSON*/null;
  const { tx, vnTime } = I18N;
  const $ = (id) => document.getElementById(id);
  if (!$('pact-sec')) return;
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  const nf = (d) => new Intl.NumberFormat('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d });
  const n1 = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });
  const ok = (x) => x != null && isFinite(x);
  const pc = (x, d = 0) => (ok(x) ? nf(d).format(x * 100) + '%' : '—');
  const usd = (x) => (ok(x) ? nf(0).format(x) + ' $' : '—');
  const spc = (x, d = 1) => (ok(x) ? (x > 0 ? '+' : x < 0 ? '−' : '') + nf(d).format(Math.abs(x * 100)) + '%' : '—');
  const sR = (x) => (ok(x) ? (x > 0.005 ? '+' : x < -0.005 ? '−' : '') + nf(2).format(Math.abs(x)) + 'R' : '—');
  const vnDate = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`;
  const parseNum = (v) => {  // như ls.js: "1.5" = 1,5; "1.000" = 1000
    const t = String(v || '').replace(/\s/g, ''), m = t.match(/^(.*?)[.,](\d{1,2})$/), int = (m ? m[1] : t).replace(/[.,]/g, ''), dec = m ? m[2] : '';
    const x = /^\d*$/.test(int) && (int || dec) ? Number((int || '0') + (dec ? '.' + dec : '')) : NaN;
    return isFinite(x) && x > 0 ? x : null;
  };
  // ----- đồ thị nến dùng chung (bảng này và src/pa.js): nến, vùng tô màu, đường giá có nhãn ở lề phải, rê chuột xem giá -----
  const NS = 'http://www.w3.org/2000/svg';
  const sv = (t, at) => { const e = document.createElementNS(NS, t); for (const k in at) e.setAttribute(k, at[k]); return e; };
  const n0 = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });
  function drawChart(box, cand, o = {}) {
    const W = box.clientWidth;
    if (!W || !cand.length) return;
    const H = o.height || 300, m = { l: 6, r: 128, t: 12, b: 24 }, n = cand.length, cw = (W - m.l - m.r) / n;
    const lines = (o.lines || []).filter((x) => ok(x.y)), zones = (o.zones || []).filter((z) => ok(z.lo) && ok(z.hi));
    const vals = [];
    for (const k of cand) { if (ok(k.h)) vals.push(k.h); if (ok(k.l)) vals.push(k.l); }
    for (const x of lines) vals.push(x.y);
    for (const z of zones) vals.push(z.lo, z.hi);
    let lo = Math.min(...vals), hi = Math.max(...vals);
    const pad = (hi - lo) * 0.04 || hi * 0.01; lo -= pad; hi += pad;
    const X = (i) => m.l + (i + 0.5) * cw, Y = (v) => m.t + (hi - v) / (hi - lo) * (H - m.t - m.b);
    const svg = sv('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, class: 'pa-svg', role: 'img', 'aria-label': o.label || '' });
    const raw = (hi - lo) / 5, mag = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 2.5, 5, 10].map((x) => x * mag).find((x) => x >= raw);
    for (let v = Math.ceil(lo / step) * step; v < hi; v += step) {
      svg.append(sv('line', { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: 'grid' }));
      const t = sv('text', { x: m.l + 4, y: Y(v) - 3, class: 'ax' }); t.textContent = n0.format(v); svg.append(t);
    }
    for (const z of zones) svg.append(sv('rect', { x: m.l, width: W - m.l - m.r, y: Y(z.hi), height: Math.max(1, Y(z.lo) - Y(z.hi)), class: 'zn ' + z.cls }));
    const bw = Math.max(1, Math.min(9, cw * 0.66));
    cand.forEach((k, i) => {
      if (!ok(k.c) || !ok(k.h) || !ok(k.l)) return;
      const op = ok(k.o) ? k.o : k.c, cls = k.c >= op ? 'cu' : 'cd';
      svg.append(sv('line', { x1: X(i), x2: X(i), y1: Y(k.h), y2: Y(k.l), class: 'wk ' + cls }));
      svg.append(sv('rect', { x: X(i) - bw / 2, width: bw, y: Y(Math.max(op, k.c)), height: Math.max(1, Math.abs(Y(op) - Y(k.c))), class: cls }));
    });
    const labs = lines.map((x) => ({ ...x, yy: Y(x.y) })).sort((a, b) => a.yy - b.yy);
    labs.forEach((x, i) => { x.ly = i ? Math.max(x.yy, labs[i - 1].ly + 18) : Math.max(x.yy, m.t + 8); });
    const over = labs.length ? labs[labs.length - 1].ly - (H - m.b - 2) : 0;
    if (over > 0) labs.forEach((x) => { x.ly -= over; });
    for (const x of labs) {
      svg.append(sv('line', { x1: m.l, x2: W - m.r, y1: x.yy, y2: x.yy, class: 'pl ' + x.cls }));
      if (!x.label) continue;
      const g = sv('g', { class: 'pt ' + x.cls });
      g.append(sv('rect', { x: W - m.r + 4, y: x.ly - 8, width: m.r - 6, height: 16, rx: 6 }));
      const t = sv('text', { x: W - m.r + 9, y: x.ly + 4 }); t.textContent = `${x.label} ${n0.format(x.y)}`; g.append(t);
      svg.append(g);
    }
    const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor((W - m.r) / 80))));
    cand.forEach((k, i) => {   // nhãn ngày / giờ, bỏ nhãn sát hai mép để không bị cắt
      if (i % every || !k.d || X(i) < 26 || X(i) > W - m.r - 26) return;
      const t = sv('text', { x: X(i), y: H - 7, 'text-anchor': 'middle', class: 'ax' }); t.textContent = k.d; svg.append(t);
    });
    const cross = sv('line', { y1: m.t, y2: H - m.b, class: 'cross', visibility: 'hidden' });
    svg.append(cross);
    const tip = el('div', 'tip');
    svg.addEventListener('pointermove', (ev) => {
      const r = svg.getBoundingClientRect(), i = Math.max(0, Math.min(n - 1, Math.floor((ev.clientX - r.left - m.l) / cw))), k = cand[i];
      cross.setAttribute('x1', X(i)); cross.setAttribute('x2', X(i)); cross.setAttribute('visibility', 'visible');
      tip.textContent = o.tip ? o.tip(k) : `${k.full || k.d}: ${n0.format(k.c)}`;
      tip.style.display = 'block';
      const left = X(i) + 12, w = tip.offsetWidth;
      tip.style.left = (left + w > W - 4 ? Math.max(4, X(i) - w - 12) : left) + 'px'; tip.style.top = '8px';
    });
    svg.addEventListener('pointerleave', () => { tip.style.display = 'none'; cross.setAttribute('visibility', 'hidden'); });
    box.replaceChildren(svg, tip);
  }
  window.PA_CHART = drawChart;

  if (!PACT) { $('pact-none').hidden = false; $('pact-body').hidden = true; return; }
  const ST = PACT.state, A = ST.atr, W = ST.w, KS = [1, 3, 7, 30];
  const view = { side: 'long' };
  const sideName = (s) => tx(s === 'long' ? 'web.pact.side_long' : 'web.pact.side_short');
  const CAND = (PACT.candles || []).map(([d, o, h, l, c]) => ({ d: `${d.slice(8, 10)}/${d.slice(5, 7)}`, full: vnDate(d), o, h, l, c }));
  const tipOf = (k) => tx('web.pact.ch_tip', k.full, usd(k.o), usd(k.h), usd(k.l), usd(k.c));
  // ----- Long / Short / Hold (mục pa_hold): chỉ đề xuất vào lệnh khi Long/Short đủ 6/6 và hành động giá rõ cùng hướng -----
  const UP = ['ho_tro', 'cau_truc_tang', 'pin_bar_ho_tro', 'inside_bar_ho_tro', 'pha_vo_gia_duoi'];
  const DN = ['khang_cu', 'cau_truc_giam', 'pin_bar_khang_cu', 'inside_bar_khang_cu', 'pha_vo_gia_tren'];
  function clarity() {
    const u = ST.active.filter((c) => UP.includes(c)), d = ST.active.filter((c) => DN.includes(c));
    return { kind: u.length && !d.length ? 'up' : d.length && !u.length ? 'down' : u.length ? 'mixed' : 'none', names: [...u, ...d] };
  }
  function decision() {
    const v = window.LS_VERDICT || null, c = clarity();
    const action = v && v.verdict === 'nen_long' && c.kind === 'up' ? 'long' : v && v.verdict === 'nen_short' && c.kind === 'down' ? 'short' : 'hold';
    return { action, v, c };
  }
  const holdName = (H) => tx(H === 7 ? 'web.pact.hold_7' : 'web.pact.hold_30');

  // ----- giống hệt bot/models/pa_sheet.py -----
  function idx(x) {
    const i = Math.floor(x / PACT.step + 0.5);
    return [Math.min(PACT.levels, Math.max(1, i)) - 1, !(i >= 1 && i <= PACT.levels)];
  }
  function wilson(p, n, z = 1.96) {
    if (!(n > 0)) return [NaN, NaN];
    const c = p + z * z / (2 * n), m = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n));
    return [(c - m) / (1 + z * z / n), (c + m) / (1 + z * z / n)];
  }
  function suggest(side, E) {
    const lows = ST.lows.map((x) => x.price).filter((p) => p < E), highs = ST.highs.map((x) => x.price).filter((p) => p > E);
    const S = lows.length ? Math.max(...lows) : null, R = highs.length ? Math.min(...highs) : null;
    let SL, TP;
    if (side === 'long') {
      SL = S != null ? S - W : E - A;
      TP = R != null && R - W > E ? R - W : E + 2 * (E - SL);
    } else {
      SL = R != null ? R + W : E + A;
      TP = S != null && S + W < E ? S + W : E - 2 * (SL - E);
    }
    return { S, R, SL, TP };
  }
  function check(side, E, SL, TP, H) {
    const sg = suggest(side, E);
    SL = SL == null ? sg.SL : SL; TP = TP == null ? sg.TP : TP;
    const long = side === 'long';
    if (!(long ? SL < E && E < TP : TP < E && E < SL)) return { valid: false, ...sg, SL, TP };
    const t = PACT.touch[String(H)], risk = Math.abs(E - SL), reward = Math.abs(TP - E);
    const [iu, cu] = idx((long ? reward : risk) / A), [id, cd] = idx((long ? risk : reward) / A);
    const up = t.up[iu][id], down = t.down[iu][id], same = t.same[iu][id], N = t.N;
    const [pt, ps] = long ? [up, down + same] : [down, up + same];
    const Pt = pt / N, Ps = ps / N, p = Pt + Ps ? Pt / (Pt + Ps) : NaN, nEff = N * (Pt + Ps) / H;
    const ci = wilson(p, nEff), q = risk / (risk + reward);
    return { valid: true, ...sg, SL, TP, risk: risk / E, reward: reward / E, risk_atr: risk / A, reward_atr: reward / A, rr: reward / risk, q,
      Pt, Ps, Pn: Math.max(0, 1 - Pt - Ps), p, ci, n_eff: nEff, exp_r: p * reward / risk - (1 - p), verdict: ci[0] > q ? 'loi' : ci[1] < q ? 'bat_loi' : 'ngang', clamped: cu || cd };
  }
  window.BOT_PACT = { check, suggest };
  const vTone = (v) => (v === 'loi' ? 'good' : v === 'bat_loi' ? 'bad' : 'mid');

  function kpi(cls, lab, val, sub) {
    const k = el('div', 'kpi ' + cls);
    k.append(el('div', 'lab', lab), el('div', 'val', val), el('div', 'sub', sub));
    return k;
  }
  const research = (crit, k) => (PACT.research ? PACT.research.rows.find((r) => r.crit === crit && r.k === k) : null);

  function renderNow() {
    const R0 = PACT.research;
    $('pact-lead').textContent = tx('web.pact.lead', PACT.since.slice(0, 4), R0 ? R0.from.slice(0, 4) : '—', R0 ? R0.to.slice(0, 4) : '—',
      R0 ? R0.counts.hon : '—', R0 ? R0.n_pairs : '—');
    const g = suggest('long', ST.close), zone = (x) => (x != null ? tx('web.pact.k_zone', usd(x - W), usd(x + W)) : tx('web.pact.k_level_none'));
    const stc = { up: 'good', down: 'bad', none: 'info' }[ST.structure];
    const kp = el('div', 'kpis');
    kp.append(kpi('info', tx('web.pact.k_close'), usd(ST.close), tx('web.pact.k_close_sub', usd(A), pc(A / ST.close, 1))),
      kpi('good', tx('web.pact.k_sup'), usd(g.S), zone(g.S)), kpi('bad', tx('web.pact.k_res'), usd(g.R), zone(g.R)),
      kpi(stc, tx('web.pact.k_struct'), tx('web.pact.st_' + ST.structure), tx('web.pact.st_' + ST.structure + '_sub')));
    const act = el('div', 'pact-act');
    act.append(el('p', 'sm', tx('web.pact.active_title')));
    if (!ST.active.length) act.append(el('p', 'muted', tx('web.pact.active_none')));
    else {
      const chips = el('div', 'chips');
      for (const c of ST.active) chips.append(el('span', 'chip on', tx('web.pact.c_' + c)));
      act.append(chips);
      for (const c of ST.active) {
        const a7 = research(c, 7), a30 = research(c, 30);
        if (a7 && a30) act.append(el('p', 'muted', tx('web.pact.active_line', tx('web.pact.c_' + c), pc(a7.hit, 0), pc(a7.base, 0), pc(a30.hit, 0), pc(a30.base, 0),
          tx('web.pact.vt_' + (a7.verdict === 'hon' || a30.verdict === 'hon' ? 'hon' : a7.verdict === 'kem' && a30.verdict === 'kem' ? 'kem' : a30.verdict)))));
      }
    }
    $('pact-now').replaceChildren(el('p', 'kicker', tx('web.pact.now_kicker', vnDate(ST.anchor))), kp, act);
  }

  const inputs = () => ({ E: parseNum($('pact-entry').value), SL: parseNum($('pact-stop').value), TP: parseNum($('pact-target').value), H: Number($('pact-hold').value) });

  function renderCheck() {
    if (view.side === 'hold') { renderHold(); return; }
    const { E, SL, TP, H } = inputs(), side = view.side, ans = $('pact-answer');
    if (!E) { ans.replaceChildren(el('p', 'warn', tx('web.pact.entry_bad'))); return; }
    const sg = suggest(side, E);
    $('pact-stop').placeholder = tx('web.pact.ph_suggest', n1.format(sg.SL));
    $('pact-target').placeholder = tx('web.pact.ph_suggest', n1.format(sg.TP));
    const r = check(side, E, SL, TP, H), parts = [];
    parts.push(el('p', 'kicker', tx('web.pact.v_kicker', sideName(side), usd(E), holdName(H))));
    const dc = decision();
    parts.push(el('p', 'muted', tx('web.pact.now_action', tx('web.pact.act_' + dc.action))));
    if (!r.valid) { parts.push(el('p', 'warn', tx(side === 'long' ? 'web.pact.invalid_long' : 'web.pact.invalid_short'))); ans.replaceChildren(...parts); return; }
    parts.push(el('div', 'pact-v ' + vTone(r.verdict), tx('web.pact.v_' + r.verdict)));
    const inS = r.S != null && E <= r.S + W, inR = r.R != null && E >= r.R - W;
    parts.push(el('p', null, inS && inR ? tx('web.pact.loc_both', usd(r.S), usd(r.R)) : inS ? tx('web.pact.loc_sup', usd(r.S - W), usd(r.S + W))
      : inR ? tx('web.pact.loc_res', usd(r.R - W), usd(r.R + W)) : tx('web.pact.loc_mid', usd(r.S), usd(r.R))));
    const good = side === 'long' ? inS && !inR : inR && !inS, bad = side === 'long' ? inR : inS;
    if (good || bad) parts.push(el('p', good ? 'muted' : 'warn', tx('web.pact.loc_' + (good ? 'good' : 'bad') + '_' + side)));
    const kp = el('div', 'kpis pact-lv');
    kp.append(kpi('bad', tx('web.pact.p_stop'), usd(r.SL), tx('web.pact.p_atr', spc((r.SL - E) / E), n1.format(r.risk_atr)) + ' · ' + tx(SL == null ? 'web.pact.p_suggested' : 'web.pact.p_yours')),
      kpi('good', tx('web.pact.p_target'), usd(r.TP), tx('web.pact.p_atr', spc((r.TP - E) / E), n1.format(r.reward_atr)) + ' · ' + tx(TP == null ? 'web.pact.p_suggested' : 'web.pact.p_yours')),
      kpi('info', tx('web.pact.p_rr'), '1 : ' + nf(2).format(r.rr), tx('web.pact.th_q') + ' ' + pc(r.q, 0)));
    parts.push(kp);
    const bar = el('div', 'pact-bar'), leg = el('div', 'pact-leg');
    for (const [c, v, k] of [['tp', r.Pt, 'web.pact.lg_tp'], ['sl', r.Ps, 'web.pact.lg_sl'], ['nn', r.Pn, 'web.pact.lg_none']]) {
      const i = el('i', c); i.style.width = (100 * Math.max(0, v)) + '%'; i.title = `${tx(k)}: ${pc(v, 0)}`; bar.append(i);
      const x = el('span'); x.append(el('i', c), document.createTextNode(`${tx(k)} ${pc(Math.max(0, v), 0)}`)); leg.append(x);
    }
    parts.push(bar, leg);
    parts.push(el('p', null, tx('web.pact.hist_line', vnDate(PACT.since), holdName(H), pc(r.Pt, 0), pc(r.Ps, 0), pc(r.Pn, 0))));
    parts.push(el('p', null, tx('web.pact.p_line', pc(r.p, 0), pc(r.ci[0], 0), pc(r.ci[1], 0), nf(0).format(r.n_eff), pc(r.q, 0), sR(r.exp_r))));
    if (r.clamped) parts.push(el('p', 'warn', tx('web.pact.clamped')));
    const b = PACT.base[String(H)];
    parts.push(el('p', 'muted', tx('web.pact.base_line', vnDate(PACT.since), holdName(H), tx(side === 'long' ? 'web.pact.base_up' : 'web.pact.base_down'),
      pc(side === 'long' ? b.up : b.down, 0))));
    parts.push(el('p', 'muted', tx('web.pact.caveat')));
    const box = el('div', 'pact-chart');
    parts.push(el('p', 'sm', tx('web.pact.ch_title', CAND.length)), box);
    ans.replaceChildren(...parts);
    const zones = [], lines = [{ y: E, cls: 'e', label: tx('web.pact.ch_e') }, { y: r.SL, cls: 'sl', label: tx('web.pact.ch_sl') }, { y: r.TP, cls: 'tp', label: tx('web.pact.ch_tp') }];
    if (r.S != null) { zones.push({ lo: r.S - W, hi: r.S + W, cls: 's' }); lines.push({ y: r.S, cls: 's', label: tx('web.pact.ch_s') }); }
    if (r.R != null) { zones.push({ lo: r.R - W, hi: r.R + W, cls: 'r' }); lines.push({ y: r.R, cls: 'r', label: tx('web.pact.ch_r') }); }
    view.chart = [box, { lines, zones, tip: tipOf }];
    drawChart(box, CAND, view.chart[1]);
  }

  // ----- Hold: đề xuất lúc này, từng lý do, và chờ gì ở mức giá nào -----
  const li = (good, text) => el('li', good ? 'ok' : null, text);
  function waitCard(side, L) {
    const long = side === 'long', c = el('div', 'pact-wcard ' + side);
    c.append(el('b', null, tx(long ? 'web.pact.wait_long' : 'web.pact.wait_short')));
    if (L == null) { c.append(el('p', 'muted', tx(long ? 'web.pact.wait_none_s' : 'web.pact.wait_none_r'))); return c; }
    c.append(el('div', 'lvl', tx(long ? 'web.pact.wait_lvl_s' : 'web.pact.wait_lvl_r', usd(L), spc(L / ST.close - 1), usd(L - W), usd(L + W))));
    const items = long
      ? [['ho_tro', tx('web.pact.w_hold_s', usd(L - W), usd(L + W), usd(L))], ['pha_vo_gia_duoi', tx('web.pact.w_fake_s', usd(L - W), usd(L))], ['pin_bar_ho_tro', tx('web.pact.w_pin_s', usd(L + W), usd(L))]]
      : [['khang_cu', tx('web.pact.w_hold_r', usd(L - W), usd(L + W), usd(L))], ['pha_vo_gia_tren', tx('web.pact.w_fake_r', usd(L + W), usd(L))], ['pin_bar_khang_cu', tx('web.pact.w_pin_r', usd(L - W), usd(L))]];
    const ol = el('ol');
    for (const [crit, text] of items) {
      const x = el('li', null, text), a7 = research(crit, 7), a30 = research(crit, 30);
      if (a7 && a30) x.append(el('span', 'sub', tx('web.pact.w_hist', pc(a7.hit, 0), pc(a7.base, 0), pc(a30.hit, 0), pc(a30.base, 0))));
      ol.append(x);
    }
    c.append(ol);
    return c;
  }
  function renderHold() {
    const ans = $('pact-answer'), d = decision(), g = suggest('long', ST.close), R0 = PACT.research, parts = [];
    parts.push(el('p', 'kicker', tx('web.pact.hold_kicker', vnDate(ST.anchor))));
    parts.push(el('div', 'pact-v ' + (d.action === 'hold' ? 'mid' : d.action === 'long' ? 'good' : 'bad'), tx('web.pact.hold_v_' + d.action)));
    const ul = el('ul', 'pact-why'), names = d.c.names.map((c) => tx('web.pact.c_' + c)).join(', ');
    ul.append(li(!!d.v && d.v.verdict !== 'khong', d.v ? tx('web.pact.why_ls', d.v.long, d.v.N, d.v.short) : tx('web.pact.why_ls_none')),
      li(d.c.kind === 'up' || d.c.kind === 'down', tx('web.pact.why_pa_' + d.c.kind, names)));
    if (R0) ul.append(li(R0.counts.hon > 0, tx('web.pact.why_test', R0.counts.hon, R0.n_pairs)));
    parts.push(ul);
    const cards = el('div', 'pact-wait');
    cards.append(waitCard('long', g.S), waitCard('short', g.R));
    parts.push(cards, el('p', null, tx('web.pact.hold_then')), el('p', 'muted', tx('web.pact.hold_free')), el('p', 'warn', tx('web.pact.hold_99')));
    const box = el('div', 'pact-chart');
    parts.push(el('p', 'sm', tx('web.pact.ch_title', CAND.length)), box);
    ans.replaceChildren(...parts);
    const zones = [], lines = [{ y: ST.close, cls: 'p', label: tx('web.pact.ch_now') }];
    if (g.S != null) { zones.push({ lo: g.S - W, hi: g.S + W, cls: 's' }); lines.push({ y: g.S, cls: 's', label: tx('web.pact.ch_s') }); }
    if (g.R != null) { zones.push({ lo: g.R - W, hi: g.R + W, cls: 'r' }); lines.push({ y: g.R, cls: 'r', label: tx('web.pact.ch_r') }); }
    view.chart = [box, { lines, zones, tip: tipOf }];
    drawChart(box, CAND, view.chart[1]);
  }

  function renderTrade() {
    $('pact-trade').hidden = view.side === 'hold';
    if (view.side === 'hold') return;
    const H = Number($('pact-hold').value), side = view.side, E = ST.close, g = side === 'long' ? 1 : -1;
    $('pact-trade-lead').textContent = tx('web.pact.trade_lead', sideName(side), holdName(H));
    const head = el('tr');
    for (const k of ['th_stop', 'th_target', 'th_p', 'th_q', 'th_exp', 'th_verdict']) head.append(el('th', null, tx('web.pact.' + k)));
    const thead = el('thead'), tbody = el('tbody'); thead.append(head);
    for (const k of [1, 2]) for (const m of [0.5, 1, 1.5, 2, 3]) {
      const r = check(side, E, E - g * k * A, E + g * m * k * A, H), tr = el('tr');
      tr.append(el('td', null, tx('web.pact.atr_val', n1.format(k))), el('td', null, tx('web.pact.tgt_val', n1.format(m * k), n1.format(m))),
        el('td', 'r', `${pc(r.p, 0)} (${pc(r.ci[0], 0)}–${pc(r.ci[1], 0)})`), el('td', 'r', pc(r.q, 0)),
        el('td', 'r ' + (r.exp_r > 0 ? 'good' : r.exp_r < 0 ? 'bad' : 'muted'), sR(r.exp_r)), el('td', vTone(r.verdict), tx('web.pact.vs_' + r.verdict)));
      tbody.append(tr);
    }
    $('t-pact-trade').replaceChildren(thead, tbody);
  }

  function renderTest() {
    const R0 = PACT.research;
    if (!R0) { $('pact-test').hidden = true; return; }
    $('pact-test-lead').textContent = tx('web.pact.test_lead', R0.counts.hon, R0.n_pairs, R0.counts.chua, R0.counts.it_dot);
    const head = el('tr');
    head.append(el('th', null, tx('web.pact.th_crit')));
    for (const k of KS) head.append(el('th', null, tx('web.pact.th_k', k)));
    const thead = el('thead'), tbody = el('tbody'); thead.append(head);
    const crits = [...new Set(R0.rows.map((r) => r.crit))];
    for (const c of crits) {
      const tr = el('tr');
      tr.append(el('td', null, `${tx('web.pact.c_' + c)} (${tx(research(c, KS[0]).dir > 0 ? 'web.pact.dir_up' : 'web.pact.dir_down')})`));
      for (const k of KS) {
        const r = research(c, k), td = el('td', 'r ' + (r.verdict === 'hon' ? 'good' : r.verdict === 'kem' ? 'bad' : 'muted'),
          tx('web.pact.cell', pc(r.hit, 0), pc(r.base, 0)) + (r.verdict === 'it_dot' ? tx('web.pact.few') : ''));
        td.title = tx('web.pact.vt_' + r.verdict);
        tr.append(td);
      }
      tbody.append(tr);
    }
    $('t-pact-test').replaceChildren(thead, tbody);
  }

  function renderAll() { renderCheck(); renderTrade(); }
  function setSide(s) {
    view.side = s;
    $('pact-box').classList.toggle('hold', s === 'hold');
    document.querySelectorAll('#pact-side button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.s === s)));
  }
  function reset() {
    $('pact-entry').value = nf(0).format(ST.close); $('pact-stop').value = ''; $('pact-target').value = '';
  }
  document.querySelectorAll('#pact-side button').forEach((b) => b.addEventListener('click', () => {
    setSide(b.dataset.s); $('pact-stop').value = ''; $('pact-target').value = ''; renderAll();
  }));
  for (const id of ['pact-entry', 'pact-stop', 'pact-target']) $(id).addEventListener('input', renderCheck);
  $('pact-hold').addEventListener('change', renderAll);
  $('pact-reset').addEventListener('click', () => { reset(); renderAll(); });
  $('pact-plan').addEventListener('click', () => {
    const p = window.LT_PLAN;
    if (!p) { $('pact-answer').replaceChildren(el('p', 'warn', tx('web.pact.plan_none'))); return; }
    setSide(p.side);
    $('pact-entry').value = n1.format(p.E); $('pact-stop').value = n1.format(p.SL); $('pact-target').value = n1.format(p.TP);
    renderAll();
  });
  $('pact-updated').textContent = tx('web.pact.updated', vnTime(PACT.made));
  $('pact-why-list').replaceChildren(...['why_1', 'why_2', 'why_3', 'why_4'].map((k) => el('li', null, tx('web.pact.' + k))));
  window.addEventListener('ls-verdict', () => renderCheck());
  if (window.ResizeObserver) {
    let w = 0;
    new ResizeObserver(() => { const x = $('pact-answer').clientWidth; if (x && x !== w) { w = x; if (view.chart) drawChart(view.chart[0], CAND, view.chart[1]); } }).observe($('pact-answer'));
  }
  reset();
  renderNow();
  renderAll();
  renderTest();
})();
// ===== PRICE ACTION END =====
