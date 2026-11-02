// ===== LONG/SHORT START =====
// Chế độ riêng cho hợp đồng vĩnh cửu BTCUSDT (số liệu: data/results/perp.json từ bot/models/perp_signal.py, build.py nhúng vào).
// Không đọc, không ghi gì của bên mua / bên bán (KN, st, các thẻ): bấm "Long/Short" chỉ thêm lớp body.ls-view để CSS ẩn
// các thẻ mua / bán; bấm "Bên mua" / "Bên bán" thì bỏ lớp đó. Trạng thái thị trường tính lúc bấm Chạy từ fapi.binance.com,
// ngưỡng phân vị và bảng lịch sử lấy từ lần chạy Daily; quy tắc kết luận giống hệt perp_signal.decide.
(() => {
  const LS = /*LS_JSON*/null;
  const { tx, vnTime } = I18N;
  const $ = (id) => document.getElementById(id);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  const nf = (d) => new Intl.NumberFormat('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d });
  const ok = (x) => x != null && isFinite(x);
  const pc = (x, d = 0) => (ok(x) ? nf(d).format(x * 100) + '%' : '—');
  const spc = (x, d = 2) => (ok(x) ? (x > 0 ? '+' : x < 0 ? '−' : '') + nf(d).format(Math.abs(x * 100)) + '%' : '—');
  const usd = (x) => (ok(x) ? nf(0).format(x) + ' $' : '—');
  const susd = (x) => (ok(x) ? (x > 0 ? '+' : x < 0 ? '−' : '') + nf(2).format(Math.abs(x)) + ' $' : '—');
  const vnDate = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`;
  const utcIso = (s) => s.replace(' ', 'T') + 'Z';  // '2026-11-02 09:00' (UTC) → ISO
  const parseNum = (v) => {  // như parseAmount của src/ui.js: "1.5" = 1,5; "1.000" = 1000
    const t = String(v || '').replace(/\s/g, ''), m = t.match(/^(.*?)[.,](\d{1,2})$/), int = (m ? m[1] : t).replace(/[.,]/g, ''), dec = m ? m[2] : '';
    const x = /^\d*$/.test(int) && (int || dec) ? Number((int || '0') + (dec ? '.' + dec : '')) : NaN;
    return isFinite(x) && x > 0 ? x : null;
  };
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

  const view = { unit: 'h', h: 4, raw: {}, err: null };
  const hz = (unit, h) => (LS ? LS.horizons.find((x) => x.unit === unit && x.h === h) : null);
  const hsOf = (unit) => (LS ? LS.horizons.filter((x) => x.unit === unit).map((x) => x.h) : []);

  // ----- trạng thái lúc này: cùng cách tính với perp_signal (20 nến, phân vị của 365 ngày trước, funding 24 giờ) -----
  async function loadLive(unit) {
    const k = await getJSON(`${FAPI}klines?symbol=BTCUSDT&interval=${unit === 'h' ? '1h' : '1d'}&limit=40`);
    const now = Date.now(), closed = k.filter((r) => Number(r[6]) < now);
    if (closed.length < 32) throw new Error('klines');
    const t = Number(closed[closed.length - 1][6]) + 1;  // giờ đóng của nến cuối đã đóng
    const fr = await getJSON(`${FAPI}fundingRate?symbol=BTCUSDT&limit=12`);
    const f = fr.map((x) => [Math.floor(Number(x.fundingTime) / 3600000) * 3600000, Number(x.fundingRate)]).filter(([ft]) => ft > t - 86400000 && ft <= t);
    view.raw[unit] = { c: closed.map((r) => Number(r[4])), t, price: Number(k[k.length - 1][4]), f24: f.length ? f.reduce((a, [, v]) => a + v, 0) / f.length : null };
  }
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

  // ----- đòn bẩy: nội suy tuyến tính theo ngưỡng thanh lý m = 1/L − mmr trên lưới đã đăng ký -----
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

  // ----- vẽ -----
  function fillHorizons() {
    const sel = $('ls-h'), hs = hsOf(view.unit);
    if (!hs.includes(view.h)) view.h = hs.includes(4) ? 4 : hs[0];
    sel.replaceChildren(...hs.map((h) => { const o = el('option', null, tx(view.unit === 'h' ? 'web.ls.h_opt_h' : 'web.ls.h_opt_d', h)); o.value = String(h); o.selected = h === view.h; return o; }));
    document.querySelectorAll('#ls-unit button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.u === view.unit)));
  }
  function current() {
    const H = view.h, unit = view.unit, e = hz(unit, H), now = LS.now[unit];
    if (view.raw[unit]) return { e, state: liveState(unit, H), price: view.raw[unit].price, at: view.raw[unit].t, live: true };
    return { e, state: now.states[String(H)].state, price: now.close, at: Date.parse(utcIso(now.anchor)), live: false };
  }
  function render() {
    if (!LS) { $('ls-none').hidden = false; ['ls-run', 'ls-table-sec', 'ls-method'].forEach((id) => { $(id).hidden = true; }); return; }
    fillHorizons();
    const { e, state, price, at, live } = current(), names = matched(state), d = decide(e.cells, names);
    const ans = $('ls-answer'), [vk, tone] = VERDICT[d.verdict];
    const parts = [el('p', 'kicker', tx('web.ls.state_title')), el('div', 'verdict ' + tone, tx(vk))];
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
    $('ls-status').textContent = view.err ? tx('web.ls.live_fail', view.err, vnTime(utcIso(LS.now[view.unit].anchor)))
      : live ? tx('web.ls.live_ok', vnTime(new Date(at).toISOString()), usd(price)) : tx('web.ls.first', vnTime(utcIso(LS.now[view.unit].anchor)));
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
  function renderMethod() {
    if (!LS) return;
    const edges = LS.horizons.reduce((a, h) => a + Object.values(h.cells).reduce((b, v) => b + (v.long.edge ? 1 : 0) + (v.short.edge ? 1 : 0), 0), 0);
    const items = [tx('web.ls.m1'), tx('web.ls.m2', pc(LS.costs.fee, 2), pc(LS.costs.slippage, 2)), tx('web.ls.m3'),
      tx('web.ls.m4', nf(0).format(LS.tests), nf(2).format(LS.z_bonf), nf(0).format(edges)), tx('web.ls.m5'), tx('web.ls.m6'),
      tx('web.ls.updated', vnTime(utcIso(LS.now.h.anchor)), LS.version)];
    $('ls-method-list').replaceChildren(...items.map((t) => el('li', null, t)));
    const lg = LS.log || {}, v = lg.versions && lg.versions[LS.version];
    $('ls-log').textContent = v && v.matured ? tx('web.ls.log_some', nf(0).format(v.matured), pc(v.long_win, 0), pc(v.short_win, 0), nf(0).format(v.called), nf(0).format(v.called_hit)) : tx('web.ls.log_none');
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
  document.querySelectorAll('#ls-unit button').forEach((b) => b.addEventListener('click', () => { view.unit = b.dataset.u; render(); }));
  $('ls-h').addEventListener('change', () => { view.h = Number($('ls-h').value); render(); });
  for (const id of ['ls-lev', 'ls-amt']) $(id).addEventListener('input', () => { if (LS) render(); });
  $('ls-go').addEventListener('click', async () => {
    if (!LS) return;
    const b = $('ls-go'); b.disabled = true; $('ls-status').textContent = tx('web.ls.loading');
    try { await loadLive(view.unit); view.err = null; } catch (e) { delete view.raw[view.unit]; view.err = e.message || String(e); }
    b.disabled = false; render();
  });
  renderMethod();
  let start = false;
  try { start = localStorage.getItem(KEY) === 'ls'; } catch (e) { /* bỏ qua */ }
  if (start) setView(true);
})();
// ===== LONG/SHORT END =====
