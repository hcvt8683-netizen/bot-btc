(() => {
  const { tx, vnTime } = I18N;
  const KN = /*KN_JSON*/null; // weekly recommendation from the daily job (data/recommendation.json), embedded by build.py
  const { IND, FAMILIES } = BOT;
  const { HZ, SELL_HZ, BUY_Z, SELL_Z, PRESETS, OPTIONS, zoneOf } = B3;
  const $ = (id) => document.getElementById(id);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  const nf = (d) => new Intl.NumberFormat('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d });
  const usd = (x) => (x == null || !isFinite(x) ? '—' : nf(0).format(x) + ' $');
  const pc = (x, d = 0) => (x == null || !isFinite(x) ? '—' : nf(d).format(x * 100) + '%');
  const spc = (x, d = 0) => (x == null || !isFinite(x) ? '—' : (x > 0 ? '+' : x < 0 ? '−' : '') + nf(d).format(Math.abs(x * 100)) + '%');
  const fmtDate = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`;
  const nameOf = (id) => IND.find((d) => d.id === id).ten;
  const tick = () => new Promise((r) => setTimeout(r, 0));
  const URLS = {
    fng: 'https://api.alternative.me/fng/?limit=0&format=json',
    cm: 'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD,CapMrktCurUSD,CapMVRVCur,IssTotUSD&start_time=2010-07-18&page_size=10000&ignore_forbidden_errors=true&ignore_unsupported_errors=true',
    live: ['https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', 'https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT'],
    gecko: 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
    kl: ['https://api.binance.com/api/v3/klines', 'https://data-api.binance.vision/api/v3/klines'],
  };
  const LOCAL = location.protocol.startsWith('http') && ['localhost', '127.0.0.1'].includes(location.hostname);
  const cacheHits = [];
  async function getJSON(url, timeout = 60000) {
    const once = async (u) => { const c = new AbortController(), t = setTimeout(() => c.abort(), timeout);
      try { const r = await fetch(u, { signal: c.signal, cache: 'no-store' }); if (!r.ok) throw new Error('HTTP ' + r.status); const saved = r.headers.get('X-Ban-Luu'); if (saved) cacheHits.push(saved); return await r.json(); } finally { clearTimeout(t); } };
    if (LOCAL) { try { return await once('/proxy?url=' + encodeURIComponent(url)); } catch (e) { /* thử trực tiếp */ } }
    try { return await once(url); }
    catch (e) { throw new Error(e.name === 'AbortError' ? tx('web.ui.het_thoi_gian_cho') : e.message === 'Failed to fetch' ? tx('web.ui.trinh_duyet_bi_chan_hoac_mat') : e.message); }
  }

  const st = { raw: { cm: null, kl: null, fng: null, live: null }, status: {}, S: null, vol: null,
    set: 'best', ids: new Set(IND.map((d) => d.id)), rec: null, a: null, full: null, asOf: null };
  try { const s = JSON.parse(localStorage.getItem('btc-bot3') || 'null'); if (s) { if (s.set) st.set = s.set; if (Array.isArray(s.ids)) st.ids = new Set(s.ids); } } catch (e) { /* bỏ qua */ }
  const save = () => { try { localStorage.setItem('btc-bot3', JSON.stringify({ set: st.set, ids: [...st.ids] })); } catch (e) { /* bỏ qua */ } };
  const setStatus = (k, ok, msg) => { st.status[k] = { ok, msg }; renderStatus(); };

  async function loadAll() {
    $('run').disabled = true; $('research').disabled = true; $('progress').textContent = tx('web.ui.dang_tai_du_lieu_that_tu');
    try {
      await Promise.all([
        getJSON(URLS.fng).then((j) => { st.raw.fng = j.data; setStatus('fng', true, tx('web.ui.s_0_ngay', j.data.length)); }).catch((e) => setStatus('fng', false, e.message)),
        (async () => {
          try {
            let url = URLS.cm, out = [];
            for (let k = 0; k < 6 && url; k++) { const j = await getJSON(url, 90000); out = out.concat(j.data || []); url = j.next_page_url || null; }
            if (!out.length) throw new Error(tx('web.ui.khong_co_du_lieu'));
            st.raw.cm = out; setStatus('cm', true, tx('web.ui.den_0', String(out[out.length - 1].time).slice(0, 10)) + (out.some((r) => r.IssTotUSD != null) ? '' : tx('web.ui.thieu_du_lieu_tho_dao')));
          } catch (e) {
            st.raw.cm = null;
            setStatus('cm', false, e.message + tx('web.ui.tam_dung_gia_binance_mvrv_mvrv'));
          }
        })(),
        (async () => {
          for (const base of URLS.kl) {
            try {
              let s = Date.parse('2017-08-17T00:00:00Z'), out = [];
              for (let k = 0; k < 10; k++) { const j = await getJSON(`${base}?symbol=BTCUSDT&interval=1d&startTime=${s}&limit=1000`); if (!j.length) break; out = out.concat(j); s = j[j.length - 1][0] + 86400000; if (j.length < 1000) break; }
              if (out.length) { st.raw.kl = out; setStatus('kl', true, tx('web.ui.gia_va_khoi_luong_ngay_tu', out.length)); return; }
            } catch (e2) { setStatus('kl', false, e2.message + tx('web.ui.khong_co_du_lieu_khoi_luong')); }
          }
        })(),
        loadLive(),
      ]);
      if (cacheHits.length) { const oldest = [...cacheHits].sort()[0]; setStatus('cache', false, tx('web.ui.mot_so_nguon_khong_truy_cap', oldest.slice(11, 16), oldest.slice(8, 10), oldest.slice(5, 7), oldest.slice(0, 4))); cacheHits.length = 0; }
      else if (LOCAL) setStatus('cache', true, tx('web.ui.du_lieu_vua_tai_da_duoc'));
      if (!st.raw.cm && !st.raw.kl) throw new Error(tx('web.ui.khong_tai_duoc_gia_lich_su'));
      st.S = BOT.buildSeries(st.raw);
      if (st.S.uocTinh && st.status.cm) { const u = st.S.uocTinh; setStatus('cm', true, tx('web.ui.s_0_coin_metrics_chua_cong_bo', st.status.cm.msg, u.ngay, fmtDate(u.den), fmtDate(u.tu))); }
      st.vol = BOT.volumeStudy(st.S);
      await afterLoad();
    } catch (e) {
      $('loading').hidden = false; $('loading').textContent = e.message + tx('web.ui.kiem_tra_mang_hoac_mo_bang'); $('ai-wait').textContent = $('loading').textContent;
      $('progress').textContent = '';
    } finally { /* xong */ }
  }
  async function loadLive() {
    for (const u of URLS.live) { try { const j = await getJSON(u, 15000); if (Number(j.price) > 0) { st.raw.live = { price: Number(j.price) }; setStatus('live', true, 'Binance'); onLive(); return; } } catch (e) { /* tiếp */ } }
    try { const j = await getJSON(URLS.gecko, 15000); st.raw.live = { price: j.bitcoin.usd }; setStatus('live', true, 'CoinGecko'); onLive(); } catch (e) { setStatus('live', false, e.message); }
  }

  // ---------- chạy ----------
  const avail = () => IND.filter((d) => st.S.avail.includes(d.id)).map((d) => d.id);
  const SHORT = { pi: 'Pi', mvrv: 'MVRV', mvrvz: 'MVRV Z', fng: 'F&G', puell: 'Puell', wma: tx('web.ui.ma200_tuan'), mayer: 'Mayer', rsiw: tx('web.ui.rsi_tuan'), dd: tx('web.ui.giam_tu_dinh'), vol: tx('web.ui.khoi_luong') };
  const VALID = ['best', ...OPTIONS.map((o) => o.id), 'all', 'custom'];
  if (st.set === 'rec') st.set = 'pa6'; else if (!VALID.includes(st.set)) st.set = 'best';
  const optIds = (id) => { const o = OPTIONS.find((x) => x.id === id); return (id === 'pa6' ? (st.rec ? st.rec.ids : []) : o.ids).filter((x) => st.S.avail.includes(x)); };
  const topOpt = () => (st.cmp ? st.cmp.ranked.find((x) => x.hang) : null);
  function idsForSet() {
    if (st.set === 'best') { const t = topOpt(); if (t) return t.ids; return st.rec && st.rec.ids.length ? st.rec.ids : avail(); }
    if (st.set.startsWith('pa')) { const ids = optIds(st.set); return ids.length ? ids : avail(); }
    if (st.set === 'all') return avail();
    return [...st.ids].filter((id) => st.S.avail.includes(id));
  }
  const usesRec = () => st.set === 'pa6' || (st.set === 'best' && topOpt() && topOpt().id === 'pa6');
  async function doCompare() {
    busy(true, tx('web.ui.dang_chay_6_phuong_an')); let n = 0;
    try { st.cmp = await B3.compareOptions(st.S, st.asOf, st.rec ? st.rec.ids : null, async () => { n++; $('progress').textContent = tx('web.ui.dang_chay_6_phuong_an_0', n); await tick(); }); st.cmpAsOf = st.asOf; }
    catch (e) { st.cmp = null; $('progress').textContent = e.message; }
    busy(false);
  }
  const cachedA = (ids, asOf) => { if (!st.cmp || st.cmpAsOf !== asOf) return null; const k = [...ids].sort().join(); const x = st.cmp.list.find((y) => y.a && [...y.ids].sort().join() === k); return x ? x.a : null; };
  const busy = (on, msg) => { $('run').disabled = on; $('research').disabled = on; if (msg != null) $('progress').textContent = msg; };

  async function afterLoad() {
    const S = st.S, last = S.price.length - 1;
    st.asOf = last;
    $('date').max = S.dates[last]; $('date').min = '2016-01-01'; $('date').value = S.dates[last];
    if (!st.raw.live) { $('price').textContent = usd(S.price[last]); $('when').textContent = tx('web.ui.gia_dong_cua_0', fmtDate(S.dates[last])); }
    renderSets();
    await doSearch();
    await doCompare();
    await analyzeNow(true);
  }
  async function doSearch() {
    busy(true, tx('web.ui.dang_thu_cac_bo_chi_so'));
    let n = 0;
    try {
      st.rec = await B3.search(st.S, st.asOf, avail(), async () => { n++; $('progress').textContent = tx('web.ui.dang_thu_cac_bo_chi_so_2', n); await tick(); });
    } catch (e) { st.rec = null; $('progress').textContent = e.message; }
    busy(false);
  }
  async function analyzeNow(refreshFull) {
    const ids = idsForSet();
    busy(true, tx('web.ui.dang_phan_tich')); await tick();
    try {
      const last = st.S.price.length - 1;
      if (refreshFull || !st.full || st.full.ids.join() !== ids.join()) st.full = cachedA(ids, last) || B3.analyze(st.S, last, ids);
      st.a = st.asOf === last ? st.full : cachedA(ids, st.asOf) || B3.analyze(st.S, st.asOf, ids);
      st.lv = B3.priceLevels(st.S, st.asOf, st.a);
      st.sdFull = B3.sellSide(st.S, last, st.full);
      st.sd = st.asOf === last ? st.sdFull : B3.sellSide(st.S, st.asOf, st.a);
      $('loading').hidden = true; $('app').hidden = false; $('old-body').hidden = false; $('ai-body').hidden = false; $('ai-wait').hidden = true;
      render();
      $('progress').textContent = tx('web.ui.xong_phan_tich_ngay_0_voi', fmtDate(st.a.date), ids.length);
    } catch (e) { $('progress').textContent = e.message; }
    busy(false);
  }

  // ---------- chọn bộ chỉ số ----------
  function renderSets() {
    const t = topOpt();
    const sets = [{ id: 'best', ten: tx('web.ui.tu_dong_phuong_an_tot_nhat') + (t ? ` (${t.ten.replace(tx('web.ui.phuong_an'), 'PA')})` : '') },
      ...OPTIONS.map((o) => ({ id: o.id, ten: o.ten.replace(tx('web.ui.phuong_an_2'), 'PA') + ' ' + (o.id === 'pa6' ? tx('web.ui.bot_tu_tim') : o.ids.map((x) => SHORT[x]).join(' + ')) })),
      { id: 'all', ten: tx('web.ui.tat_ca_chi_so') }, { id: 'custom', ten: tx('web.ui.tu_chon') }];
    $('sets').replaceChildren(...sets.map((x) => {
      const b = el('button', null, x.ten); b.type = 'button'; b.setAttribute('aria-pressed', String(st.set === x.id));
      b.addEventListener('click', () => { if (x.id === 'custom') st.ids = new Set(idsForSet()); st.set = x.id; save(); renderSets(); if (x.id !== 'custom') analyzeNow(); });
      return b;
    }));
    const cur = new Set(idsForSet());
    $('inds').replaceChildren(...IND.map((d) => {
      const ok = st.S.avail.includes(d.id), lab = el('label', ok ? '' : 'na'); lab.title = d.y + (ok ? '' : tx('web.ui.nguon_du_lieu_chua_tai_duoc'));
      const cb = el('input'); cb.type = 'checkbox'; cb.checked = cur.has(d.id) && ok; cb.disabled = !ok;
      cb.addEventListener('change', () => { if (st.set !== 'custom') { st.ids = new Set(idsForSet()); st.set = 'custom'; } cb.checked ? st.ids.add(d.id) : st.ids.delete(d.id); save(); renderSets(); });
      lab.append(cb, d.ten); return lab;
    }));
    const u = $('using'); u.replaceChildren(el('span', 'muted', tx('web.ui.dang_dung')), idsForSet().map(nameOf).join(', ') || tx('web.ui.chua_chon_chi_so_nao'));
    if (st.set === 'custom') u.append(el('span', 'muted', tx('web.ui.bam_chay_bot_de_tinh_lai')));
  }
  $('run').addEventListener('click', async () => {
    if (st.asOf === st.S.price.length - 1) { await loadLive(); st.S = BOT.buildSeries(st.raw); st.vol = BOT.volumeStudy(st.S); st.asOf = st.S.price.length - 1; $('price').textContent = usd(st.S.price[st.asOf]); }
    await doCompare(); analyzeNow(true);
  });
  $('research').addEventListener('click', async () => { await doSearch(); await doCompare(); renderSets(); analyzeNow(); });
  $('date').addEventListener('change', () => setDate($('date').value));
  $('today').addEventListener('click', () => setDate(st.S.dates[st.S.dates.length - 1]));
  function setDate(d) {
    if (!d || !st.S) return;
    let i = st.S.dates.indexOf(d);
    if (i < 0) i = d > st.S.dates[st.S.dates.length - 1] ? st.S.dates.length - 1 : st.S.dates.findIndex((x) => x >= d);
    if (i < 0) return;
    st.asOf = i; $('date').value = st.S.dates[i];
    (async () => { await doCompare(); renderSets(); analyzeNow(); })();
  }

  // ---------- hiển thị ----------
  const ZCOL = { buy: { phai: '--jade', cannhac: '--brass', khong: '--muted' }, sell: { nen: '--cinnabar', cannhac: '--brass', khong: '--muted' } };
  function render() {
    const a = st.a, last = st.S.price.length - 1, past = st.asOf !== last;
    const w = $('lookahead');
    if (usesRec() && st.rec && st.rec.asOfDate > a.date) {
      w.hidden = false; w.textContent = tx('web.ui.luu_y_bo_khuyen_cao_duoc', fmtDate(st.rec.asOfDate), fmtDate(a.date));
    } else w.hidden = true;
    renderGauges(); renderKN(); renderLevels(); renderOptions(); renderTiles(past); renderCriteria(); renderRec(); drawChart(); renderFeat(); drawIndCharts(); renderSets(); renderSell(); applyMode();
  }

  function zoneBar(Z, kind, score) {
    const box = el('div'), bar = el('div', 'zbar');
    const parts = [...Z].sort((x, y) => x.min - y.min);
    parts.forEach((z, k) => { const to = k + 1 < parts.length ? parts[k + 1].min : 100; const i = el('i'); i.style.width = (to - z.min) + '%'; i.style.background = `color-mix(in srgb, var(${ZCOL[kind][z.id]}) ${z.id === 'khong' ? 30 : 70}%, transparent)`; bar.append(i); });
    const mk = el('div', 'zmark'), b = el('b'); b.style.left = Math.max(1, Math.min(99, score)) + '%'; mk.append(b);
    const lab = el('div', 'zlab');
    parts.forEach((z, k) => { const to = k + 1 < parts.length ? parts[k + 1].min : 100; const s = el('span'); s.append(el('b', null, z.ten), el('br'), `${z.min}–${to}%`); s.style.width = (to - z.min) + '%'; lab.append(s); });
    box.append(bar, mk, lab); return box;
  }
  function renderGauges() {
    const a = st.a, bz = a.buy.zone, sz = a.sell.zone;
    const gb = $('g-buy'); gb.replaceChildren(el('h3', null, tx('web.ui.ty_le_nen_mua_ngay_0', fmtDate(a.date))));
    const bb = el('div', 'big'); bb.append(el('b', 'num', nf(0).format(a.buy.score) + '%'), el('span', bz.id === 'phai' ? 'good' : bz.id === 'cannhac' ? 'mid' : 'muted', bz.ten)); gb.append(bb, zoneBar(BUY_Z, 'buy', a.buy.score));
    gb.append(el('p', null, tx('web.ui.dieu_kien_ngay_nay_thuan_loi', nf(0).format(a.buy.score))));
    const ez = a.buy.ev.zones.find((z) => z.id === bz.id), eb = a.buy.ev.base;
    gb.append(el('p', 'muted', ez.n ? tx('web.ui.lich_su_o_khung_0_thang', bz.ten.toLowerCase(), pc(ez.h[2].win), pc(ez.h[3].win), ez.n, ez.eps, pc(eb.h[2].win), pc(eb.h[3].win)) : tx('web.ui.chua_co_tuan_nao_trong_lich')));
    const gs = $('g-sell'); gs.replaceChildren(el('h3', null, tx('web.ui.ty_le_nen_ban_ngay_0', fmtDate(a.date))));
    const sb = el('div', 'big'); sb.append(el('b', 'num', nf(0).format(a.sell.score) + '%'), el('span', sz.id === 'nen' ? 'bad' : sz.id === 'cannhac' ? 'mid' : 'muted', sz.ten)); gs.append(sb, zoneBar(SELL_Z, 'sell', a.sell.score));
    gs.append(el('p', null, tx('web.ui.nguy_co_gia_giam_hon_10', nf(0).format(a.sell.score))));
    const sz2 = a.sell.ev.zones.find((z) => z.id === sz.id), sbase = a.sell.ev.base;
    gs.append(el('p', 'muted', sz2.n ? tx('web.ui.lich_su_o_khung_0_gia', sz.ten.toLowerCase(), pc(sz2.h[1].giam.win), pc(sz2.h[1].giamManh.win), sz2.n, pc(sbase.h[1].giam.win), pc(sbase.h[1].giamManh.win)) : tx('web.ui.chua_co_tuan_nao_trong_lich')));
    for (const g of [gb, gs]) g.append(el('p', 'warn', tx('web.rb.gauge_note')));
  }

  // ---------- giá đề xuất mua, bán ----------
  function renderLevels() {
    const lv = st.lv, a = st.a, find = (kind, id) => lv.levels.find((L) => L.kind === kind && L.id === id);
    $('lv-lead').textContent = tx('web.ui.gia_btc_de_bot_chuyen_sang', fmtDate(lv.date));
    $('lv-sum').replaceChildren(el('b', null, tx('web.ui.gia_de_xuat_mua')), tx('web.ui.can_nhac_mua_0_phai_mua', B3.levelText(lv, find('buy', 'cannhac')), B3.levelText(lv, find('buy', 'phai'))),
      el('b', null, tx('web.ui.gia_de_xuat_ban')), tx('web.ui.can_nhac_ban_0_nen_ban', B3.levelText(lv, find('sell', 'cannhac')), B3.levelText(lv, find('sell', 'nen'))));
    // lịch sử của khung: tỷ lệ thực tế so với mốc mua, bán vào một tuần bất kỳ
    const hist = (L) => {
      const ev = a[L.kind].ev, z = ev.zones.find((x) => x.id === L.id), b = ev.base; if (!z.n) return [tx('web.ui.chua_co_tuan_nao_o_khung'), '', ''];
      const yeu = z.eps < 3 ? tx('web.ui.it_dot_doc_lap_nen_chua') : '';
      if (L.kind === 'buy') { const kem = z.h[2].win != null && z.h[2].win < b.h[2].win;
        return [tx('web.ui.thang_sau_6_thang_0_sau', pc(z.h[2].win), pc(z.h[3].win), pc(b.h[2].win), pc(b.h[3].win)), tx('web.ui.s_0_tuan_1_dot_2_3', z.n, z.eps, yeu, kem ? tx('web.ui.thap_hon_moc') : ''), kem ? 'bad' : ''];
      }
      const kem = z.h[1].giam.win != null && z.h[1].giam.win <= b.h[1].giam.win;
      return [tx('web.ui.gia_thap_hon_sau_6_thang', pc(z.h[1].giam.win), pc(z.h[1].giamManh.win), pc(b.h[1].giam.win), pc(b.h[1].giamManh.win)), tx('web.ui.s_0_tuan_1_dot_2_3', z.n, z.eps, yeu, kem ? tx('web.ui.khong_hon_moc') : ''), kem ? 'bad' : ''];
    };
    const h = el('tr'); [tx('web.ui.khuyen_cao'), tx('web.ui.gia_btc'), tx('web.ui.cach_gia_hien_tai'), tx('web.ui.hom_nay'), tx('web.ui.lich_su_o_khung_nay')].forEach((t, k) => h.append(el('th', k === 1 || k === 2 ? 'r' : '', t)));
    const tb = el('tbody');
    const row = (L) => {
      const tr = el('tr'), zc = L.kind === 'buy' ? ZCOL.buy[L.id] : ZCOL.sell[L.id], n = el('td'), d = el('i', 'zdot'); d.style.background = `var(${zc})`; n.append(d, el('b', null, L.ten), el('span', 'sub', tx('web.ui.ty_le_nen_0_tu_1', L.kind === 'buy' ? 'mua' : tx('web.ui.ban'), L.thr)));
      const g = el('td', 'r num nowrap'); if (L.gia != null) g.append(el('b', null, `${L.kind === 'buy' ? '≤' : '≥'} ${usd(L.gia)}`)); else g.append(el('span', 'muted', B3.levelText(lv, L)));
      const [t1, t2, tone] = hist(L), hc = el('td', tone); hc.append(t1); if (t2) hc.append(el('span', 'sub', t2));
      tr.append(n, g, el('td', 'r num', L.gia != null ? spc(L.gia / lv.price - 1, 1) : '—'), el('td', null, L.dat ? tx('web.ui.dang_dat') : tx('web.ui.chua_dat')), hc); return tr;
    };
    lv.levels.filter((L) => L.kind === 'sell').forEach((L) => tb.append(row(L)));
    const cur = el('tr', 'here'); cur.append(el('td', null, tx('web.ui.gia_ngay_phan_tich')), el('td', 'r num nowrap', usd(lv.price)), el('td'), el('td', null, tx('web.ui.nen_mua_0_nen_ban_1', nf(0).format(a.buy.score), nf(0).format(a.sell.score))), el('td')); tb.append(cur);
    lv.levels.filter((L) => L.kind === 'buy').forEach((L) => tb.append(row(L)));
    const th = el('thead'); th.append(h); $('t-lv').replaceChildren(th, tb);
    $('lv-notes').replaceChildren(...B3.levelNotes(lv).map((s) => el('p', 'warn', s)));
    // bảng "nếu giá là …"; một chữ số thập phân để 69,6% không hiện thành 70% mà vẫn chưa tới khung 70%
    const h2 = el('tr'); [tx('web.ui.gia_btc'), tx('web.ui.so_voi_hien_tai'), tx('web.ui.ty_le_nen_mua'), tx('web.ui.ty_le_nen_ban')].forEach((t, k) => h2.append(el('th', k ? 'r' : '', t)));
    const tb2 = el('tbody');
    lv.ladder.forEach((r) => {
      const tr = el('tr', r.f === 1 ? 'here' : ''), cell = (v, Z, kind) => { const c = el('td', 'r num'); if (v == null) { c.append('—'); return c; } const z = zoneOf(Z, v); c.append(el('b', z.id === 'khong' ? 'muted' : kind === 'buy' ? (z.id === 'phai' ? 'good' : 'mid') : (z.id === 'nen' ? 'bad' : 'mid'), nf(1).format(v) + '%'), el('span', 'sub', z.ten)); return c; };
      tr.append(el('td', 'num nowrap', usd(r.gia)), el('td', 'r num', r.f === 1 ? tx('web.ui.hien_tai') : spc(r.f - 1)), cell(r.buy, BUY_Z, 'buy'), cell(r.sell, SELL_Z, 'sell')); tb2.append(tr);
    });
    const th2 = el('thead'); th2.append(h2); $('t-lvl').replaceChildren(th2, tb2);
  }

  function rangeBar(x, base, tone) {
    const b = el('div', 'rng ' + tone);
    if (x.lo != null) { const i = el('i'); i.style.left = x.lo * 100 + '%'; i.style.width = Math.max(1, (x.hi - x.lo) * 100) + '%'; b.append(i); }
    if (x.win != null) { const m = el('b'); m.style.left = `calc(${x.win * 100}% - 1.5px)`; b.append(m); }
    if (base != null) { const s = el('s'); s.style.left = `calc(${base * 100}% - 1px)`; b.append(s); }
    return b;
  }
  function renderTiles(past) {
    const a = st.a;
    $('hold-title').textContent = tx('web.ui.xac_suat_thang_neu_mua_ngay', fmtDate(a.date), usd(a.price));
    $('tiles').replaceChildren(...a.hold.map((h) => {
      const tone = h.win == null || h.base == null ? '' : h.win - h.base >= 0.05 ? 'good' : h.win - h.base <= -0.05 ? 'bad' : 'mid';
      const d = el('div', 'tile'); d.append(el('div', 'h', tx('web.ui.giu') + h.ten), el('div', 'p num ' + tone, h.n ? pc(h.win) : '—'), rangeBar(h, h.base, tone));
      d.append(el('div', 'c', h.n ? tx('web.ui.khoang_tin_cay_0_1_mua', pc(h.lo), pc(h.hi), pc(h.base)) : tx('web.ui.chua_du_du_lieu')));
      if (h.n) d.append(el('div', 'c', tx('web.ui.lai_trung_vi_0_mot_nua', spc(h.med), spc(h.q1), spc(h.q3), h.n, h.eps)));
      if (past) { const act = el('div', 'act'); if (h.thucTe == null) act.append(el('span', 'muted', tx('web.ui.thuc_te_chua_du_thoi_gian'))); else { act.append(tx('web.ui.thuc_te_sau_do'), el('b', h.thucTe > 0 ? 'good' : 'bad', `${spc(h.thucTe)}, ${h.thucTe > 0 ? tx('web.ui.thang') : 'thua'}`)); } d.append(act); }
      return d;
    }));
  }

  function zRow(name, z, cells, here, dotVar) {
    const tr = el('tr', here ? 'here' : name.startsWith(tx('web.ui.mua_bat_ky')) || name.startsWith(tx('web.ui.bat_ky')) ? 'base' : '');
    const isBase = !dotVar;
    const n = el('td'); if (dotVar) { const d = el('i', 'zdot'); d.style.background = `var(${dotVar})`; n.append(d); } n.append(name); if (here) n.append(el('span', 'tag', tx('web.ui.dang_o_day')));
    tr.append(n, el('td', 'r num', isBase ? tx('web.ui.s_0_tuan', z.n) : z.n ? tx('web.ui.s_0_1_dot', z.n, z.eps) : '0'), ...cells); return tr;
  }
  const cellWin = (x, base, inv) => { const hiC = inv ? 'bad' : 'good', loC = inv ? 'good' : 'bad'; const c = el('td', 'r num ' + (base == null || x.win == null ? '' : x.win - base >= 0.05 ? hiC : x.win - base <= -0.05 ? loC : '')); c.append(x.n ? pc(x.win) : '—'); if (x.n) c.append(el('span', 'sub', tx('web.ui.s_0_1_2_lan', pc(x.lo), pc(x.hi), x.n))); return c; };
  function renderCriteria() {
    const a = st.a, B = a.buy.ev, Sv = a.sell.ev;
    $('crit-lead').textContent = tx('web.ui.kiem_tra_moi_tuan_tu_0', fmtDate(a.from), fmtDate(a.date));
    const hb = el('tr'); ['Khung mua', tx('web.ui.so_tuan'), ...HZ.map((h) => tx('web.ui.thang_sau') + h.ten)].forEach((t, k) => hb.append(el('th', k ? 'r' : '', t)));
    const tb = el('tbody'); tb.append(zRow(tx('web.ui.mua_bat_ky_luc_nao_moc'), B.base, B.base.h.map((x) => cellWin(x, null)), false));
    B.zones.forEach((z) => tb.append(zRow(z.ten, z, z.h.map((x, k) => cellWin(x, B.base.h[k].win)), z.id === a.buy.zone.id, ZCOL.buy[z.id])));
    const th = el('thead'); th.append(hb); $('t-buy').replaceChildren(th, tb);
    const hs = el('tr'); [tx('web.ui.khung_ban'), tx('web.ui.so_tuan'), ...SELL_HZ.flatMap((h) => [tx('web.ui.gia_thap_hon_sau_0', h.ten), tx('web.ui.giam_hon_10_sau_0', h.ten)])].forEach((t, k) => hs.append(el('th', k ? 'r' : '', t)));
    const ts = el('tbody'); ts.append(zRow(tx('web.ui.bat_ky_luc_nao_moc'), Sv.base, Sv.base.h.flatMap((x) => [cellWin(x.giam, null), cellWin(x.giamManh, null)]), false));
    Sv.zones.forEach((z) => ts.append(zRow(z.ten, z, z.h.flatMap((x, k) => [cellWin(x.giam, Sv.base.h[k].giam.win, true), cellWin(x.giamManh, Sv.base.h[k].giamManh.win, true)]), z.id === a.sell.zone.id, ZCOL.sell[z.id])));
    const th2 = el('thead'); th2.append(hs); $('t-sell').replaceChildren(th2, ts);
  }

  function renderRec() {
    const r = st.rec;
    if (!r) { $('rec-lead').textContent = tx('web.ui.chua_tim_duoc_bo_khuyen_cao'); $('t-rec').replaceChildren(); return; }
    $('rec-lead').textContent = tx('web.ui.bot_thu_them_dan_tung_chi', fmtDate(r.from), fmtDate(r.asOfDate)) + ' ' + tx('web.kn.warn_legend');
    const h = el('tr'); [tx('web.ui.bo_chi_so'), ...HZ.map((x) => tx('web.ui.thang_2') + x.ten), tx('web.ui.nua_dau_6_thang'), tx('web.ui.nua_sau_6_thang'), ''].forEach((t, k) => h.append(el('th', k && k < 7 ? 'r' : '', t)));
    const tb = el('tbody'), base = r.ranking[0] && r.ranking[0].base;
    if (base) { const tr = el('tr', 'base'); tr.append(el('td', null, tx('web.ui.mua_bat_ky_luc_nao_moc')), ...base.h.map((x) => el('td', 'r num', pc(x.win))), el('td'), el('td'), el('td')); tb.append(tr); }
    const curKey = idsForSet().slice().sort().join(',');
    const ok = r.ranking.filter((x) => isFinite(x.score)), weak = r.ranking.filter((x) => !isFinite(x.score));
    ok.slice(0, 10).forEach((x, k) => {
      const tr = el('tr', [...x.ids].sort().join(',') === curKey ? 'here' : ''), n = el('td');
      const wr = warnOf(x.phai.eps, x.nua1[2], x.nua2[2]); if (wr) n.append(el('span', 'mid', tx('web.kn.warn_mark')));
      n.append(el('b', null, x.ten)); if (k === 0) n.append(el('span', 'tag', tx('web.ui.cao_nhat'))); n.append(el('span', 'sub', x.ids.map(nameOf).join(', ')));
      if (wr) n.append(el('span', 'sub mid', wr));
      tr.append(n, ...x.phai.h.map((y, i) => { const c = el('td', 'r num ' + (y.win == null ? '' : y.win - base.h[i].win >= 0.05 ? 'good' : y.win - base.h[i].win <= -0.05 ? 'bad' : '')); c.append(y.n ? pc(y.win) : '—'); if (y.n) c.append(el('span', 'sub', tx('web.ui.s_0_lan', y.n))); return c; }));
      const n1 = x.nua1[2], n2 = x.nua2[2];
      tr.append(el('td', 'r num', n1.n ? `${pc(n1.win)} (${n1.n})` : tx('web.ui.khong_co_tin_hieu')), el('td', 'r num ' + (n2.n && n2.win < 0.5 ? 'bad' : ''), n2.n ? `${pc(n2.win)} (${n2.n})` : tx('web.ui.khong_co_tin_hieu')));
      const bt = el('button', 'btn nowrap', tx('web.ui.dung_bo_nay')); bt.type = 'button';
      bt.addEventListener('click', () => { if (k === 0) st.set = 'pa6'; else { st.set = 'custom'; st.ids = new Set(x.ids); } save(); renderSets(); analyzeNow(); window.scrollTo({ top: 0, behavior: 'smooth' }); });
      const c = el('td'); c.append(bt); tr.append(c); tb.append(tr);
    });
    const th = el('thead'); th.append(h); $('t-rec').replaceChildren(th, tb);
    $('rec-weak').textContent = weak.length ? tx('web.ui.khong_du_tin_hieu_phai_mua', weak.map((x) => x.ten).join(', ')) : '';
  }

  // ---------- so sánh phương án ----------
  const HCOL = ['0.35', '0.55', '0.78', '1'];
  function renderOptions() {
    const c = st.cmp;
    if (!c || !c.ranked.length) { $('pa-lead').textContent = tx('web.ui.chua_chay_duoc_cac_phuong_an'); $('t-pa').replaceChildren(); $('pa-cons').textContent = ''; return; }
    const dt = c.dongThuan, top = topOpt();
    $('pa-lead').textContent = tx('web.ui.bot_chay_ca_6_phuong_an', fmtDate(st.S.dates[st.asOf]), fmtDate(c.from)) + ' ' + tx('web.kn.warn_legend');
    const cons = $('pa-cons'); cons.replaceChildren();
    cons.append(el('b', null, tx('web.ui.dong_thuan_cua_0_phuong_an', dt.tong)), dt.mua.filter((z) => z.n).map((z) => `${z.n} ${z.ten.toLowerCase()}`).join(', ') + '; ' + dt.ban.filter((z) => z.n).map((z) => `${z.n} ${z.ten.toLowerCase()}`).join(', ') + '. ');
    cons.append(tx('web.ui.trung_binh_ty_le_nen_mua', nf(0).format(dt.tbMua), nf(0).format(dt.tbBan)));
    const split = dt.mua.find((z) => z.id === 'phai').n && dt.mua.find((z) => z.id === 'khong').n;
    cons.append(split ? el('span', 'mid', tx('web.ui.cac_phuong_an_dang_bat_dong')) : el('span', 'good', tx('web.ui.cac_phuong_an_khong_mau_thuan')));
    if (top) cons.append(tx('web.ui.hang_1_la_0_1_2', top.ten, top.a.buy.zone.ten.toLowerCase(), nf(0).format(top.a.buy.score)));
    const h = el('tr'); [tx('web.ui.hang'), tx('web.ui.phuong_an'), tx('web.ui.nen_mua_hom_nay'), tx('web.ui.nen_ban_hom_nay'), ...HZ.map((x) => tx('web.ui.thang_2') + x.ten), tx('web.ui.nua_dau_nua_sau'), tx('web.ui.khi_nen_ban_gia_thap_hon'), ''].forEach((t, k) => h.append(el('th', k >= 2 && k <= 9 ? 'r' : '', t)));
    const tb = el('tbody'), cur = [...idsForSet()].sort().join();
    const rows = [...c.ranked, ...c.list.filter((x) => !c.ranked.includes(x))];
    for (const x of rows) {
      const tr = el('tr', x.a && [...x.ids].sort().join() === cur ? 'here' : '');
      tr.append(el('td', 'num', x.hang ? String(x.hang) : '—'));
      const n = el('td'), wp = x.a && !x.trung ? warnOf((x.xepTheo === 'rong' ? x.rong : x.evB.zones[0]).eps, x.nua1, x.nua2) : null;
      if (wp) n.append(el('span', 'mid', tx('web.kn.warn_mark')));
      n.append(el('b', null, x.ten)); if (x.hang === 1) n.append(el('span', 'tag', tx('web.ui.tot_nhat')));
      if (wp) n.append(el('span', 'sub mid', wp));
      n.append(el('span', 'sub', (x.ids.length ? x.ids.map(nameOf).join(' + ') : '—') + '. ' + x.lyDo + (x.thieu.length ? tx('web.ui.thieu_du_lieu_0', x.thieu.map(nameOf).join(', ')) : '')));
      tr.append(n);
      if (!x.a || x.trung) {
        tr.append(Object.assign(el('td', 'muted', x.trung ? tx('web.ui.trung_0', x.trung) : x.loi), { colSpan: 8 }));
        tr.append(el('td')); tb.append(tr); continue;
      }
      const bz = x.a.buy.zone, sz = x.a.sell.zone;
      const b1 = el('td', 'r num'); b1.append(el('b', bz.id === 'phai' ? 'good' : bz.id === 'cannhac' ? 'mid' : 'muted', nf(0).format(x.a.buy.score) + '%'), el('span', 'sub', bz.ten));
      const s1 = el('td', 'r num'); s1.append(el('b', sz.id === 'nen' ? 'bad' : sz.id === 'cannhac' ? 'mid' : 'muted', nf(0).format(x.a.sell.score) + '%'), el('span', 'sub', sz.ten));
      tr.append(b1, s1);
      const z = x.xepTheo === 'rong' ? x.rong : x.evB.zones[0], base = x.evB.base;
      z.h.forEach((y, i) => { const cl = el('td', 'r num ' + (y.win == null ? '' : y.win - base.h[i].win >= 0.05 ? 'good' : y.win - base.h[i].win <= -0.05 ? 'bad' : '')); cl.append(y.n ? pc(y.win) : '—', el('span', 'sub', y.n ? tx('web.ui.s_0_lan_1', y.n, x.xepTheo === 'rong' ? tx('web.ui.khung_rong') : '') : tx('web.ui.it_tin_hieu'))); tr.append(cl); });
      tr.append(el('td', 'r num ' + (x.nua2.n && x.nua2.win < base.h[2].win ? 'bad' : ''), `${x.nua1.n ? pc(x.nua1.win) : '—'} / ${x.nua2.n ? pc(x.nua2.win) : '—'}`));
      const bd = el('td', 'r num'); if (x.banDung) { bd.append(el('span', x.banDung.win - x.banMoc >= 0.05 ? 'good' : x.banDung.win - x.banMoc <= -0.05 ? 'bad' : '', pc(x.banDung.win))); bd.append(el('span', 'sub', tx('web.ui.moc_0_1_lan', pc(x.banMoc), x.banDung.n))); } else bd.append(el('span', 'muted', tx('web.ui.it_tin_hieu'))); tr.append(bd);
      const bt = el('button', 'btn nowrap', tx('web.ui.dung')); bt.type = 'button';
      bt.addEventListener('click', () => { st.set = x.id; save(); renderSets(); analyzeNow(); window.scrollTo({ top: 0, behavior: 'smooth' }); });
      const ct = el('td'); ct.append(bt); tr.append(ct); tb.append(tr);
    }
    const th = el('thead'); th.append(h); $('t-pa').replaceChildren(th, tb);
    drawOptCharts();
  }

  function canvasSetup(cv) {
    const cs = getComputedStyle(document.documentElement), c = (n) => cs.getPropertyValue(n).trim();
    const W = cv.clientWidth, H = baseH(cv), dpr = window.devicePixelRatio || 1;
    cv.style.height = H + 'px'; cv.width = W * dpr; cv.height = H * dpr; const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H); g.font = `12px ${c('--font')}`;
    return { g, W, H, c };
  }
  function drawOptCharts() {
    const cm = st.cmp; if (!cm || !cm.ranked.length) return;
    const opts = cm.ranked.filter((x) => x.a);
    // 1) tỷ lệ thắng theo kỳ giữ
    { const cv = $('c-pa-win'); if (cv.clientWidth) {
      const { g, W, H, c } = canvasSetup(cv), L = 40, R = 8, T = 10, B = 40, ph = H - T - B, gw = (W - L - R) / opts.length, bw = Math.min(22, (gw - 12) / 4);
      const y = (v) => T + ph - v * ph;
      g.strokeStyle = c('--line'); g.fillStyle = c('--muted'); g.lineWidth = 1; g.textAlign = 'right'; g.textBaseline = 'middle';
      [0, 0.25, 0.5, 0.75, 1].forEach((v) => { g.beginPath(); g.moveTo(L, Math.round(y(v)) + 0.5); g.lineTo(W - R, Math.round(y(v)) + 0.5); g.stroke(); g.fillText(nf(0).format(v * 100) + '%', L - 6, y(v)); });
      opts.forEach((x, k) => {
        const z = x.xepTheo === 'rong' ? x.rong : x.evB.zones[0], x0 = L + k * gw + (gw - 4 * bw - 6) / 2;
        z.h.forEach((h, i) => {
          const xx = x0 + i * (bw + 2);
          if (h.n) { g.fillStyle = c('--blue'); g.globalAlpha = Number(HCOL[i]); g.fillRect(xx, y(h.win), bw, y(0) - y(h.win)); g.globalAlpha = 1; }
          const bv = x.evB.base.h[i].win; if (bv != null) { g.fillStyle = c('--ink'); g.fillRect(xx - 1, y(bv) - 1, bw + 2, 2); }
        });
        g.fillStyle = c('--ink'); g.textAlign = 'center'; g.textBaseline = 'top'; g.fillText(x.ten.replace(tx('web.ui.phuong_an_2'), 'PA'), L + k * gw + gw / 2, T + ph + 6);
        g.fillStyle = c('--muted'); g.fillText(x.xepTheo === 'rong' ? tx('web.ui.khung_rong_2') : x.hang ? tx('web.ui.hang_2') + x.hang : tx('web.ui.it_tin_hieu'), L + k * gw + gw / 2, T + ph + 21);
      });
      $('l-pa-win').replaceChildren(...HZ.map((h, i) => { const s = el('span'); const ic = el('i'); ic.style.background = 'var(--blue)'; ic.style.opacity = HCOL[i]; s.append(ic, h.ten); return s; }),
        (() => { const s = el('span'); const ic = el('i'); ic.style.background = 'var(--ink)'; ic.style.height = '2px'; s.append(ic, tx('web.ui.mua_bat_ky_luc_nao')); return s; })());
    } }
    // 2) tỷ lệ nên mua, nên bán hôm nay của từng phương án
    { const cv = $('c-pa-today'); if (cv.clientWidth) {
      const { g, W, H, c } = canvasSetup(cv), L = 52, R = 40, T = 22, rowH = (H - T - 10) / opts.length, tw = W - L - R, x = (v) => L + (v / 100) * tw;
      g.fillStyle = c('--muted'); g.textAlign = 'center'; g.textBaseline = 'bottom'; [0, 60, 70, 80, 85, 100].forEach((v) => g.fillText(String(v), x(v), T - 6));
      opts.forEach((o, k) => {
        const y0 = T + k * rowH + 4, bh = Math.min(12, (rowH - 14) / 2);
        g.fillStyle = c('--ink'); g.textAlign = 'right'; g.textBaseline = 'middle'; g.fillText(o.ten.replace(tx('web.ui.phuong_an_2'), 'PA'), L - 8, y0 + bh + 2);
        const track = (yy, Z, kind, v) => {
          [...Z].sort((a, b) => a.min - b.min).forEach((z, i, arr) => { const to = i + 1 < arr.length ? arr[i + 1].min : 100; g.fillStyle = c(ZCOL[kind][z.id]); g.globalAlpha = z.id === 'khong' ? 0.22 : 0.45; g.fillRect(x(z.min), yy, x(to) - x(z.min), bh); });
          g.globalAlpha = 1; g.fillStyle = c('--ink'); g.fillRect(x(v) - 1.5, yy - 2, 3, bh + 4);
          g.textAlign = 'left'; g.fillStyle = c('--muted'); g.fillText(nf(0).format(v) + '%', W - R + 4, yy + bh / 2);
        };
        track(y0, BUY_Z, 'buy', o.a.buy.score); track(y0 + bh + 4, SELL_Z, 'sell', o.a.sell.score);
      });
      $('l-pa-today').replaceChildren(...[['--jade', 0.45, tx('web.ui.mua_phai_mua')], ['--brass', 0.45, tx('web.ui.can_nhac')], ['--cinnabar', 0.45, tx('web.ui.ban_nen_ban')]].map(([v, op, t]) => { const s = el('span'); const ic = el('i'); ic.style.background = `var(${v})`; ic.style.opacity = op; s.append(ic, t); return s; }),
        el('span', null, tx('web.ui.moi_phuong_an_dai_tren_la')));
    } }
  }

  // ---------- biểu đồ, bấm để chọn ngày ----------
  let geo = null;
  function drawChart() {
    const full = st.full, cv = $('chart'); if (!full || !cv.clientWidth) return;
    const cs = getComputedStyle(document.documentElement), c = (n) => cs.getPropertyValue(n).trim();
    const W = cv.clientWidth, H = baseH(cv), dpr = window.devicePixelRatio || 1;
    cv.style.height = H + 'px'; cv.width = W * dpr; cv.height = H * dpr; const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
    g.font = `12px ${c('--font')}`;
    const bs = full.buy.series, ss = new Map(full.sell.series.map((x) => [x.j, x])), S = st.S; if (!bs.length) return;
    let lo = Infinity, hi = 0; bs.forEach((x) => { lo = Math.min(lo, S.price[x.i]); hi = Math.max(hi, S.price[x.i]); }); lo *= 0.88; hi *= 1.1;
    const ticks = [1e3, 2e3, 3e3, 5e3, 1e4, 2e4, 3e4, 5e4, 7e4, 1e5, 1.5e5, 2e5].filter((t) => t >= lo && t <= hi);
    const L = 46, R = 10, T = 8, strip = 12, B = 26 + strip + 6, ph = H - T - B;
    const t0 = Date.parse(bs[0].date), t1 = Date.parse(bs[bs.length - 1].date);
    const x = (d) => L + ((Date.parse(d) - t0) / Math.max(1, t1 - t0)) * (W - L - R), y = (p) => T + ph - ((Math.log(p) - Math.log(lo)) / (Math.log(hi) - Math.log(lo))) * ph;
    const bw = Math.max(1, (W - L - R) / bs.length + 0.6);
    bs.forEach((b) => { const z = zoneOf(BUY_Z, b.score); if (z.id === 'khong') return; g.fillStyle = c(ZCOL.buy[z.id]); g.globalAlpha = z.id === 'phai' ? 0.22 : 0.12; g.fillRect(x(b.date) - bw / 2, T, bw, ph); });
    g.globalAlpha = 1;
    const sy = T + ph + 6;
    bs.forEach((b) => { const s = ss.get(b.j); if (!s) return; const z = zoneOf(SELL_Z, s.score); g.fillStyle = z.id === 'khong' ? c('--line') : c(ZCOL.sell[z.id]); g.globalAlpha = z.id === 'khong' ? 0.6 : z.id === 'nen' ? 1 : 0.6; g.fillRect(x(b.date) - bw / 2, sy, bw, strip); });
    g.globalAlpha = 1;
    g.strokeStyle = c('--line'); g.fillStyle = c('--muted'); g.lineWidth = 1; g.textAlign = 'right'; g.textBaseline = 'middle';
    ticks.forEach((t) => { const yy = Math.round(y(t)) + 0.5; g.beginPath(); g.moveTo(L, yy); g.lineTo(W - R, yy); g.stroke(); g.fillText(nf(0).format(t / 1000) + 'k', L - 6, yy); });
    g.fillText(tx('web.ui.ban_2'), L - 6, sy + strip / 2);
    g.textAlign = 'center'; g.textBaseline = 'top'; let lx = -1e9;
    for (let yr = Number(bs[0].date.slice(0, 4)) + 1; yr <= Number(bs[bs.length - 1].date.slice(0, 4)); yr++) { const xx = x(yr + '-01-01'); if (xx - lx > 36) { g.fillText(String(yr), xx, H - 18); lx = xx; } }
    g.strokeStyle = c('--ink'); g.lineWidth = 1.6; g.beginPath(); bs.forEach((b, k) => (k ? g.lineTo(x(b.date), y(S.price[b.i])) : g.moveTo(x(b.date), y(S.price[b.i])))); g.stroke();
    const ad = st.S.dates[st.asOf];
    if (ad >= bs[0].date) { const xx = x(ad); g.strokeStyle = c('--blue'); g.lineWidth = 2; g.setLineDash([5, 4]); g.beginPath(); g.moveTo(xx, T); g.lineTo(xx, T + ph); g.stroke(); g.setLineDash([]); g.fillStyle = c('--blue'); g.textAlign = xx > W - 120 ? 'right' : 'left'; g.textBaseline = 'top'; g.fillText(tx('web.ui.ngay_phan_tich'), xx + (xx > W - 120 ? -6 : 6), T + 2); }
    geo = { bs, ss, x, y };
    $('legend').replaceChildren(...[['--jade', 0.35, tx('web.ui.phai_mua')], ['--brass', 0.25, tx('web.ui.can_nhac_mua')], ['--cinnabar', 1, tx('web.ui.dai_duoi_nen_ban')], ['--brass', 0.6, tx('web.ui.dai_duoi_can_nhac_ban')]].map(([v, o, t]) => { const s = el('span'); const i = el('i'); i.style.background = `var(${v})`; i.style.opacity = o; s.append(i, t); return s; }));
  }
  function nearest(ev) { if (!geo) return null; const mx = ev.clientX - $('chart').getBoundingClientRect().left; let best = null, bd = 1e9; for (const b of geo.bs) { const d = Math.abs(geo.x(b.date) - mx); if (d < bd) { bd = d; best = b; } } return bd < 24 ? best : null; }
  $('chart').addEventListener('mousemove', (ev) => {
    const b = nearest(ev), tip = $('tip'); if (!b) { tip.style.display = 'none'; return; }
    const s = geo.ss.get(b.j);
    tip.replaceChildren(el('b', null, `${fmtDate(b.date)}, ${usd(st.S.price[b.i])}`), el('span', null, tx('web.ui.nen_mua_0_1', nf(0).format(b.score), zoneOf(BUY_Z, b.score).ten)), el('br'), el('span', null, s ? tx('web.ui.nen_ban_0_1', nf(0).format(s.score), zoneOf(SELL_Z, s.score).ten) : ''), el('br'), el('span', 'muted', tx('web.ui.bam_de_phan_tich_ngay_nay')));
    tip.style.display = 'block'; const box = $('chart-box');
    tip.style.left = Math.min(box.clientWidth - tip.offsetWidth - 8, Math.max(8, geo.x(b.date) + 14)) + 'px'; tip.style.top = Math.max(8, geo.y(st.S.price[b.i]) - 60) + 'px';
  });
  $('chart').addEventListener('mouseleave', () => { $('tip').style.display = 'none'; });
  $('chart').addEventListener('click', (ev) => { const b = nearest(ev); if (b) { setDate(b.date); window.scrollTo({ top: 0, behavior: 'smooth' }); } });
  new ResizeObserver(() => { if (st.full) drawChart(); if (st.cmp) drawOptCharts(); }).observe($('chart-box'));

  function renderFeat() {
    const a = st.a, h = el('tr'); [tx('web.ui.chi_so'), tx('web.ui.nhom'), tx('web.ui.gia_tri'), tx('web.ui.trong_so_6_thang'), tx('web.ui.y_nghia')].forEach((t, k) => h.append(el('th', k === 2 || k === 3 ? 'r' : '', t)));
    const tb = el('tbody');
    a.feats.forEach((f) => {
      const d = IND.find((x) => x.id === f.id), w = a.weights && a.weights.find((x) => x.id === f.id), tr = el('tr');
      const det = el('details'); det.append(el('summary', null, 'Xem'), el('p', null, d.y));
      const mean = el('td'); mean.append(det);
      tr.append(el('td', null, d.ten), el('td', 'muted', FAMILIES[d.nhom]), el('td', 'r num', f.v == null ? '—' : nf(d.dec).format(f.v) + (d.unit || '')), el('td', 'r num ' + (w ? (w.w > 0 ? 'good' : 'bad') : ''), w ? (w.w > 0 ? '+' : '−') + nf(2).format(Math.abs(w.w)) : '—'), mean);
      tb.append(tr);
    });
    const th = el('thead'); th.append(h); $('t-feat').replaceChildren(th, tb);
    const v = st.vol, wk = v ? v.weeks.filter((x) => x.cls && x.date <= a.date).pop() : null;
    $('vol-line').textContent = wk ? tx('web.ui.khoi_luong_binance_tuan_ket_thuc', fmtDate(wk.date), spc(wk.chg), nf(2).format(wk.rv), BOT.VCLS[wk.cls].ten.toLowerCase()) : tx('web.ui.chua_co_du_lieu_khoi_luong');
  }

  // ---------- xuất file và Claude ----------
  const sourcesText = () => Object.entries(st.status).filter(([, x]) => x.ok).map(([k]) => ({ live: tx('web.ui.gia_truc_tiep_binance_coingecko'), fng: 'Fear & Greed Alternative.me', cm: 'Coin Metrics', kl: tx('web.ui.binance_gia_khoi_luong_ngay'), cache: tx('web.ui.ban_luu_tren_may') }[k])).filter(Boolean).join(', ');
  const report = (verified = true) => B3.report(st.S, st.a, st.rec, st.vol && { last: st.vol.weeks.filter((x) => x.cls && x.date <= st.a.date).pop() }, sourcesText(), st.asOf === st.S.price.length - 1, st.cmp, st.sd, st.lv, KN, { verified });
  // Gói cho claude.ai (không cần khóa API): chỉ dẫn chuyên gia + hồ sơ của người dùng + báo cáo có đủ phần đã kiểm định.
  function profileText() {
    const lines = [['cp-horizon', 'ho_so_horizon'], ['cp-drawdown', 'ho_so_drawdown'], ['cp-share', 'ho_so_share']]
      .filter(([id]) => $(id).value).map(([id, k]) => tx('web.ui.ho_so_dong', tx('web.page.' + k), $(id).options[$(id).selectedIndex].text));
    const amt = PLAN ? parseAmount($('plan-amount').value) : null;
    if (amt > 0) lines.push(tx('web.ui.ho_so_tien', nf(UNIT[pl.unit].d).format(amt), tx('web.plan.unit_' + pl.unit), fmtDate($('plan-start').value || nextMonday())));
    return lines.length ? lines.join('\n') : tx('web.ui.ho_so_chua_co');
  }
  const claudePackage = () => tx('web.ui.claude_ai_prompt', profileText(), report(true), tx('web.ui.hay_nhan_dinh_ve_ket_luan'));
  function download(name, text, type) { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000); }
  $('dl-md').addEventListener('click', () => download(`bao-cao-bot-btc-${st.a.date}.md`, report(), 'text/markdown;charset=utf-8'));
  $('dl-pkg').addEventListener('click', () => download(`goi-claude-ai-bot-btc-${st.a.date}.md`, claudePackage(), 'text/markdown;charset=utf-8'));
  $('dl-csv').addEventListener('click', () => download(`du-lieu-tuan-bot-btc-${st.a.date}.csv`, B3.csvWeekly(st.S, st.a), 'text/csv;charset=utf-8'));
  $('dl-pa').addEventListener('click', () => { if (!st.cmp) { $('copy-msg').textContent = tx('web.ui.chua_co_ket_qua_so_sanh'); return; } download(`so-sanh-phuong-an-bot-btc-${st.a.date}.csv`, B3.csvOptions(st.cmp), 'text/csv;charset=utf-8'); });


  // ================================================================ BÊN BÁN
  try { const md = localStorage.getItem('btc-bot3-mode'); if (md === 'sell' || md === 'buy') st.mode = md; } catch (e) { /* bỏ qua */ }
  st.mode = st.mode || 'buy';
  function applyMode() {
    const sell = st.mode === 'sell';
    $('mode-buy').setAttribute('aria-pressed', String(!sell)); $('mode-sell').setAttribute('aria-pressed', String(sell));
    $('buy-view').hidden = sell; $('sell-view').hidden = !sell; $('plan-sec').hidden = sell; $('sp-sec').hidden = !sell;
    document.querySelector('#tabs [data-tab=plan]').textContent = tx(sell ? 'web.sp.tab' : 'web.page.tab_plan');
    if (sell) renderSellPlan();
    if ($('cp-sec')) renderCalib();
    renderEntry();
    renderHome();
    requestAnimationFrame(redraw);
    if (sell && st.sd) requestAnimationFrame(drawSellChart);
    if (!sell && st.a) requestAnimationFrame(drawChart);
  }
  const setMode = (md) => { st.mode = md; try { localStorage.setItem('btc-bot3-mode', md); } catch (e) { /* bỏ qua */ } applyMode(); };
  $('mode-buy').addEventListener('click', () => setMode('buy'));
  $('mode-sell').addEventListener('click', () => setMode('sell'));
  const pos = () => { try { return JSON.parse(localStorage.getItem('btc-bot3-pos') || '{}'); } catch (e) { return {}; } };
  const savePos = (p) => { try { localStorage.setItem('btc-bot3-pos', JSON.stringify(p)); } catch (e) { /* bỏ qua */ } };
  const VTONE = { giu: 'good', chot: 'mid', ban: 'bad' };
  const FAMCOL = { xuhuong: '--blue', onchain: '--jade', tamly: '--brass', thodao: '--muted', mohinh: '--cinnabar' };

  function renderSell() {
    const sd = st.sd, a = st.a; if (!sd) return;
    const v = sd.verdict, box = $('s-hero'); box.replaceChildren();
    box.append(el('h2', null, tx('web.ui.nen_giu_hay_chot_loi_ngay', fmtDate(sd.date), usd(sd.price))));
    box.append(el('div', 'verdict-big ' + VTONE[v.id], v.ten), el('p', null, v.goiY));
    const trusted = sd.crit.filter((c) => c.dangTin), famAll = [...new Set(trusted.map((c) => c.nhom))];
    if (!trusted.length) box.append(el('p', 'muted', tx('web.ui.trong_lich_su_chua_tieu_chi')));
    else {
      box.append(el('p', null, tx('web.ui.so_nhom_tieu_chi_dang_tin', sd.nFam, famAll.length)));
      const chips = el('div', 'chips'); trusted.forEach((c) => chips.append(el('span', 'chip' + (c.nowOn ? ' on' : ''), `${c.nowOn ? tx('web.ui.dang_bat') : ''}${c.ten}`))); box.append(chips);
    }
    box.append(el('p', 'muted', tx('web.ui.ty_le_nen_ban_cua_bot', nf(0).format(a.sell.score), a.sell.zone.ten.toLowerCase())));
    const pl = el('div', 'pl'), p0 = pos();
    const mk = (id, lab, val, ph) => { const l = el('label'); l.append(lab); const i = el('input'); i.type = 'number'; i.min = '0'; i.step = 'any'; i.id = id; i.value = val ?? ''; i.placeholder = ph; l.append(i); return l; };
    const out = el('div', 'num');
    pl.append(mk('s-cost', tx('web.ui.gia_von_trung_binh'), p0.cost, tx('web.ui.vi_du_62000')), mk('s-qty', tx('web.ui.so_btc_dang_giu'), p0.qty, tx('web.ui.vi_du_0_5')), out);
    box.append(pl);
    const upd = () => {
      const cost = Number($('s-cost').value), qty = Number(String($('s-qty').value).replace(',', '.'));
      savePos({ cost: $('s-cost').value, qty: $('s-qty').value });
      out.replaceChildren();
      if (!(cost > 0)) { out.append(el('span', 'muted', tx('web.ui.nhap_gia_von_de_xem_lai'))); return; }
      const r = sd.price / cost - 1; out.append(tx('web.ui.ban_dang'), el('b', r >= 0 ? 'good' : 'bad', `${r >= 0 ? tx('web.ui.lai') : tx('web.ui.lo')} ${spc(r, 1)}`));
      if (qty > 0) { out.append(` (${usd(Math.abs(sd.price - cost) * qty)}).`); const f = v.id === 'ban' ? 0.5 : v.id === 'chot' ? (sd.nFam >= 2 ? 0.3 : 0.1) : 0;
        if (f) out.append(tx('web.ui.theo_goi_y_chot_khoang_0', nf(2).format(qty * f), usd(qty * f * sd.price))); else out.append(tx('web.ui.theo_goi_y_chua_can_ban')); }
      else out.append('.');
    };
    $('s-cost').addEventListener('input', upd); $('s-qty').addEventListener('input', upd); upd();

    $('s-hold-title').textContent = tx('web.ui.giu_tiep_co_loi_khong_tinh', fmtDate(sd.date));
    $('s-tiles').replaceChildren(...a.hold.map((h) => {
      const tone = h.win == null || h.base == null ? '' : h.win - h.base >= 0.05 ? 'good' : h.win - h.base <= -0.05 ? 'bad' : 'mid';
      const d = el('div', 'tile'); d.append(el('div', 'h', tx('web.ui.gia_cao_hon_sau') + h.ten), el('div', 'p num ' + tone, h.n ? pc(h.win) : '—'), rangeBar(h, h.base, tone));
      d.append(el('div', 'c', h.n ? tx('web.ui.giu_tiep_lai_trung_vi_0', spc(h.med), spc(h.q1), spc(h.q3), pc(h.base)) : tx('web.ui.chua_du_du_lieu')));
      if (h.thucTe != null && st.asOf !== st.S.price.length - 1) { const act = el('div', 'act'); act.append(tx('web.ui.thuc_te_sau_do'), el('b', h.thucTe > 0 ? 'good' : 'bad', `${spc(h.thucTe)}, ${h.thucTe > 0 ? tx('web.ui.giu_co_loi_hon') : tx('web.ui.ban_co_loi_hon')}`)); d.append(act); }
      return d;
    }));

    $('s-tp-lead').textContent = tx('web.ui.moi_dot_la_lan_dau_tieu', pc(sd.baseDung6));
    const H = [tx('web.ui.tieu_chi'), tx('web.ui.hom_nay'), tx('web.ui.so_dot'), tx('web.ui.gia_thap_hon_sau_6_thang_2'), tx('web.ui.sau_1_nam'), tx('web.ui.gia_6_thang_sau_tin_hieu'), tx('web.ui.con_tang_them_truoc_khi_giam'), tx('web.ui.giam_sau_nhat_trong_1_nam'), ''];
    const hr = el('tr'); H.forEach((t, k) => hr.append(el('th', k >= 2 && k <= 7 ? 'r' : '', t)));
    const tb = el('tbody');
    const base = el('tr', 'base'); base.append(el('td', null, tx('web.ui.ban_vao_mot_tuan_bat_ky')), el('td'), el('td'), el('td', 'r num', pc(sd.baseDung6)), el('td', 'r num', pc(sd.baseDung12)), el('td'), el('td'), el('td'), el('td')); tb.append(base);
    sd.ranked.forEach((c) => {
      const tr = el('tr', c.nowOn ? 'here' : ''), n = el('td'); n.append(el('b', null, c.ten)); n.append(el('span', 'sub', c.loai === 'ket_hop' ? tx('web.ui.ket_hop_nhieu_nhom') : `${B3.NHOM_TP[c.nhom]}, ${c.loai === 'kinh_dien' ? tx('web.ui.nguong_kinh_dien') : c.loai === 'thich_nghi' ? tx('web.ui.nguong_thich_nghi') : tx('web.ui.mo_hinh_cua_bot')}`));
      const now = el('td'); now.append(el('span', c.nowOn ? 'bad' : 'muted', c.nowOn ? tx('web.ui.dang_bat_2') : tx('web.ui.chua_bat'))); if (c.nowVal != null && c.loai !== 'ket_hop') { const d = c.ind ? IND.find((x) => x.id === c.ind) : null; now.append(el('span', 'sub', d ? nf(d.dec).format(c.nowVal) + (d.unit || '') : nf(0).format(c.nowVal) + '%')); }
      const cw = (k, n2, lo, hi) => { const td = el('td', 'r num ' + (k == null ? '' : k - sd.baseDung6 >= 0.1 ? 'good' : k < sd.baseDung6 ? 'bad' : '')); td.append(n2 ? pc(k) : '—'); if (n2) td.append(el('span', 'sub', tx('web.ui.s_0_1_2_dot', pc(lo), pc(hi), n2))); return td; };
      tr.append(n, now, el('td', 'r num', String(c.dot)), cw(c.dung6, c.n6, c.lo6, c.hi6), cw(c.dung12, c.n12, c.lo12, c.hi12), el('td', 'r num', spc(c.med6)), el('td', 'r num', spc(c.up)), el('td', 'r num', spc(c.dn)));
      const ok = el('td'); if (c.dangTin) ok.append(el('span', 'tag', tx('web.ui.dang_tin'))); tr.append(ok); tb.append(tr);
    });
    const th = el('thead'); th.append(hr); $('t-tp').replaceChildren(th, tb);
    const weak = [...sd.crit, ...sd.combos].filter((c) => !sd.ranked.includes(c));
    if (weak.length) { let w = $('s-tp-weak'); if (!w) { w = el('p', 'lead'); w.id = 's-tp-weak'; w.style.margin = '10px 0 0'; $('t-tp').parentElement.after(w); } w.textContent = tx('web.ui.chua_du_3_dot_co_ket') + weak.map((c) => c.ten + (c.coDuLieu ? tx('web.ui.s_0_dot', c.dot) : tx('web.ui.thieu_du_lieu'))).join('; ') + '.'; }

    const lv = sd.crit.filter((c) => c.trigger && c.trigger.gia).sort((x, y) => x.trigger.gia - y.trigger.gia);
    const hl = el('tr'); [tx('web.ui.tieu_chi'), tx('web.ui.nguong'), tx('web.ui.hom_nay'), tx('web.ui.gia_btc_de_bat'), tx('web.ui.cach_gia_hien_tai'), ''].forEach((t, k) => hl.append(el('th', k >= 1 && k <= 4 ? 'r' : '', t)));
    const tl = el('tbody');
    lv.forEach((c) => { const d = IND.find((x) => x.id === c.ind), tr = el('tr', c.dangTin ? '' : 'base');
      tr.append(el('td', null, c.ten), el('td', 'r num', nf(d.dec).format(c.trigger.thr) + (d.unit || '')), el('td', 'r num', c.nowVal == null ? '—' : nf(d.dec).format(c.nowVal) + (d.unit || '')), el('td', 'r num', usd(c.trigger.gia)), el('td', 'r num', spc(c.trigger.gia / sd.price - 1)));
      const t2 = el('td'); if (c.dangTin) t2.append(el('span', 'tag', tx('web.ui.dang_tin'))); else t2.append(el('span', 'muted', tx('web.ui.chua_dang_tin'))); tr.append(t2); tl.append(tr); });
    const thl = el('thead'); thl.append(hl); $('t-tplv').replaceChildren(thl, tl);

    const hs = el('tr'); [tx('web.ui.bat_dau'), tx('web.ui.giu_nguyen_1_btc'), tx('web.ui.theo_quy_tac_chot_loi'), 'Quy ra BTC', tx('web.ui.lan_ban_mua_lai'), tx('web.ui.sut_giam_lon_nhat_giu_theo'), tx('web.ui.tien_mat_cuoi_ky')].forEach((t, k) => hs.append(el('th', k ? 'r' : '', t)));
    const ts = el('tbody');
    if (!sd.sims.length) { const tr = el('tr'); const td = el('td', 'muted', tx('web.ui.chua_du_du_lieu_de_mo')); td.colSpan = 7; tr.append(td); ts.append(tr); }
    sd.sims.forEach((x) => { const tr = el('tr'), better = x.tcGT > x.giuGT * 1.001, worse = x.tcGT < x.giuGT * 0.999;
      tr.append(el('td', 'num', `${fmtDate(x.tu)} → ${fmtDate(x.den)}`), el('td', 'r num', usd(x.giuGT)), el('td', 'r num ' + (better ? 'good' : worse ? 'bad' : ''), usd(x.tcGT)), el('td', 'r num', nf(3).format(x.tcBTC) + ' BTC'),
        el('td', 'r num', `${x.ban} / ${x.mua}`), el('td', 'r num', `${spc(x.mddH)} / ${spc(x.mdd)}`), el('td', 'r num', usd(x.tienMat))); ts.append(tr); });
    const ths = el('thead'); ths.append(hs); $('t-sim').replaceChildren(ths, ts);
    if (st.mode === 'sell') requestAnimationFrame(drawSellChart);
  }

  let sgeo = null;
  function drawSellChart() {
    const sd = st.sdFull, cv = $('s-chart'); if (!sd || !cv.clientWidth) return;
    const cs = getComputedStyle(document.documentElement), c = (n) => cs.getPropertyValue(n).trim(), S = st.S;
    const W = cv.clientWidth, H = baseH(cv), dpr = window.devicePixelRatio || 1;
    cv.style.height = H + 'px'; cv.width = W * dpr; cv.height = H * dpr; const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H); g.font = `12px ${c('--font')}`;
    const ser = sd.series.filter((x) => x.on.some((f) => f != null)); if (!ser.length) return;
    const fams = Object.keys(B3.NHOM_TP), lane = 9, lanes = fams.length * (lane + 3), L = Math.ceil(Math.max(...fams.map((f) => g.measureText(B3.NHOM_TP[f]).width))) + 14, R = 10, T = 8, B = 24 + lanes + 6, ph = H - T - B;
    let lo = Infinity, hi = 0; ser.forEach((x) => { lo = Math.min(lo, S.price[x.i]); hi = Math.max(hi, S.price[x.i]); }); lo *= 0.8; hi *= 1.15;
    const t0 = Date.parse(ser[0].date), t1 = Date.parse(ser[ser.length - 1].date), x = (d) => L + ((Date.parse(d) - t0) / Math.max(1, t1 - t0)) * (W - L - R);
    const y = (p) => T + ph - ((Math.log(p) - Math.log(lo)) / (Math.log(hi) - Math.log(lo))) * ph, bw = Math.max(1, (W - L - R) / ser.length + 0.6);
    ser.forEach((s) => { if (!s.n) return; g.fillStyle = c('--cinnabar'); g.globalAlpha = Math.min(0.4, 0.12 * s.n); g.fillRect(x(s.date) - bw / 2, T, bw, ph); }); g.globalAlpha = 1;
    const ticks = []; for (let e = -1; e <= 6; e++) for (const m2 of [1, 3]) { const t = m2 * 10 ** e; if (t >= lo && t <= hi) ticks.push(t); }
    g.strokeStyle = c('--line'); g.fillStyle = c('--muted'); g.lineWidth = 1; g.textAlign = 'right'; g.textBaseline = 'middle';
    ticks.forEach((t) => { const yy = Math.round(y(t)) + 0.5; g.beginPath(); g.moveTo(L, yy); g.lineTo(W - R, yy); g.stroke(); g.fillText(t >= 1000 ? nf(0).format(t / 1000) + 'k' : nf(t < 1 ? 1 : 0).format(t), L - 6, yy); });
    const trustedIdx = B3.TP.map((t, k) => (st.sdFull.crit[k].dangTin ? k : -1)).filter((k) => k >= 0);
    fams.forEach((f, r) => {
      const yy = T + ph + 8 + r * (lane + 3); g.fillStyle = c('--muted'); g.textAlign = 'right'; g.fillText(B3.NHOM_TP[f], L - 6, yy + lane / 2);
      g.fillStyle = c('--line'); g.globalAlpha = 0.5; g.fillRect(L, yy, W - L - R, lane); g.globalAlpha = 1;
      ser.forEach((s) => { const ks = B3.TP.map((t, k) => k).filter((k) => B3.TP[k].nhom === f && s.on[k]); if (!ks.length) return; const tr = ks.some((k) => trustedIdx.includes(k));
        g.fillStyle = c(FAMCOL[f]); g.globalAlpha = tr ? 1 : 0.3; g.fillRect(x(s.date) - bw / 2, yy, bw, lane); });
      g.globalAlpha = 1;
    });
    g.textAlign = 'center'; g.textBaseline = 'top'; g.fillStyle = c('--muted'); let lx = -1e9;
    for (let yr = Number(ser[0].date.slice(0, 4)) + 1; yr <= Number(ser[ser.length - 1].date.slice(0, 4)); yr++) { const xx = x(yr + '-01-01'); if (xx - lx > 34) { g.fillText(String(yr), xx, H - 18); lx = xx; } }
    g.strokeStyle = c('--ink'); g.lineWidth = 1.5; g.beginPath(); ser.forEach((s, k) => (k ? g.lineTo(x(s.date), y(S.price[s.i])) : g.moveTo(x(s.date), y(S.price[s.i])))); g.stroke();
    const ad = S.dates[st.asOf]; if (ad >= ser[0].date) { const xx = x(ad); g.strokeStyle = c('--blue'); g.lineWidth = 2; g.setLineDash([5, 4]); g.beginPath(); g.moveTo(xx, T); g.lineTo(xx, T + ph); g.stroke(); g.setLineDash([]); }
    sgeo = { ser, x, y };
    $('s-legend').replaceChildren(...fams.map((f) => { const s = el('span'); const i = el('i'); i.style.background = `var(${FAMCOL[f]})`; s.append(i, B3.NHOM_TP[f]); return s; }), el('span', null, tx('web.ui.mau_nhat_tieu_chi_chua_dang')));
  }
  const snear = (ev) => { if (!sgeo) return null; const mx = ev.clientX - $('s-chart').getBoundingClientRect().left; let b = null, bd = 1e9; for (const s of sgeo.ser) { const d = Math.abs(sgeo.x(s.date) - mx); if (d < bd) { bd = d; b = s; } } return bd < 24 ? b : null; };
  $('s-chart').addEventListener('mousemove', (ev) => {
    const s = snear(ev), tip = $('s-tip'); if (!s) { tip.style.display = 'none'; return; }
    const names = B3.TP.filter((t, k) => s.on[k]).map((t) => t.ten);
    tip.replaceChildren(el('b', null, `${fmtDate(s.date)}, ${usd(st.S.price[s.i])}`), el('span', null, tx('web.ui.s_0_nhom_dang_tin_dang_bat', s.n)), el('br'), el('span', 'muted', names.length ? names.slice(0, 4).join('; ') + (names.length > 4 ? '…' : '') : tx('web.ui.khong_tieu_chi_nao_bat')));
    tip.style.display = 'block'; tip.style.left = Math.min($('s-chart-box').clientWidth - tip.offsetWidth - 8, Math.max(8, sgeo.x(s.date) + 14)) + 'px'; tip.style.top = Math.max(8, sgeo.y(st.S.price[s.i]) - 60) + 'px';
  });
  $('s-chart').addEventListener('mouseleave', () => { $('s-tip').style.display = 'none'; });
  $('s-chart').addEventListener('click', (ev) => { const s = snear(ev); if (s) { setDate(s.date); window.scrollTo({ top: 0, behavior: 'smooth' }); } });
  new ResizeObserver(() => { if (st.mode === 'sell' && st.sdFull) drawSellChart(); }).observe($('s-chart-box'));
  $('dl-tp').addEventListener('click', () => download(`tieu-chi-chot-loi-bot-btc-${st.sd.date}.csv`, B3.csvSell(st.sd), 'text/csv;charset=utf-8'));

  function baseH(cv) { if (!cv.dataset.h) cv.dataset.h = cv.getAttribute('height') || '300'; return Number(cv.dataset.h); }
  // ---------- biểu đồ từng chỉ số ----------
  function drawIndCharts() {
    const a = st.a, S = st.S, box = $('ind-charts'); if (!a) return;
    const cs = getComputedStyle(document.documentElement), c = (n) => cs.getPropertyValue(n).trim();
    const start = S.dates.findIndex((d) => d >= '2014-01-01');
    const weeks = []; for (let i = Math.max(0, start); i < S.price.length; i++) if (new Date(S.dates[i] + 'T00:00:00Z').getUTCDay() === 0 || i === S.price.length - 1) weeks.push(i);
    box.replaceChildren(...a.ids.map((id) => {
      const d = IND.find((x) => x.id === id), card = el('div', 'ind-card'), cv = el('canvas'); cv.setAttribute('height', '170');
      const pts = weeks.map((i) => [i, S.v[id][i]]).filter((p) => p[1] != null);
      const now = S.v[id][st.asOf], sc = d.vote ? (d.high ? (now >= d.vote[1] ? 2 : now >= d.vote[0] ? 1 : now < d.vote[2] ? -1 : 0) : (now <= d.vote[1] ? 2 : now <= d.vote[0] ? 1 : now >= d.vote[2] ? -1 : 0)) : null;
      const hd = el('div', 'h'); hd.append(el('b', null, d.ten));
      hd.append(el('span', sc == null ? 'muted' : sc > 0 ? 'good' : sc < 0 ? 'bad' : 'muted', `${fmtDate(S.dates[st.asOf])}: ${now == null ? '—' : nf(d.dec).format(now) + (d.unit || '')}${sc == null ? '' : sc > 0 ? tx('web.ui.vung_re') : sc < 0 ? tx('web.ui.vung_nong') : tx('web.ui.binh_thuong')}`));
      card.append(hd, cv);
      requestAnimationFrame(() => {
        if (!pts.length || !cv.clientWidth) return;
        const W = cv.clientWidth, H = 170, dpr = window.devicePixelRatio || 1; cv.style.height = H + 'px'; cv.width = W * dpr; cv.height = H * dpr;
        const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.font = `11px ${c('--font')}`;
        const vals = pts.map((p) => p[1]).sort((x, y) => x - y), q = (f) => vals[Math.min(vals.length - 1, Math.floor(f * (vals.length - 1)))];
        let lo = q(0.005), hi = q(0.995); if (d.vote) { lo = Math.min(lo, d.vote[1], d.vote[0]); hi = Math.max(hi, d.vote[2] * 1.05); }
        if (now != null) { lo = Math.min(lo, now); hi = Math.max(hi, now); }
        const pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
        const L = 44, R = 8, T = 6, B = 18, ph = H - T - B, t0 = Date.parse(S.dates[pts[0][0]]), t1 = Date.parse(S.dates[pts[pts.length - 1][0]]);
        const x = (i) => L + ((Date.parse(S.dates[i]) - t0) / Math.max(1, t1 - t0)) * (W - L - R), y = (v) => T + ph - ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * ph;
        if (d.vote) {
          const [b1, , hot] = d.vote;
          g.globalAlpha = 0.14; g.fillStyle = c('--jade');
          if (d.high) g.fillRect(L, T, W - L - R, y(b1) - T); else g.fillRect(L, y(b1), W - L - R, T + ph - y(b1));
          g.fillStyle = c('--cinnabar');
          if (d.high) g.fillRect(L, y(hot), W - L - R, T + ph - y(hot)); else g.fillRect(L, T, W - L - R, y(hot) - T);
          g.globalAlpha = 1;
        }
        g.strokeStyle = c('--line'); g.fillStyle = c('--muted'); g.lineWidth = 1; g.textAlign = 'right'; g.textBaseline = 'middle';
        [lo + pad, (lo + hi) / 2, hi - pad].forEach((v) => { const yy = Math.round(y(v)) + 0.5; g.beginPath(); g.moveTo(L, yy); g.lineTo(W - R, yy); g.stroke(); g.fillText(nf(Math.abs(v) >= 10 ? 0 : 2).format(v), L - 5, yy); });
        g.textAlign = 'center'; g.textBaseline = 'top'; let lx = -1e9;
        for (let yr = Number(S.dates[pts[0][0]].slice(0, 4)) + 1; yr <= Number(S.dates[pts[pts.length - 1][0]].slice(0, 4)); yr++) { const xx = L + ((Date.parse(yr + '-01-01') - t0) / (t1 - t0)) * (W - L - R); if (xx - lx > 34) { g.fillText(String(yr).slice(2), xx, H - 14); lx = xx; } }
        g.strokeStyle = c('--ink'); g.lineWidth = 1.3; g.beginPath(); pts.forEach((p, k) => (k ? g.lineTo(x(p[0]), y(p[1])) : g.moveTo(x(p[0]), y(p[1])))); g.stroke();
        const xa = x(st.asOf); g.strokeStyle = c('--blue'); g.lineWidth = 1.5; g.setLineDash([4, 3]); g.beginPath(); g.moveTo(xa, T); g.lineTo(xa, T + ph); g.stroke(); g.setLineDash([]);
        if (now != null) { g.fillStyle = c('--blue'); g.beginPath(); g.arc(xa, y(now), 3.5, 0, Math.PI * 2); g.fill(); }
      });
      return card;
    }));
  }
  let indW = 0;
  new ResizeObserver(() => { const w = $('ind-charts').clientWidth; if (st.a && Math.abs(w - indW) > 2) { indW = w; drawIndCharts(); } }).observe($('ind-charts'));
  $('copy-md').addEventListener('click', async () => {
    const text = claudePackage();
    try { await navigator.clipboard.writeText(text); } catch (e) { const ta = el('textarea'); ta.value = text; document.body.append(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
    $('copy-msg').textContent = tx('web.ui.da_sao_chep_dan_vao_khung');
  });
  const KEY_STORE = 'btc-claude-key';
  try { const k = localStorage.getItem(KEY_STORE); if (k) { $('ck').value = k; $('ck-remember').checked = true; } } catch (e) { /* bỏ qua */ }
  $('ck-remember').addEventListener('change', () => { try { if ($('ck-remember').checked) localStorage.setItem(KEY_STORE, $('ck').value.trim()); else localStorage.removeItem(KEY_STORE); } catch (e) { /* bỏ qua */ } });
  $('ck').addEventListener('change', () => { try { if ($('ck-remember').checked) localStorage.setItem(KEY_STORE, $('ck').value.trim()); } catch (e) { /* bỏ qua */ } });

  const SYS = tx('web.ui.ban_la_chuyen_gia_phan_tich');
  const chat = [];
  function mdToNodes(text) {
    const box = el('div'); const lines = text.split('\n'); let list = null, tbl = null;
    const inline = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/(^|\s)\*(\S.+?)\*(?=\s|$)/g, '$1<i>$2</i>');
    for (const raw of lines) {
      const t = raw.trim();
      if (/^\|.*\|$/.test(t)) {
        if (/^\|[\s:|-]+\|$/.test(t)) continue;
        if (!tbl) { tbl = el('table'); const w = el('div', 'box md-tbl'); w.append(tbl); box.append(w); }
        const tr = el('tr'); t.slice(1, -1).split('|').forEach((c) => { const td = el(tbl.rows.length ? 'td' : 'th'); td.innerHTML = inline(c.trim()); tr.append(td); }); tbl.append(tr); list = null; continue;
      }
      tbl = null;
      const m = t.match(/^([-*•]|\d+\.)\s+(.*)$/);
      if (m) { const ord = /\d/.test(m[1]); if (!list || list.tagName !== (ord ? 'OL' : 'UL')) { list = el(ord ? 'ol' : 'ul'); box.append(list); } const li = el('li'); li.innerHTML = inline(m[2]); list.append(li); continue; }
      list = null; if (!t) continue;
      const h = t.match(/^#{1,4}\s+(.*)$/); const p = el(h ? 'h4' : 'p'); p.innerHTML = inline(h ? h[1] : t); box.append(p);
    }
    return box;
  }
  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  function srcNodes(srcs) {
    if (!srcs || !srcs.length) return [];
    const ol = el('ol', 'srcs'); srcs.forEach((x) => { const li = el('li'); const a = el('a', null, x.title); a.href = x.url; a.target = '_blank'; a.rel = 'noopener'; li.append(a); ol.append(li); });
    return [el('div', 'sub', tx('web.ui.nguon_claude_da_doc')), ol];
  }
  function addMsg(role, text, srcs) {
    const m = el('div', 'msg ' + role);
    if (role === 'assistant') m.append(mdToNodes(text), ...srcNodes(srcs));
    else m.textContent = text;
    $('chat').append(m); m.scrollIntoView({ behavior: 'smooth', block: 'end' });
    return m;
  }
  // Hồ sơ dữ liệu gửi kèm câu hỏi đầu tiên: kết quả đã kiểm định từ báo cáo tuần (KN) và lựa chọn của người dùng; không lưu lại.
  function dossier() {
    const pick = (id) => { const s = $(id); return s && s.value ? s.options[s.selectedIndex].text : null; };
    const amt = PLAN ? parseAmount($('plan-amount').value) : null, F = KN && KN.forecast;
    return {
      thoi_diem_hoi: new Date().toISOString(),
      gia_truc_tiep_chi_de_hien_thi: st.raw.live ? st.raw.live.price : null,
      ngay_phan_tich: st.a ? st.a.date : null,
      ngay_phan_tich_la_hom_nay: !!st.S && st.asOf === st.S.price.length - 1,
      khuyen_nghi_tuan: KN ? { he_so: knStale() ? 1 : KN.multiplier, che_do: KN.mode, ly_do: KN.reasons, cap_nhat: KN.generated_at, du_lieu_cu: knStale(), do_moi: KN.freshness } : null,
      ban_xay_lai: RB,
      xac_suat_co_lai_da_hieu_chinh: KN && KN.calib ? KN.calib : null,
      su_kien: KN ? { danh_sach: KN.events, moc_chot: KN.events_meta || null } : null,
      du_bao_dai_gia: F ? { ngay_goc: F.anchor, gia_goc: F.price, phien_ban: F.version, dai: F.rows,
        kiem_chung_lich_su: Object.fromEntries(Object.entries(F.check || {}).map(([k, v]) => [k, v.vol])), kiem_chung_truc_tiep: F.log, so_sanh_phuong_phap: F.search || null } : null,
      ke_hoach_giai_ngan: PLAN ? { ...PLAN, so_tien_nguoi_dung: amt > 0 ? { so_tien: amt, don_vi: pl.unit, bat_dau: $('plan-start').value } : null } : null,
      gia_cho_mua_va_ngay_re_nhat: EN ? { ngay_goc: EN.anchor, gia_dong_bitstamp: EN.price, do_dao_dong_ngay: EN.sigma, phien_ban: EN.version,
        gia_thap_nhat_k_ngay_toi: EN.rows.map(({ z, ...r }) => r), kiem_chung_lich_su: EN.check, mua_ngay_hay_cho: EN.wait, ngay_re_nhat_7_ngay: EN.cheapest,
        kiem_chung_truc_tiep: EN.log, gia_nguoi_dung_muon_mua: targetOf('buy') > 0 ? { gia: targetOf('buy'), so_voi_gia_luc_tra: targetOf('buy') / refPrice() - 1 } : null } : null,
      gia_cho_ban_va_ngay_dat_nhat: EX ? { ngay_goc: EX.anchor, gia_dong_bitstamp: EX.price, do_dao_dong_ngay: EX.sigma, phien_ban: EX.version,
        gia_cao_nhat_k_ngay_toi: EX.rows.map(({ z, ...r }) => r), kiem_chung_lich_su: EX.check, ban_ngay_hay_cho: EX.wait, ngay_dat_nhat_7_ngay: EX.highest,
        kiem_chung_truc_tiep: EX.log, gia_nguoi_dung_muon_ban: targetOf('sell') > 0 ? { gia: targetOf('sell'), so_voi_gia_luc_tra: targetOf('sell') / refPrice() - 1 } : null } : null,
      gia_truc_tiep_24_gio: live.day ? { mo_cua: live.day.open, cao: live.day.high, thap: live.day.low, dang_truc_tiep: streaming() } : null,
      ho_so_nguoi_dung: { thoi_gian_nam_giu: pick('cp-horizon'), chiu_giam_tam_thoi: pick('cp-drawdown'), ty_trong_btc: pick('cp-share') },
    };
  }
  const apiError = (status, j) => (status === 401 ? tx('web.ui.khoa_api_khong_hop_le') : status === 429 ? tx('web.ui.claude_dang_gioi_han_so_luot')
    : status === 529 || (j.error && j.error.type === 'overloaded_error') ? tx('web.ui.claude_qua_tai') : tx('web.ui.claude_api_bao_loi_0_1', status, (j.error && j.error.message) || ''));
  // Đọc luồng sự kiện (SSE) của Messages API, dựng lại các khối nội dung để gửi lại nguyên vẹn khi gặp pause_turn.
  async function readStream(r, onEvent) {
    const reader = r.body.getReader(), dec = new TextDecoder(), blocks = [], json = {};
    let buf = '', stopReason = null, stopDetails = null;
    const handle = (d) => {
      if (d.type === 'content_block_start') {
        blocks[d.index] = { ...d.content_block };
        if (d.content_block.type === 'server_tool_use' || d.content_block.type === 'tool_use') json[d.index] = '';
      } else if (d.type === 'content_block_delta') {
        const b = blocks[d.index], x = d.delta;
        if (x.type === 'text_delta') { b.text = (b.text || '') + x.text; onEvent({ kind: 'text', text: x.text }); }
        else if (x.type === 'citations_delta') (b.citations = b.citations || []).push(x.citation);
        else if (x.type === 'thinking_delta') { b.thinking = (b.thinking || '') + x.thinking; onEvent({ kind: 'thinking', text: b.thinking }); }
        else if (x.type === 'signature_delta') b.signature = (b.signature || '') + x.signature;
        else if (x.type === 'input_json_delta') json[d.index] += x.partial_json;
      } else if (d.type === 'content_block_stop') {
        const b = blocks[d.index];
        if (b && d.index in json) { try { b.input = json[d.index] ? JSON.parse(json[d.index]) : {}; } catch (e) { b.input = {}; } onEvent({ kind: 'tool', block: b }); }
      } else if (d.type === 'message_delta') { stopReason = d.delta.stop_reason || stopReason; stopDetails = d.delta.stop_details || stopDetails; }
      else if (d.type === 'error') throw new Error(apiError(0, d));
    };
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true }).replace(/\r\n/g, '\n');
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const data = buf.slice(0, i).split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim()).join('');
        buf = buf.slice(i + 2);
        if (data) handle(JSON.parse(data));
      }
    }
    return { blocks: blocks.filter(Boolean), stopReason, stopDetails };
  }
  let aiAbort = null;
  async function callClaude(onEvent) {
    const key = $('ck').value.trim(); if (!key) throw new Error(tx('web.ui.hay_dan_khoa_api_cua_claude'));
    const model = $('cmodel').value, current = !/haiku/.test(model);  // Opus 5.5 / Sonnet 5.5: web search with dynamic filtering and server-side fallback
    const body = { model, max_tokens: 32000, stream: true, system: SYS, cache_control: { type: 'ephemeral' },
      thinking: { type: 'adaptive', display: 'summarized' }, output_config: { effort: $('ceffort').value }, messages: chat.map((x) => ({ role: x.role, content: x.content })) };
    if ($('cweb').checked) body.tools = [{ type: current ? 'web_search_20260209' : 'web_search_20250305', name: 'web_search', max_uses: 5 }];
    const headers = { 'content-type': 'application/json', 'x-api-key': key, 'anthropic-version': '2026-10-21', 'anthropic-dangerous-direct-browser-access': 'true' };
    let fallback = current, text = '', srcs = [], res = null;
    aiAbort = new AbortController();
    for (let k = 0; k < 6; k++) {
      const req = fallback ? { ...body, fallbacks: 'default' } : body;
      let r;
      try {
        r = await fetch('https://api.anthropic.com/v1/messages', { method: 'POST', signal: aiAbort.signal, body: JSON.stringify(req),
          headers: fallback ? { ...headers, 'anthropic-beta': 'server-side-fallback-2026-07-01' } : headers });
      } catch (e) {
        if (e.name === 'AbortError') throw e;
        if (fallback) { fallback = false; k--; continue; }  // a network path that rejects the beta header: try once without the fallback
        throw new Error(tx('web.ui.khong_ket_noi_duoc_claude_api'));
      }
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        if (fallback && r.status === 400 && /fallback|beta/i.test((j.error && j.error.message) || '')) { fallback = false; k--; continue; }
        throw new Error(apiError(r.status, j));
      }
      res = await readStream(r, onEvent);
      for (const b of res.blocks) {
        if (b.type === 'text') { text += b.text || ''; (b.citations || []).forEach((c) => c.url && srcs.push({ title: c.title || c.url, url: c.url })); }
        if (b.type === 'web_search_tool_result' && Array.isArray(b.content)) b.content.forEach((x) => x.url && srcs.push({ title: x.title || x.url, url: x.url }));
      }
      if (res.stopReason === 'pause_turn') { body.messages = [...body.messages, { role: 'assistant', content: res.blocks }]; continue; }
      break;
    }
    if (res && res.stopReason === 'refusal') throw new Error(tx('web.ui.claude_tu_choi', (res.stopDetails && (res.stopDetails.explanation || res.stopDetails.category)) || '—'));
    const seen = new Set(); srcs = srcs.filter((x) => !seen.has(x.url) && seen.add(x.url)).slice(0, 12);
    return { text: text.trim(), srcs, cut: !!res && res.stopReason === 'max_tokens' };
  }
  async function sendToClaude(q, first) {
    const btns = [$('ai-first'), $('ai-send')]; btns.forEach((b) => { b.disabled = true; }); $('ai-busy').hidden = false; $('ai-err').hidden = true; $('ai-stop').hidden = false;
    const content = first ? tx('web.ui.day_la_bao_cao_moi_nhat', JSON.stringify(dossier()), report(false), q) : q;
    chat.push({ role: 'user', content }); addMsg('user', q);
    const m = el('div', 'msg assistant'), status = el('p', 'muted', tx('web.ui.claude_dang_suy_luan')), out = el('div');
    m.append(status, out); $('chat').append(m);
    let live = '', raf = 0;
    const paint = () => { raf = 0; out.replaceChildren(mdToNodes(live)); };
    const onEvent = (ev) => {
      if (ev.kind === 'thinking' && !live) status.textContent = `${tx('web.ui.claude_dang_suy_luan')} ${ev.text.trim().split(/\n+/).pop().slice(-160)}`;
      else if (ev.kind === 'tool' && ev.block.name === 'web_search') status.textContent = tx('web.ui.claude_dang_tim_tin', (ev.block.input && ev.block.input.query) || '');
      else if (ev.kind === 'text') { live += ev.text; status.textContent = tx('web.ui.claude_dang_viet'); if (!raf) raf = requestAnimationFrame(paint); }
    };
    const settle = () => { if (raf) cancelAnimationFrame(raf); raf = 0; };  // a pending redraw must not overwrite the final answer
    try {
      const r = await callClaude(onEvent);
      settle();
      const final = (r.text || tx('web.ui.claude_khong_tra_loi_noi_dung')) + (r.cut ? '\n\n' + tx('web.ui.claude_cat_ngang') : '');
      status.remove(); out.replaceChildren(mdToNodes(final), ...srcNodes(r.srcs));
      chat.push({ role: 'assistant', content: r.text || tx('web.ui.claude_khong_tra_loi_noi_dung') });
    } catch (e) {
      settle();
      if (e.name === 'AbortError' && live) { status.remove(); out.replaceChildren(mdToNodes(live + '\n\n' + tx('web.ui.claude_da_dung'))); chat.push({ role: 'assistant', content: live }); }
      else { m.remove(); chat.pop(); if (e.name !== 'AbortError') { $('ai-err').textContent = e.message; $('ai-err').hidden = false; } }
    } finally { btns.forEach((b) => { b.disabled = false; }); $('ai-busy').hidden = true; $('ai-stop').hidden = true; aiAbort = null; }
  }
  $('ai-stop').addEventListener('click', () => { if (aiAbort) aiAbort.abort(); });
  $('ai-first').addEventListener('click', () => { chat.length = 0; $('chat').replaceChildren(); sendToClaude(tx('web.ui.hay_nhan_dinh_ve_ket_luan'), true); });
  $('ai-send').addEventListener('click', () => { const q = $('ai-q').value.trim(); if (!q) return; $('ai-q').value = ''; sendToClaude(q, chat.length === 0); });
  $('ai-q').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) $('ai-send').click(); });

  // ---------- khuyến nghị giải ngân tuần này (chế độ an toàn: mua đều khi mô hình chưa đạt hoặc dữ liệu cũ) ----------
  // ⚠ for an indicator set: fewer than 10 independent episodes, or 6-month results of the two halves more than 20 points apart
  function warnOf(eps, h1, h2) {
    if (eps < 10) return tx('web.kn.warn_eps', eps);
    if (h1 && h2 && h1.n && h2.n && Math.abs(h1.win - h2.win) > 0.2) return tx('web.kn.warn_halves', nf(0).format(Math.abs(h1.win - h2.win) * 100));
    return null;
  }
  const knStale = () => !!KN && (Date.now() - Date.parse(KN.generated_at)) / 86400000 > KN.stale_data_days;
  function renderKN() {
    const stale = knStale(), m = !KN || stale ? 1 : KN.multiplier, ex = KN ? KN.amount_example_usd : 100;
    const safe = !KN || stale || KN.mode === 'safe';
    $('kn-sum').replaceChildren(el('b', null, `${tx('web.kn.m_label')}: ${nf(1).format(m)}`), ` — ${tx('web.kn.amount', usd(ex * m), usd(ex))}. `,
      el('span', safe ? 'good' : 'mid', safe ? tx('web.kn.mode_safe') : tx('web.kn.mode_model', tx('web.kn.layer_' + KN.layer))));
    const notes = [];
    if (!KN) notes.push(el('p', 'warn', tx('web.kn.reason_missing')));
    else {
      if (stale || KN.reasons.includes('data_stale')) notes.push(el('p', 'warn', tx('web.kn.reason_data_stale')));
      if (KN.reasons.includes('model_failed') && RB) { const p = el('p', 'lead'); p.append(el('b', null, tx('web.kn.why')), whyRb()); notes.push(p); }
      else if (KN.reasons.includes('model_failed')) { const p = el('p', 'lead'); p.append(el('b', null, tx('web.kn.why')), tx('web.kn.reason_model_failed'), ' ', tx('web.kn.current_zone_note')); notes.push(p); }
    }
    $('kn-notes').replaceChildren(...notes);
    if (RB) renderCriteriaRb();
    else renderEvidenceOld();
    const evs = KN ? KN.events.map((e) => el('li', e.flag ? 'err' : null, e.flag ? tx('web.kn.ev_flag', vnTime(e.time), tx('web.kn.ev_' + e.type)) : tx('web.kn.event_line', vnTime(e.time), tx('web.kn.ev_' + e.type)))) : [];
    const meta = (KN && KN.events_meta) || {};
    if (meta.rerun_after) evs.push(el('li', 'err', tx('web.kn.rerun', fmtDate(meta.rerun_after))));
    for (const [k, d] of Object.entries(meta.stale || {})) evs.push(el('li', null, tx('web.kn.stale_cal', tx('web.kn.ev_' + k), d ? fmtDate(d) : '—')));
    $('kn-events').replaceChildren(...(evs.length ? evs : [el('li', null, tx('web.kn.events_none'))]), ...(KN && !KN.event_delay ? [el('li', null, tx('web.kn.no_delay'))] : []));
    $('kn-fresh').replaceChildren(...(KN ? Object.entries(KN.freshness).map(([k, s]) => el('li', s.ok ? 'ok' : 'err',
      !s.ok ? tx('web.kn.fresh_err', tx('sources.' + k), s.error) : s.via ? tx('web.kn.fresh_via', tx('sources.' + k), fmtDate(s.last), s.via, s.age_days)
        : tx('web.kn.fresh_ok', tx('sources.' + k), fmtDate(s.last)))) : []));
    if (KN) { $('updated').textContent = tx('web.home.kn_time', vnTime(KN.generated_at)); $('updated').hidden = false; }
    $('stale').hidden = !stale;
    if (stale) $('stale').textContent = tx('web.kn.stale_banner', vnTime(KN.generated_at));
  }
  // ----- bản xây lại: 6 tiêu chí chấp nhận (Phần I), đọc tuần này từ mô hình đóng băng (KN.rebuild) -----
  const RB = KN && KN.rebuild && KN.rebuild.acceptance ? KN.rebuild : null;
  const ZN = (z) => (z ? tx('web.rb.zone_' + z) : '—');
  const rk = (x) => (x == null ? '—' : nf(0).format(x));
  function whyRb() {
    const A = RB.acceptance, n = Object.values(A.criteria).filter((c) => c.pass).length;
    return tx('web.kn.why_rb', n, fmtDate(A.holdout_start), fmtDate(A.last_week), A.holdout_weeks, fmtDate(A.run_at.slice(0, 10)));
  }
  function renderCriteriaRb() {
    const C = RB.acceptance.criteria, dec = (x, d) => (x == null || !isFinite(x) ? '—' : nf(d).format(x));
    const yrs = Object.values(C.c1.years || {}), mono = Object.values(C.c4.monotone || {}), h6 = C.c6.holdout || {};
    const val = {
      c1: tx('web.kn.c1_v', yrs.filter((v) => v > 0).length, yrs.length, spc(C.c1.holdout, 1)),
      c2: tx('web.kn.c2_v', spc(C.c2.holdout, 1), spc(C.c2.ci && C.c2.ci[0], 1), spc(C.c2.ci && C.c2.ci[1], 1)),
      c3: tx('web.kn.c3_v', dec(C.c3.p_ic, 3), dec(C.c3.p_cost, 3)),
      c4: tx('web.kn.c4_v', mono.filter(Boolean).length, mono.length, C.c4.drops ?? '—', C.c4.model_weeks ?? '—'),
      c5: C.c5.weeks ? tx('web.kn.c5_v', dec(C.c5.brier, 3), dec(C.c5.brier_base, 3), C.c5.weeks) : tx('web.kn.c5_none'),
      c6: tx('web.kn.c6_v', spc(h6['Lồng nhau'], 1), spc(h6['Quy tắc MVRV'], 1), spc(h6['Quy tắc Giá/MA 200 tuần'], 1)),
    };
    $('kn-cmp-title').textContent = tx('web.kn.crit_title');
    const h = el('tr');
    ['#', tx('web.kn.col_crit'), tx('web.kn.col_result'), tx('web.kn.col_pass')].forEach((x, i) => h.append(el('th', i === 3 ? 'r' : '', x)));
    const tb = el('tbody');
    Object.keys(val).forEach((k, i) => { const tr = el('tr'); tr.append(el('td', 'num', String(i + 1)), el('td', null, tx('web.kn.' + k)), el('td', 'num', val[k]),
      el('td', 'r ' + (C[k].pass ? 'good' : 'bad'), tx(C[k].pass ? 'web.kn.pass_yes' : 'web.kn.pass_no'))); tb.append(tr); });
    const th = el('thead'); th.append(h); $('t-kn').replaceChildren(th, tb);
    $('kn-ev').replaceChildren(el('li', null, tx('web.rb.report_link')));
  }
  // ----- xác suất có lãi đã hiệu chỉnh 1/3/6/12 tháng, lợi nhuận dự đoán, bên mua và bên bán (KN.calib, bot/models/calib_prob.py) -----
  function renderCalib() {
    const C = KN && KN.calib && Object.keys(KN.calib).length ? KN.calib : null, sell = st.mode === 'sell';
    $('cp-title').textContent = tx(sell ? 'web.cp.title_sell' : 'web.cp.title');
    $('cp-lead').textContent = tx(sell ? 'web.cp.lead_sell' : 'web.cp.lead');
    if (!C) { $('cp-sum').replaceChildren(el('span', 'warn', tx('web.cp.none'))); for (const id of ['t-cp', 't-cp2', 'cp-notes']) $(id).replaceChildren(); return; }
    const hs = Object.keys(C).sort((a, b) => a - b), o = (h) => C[h], d3 = (x) => (x == null || !isFinite(x) ? '—' : nf(3).format(x));
    const pOf = (h) => (sell ? 1 - o(h).now.p : o(h).now.p), drop = (x) => (x == null ? null : 1 - x);
    const n0 = o(hs[0]).now, last = st.S ? st.S.price.length - 1 : -1;
    const price = last >= 0 ? st.S.price[last] : n0.close;
    const when = last >= 0 && st.raw.live ? tx('web.cp.price_live') : tx('web.cp.price_close', fmtDate(last >= 0 ? st.S.dates[last] : n0.close_date));
    const any = hs.some((h) => o(h).pick), items = hs.map((h) => tx('web.cp.sum_item', tx('web.cp.h_' + h), pc(pOf(h)))).join(', ');
    const p1 = el('p'); p1.append(el('b', null, tx(sell ? 'web.cp.sum_sell' : 'web.cp.sum', items)));
    const sum = [p1, el('p', null, tx('web.cp.price_now', usd(price), when, fmtDate(n0.date)))];
    sum.push(el('p', null, tx(any ? 'web.cp.sum_pick' : sell ? 'web.cp.sum_nopick_sell' : 'web.cp.sum_nopick')));
    if (sell && hs.every((h) => pOf(h) < 0.5)) sum.push(el('p', null, tx('web.cp.sum_hold')));
    $('cp-sum').replaceChildren(...sum);
    const table = (id, cols, rows) => {
      const head = el('tr'); cols.forEach((k, i) => head.append(el('th', i ? 'r' : '', tx('web.cp.' + k))));
      const th = el('thead'), tb = el('tbody'); th.append(head); rows.forEach((r) => tb.append(r)); $(id).replaceChildren(th, tb);
    };
    const cell = (main, sub, cls = 'r num') => { const td = el('td', cls, main); if (sub) td.append(el('span', 'sub', sub)); return td; };
    table('t-cp', sell ? ['col_h_sell', 'col_p_sell', 'col_ret_sell', 'col_price', 'col_pick_sell'] : ['col_h', 'col_p', 'col_ret', 'col_price', 'col_pick'], hs.map((h) => {
      const x = o(h), q = x.ret ? x.ret.now.q : null, tr = el('tr', x.pick ? 'here' : '');
      tr.append(el('td', 'nowrap', tx('web.cp.h_' + h)), el('td', 'r num', pc(pOf(h))),
        cell(q ? spc(q[1]) : '—', q ? tx('web.cp.ret_sub', spc(q[0]), spc(q[2])) : ''),
        cell(q ? usd(price * (1 + q[1])) : '—', q ? tx('web.cp.price_sub', usd(price * (1 + q[0])), usd(price * (1 + q[2]))) : ''),
        el('td', 'r ' + (x.pick ? 'good' : 'muted'), tx(x.pick ? 'web.cp.pick_yes' : 'web.cp.pick_no')));
      return tr;
    }));
    const flagCell = (f, fn) => (f && f.weeks ? cell(pc(fn(f.win)), tx('web.cp.said80_sub', f.weeks, f.episodes, pc(fn(f.base)))) : cell(tx('web.cp.said80_none'), ''));
    table('t-cp2', sell ? ['col_h', 'col_logit_sell', 'col_bins_sell', 'col_brier', 'col_said20', 'col_bottom20', 'col_cover'] : ['col_h', 'col_logit', 'col_bins', 'col_brier', 'col_said80', 'col_cover'], hs.map((h) => {
      const x = o(h), m = x.methods, best = m[x.best], tr = el('tr'), r = x.ret, rm = r ? r.methods[r.now.method] : null;
      const f = sell ? drop : (v) => v;
      tr.append(el('td', 'nowrap', tx('web.cp.h_' + h)), el('td', 'r num muted', pc(f(x.now.logit_p))), el('td', 'r num muted', pc(f(x.now.bins_p))),
        cell(tx('web.cp.brier_cell', d3(m.base.brier), d3(best.brier)), tx('web.cp.brier_sub', d3(m.base.brier - best.brier), d3(best.gain_ci[0]), d3(best.gain_ci[1]))));
      if (sell) tr.append(flagCell(x.said20 && x.said20.logit, drop), flagCell(x.bottom20, drop));
      else tr.append(flagCell(x.said80 && x.said80.logit, (v) => v));
      tr.append(cell(rm ? pc(rm.cover80) : '—', rm ? tx('web.cp.cover_sub', r.weeks) : ''));
      return tr;
    }));
    const lastH = o(hs[hs.length - 1]), retBins = hs.some((h) => o(h).ret && o(h).ret.now.method === 'bins');
    const notes = sell ? [tx('web.cp.note_sell_same'), tx('web.cp.note_method'), tx('web.cp.note_rule')] : [tx('web.cp.note_method'), tx('web.cp.note_rule'), tx('web.cp.note_overconf')];
    notes.push(tx(retBins ? 'web.cp.note_ret_bins' : 'web.cp.note_ret_base'));
    if (lastH.h >= 52) notes.push(tx('web.cp.note_few', nf(0).format(lastH.weeks / lastH.h), fmtDate(lastH.from), fmtDate(lastH.to)));
    notes.push(tx('web.cp.note_data', fmtDate(o(hs[0]).from), fmtDate(lastH.to)), tx('web.fc.note_ref'));
    $('cp-notes').replaceChildren(...notes.map((x) => el('li', null, x)));
  }
  function renderRebuild() {
    if (!RB) {
      $('rb-sum').replaceChildren(el('span', 'warn', tx('web.rb.none')));
      for (const id of ['t-rb-zones', 't-rb-scn', 'rb-notes']) $(id).replaceChildren();
      $('rb-scn-title').textContent = '';
      return;
    }
    const W = RB.week, M = RB.model, F = RB.fed;
    const sum = [el('p', null, tx('web.rb.week', fmtDate(W.date), usd(W.close), rk(W.rank), ZN(W.zone), rk(W.rank_mvrv), ZN(W.zone_mvrv), rk(W.rank_200w), ZN(W.zone_200w))),
      el('p', null, tx('web.rb.rank_note')), el('p', null, tx('web.rb.sell', W.sell_groups, tx('web.rb.level_' + W.sell_level), RB.sell_trusted))];
    const fp = el('p', null, tx('web.rb.fed', tx('web.rb.reg_' + F.regime), fmtDate(F.since)));
    if (F.warn && F.warn.length) fp.append(' ', el('b', 'mid', tx('web.rb.fed_warn', F.warn.join(', '))));
    sum.push(fp);
    $('rb-sum').replaceChildren(...sum);
    const h = el('tr');
    ['col_strategy', 'col_zone', 'col_h', 'col_weeks', 'col_eps', 'col_win', 'col_base', 'col_diff', 'col_verdict'].forEach((k, i) => h.append(el('th', i > 2 && i < 8 ? 'r' : '', tx('web.rb.' + k))));
    const tb = el('tbody');
    for (const z of RB.zones) {
      const tr = el('tr'), v = z.verdict || 'it_dot';
      tr.append(el('td', null, z.strategy === 'Lồng nhau' ? tx('web.rb.strat_nested') : z.strategy), el('td', 'nowrap', ZN(z.zone)), el('td', 'nowrap', tx('web.rb.h_' + z.h)),
        el('td', 'r num', String(z.weeks)), el('td', 'r num', String(z.episodes)), el('td', 'r num', pc(z.win)), el('td', 'r num', pc(z.base)),
        el('td', 'r num nowrap', tx('web.rb.diff_cell', spc(z.diff, 1), spc(z.ci && z.ci[0], 1), spc(z.ci && z.ci[1], 1))),
        el('td', v === 'hon_moc' ? 'good' : v === 'kem_moc' ? 'bad' : 'muted', tx('web.rb.v_' + v)));
      tb.append(tr);
    }
    const th = el('thead'); th.append(h); $('t-rb-zones').replaceChildren(th, tb);
    const S = RB.scenarios, rng = (r) => (r == null ? '—' : Math.round(r[0]) === Math.round(r[1]) ? rk(r[0]) : `${rk(r[0])}–${rk(r[1])}`);
    $('rb-scn-title').textContent = S ? tx('web.rb.scn_title', S.k) : '';
    $('rb-scn-lead').textContent = S ? tx('web.rb.scn_lead', usd(W.close), fmtDate(W.date), S.k) : '';
    if (S) {
      const sh = el('tr');
      ['col_price', 'col_change', 'col_fng', 'col_200w', 'col_mvrv', 'col_sell'].forEach((k, i) => sh.append(el('th', i < 3 ? 'r' : '', tx('web.rb.' + k))));
      const sb = el('tbody');
      for (const r of S.rows) {
        const tr = el('tr', r.delta === 0 ? 'here' : '');
        tr.append(el('td', 'r num', usd(r.price)), el('td', 'r num', r.delta ? spc(r.delta) : tx('web.rb.now')), el('td', 'r num nowrap', `${rk(r.fng[1])} (${rk(r.fng[0])}–${rk(r.fng[2])})`),
          el('td', null, `${rng(r.range_200w)} → ${r.zones_200w.map(ZN).join(' / ')}`), el('td', null, `${rk(r.rank_mvrv)} (${rng(r.range_mvrv)}) → ${r.zones_mvrv.map(ZN).join(' / ')}`),
          el('td', null, `${rng(r.groups)} → ${r.levels.map((x) => tx('web.rb.level_' + x)).join(' / ')}`));
        sb.append(tr);
      }
      const sth = el('thead'); sth.append(sh); $('t-rb-scn').replaceChildren(sth, sb);
    } else $('t-rb-scn').replaceChildren();
    const notes = [tx('web.rb.model', M.version, fmtDate(M.asof), M.set, M.features.map(nameOfFeat).join(', ') || '—', M.dropped.length ? tx('web.rb.model_dropped', M.dropped.map(nameOfFeat).join(', ')) : '', M.weeks_logged)];
    if (S) notes.push(tx('web.rb.scn_note'));
    notes.push(tx('web.rb.report_link'));
    $('rb-notes').replaceChildren(...notes.map((x) => el('li', null, x)));
  }
  const nameOfFeat = (f) => { const d = IND.find((x) => x.id === f || x.id === FEAT_ID[f]); return d ? d.ten : f; };
  const FEAT_ID = { p_200wma: 'wma', mvrv: 'mvrv', fng: 'fng', pi_ratio: 'pi', puell: 'puell', mayer: 'mayer', rsi_14w: 'rsiw', dd_ath: 'dd', mvrv_z: 'mvrvz', vol_rel: 'vol' };
  function renderEvidenceOld() {
    const ev = KN && KN.evidence;
    const h = el('tr');
    [tx('web.kn.col_strategy'), tx('web.kn.col_median'), tx('web.kn.col_p10'), tx('web.kn.col_cba'), tx('web.kn.col_mdd'), tx('web.kn.col_placebo')]
      .forEach((x, k) => h.append(el('th', k >= 1 ? 'r' : '', x)));
    const tb = el('tbody'), tone = (v) => (v == null ? '' : v > 1.0005 ? 'good' : v < 0.9995 ? 'bad' : '');
    if (ev) for (const [key, name] of [['current_bot', tx('web.kn.row_current')], ['candidate', tx('web.kn.row_candidate')]]) {
      for (const [pk, pname] of [['validation', tx('web.kn.period_validation')], ['holdout', tx('web.kn.period_holdout')]]) {
        const x = ev[key][pk], tr = el('tr'), n = el('td'); n.append(el('b', null, name), el('span', 'sub', pname));
        tr.append(n, el('td', 'r num ' + tone(x.median), nf(3).format(x.median)), el('td', 'r num ' + tone(x.p10), nf(3).format(x.p10)),
          el('td', 'r num', spc(x.cba, 1)), el('td', 'r num nowrap', `${spc(x.mdd)} / ${spc(x.mdd_dca)}`), el('td', 'r num', pk === 'holdout' ? pc(ev[key].placebo_holdout) : '—'));
        tb.append(tr);
      }
    }
    const th = el('thead'); th.append(h); $('t-kn').replaceChildren(th, tb);
    const li = [];
    if (ev) {
      Object.entries(ev.episodes).sort((a, b) => Number(b[0]) - Number(a[0])).forEach(([k, n]) => {
        const x = el('li'); x.append(tx('web.kn.evidence_line', tx('web.kn.bucket', nf(2).format(Number(k))), n));
        if (n < 10) x.append(' — ', el('b', 'mid', tx('web.kn.low_evidence')));
        li.push(x);
      });
      const ci = (k) => ev[k].ci_holdout.map((v) => nf(3).format(v));
      li.push(el('li', null, tx('web.kn.ci_line', ...ci('candidate'), ...ci('current_bot'))), el('li', null, tx('web.kn.trials_line', ev.trials)));
    }
    $('kn-ev').replaceChildren(...li);
  }
  // ----- Kế hoạch giải ngân một khoản tiền: số liệu lịch sử từ báo cáo tuần (KN.plan), lịch tính trên máy người dùng, không lưu số tiền -----
  const PLAN = KN && KN.plan && KN.plan.options && KN.plan.options.length ? KN.plan : null;
  const pl = { unit: 'vnd', pick: PLAN ? PLAN.recommended : null };
  const UNIT = { vnd: { cents: 1, step: 1000, d: 0, sym: ' ₫' }, usd: { cents: 100, step: 1, d: 2, sym: ' $' } };  // step: each part is a multiple of it (minor units)
  const money = (x) => (x == null || !isFinite(x) ? '—' : nf(UNIT[pl.unit].d).format(x) + UNIT[pl.unit].sym);
  const approx = (x) => { if (x == null || !isFinite(x) || x === 0) return money(x); const k = 10 ** Math.max(0, Math.floor(Math.log10(Math.abs(x))) - 2); return money(Math.round(x / k) * k); };  // 3 significant digits
  const planName = (n) => (n === 1 ? tx('web.plan.opt_1') : tx('web.plan.opt_n', n));
  const isoDay = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const weekday = (s) => new Intl.DateTimeFormat('vi-VN', { weekday: 'long' }).format(new Date(s + 'T12:00:00'));
  function nextMonday() { const d = new Date(); d.setHours(12, 0, 0, 0); while (d.getDay() !== 1) d.setDate(d.getDate() + 1); return isoDay(d); }
  function parseAmount(s) {
    const t = String(s || '').replace(/\s/g, '');
    if (!t) return null;
    const m = t.match(/^(.*?)[.,](\d{1,2})$/), int = (m ? m[1] : t).replace(/[.,]/g, ''), dec = m ? m[2] : '';
    return /^\d*$/.test(int) && (int || dec) ? Number((int || '0') + (dec ? '.' + dec : '')) : NaN;
  }
  function schedule(amount, n, start) {
    const { cents: c, step } = UNIT[pl.unit], total = Math.round(amount * c), base = Math.floor(total / n / step) * step, d0 = new Date(start + 'T12:00:00'), rows = [];
    let cum = 0;
    for (let k = 0; k < n; k++) {
      const part = k === n - 1 ? total - base * (n - 1) : base, d = new Date(d0);
      cum += part; d.setDate(d0.getDate() + 7 * k);
      rows.push({ k: k + 1, date: isoDay(d), amount: part / c, cum: cum / c, share: cum / total });
    }
    return rows;
  }
  function renderPlan() {
    const optEl = $('plan-opts');
    $('plan-unit').replaceChildren(...['vnd', 'usd'].map((u) => { const b = el('button', null, tx('web.plan.unit_' + u)); b.type = 'button'; b.setAttribute('aria-pressed', String(pl.unit === u));
      b.addEventListener('click', () => { pl.unit = u; renderPlan(); }); return b; }));
    if (!PLAN) {
      $('plan-sum').replaceChildren(el('span', 'warn', tx('web.plan.none')));
      for (const id of ['t-plan', 't-plan-sched', 'plan-notes', 'plan-opts']) $(id).replaceChildren();
      $('dl-plan').disabled = true;
      return;
    }
    const opt = (n) => PLAN.options.find((o) => o.weeks === n), rec = opt(PLAN.recommended), best = opt(PLAN.best_roi);
    const amount = parseAmount($('plan-amount').value), ok = amount != null && isFinite(amount) && amount > 0, start = $('plan-start').value || nextMonday();
    const sum = [];
    if (amount != null && !ok) sum.push(el('p', 'warn', tx('web.plan.bad_amount')));
    else if (!ok) sum.push(el('p', null, tx('web.plan.enter')));
    else {
      const rows = schedule(amount, rec.weeks, start), last = rows[rows.length - 1], p1 = el('p');
      p1.append(el('b', null, rec.weeks === 1 ? tx('web.plan.sum_rec_1', money(amount), fmtDate(start)) : tx('web.plan.sum_rec', planName(rec.weeks), rec.weeks, money(rows[0].amount), fmtDate(rows[0].date), fmtDate(last.date))),
        ' ', tx('web.plan.sum_hist', spc(rec.median), approx(amount * (1 + rec.median)), spc(rec.p10), approx(amount * (1 + rec.p10)), spc(rec.worst), pc(rec.loss_share)));
      sum.push(p1);
    }
    if (rec !== best) sum.push(el('p', null, tx('web.plan.sum_best_diff', planName(best.weeks), spc(best.median))));
    else if (ok) sum.push(el('p', null, tx('web.plan.sum_best_same')));   // "đây cũng là…" chỉ có nghĩa khi đã có câu đề xuất phía trước
    const safer = PLAN.options.filter((o) => o.not_worse && o !== rec && o.worst > rec.worst).sort((a, b) => b.worst - a.worst)[0];
    if (safer) sum.push(el('p', null, tx('web.plan.safer', planName(safer.weeks), spc(safer.median), spc(safer.worst), spc(rec.worst))));
    $('plan-sum').replaceChildren(...sum);
    const h = el('tr');
    ['col_plan', 'col_median', 'col_p10', 'col_worst', 'col_loss', 'col_mdd', 'col_beat', 'col_value'].forEach((k, i) => h.append(el('th', i ? 'r' : '', tx('web.plan.' + k))));
    const tb = el('tbody');
    for (const o of PLAN.options) {
      const tr = el('tr', o === rec ? 'here' : ''), n = el('td');
      n.append(el('b', 'nowrap', planName(o.weeks)));
      if (o === best) n.append(el('span', 'tag', tx('web.plan.tag_best')));
      if (o === rec) n.append(el('span', 'tag', tx('web.plan.tag_rec')));
      n.append(el('span', 'sub', o.weeks === 1 ? (o.not_worse ? '' : tx('web.plan.worse')) : tx('web.plan.opt_n_sub', o.weeks) + (o.not_worse ? '' : ' · ' + tx('web.plan.worse'))));
      const beat = el('td', 'r num'), val = el('td', 'r num nowrap', ok ? approx(amount * (1 + o.median)) : '—');
      if (ok) val.append(el('span', 'sub', tx('web.plan.value_sub', approx(amount * (1 + o.p10)))));
      beat.append(o.beat_lump == null ? '—' : pc(o.beat_lump));
      if (o.beat_lump != null && o.beat_lump_ci) beat.append(el('span', 'sub', tx('web.plan.beat_sub', pc(o.beat_lump_ci[0]), pc(o.beat_lump_ci[1]))));
      tr.append(n, el('td', 'r num ' + (o.median >= 0 ? 'good' : 'bad'), spc(o.median)), el('td', 'r num bad', spc(o.p10)), el('td', 'r num bad', spc(o.worst)),
        el('td', 'r num', pc(o.loss_share)), el('td', 'r num', spc(o.mdd_median)), beat,
        val);
      tb.append(tr);
    }
    const th = el('thead'); th.append(h); $('t-plan').replaceChildren(th, tb);
    const notes = [tx('web.plan.note_data', PLAN.starts, fmtDate(PLAN.from), fmtDate(PLAN.to), PLAN.episodes, pc(PLAN.cost, 2)), tx('web.plan.note_rule'), tx('web.plan.note_beat')];
    if (!PLAN.signals_passed) notes.push(tx('web.plan.note_signals'));
    notes.push(tx('web.plan.note_past'), tx('web.plan.note_ref'));
    $('plan-notes').replaceChildren(...notes.map((x) => el('li', null, x)));
    optEl.replaceChildren(...PLAN.options.map((o) => { const b = el('button', null, planName(o.weeks)); b.type = 'button'; b.setAttribute('aria-pressed', String(pl.pick === o.weeks));
      b.addEventListener('click', () => { pl.pick = o.weeks; renderPlan(); }); return b; }));
    const sh = el('tr');
    ['col_n', 'col_date', 'col_amount', 'col_cum', 'col_share'].forEach((k, i) => sh.append(el('th', i > 1 ? 'r' : '', tx('web.plan.' + k))));
    const sb = el('tbody');
    if (ok) for (const r of schedule(amount, pl.pick, start)) {
      const tr = el('tr'), dc = el('td', 'nowrap');
      dc.append(fmtDate(r.date), el('span', 'sub', weekday(r.date)));
      tr.append(el('td', 'num', String(r.k)), dc, el('td', 'r num nowrap', money(r.amount)), el('td', 'r num nowrap', money(r.cum)), el('td', 'r num', pc(r.share)));
      sb.append(tr);
    }
    else { const tr = el('tr'), td = el('td', 'muted', tx('web.plan.enter')); td.colSpan = 5; tr.append(td); sb.append(tr); }
    const sth = el('thead'); sth.append(sh); $('t-plan-sched').replaceChildren(sth, sb);
    $('dl-plan').disabled = !ok;
  }
  // ----- Dự báo dải giá theo ngày: số liệu, kiểm chứng lịch sử và nhật ký từ báo cáo tuần (KN.forecast) -----
  function renderForecast() {
    const F = KN && KN.forecast && KN.forecast.rows && KN.forecast.rows.length ? KN.forecast : null;
    if (!F) {
      $('fc-sum').replaceChildren(el('span', 'warn', tx('web.fc.none')));
      for (const id of ['t-fc', 'fc-notes', 't-fc-verify']) $(id).replaceChildren();
      $('fc-verify-sum').textContent = '';
      return;
    }
    const row = (k) => F.rows.find((r) => r.k === k), chk = (k) => (F.check && F.check[k] ? F.check[k].vol : null), r7 = row(7), r30 = row(30);
    const sum = [el('p', null, tx('web.fc.sum', fmtDate(F.anchor), usd(F.price), fmtDate(r7.target), usd(r7.q10), usd(r7.q90), fmtDate(r30.target), usd(r30.q10), usd(r30.q90)))];
    if (chk(7) && chk(30)) sum.push(el('p', null, tx('web.fc.sum_check', fmtDate(chk(7).from), pc(chk(7).cover80), pc(chk(30).cover80))));
    $('fc-sum').replaceChildren(...sum);
    const h = el('tr');
    ['col_date', 'col_k', 'col_mid', 'col_50', 'col_80', 'col_hist'].forEach((k, i) => h.append(el('th', i > 1 ? 'r' : '', tx('web.fc.' + k))));
    const tb = el('tbody');
    for (const r of F.rows) {
      const tr = el('tr'), d = el('td', 'nowrap'), c = chk(r.k), hist = el('td', 'r num');
      d.append(fmtDate(r.target), el('span', 'sub', weekday(r.target)));
      hist.append(c ? pc(c.cover80) : '—');
      if (c) hist.append(el('span', 'sub', tx('web.fc.hist_sub', pc(c.cover80_ci[0]), pc(c.cover80_ci[1]), c.n_eff)));
      tr.append(d, el('td', 'nowrap', tx('web.fc.k_days', r.k)), el('td', 'r num', usd(r.q50)), el('td', 'r num nowrap', tx('web.fc.range', usd(r.q25), usd(r.q75))),
        el('td', 'r num nowrap', tx('web.fc.range', usd(r.q10), usd(r.q90))), hist);
      tb.append(tr);
    }
    const th = el('thead'); th.append(h); $('t-fc').replaceChildren(th, tb);
    const notes = [tx('web.fc.note_method'), tx('web.fc.note_direction', pc(chk(7) ? chk(7).above_median : null)), tx('web.fc.note_time'), tx('web.fc.note_wide'), tx('web.fc.note_ref')];
    const Sx = F.search;
    if (Sx) {
      const args = [Sx.n_variants, fmtDate(Sx.data_from), `${Sx.selection[0].slice(0, 4)}–${Sx.selection[1].slice(0, 4)}`, `${Sx.confirm_from.slice(0, 4)}–nay`, spc(Sx.diff, 1), spc(Sx.ci[0], 1), spc(Sx.ci[1], 1)];
      notes.splice(1, 0, Sx.switch ? tx('web.fc.note_search_switch', ...args) : tx('web.fc.note_search', ...args));
    }
    $('fc-notes').replaceChildren(...notes.map((x) => el('li', null, x)));
    const lg = F.log || { matured: 0, versions: {}, recent: [] }, v = (lg.versions || {})[F.version];
    $('fc-verify-sum').textContent = !lg.matured ? tx('web.fc.verify_none', lg.first_due ? fmtDate(lg.first_due) : '—')
      : tx('web.fc.verify_sum', v ? v.matured : lg.matured, v ? v.in80 : 0, pc(v ? v.in80 / v.matured : null), v ? v.in50 : 0, pc(v ? v.in50 / v.matured : null))
        + (lg.indep ? ' ' + tx('web.fc.verify_ci', lg.indep.anchors, pc(lg.indep.ci80[0]), pc(lg.indep.ci80[1]), pc(lg.indep.ci50[0]), pc(lg.indep.ci50[1]))
          + (lg.indep.few ? ' ' + tx('web.fc.verify_few') : '') : '');
    $('fc-verify-box').hidden = !lg.matured;
    if (lg.matured) {
      const vh = el('tr');
      ['col_issued', 'col_date', 'col_k', 'col_80', 'col_actual', 'col_in80', 'col_in50'].forEach((k, i) => vh.append(el('th', i > 2 ? 'r' : '', tx('web.fc.' + k))));
      const vb = el('tbody');
      for (const r of lg.recent.slice().reverse()) {
        const tr = el('tr');
        tr.append(el('td', 'nowrap', fmtDate(r.issued)), el('td', 'nowrap', fmtDate(r.target)), el('td', 'nowrap', tx('web.fc.k_days', r.k)),
          el('td', 'r num nowrap', tx('web.fc.range', usd(+r.q10), usd(+r.q90))), el('td', 'r num', usd(r.actual)),
          el('td', 'r ' + (r.in80 ? 'good' : 'bad'), tx(r.in80 ? 'web.fc.yes' : 'web.fc.no')), el('td', 'r ' + (r.in50 ? 'good' : 'bad'), tx(r.in50 ? 'web.fc.yes' : 'web.fc.no')));
        vb.append(tr);
      }
      const vth = el('thead'); vth.append(vh); $('t-fc-verify').replaceChildren(vth, vb);
    }
  }

  function initPlan() {
    if (!$('plan-sec')) return;
    $('plan-start').value = nextMonday();
    $('plan-amount').addEventListener('input', renderPlan);
    $('plan-amount').addEventListener('change', () => { const a = parseAmount($('plan-amount').value); if (a > 0) $('plan-amount').value = nf(UNIT[pl.unit].d).format(a); renderPlan(); });
    $('plan-start').addEventListener('change', renderPlan);
    $('dl-plan').addEventListener('click', () => {
      const a = parseAmount($('plan-amount').value);
      if (!PLAN || !(a > 0)) return;
      const start = $('plan-start').value || nextMonday(), d = UNIT[pl.unit].d, cell = (x) => (/[",\n]/.test(x) ? `"${x.replace(/"/g, '""')}"` : x);
      const head = ['col_n', 'col_date', 'col_amount', 'col_cum', 'col_share'].map((k) => tx('web.plan.' + k));
      const rows = schedule(a, pl.pick, start).map((r) => [String(r.k), r.date, r.amount.toFixed(d), r.cum.toFixed(d), r.share.toFixed(4)]);
      download(`lich-giai-ngan-bot-btc-${start}.csv`, '﻿' + [head, ...rows].map((r) => r.map(cell).join(',')).join('\n'), 'text/csv;charset=utf-8');
    });
    renderPlan();
  }

  // ----- Chốt lời dần (bên bán): bán một lượng BTC theo từng đợt; số liệu lịch sử từ báo cáo tuần (KN.sell_plan, bot/models/sell_plan.py) -----
  const SP = KN && KN.sell_plan && KN.sell_plan.options && KN.sell_plan.options.length ? KN.sell_plan : null;
  const sp = { pick: SP ? SP.recommended : null };
  const spName = (n) => (n === 1 ? tx('web.sp.opt_1') : tx('web.sp.opt_n', n));
  const btc = (x) => (x == null || !isFinite(x) ? '—' : new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 8 }).format(x));
  function spSchedule(amount, n, start) {  // phần nhỏ nhất 1 satoshi; đợt cuối bán phần còn lại
    const total = Math.round(amount * 1e8), base = Math.floor(total / n), d0 = new Date(start + 'T12:00:00'), rows = [];
    let cum = 0;
    for (let k = 0; k < n; k++) {
      const part = k === n - 1 ? total - base * (n - 1) : base, d = new Date(d0);
      cum += part; d.setDate(d0.getDate() + 7 * k);
      rows.push({ k: k + 1, date: isoDay(d), amount: part / 1e8, cum: cum / 1e8, share: cum / total });
    }
    return rows;
  }
  function renderSellPlan() {
    if (!$('sp-sec')) return;
    if (!SP) {
      $('sp-sum').replaceChildren(el('span', 'warn', tx('web.sp.none')));
      for (const id of ['t-sp', 't-sp-sched', 'sp-notes', 'sp-opts']) $(id).replaceChildren();
      return;
    }
    const opt = (n) => SP.options.find((o) => o.weeks === n), rec = opt(SP.recommended), best = opt(SP.best);
    const amount = parseAmount($('sp-amount').value), ok = amount != null && isFinite(amount) && amount > 0, start = $('sp-start').value || nextMonday();
    const ref = KN && (KN.exit || KN.entry), px = st.raw && st.raw.live ? st.raw.live.price : (ref && ref.price) || null;
    const usdOf = (b, r) => (px ? usd(b * px * (1 + r)) : '—');
    const sum = [];
    if (amount != null && !ok) sum.push(el('p', 'warn', tx('web.sp.bad_amount')));
    else if (!ok) sum.push(el('p', null, tx('web.sp.enter')));
    else {
      const rows = spSchedule(amount, rec.weeks, start), last = rows[rows.length - 1], p1 = el('p');
      p1.append(el('b', null, rec.weeks === 1 ? tx('web.sp.sum_rec_1', btc(amount), fmtDate(start)) : tx('web.sp.sum_rec', spName(rec.weeks), btc(rows[0].amount), fmtDate(rows[0].date), fmtDate(last.date))),
        ' ', tx('web.sp.sum_hist', spc(rec.median), spc(rec.p10), spc(rec.worst), usdOf(amount, rec.median), usdOf(amount, rec.p10)));
      sum.push(p1);
    }
    if (rec.weeks > 1) sum.push(el('p', null, tx('web.sp.sum_why', spc(rec.p10))));
    const safer = SP.options.filter((o) => o.weeks > 1 && o.weeks < rec.weeks).sort((a, b) => b.p10 - a.p10)[0];
    if (safer) sum.push(el('p', 'muted', tx('web.sp.sum_risk', spName(safer.weeks), spc(safer.p10))));
    $('sp-sum').replaceChildren(...sum);
    const h = el('tr');
    ['col_plan', 'col_median', 'col_p10', 'col_worst', 'col_below', 'col_mdd', 'col_beat', 'col_value'].forEach((k, i) => h.append(el('th', i ? 'r' : '', tx('web.sp.' + k))));
    const tb = el('tbody');
    for (const o of SP.options) {
      const tr = el('tr', o === rec ? 'here' : ''), n = el('td');
      n.append(el('b', 'nowrap', spName(o.weeks)));
      if (o === best) n.append(el('span', 'tag', tx('web.sp.tag_best')));
      if (o === rec) n.append(el('span', 'tag', tx('web.sp.tag_rec')));
      n.append(el('span', 'sub', o.weeks === 1 ? '' : tx('web.sp.opt_n_sub', o.weeks) + (o.not_worse ? '' : ' · ' + tx('web.sp.worse'))));
      const beat = el('td', 'r num'), val = el('td', 'r num nowrap', ok ? usdOf(amount, o.median) : '—');
      if (ok) val.append(el('span', 'sub', tx('web.sp.value_sub', usdOf(amount, o.p10))));
      beat.append(o.beat_once == null ? '—' : pc(o.beat_once));
      if (o.beat_once != null && o.beat_once_ci) beat.append(el('span', 'sub', tx('web.sp.beat_sub', pc(o.beat_once_ci[0]), pc(o.beat_once_ci[1]))));
      tr.append(n, el('td', 'r num ' + (o.median >= 0 ? 'good' : 'bad'), spc(o.median)), el('td', 'r num ' + (o.p10 >= 0 ? 'good' : 'bad'), spc(o.p10)),
        el('td', 'r num ' + (o.worst >= 0 ? 'good' : 'bad'), spc(o.worst)), el('td', 'r num', pc(o.below_start)), el('td', 'r num', spc(o.mdd_median)), beat, val);
      tb.append(tr);
    }
    const th = el('thead'); th.append(h); $('t-sp').replaceChildren(th, tb);
    const notes = [tx('web.sp.note_data', SP.starts, fmtDate(SP.from), fmtDate(SP.to), SP.episodes, pc(SP.cost, 2)), tx('web.sp.note_rule'), tx('web.sp.note_value')];
    if (!SP.signals_passed) notes.push(tx('web.sp.note_signals'));
    notes.push(tx('web.sp.note_past'));
    $('sp-notes').replaceChildren(...notes.map((x) => el('li', null, x)));
    $('sp-opts').replaceChildren(...SP.options.map((o) => { const b = el('button', null, spName(o.weeks)); b.type = 'button'; b.setAttribute('aria-pressed', String(sp.pick === o.weeks));
      b.addEventListener('click', () => { sp.pick = o.weeks; renderSellPlan(); }); return b; }));
    const sh = el('tr');
    ['col_n', 'col_date', 'col_btc', 'col_cum', 'col_share', 'col_usd'].forEach((k, i) => sh.append(el('th', i > 1 ? 'r' : '', tx('web.sp.' + k))));
    const sb = el('tbody');
    if (ok) for (const r of spSchedule(amount, sp.pick, start)) {
      const tr = el('tr'), dc = el('td', 'nowrap');
      dc.append(fmtDate(r.date), el('span', 'sub', weekday(r.date)));
      tr.append(el('td', 'num', String(r.k)), dc, el('td', 'r num nowrap', btc(r.amount)), el('td', 'r num nowrap', btc(r.cum)), el('td', 'r num', pc(r.share)), el('td', 'r num nowrap', usdOf(r.amount, 0)));
      sb.append(tr);
    }
    else { const tr = el('tr'), td = el('td', 'muted', tx('web.sp.enter')); td.colSpan = 6; tr.append(td); sb.append(tr); }
    const sth = el('thead'); sth.append(sh); $('t-sp-sched').replaceChildren(sth, sb);
  }
  function initSellPlan() {
    if (!$('sp-sec')) return;
    $('sp-start').value = nextMonday();
    $('sp-amount').addEventListener('input', renderSellPlan);
    $('sp-start').addEventListener('change', renderSellPlan);
    renderSellPlan();
  }

  // ================================================================ GIÁ & NGÀY MUA / BÁN (KN.entry: bot/models/entry_timing.py, KN.exit: bot/models/exit_timing.py)
  // Máy chủ gửi 99 phân vị của z = log(giá thấp nhất (bên mua) hoặc cao nhất (bên bán) k ngày tới / giá mốc) / (σ√k); trang lấy giá lúc tra làm mốc.
  const EN = KN && KN.entry && KN.entry.rows && KN.entry.rows.length ? KN.entry : null;
  const EX = KN && KN.exit && KN.exit.rows && KN.exit.rows.length ? KN.exit : null;
  const isSell = () => st.mode === 'sell';
  const SD = () => (isSell() ? EX : EN);  // số liệu của chế độ đang chọn
  const K = (key, ...a) => tx((isSell() ? 'web.ex.' : 'web.en.') + key, ...a);  // chữ của chế độ đang chọn (cùng khóa ở web.en và web.ex)
  const sgn = () => (isSell() ? 1 : -1);  // bên mua đặt thấp hơn, bên bán đặt cao hơn giá hiện tại
  const enRow = (k) => { const D = SD(); return D ? D.rows.find((r) => r.k === k) : null; };
  const refPrice = () => (st.raw.live ? st.raw.live.price : EN || EX ? (EN || EX).price : null);
  const QUICK = [0.01, 0.02, 0.03, 0.05, 0.08, 0.1], HEAT = [0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.1], WEEK = [1, 2, 3, 4, 5, 6, 7];
  const en = { buy: { pct: 0.03, price: null }, sell: { pct: 0.03, price: null } }, cur = () => en[isSell() ? 'sell' : 'buy'];
  const targetOf = (side) => { const s = en[side]; return s.pct != null ? refPrice() * (1 + (side === 'sell' ? 1 : -1) * s.pct) : s.price; };
  const target = () => targetOf(isSell() ? 'sell' : 'buy');
  const beyond = (X, L) => (isSell() ? X > L : X < L);  // giá đặt nằm ở phía phải chờ (thấp hơn khi mua, cao hơn khi bán)
  const utcDay = () => new Date(Date.now()).toISOString().slice(0, 10);
  const addDays = (s, k) => { const d = new Date(s + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + k); return d.toISOString().slice(0, 10); };
  // Lúc tra được coi như giá đóng ngày gốc (đăng ký trước, mục touch.live): ngày thứ k tính từ hôm nay (giờ UTC), kể cả khi số liệu chậm một ngày.
  const dayK = (k) => { const t = utcDay(), a1 = addDays(SD().anchor, 1); return addDays(t > a1 ? t : a1, k - 1); };
  const dm = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}`;
  const wdOf = (s) => new Intl.DateTimeFormat('vi-VN', { weekday: 'short', timeZone: 'UTC' }).format(new Date(s + 'T00:00:00Z'));
  const dayLab = (s) => (s === utcDay() ? tx('web.en.today') : `${wdOf(s)} ${dm(s)}`);
  const dayFull = (s) => (s === utcDay() ? tx('web.en.today_full', `${wdOf(s)} ${dm(s)}`) : `${wdOf(s)} ${dm(s)}`);
  const kusd = (x) => (x == null || !isFinite(x) ? '—' : tx('web.home.kilo', nf(1).format(x / 1000)));
  const pcx = (x) => pc(x, Math.abs(x * 100 - Math.round(x * 100)) < 1e-6 ? 0 : 1);  // 3% hoặc 3,4%
  // Khả năng giá chạm X trong k ngày: bên mua P(z ≤ z*), bên bán P(z ≥ z*); nội suy tuyến tính giữa 99 phân vị, ngoài 1–99% thì giữ ở hai đầu
  function touchP(X, k) {
    const r = enRow(k), L = refPrice(), D = SD();
    if (!r || !(X > 0) || !(L > 0)) return null;
    const z = Math.log(X / L) / (D.sigma * Math.sqrt(k)), q = r.z;
    let F = null, end = 0;
    if (z < q[0]) { F = 0.01; end = -1; } else if (z > q[98]) { F = 0.99; end = 1; }
    else for (let i = 1; i < 99; i++) if (z <= q[i]) { const d = q[i] - q[i - 1]; F = (i + (d > 0 ? (z - q[i - 1]) / d : 1)) / 100; break; }
    if (F == null) { F = 0.99; end = 1; }
    if (isSell()) { F = 1 - F; end = -end; }
    return { p: F, lt: end < 0, gt: end > 0 };
  }
  const pT = (o) => (o == null ? '—' : o.lt ? tx('web.en.lt1') : o.gt ? tx('web.en.gt99') : pc(o.p));
  const bandAt = (k, q) => { const r = enRow(k), L = refPrice(); return r && L ? L * Math.exp(r.z[q - 1] * SD().sigma * Math.sqrt(k)) : null; };  // q = phân vị 1..99
  function rrect(g, x, y, w, h, r) { g.beginPath(); if (g.roundRect) g.roundRect(x, y, w, h, Math.min(r, Math.abs(h) / 2, w / 2)); else g.rect(x, y, w, h); g.fill(); }
  function niceTicks(lo, hi, n) {
    const raw = (hi - lo) / n, mag = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || raw, out = [];
    for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) out.push(t);
    return out;
  }

  function renderEntry() {
    const D = SD();
    $('tab-entry-lab').textContent = tx(isSell() ? 'web.page.tab_exit' : 'web.page.tab_entry');
    for (const [id, key] of [['en-a-title', 'a_title'], ['en-a-lead', 'a_lead'], ['en-target-lab', 'target_label'], ['en-heat-title', 'heat_title'], ['en-check-title', 'check_title'],
      ['en-c-title', 'c_title'], ['en-c-lead', 'c_lead'], ['en-c-check-title', 'c_check_title'], ['en-b-title', 'b_title'], ['en-b-lead', 'b_lead'], ['en-none', 'none']]) $(id).textContent = K(key);
    $('en-none').hidden = !!D;
    for (const id of ['en-a', 'en-b', 'en-c']) $(id).hidden = !D;
    if (!D) return;
    const L = refPrice(), X = target(), ok = X > 0 && isFinite(X), inp = $('en-target'), today = utcDay(), s = cur();
    if (document.activeElement !== inp) inp.value = ok ? nf(0).format(Math.round(X)) : inp.value;
    $('en-quick').replaceChildren(...QUICK.map((x) => {
      const b = el('button', null, spc(sgn() * x)); b.type = 'button'; b.setAttribute('aria-pressed', String(s.pct === x));
      b.addEventListener('click', () => { s.pct = x; s.price = null; renderEntry(); renderHome(); requestAnimationFrame(redraw); });
      return b;
    }));
    const ans = $('en-answer');
    if (!ok) ans.replaceChildren(el('p', 'warn', K('answer_bad')));
    else if (!beyond(X, L)) ans.replaceChildren(el('p', null, K('answer_now', usd(L))));
    else ans.replaceChildren(el('div', 'muted', K('answer', usd(X), spc(X / L - 1, 1), usd(L))), el('div', 'big num', pT(touchP(X, 7))),
      el('div', null, K('answer_more', pT(touchP(X, 1)), pT(touchP(X, 3)), pT(touchP(X, 30)))));
    $('en-bars-title').textContent = K('bars_title', ok ? usd(X) : '—');
    $('en-bars').replaceChildren(...D.rows.map((r) => {
      const o = !ok ? null : !beyond(X, L) ? { p: 1 } : touchP(X, r.k);
      const row = el('div', 'bar'), lab = el('span', null, tx('web.en.bar_lab', r.k)), tr = el('span', 'tr'), i = el('i');
      lab.title = tx('web.en.bar_until', fmtDate(dayK(r.k))); i.style.width = (o ? o.p * 100 : 0) + '%'; tr.append(i);
      row.append(lab, tr, el('b', null, pT(o)));
      return row;
    }));
    // bảng nhiệt: khả năng chạm từng mức theo từng kỳ hạn
    const h = el('tr');
    h.append(el('th', null, tx('web.en.col_level')));
    D.rows.forEach((r) => h.append(el('th', null, tx('web.en.col_k', r.k))));
    const tb = el('tbody');
    for (const x of HEAT) {
      const tr = el('tr', x === 0 ? 'base' : ''), P = L * (1 + sgn() * x), c0 = el('td', 'nowrap');
      c0.append(x ? usd(P) : K('level_now', usd(P)));
      if (x) c0.append(el('span', 'sub', spc(sgn() * x)));
      tr.append(c0);
      for (const r of D.rows) {
        const o = touchP(P, r.k), td = el('td', null, pT(o));
        if (o) td.style.background = `color-mix(in srgb, var(--brand) ${Math.round(o.p * 55)}%, transparent)`;
        tr.append(td);
      }
      tb.append(tr);
    }
    const th = el('thead'); th.append(h); $('t-en-heat').replaceChildren(th, tb);
    const notes = [K('note_method', pc(D.sigma, 1)), K('note_live', fmtDate(D.anchor)), K('note_fill'), tx('web.en.note_utc'), K('note_direction'), tx('web.fc.note_ref')];
    if (Math.round((Date.parse(today) - Date.parse(D.anchor)) / 86400000) > 2) notes.unshift(tx('web.en.stale', fmtDate(D.anchor)));
    $('en-a-notes').replaceChildren(...notes.map((x) => el('li', null, x)));
    renderEntryCheck();
    renderDays();
    renderWait();
  }

  function renderEntryCheck() {
    const D = SD(), C = D.check || {}, c7 = C[7], c30 = C[30];
    $('en-check-sum').textContent = c7 && c30 && c7.n ? K('check_sum', fmtDate(c7.from), fmtDate(c7.to), pc(c7.cover80), pc(c30.cover80)) : '';
    const xs = [0.02, 0.05], h = el('tr');
    [tx('web.en.col_ck'), K('col_cover'), ...xs.map((x) => K('col_x', pc(x))), tx('web.en.col_brier')].forEach((t, i) => h.append(el('th', i ? 'r' : '', t)));
    const tb = el('tbody'), d3 = (x) => (x == null || !isFinite(x) ? '—' : nf(3).format(x));
    for (const r of D.rows) {
      const c = C[r.k]; if (!c || !c.n) continue;
      const tr = el('tr'), cov = el('td', 'r num ' + (c.trusted ? '' : 'bad'), pc(c.cover80));
      cov.append(el('span', 'sub', tx('web.en.cover_sub', pc(c.cover80_ci[0]), pc(c.cover80_ci[1]), c.n_eff) + (c.trusted ? '' : ' · ' + tx('web.en.untrusted'))));
      tr.append(el('td', 'nowrap', tx('web.fc.k_days', r.k)), cov);
      xs.forEach((x) => { const p = c.probs.find((y) => Math.abs(y.x - x) < 1e-9); tr.append(el('td', 'r num', p ? tx('web.en.pred_cell', pc(p.pred), pc(p.actual)) : '—')); });
      tr.append(el('td', 'r num', tx('web.en.brier_cell', d3(c.brier), d3(c.brier_raw))));
      tb.append(tr);
    }
    const th = el('thead'); th.append(h); $('t-en-check').replaceChildren(th, tb);
    const lg = D.log || { matured: 0, versions: {} }, v = (lg.versions || {})[D.version];
    $('en-log').textContent = !lg.matured ? K('log_none')
      : K('log_sum', v ? v.matured : lg.matured, v ? v.in80 : 0, pc(v ? v.in80 / v.matured : null), v ? v.in50 : 0, pc(v ? v.in50 / v.matured : null));
  }

  // ngày rẻ nhất (bên mua) hoặc có giá cao nhất (bên bán) trong 7 ngày tới, ngày tính từ hôm nay
  const dayData = () => (isSell() ? EX && EX.highest : EN && EN.cheapest);
  const daysAhead = () => dayData().days.map((x) => ({ ...x, date: dayK(x.pos) }));
  function renderDays() {
    const C = dayData(); if (!C) return;
    const d = daysAhead(), best = d.reduce((a, b) => (b.share > a.share ? b : a)), mids = d.slice(1, -1).map((x) => x.share);
    const p1 = el('p'); p1.append(el('b', null, K('c_sum_top', dayFull(best.date), pc(best.share), nf(1).format(best.share * d.length), pc(Math.min(...mids)), pc(Math.max(...mids)))));
    const nb = isSell() ? C.none_above : C.none_below;
    $('en-c-sum').replaceChildren(p1, el('p', null, K('c_why')),
      el('p', null, C.standout.length ? K('c_standout', C.standout.map((j) => tx('web.en.c_pos', j)).join(', ')) : K('c_standout_none')),
      el('p', null, K('c_meaning')), el('p', 'muted', K('c_none', fmtDate(SD().anchor), nb < 0.0101 ? tx('web.en.lt1') : pc(nb))));
    $('en-days-legend').replaceChildren(...[['--brand', 1, K('c_bar')], ['--ink', 0.6, tx('web.en.c_ref')]].map(([v, o, t]) => { const s = el('span'), i = el('i'); i.style.background = `var(${v})`; i.style.opacity = o; if (v === '--ink') i.style.height = '2px'; s.append(i, t); return s; }));
    const h = el('tr');
    h.append(el('th', null, tx('web.en.col_pos')));
    C.halves.forEach((x) => { const c = el('th', 'r', tx('web.en.col_half', fmtDate(x.from), fmtDate(x.to))); c.append(el('span', 'sub', tx('web.en.half_sub', x.n_eff))); h.append(c); });
    const tb = el('tbody');
    d.forEach((x, j) => {
      const tr = el('tr', C.standout.includes(j + 1) ? 'here' : '');
      tr.append(el('td', null, tx('web.en.c_pos', j + 1)));
      C.halves.forEach((hv) => tr.append(el('td', 'r num', tx('web.en.half_cell', pc(hv.shares[j]), pc(hv.ci[j][0]), pc(hv.ci[j][1])))));
      tb.append(tr);
    });
    const th = el('thead'); th.append(h); $('t-en-days').replaceChildren(th, tb);
  }

  function renderWait() {
    const Wt = SD().wait; if (!Wt) return;
    const rows = Wt.rows, xs = [...new Set(rows.map((r) => r.x))], ks = [...new Set(rows.map((r) => r.k))], at = (x, k) => rows.find((r) => r.x === x && r.k === k);
    const cho = rows.filter((r) => r.verdict === 'cho'), ngay = rows.filter((r) => r.verdict === 'ngay').length, cfgName = (r) => K('cfg', pc(r.x), r.k);
    const p1 = el('p'); p1.append(el('b', null, cho.length ? K('b_sum_some', cho.length, cho.map(cfgName).join('; '), ngay) : K('b_sum_none', rows.length, ngay)));
    const sum = [p1], ex = at(0.02, 7);
    if (isSell()) {
      if (ex) sum.push(el('p', null, tx('web.ex.b_why', pc(ex.x), ex.k, pc(ex.fill), spc(Math.abs(ex.mean) < 5e-5 ? 0 : ex.mean, 2))));
      sum.push(el('p', null, tx('web.ex.b_meaning', pc(Math.max(...rows.map((r) => Math.abs(r.mean))), 1))));
    } else {
      if (ex && ex.mean < 0) sum.push(el('p', null, tx('web.en.b_why', pc(ex.x), ex.k, pc(ex.fill), tx('web.en.worse', spc(Math.abs(ex.mean), 1).replace('+', '')))));
      if (!cho.length) sum.push(el('p', null, tx('web.en.b_meaning')));
    }
    $('en-b-sum').replaceChildren(...sum);
    const h = el('tr');
    h.append(el('th', null, K('col_x_b')));
    ks.forEach((k) => h.append(el('th', null, tx('web.en.col_k_b', k))));
    const tb = el('tbody'), TONE = { cho: 'good', ngay: 'bad', chua: 'muted' }, TINT = { cho: '--jade', ngay: '--cinnabar' };
    for (const x of xs) {
      const tr = el('tr');
      tr.append(el('td', 'nowrap', spc(sgn() * x)));
      for (const k of ks) {
        const r = at(x, k), td = el('td', r ? TONE[r.verdict] : '', r ? spc(Math.abs(r.mean) < 5e-5 ? 0 : r.mean, 2) : '—');
        if (r) {
          td.append(el('span', 'sub', tx('web.en.cell_sub', pc(r.fill))));
          td.title = tx('web.en.cell_title', spc(r.mean, 2), spc(r.ci[0], 2), spc(r.ci[1], 2), spc(r.median, 1), pc(r.better), spc(r.p10, 1), nf(3).format(r.p_holm));
          if (TINT[r.verdict]) td.style.background = `color-mix(in srgb, var(${TINT[r.verdict]}) 13%, transparent)`;
        }
        tr.append(td);
      }
      tb.append(tr);
    }
    const th = el('thead'); th.append(h); $('t-en-wait').replaceChildren(th, tb);
    const r0 = rows[0], leg = el('li');
    ['cho', 'ngay', 'chua'].forEach((v) => leg.append(el('span', 'pill ' + TONE[v], K('v_' + v)), ' '));
    $('en-b-notes').replaceChildren(leg, el('li', null, K('b_note_cells') + ' ' + K('b_note_stats', Wt.n_configs, fmtDate(r0.from), fmtDate(r0.split), fmtDate(r0.to))), el('li', null, K('b_note_fees')));
  }

  // biểu đồ: cột giá thấp nhất (bên mua) hoặc cao nhất (bên bán) từng ngày (đoạn 25–75% đậm, 10–90% nhạt), đường giá hiện tại và giá muốn đặt
  function drawFan() {
    const cv = $('h-fan'), D = SD();
    $('h-fan-title').textContent = K('fan_title'); $('h-fan-lead').textContent = K('fan_lead'); $('h-fan-ic').textContent = isSell() ? '↥' : '↧';
    if (!D || !cv.clientWidth) return;
    const { g, W, H, c } = canvasSetup(cv), L = refPrice(), X = target(), rows = WEEK.map(enRow).filter(Boolean), today = utcDay(), up = isSell(), show = X > 0 && beyond(X, L);
    const ends = rows.map((r) => bandAt(r.k, up ? 90 : 10));
    const lo = (up ? L : Math.min(...ends, show ? X : Infinity)) * 0.996, hi = (up ? Math.max(...ends, show ? X : 0) : L) * 1.004;
    const PL = 58, PR = 12, PT = 12, PB = 40, ph = H - PT - PB, cw = (W - PL - PR) / rows.length, y = (p) => PT + ((hi - p) / (hi - lo)) * ph;
    g.strokeStyle = c('--line'); g.fillStyle = c('--muted'); g.lineWidth = 1; g.textAlign = 'right'; g.textBaseline = 'middle';
    const ticks = niceTicks(lo, hi, 4), step = ticks.length > 1 ? ticks[1] - ticks[0] : 1000, narrow = cw < 72;
    ticks.forEach((t) => { const yy = Math.round(y(t)) + 0.5; g.beginPath(); g.moveTo(PL, yy); g.lineTo(W - PR, yy); g.stroke(); g.fillText(step >= 100 ? kusd(t) : nf(0).format(t), PL - 8, yy); });
    rows.forEach((r, i) => {
      const cx = PL + cw * (i + 0.5), bw = Math.min(54, cw * 0.58), day = dayK(r.k);
      g.fillStyle = c('--brand'); g.globalAlpha = 0.25; rrect(g, cx - bw / 2, y(bandAt(r.k, 90)), bw, y(bandAt(r.k, 10)) - y(bandAt(r.k, 90)), 6);
      g.globalAlpha = 0.7; rrect(g, cx - bw / 2, y(bandAt(r.k, 75)), bw, y(bandAt(r.k, 25)) - y(bandAt(r.k, 75)), 4);
      g.globalAlpha = 1; g.fillStyle = c('--ink'); g.fillRect(cx - bw / 2, Math.round(y(bandAt(r.k, 50))) - 1, bw, 2);
      g.textAlign = 'center'; g.textBaseline = 'top'; g.fillStyle = day === today ? c('--brand-ink') : c('--ink'); g.font = `600 ${narrow ? 10.5 : 12}px ${c('--font')}`;
      g.fillText(narrow ? dm(day) : dayLab(day), cx, H - PB + 8); g.font = `${narrow ? 10.5 : 12}px ${c('--font')}`; g.fillStyle = c('--muted');
      if (!narrow) g.fillText(tx('web.fc.k_days', r.k), cx, H - PB + 23);
    });
    const line = (p, col, dash, label, below) => {
      const yy = Math.round(y(p)) + 0.5; g.strokeStyle = col; g.lineWidth = 1.5; g.setLineDash(dash); g.beginPath(); g.moveTo(PL, yy); g.lineTo(W - PR, yy); g.stroke(); g.setLineDash([]);
      g.font = `600 12px ${c('--font')}`; g.textAlign = 'right'; g.textBaseline = below ? 'top' : 'bottom'; const tw = g.measureText(label).width;
      g.fillStyle = c('--panel'); g.globalAlpha = 0.85; g.fillRect(W - PR - tw - 6, below ? yy + 2 : yy - 17, tw + 6, 15); g.globalAlpha = 1;
      g.fillStyle = col; g.fillText(label, W - PR - 3, below ? yy + 3 : yy - 3); g.font = `12px ${c('--font')}`;
    };
    line(L, c('--ink'), [], `${tx('web.en.fan_now')} ${usd(L)}`, up);
    if (show) line(X, c('--blue'), [6, 4], `${K('fan_target')} ${usd(X)}`, !up);
    const sw = (v, o, t, hgt) => { const s = el('span'), i = el('i'); i.style.background = `var(${v})`; i.style.opacity = o; if (hgt) i.style.height = hgt; s.append(i, t); return s; };
    $('h-fan-legend').replaceChildren(sw('--brand', 0.25, tx('web.en.fan_80')), sw('--brand', 0.7, tx('web.en.fan_50')), sw('--ink', 1, tx('web.en.fan_mid'), '2px'), sw('--ink', 1, tx('web.en.fan_now'), '2px'), sw('--blue', 1, K('fan_target'), '2px'));
  }

  // biểu đồ cột: tỷ lệ mỗi ngày trong 7 ngày tới là ngày rẻ nhất (bên mua) hoặc có giá cao nhất (bên bán); mini = bản nhỏ trong thẻ tổng quan
  function drawDays(cv, mini) {
    const C = dayData(); if (!C || !cv || !cv.clientWidth) return;
    const { g, W, H, c } = canvasSetup(cv), d = daysAhead(), best = d.reduce((a, b) => (b.share > a.share ? b : a)), today = utcDay();
    const top = Math.max(0.2, best.share * 1.18), PL = mini ? 0 : 40, PR = mini ? 0 : 8, PT = mini ? 14 : 22, PB = mini ? 16 : 40, ph = H - PT - PB, cw = (W - PL - PR) / d.length;
    const y = (v) => PT + ph - (v / top) * ph;
    if (!mini) {
      g.strokeStyle = c('--line'); g.fillStyle = c('--muted'); g.lineWidth = 1; g.textAlign = 'right'; g.textBaseline = 'middle';
      niceTicks(0, top, 4).forEach((t) => { const yy = Math.round(y(t)) + 0.5; g.beginPath(); g.moveTo(PL, yy); g.lineTo(W - PR, yy); g.stroke(); g.fillText(pc(t), PL - 6, yy); });
    }
    d.forEach((x, i) => {
      const bw = cw * (mini ? 0.62 : 0.56), bx = PL + cw * i + (cw - bw) / 2, on = x === best;
      g.fillStyle = on ? c('--brand') : c('--muted'); g.globalAlpha = on ? 1 : 0.4; rrect(g, bx, y(x.share), bw, y(0) - y(x.share), mini ? 3 : 6); g.globalAlpha = 1;
      g.textAlign = 'center'; g.textBaseline = 'bottom'; g.fillStyle = on ? c('--brand-ink') : c('--muted');
      g.font = `${on ? 700 : 500} ${mini ? 11 : 12}px ${c('--font')}`;
      if (!mini || on) g.fillText(pc(x.share), bx + bw / 2, y(x.share) - 3);
      g.textBaseline = 'top'; g.fillStyle = x.date === today ? c('--brand-ink') : c('--muted'); g.font = `${x.date === today ? 700 : 500} ${mini || cw < 56 ? 10.5 : 12}px ${c('--font')}`;
      if (mini) g.fillText(wdOf(x.date), bx + bw / 2, H - PB + 3);
      else { g.fillText(x.date === today ? tx('web.en.today') : wdOf(x.date), bx + bw / 2, H - PB + 8); g.fillText(dm(x.date), bx + bw / 2, H - PB + 23); }
    });
    const yr = Math.round(y(1 / 7)) + 0.5;
    g.strokeStyle = c('--ink'); g.globalAlpha = 0.55; g.lineWidth = 1.2; g.setLineDash([5, 4]); g.beginPath(); g.moveTo(PL, yr); g.lineTo(W - PR, yr); g.stroke(); g.setLineDash([]); g.globalAlpha = 1;
  }

  // ----- Tổng quan: các thẻ số chính theo chế độ Mua / Bán -----
  function renderHome() {
    const sell = isSell(), cards = [], stale = knStale(), m = !KN || stale ? 1 : KN.multiplier, ex = KN ? KN.amount_example_usd : 100;
    const card = (tone, lab, val, sub, go) => {
      const k = el('div', 'kpi ' + tone); k.append(el('span', 'lab', lab), el('div', 'val num', val));
      if (sub) k.append(el('span', 'sub', sub));
      if (go) { const b = el('button', 'go', tx('web.home.go')); b.type = 'button'; b.addEventListener('click', () => { showTab(go); window.scrollTo({ top: 0 }); }); k.append(b); }
      return k;
    };
    if (!sell) {
      const npass = RB ? Object.values(RB.acceptance.criteria).filter((x) => x.pass).length : null, safe = !KN || stale || KN.mode === 'safe';
      cards.push(card(safe ? 'good' : 'mid', tx('web.home.rec_lab'), safe ? tx('web.home.rec_val') : tx('web.home.rec_val_model', nf(1).format(m)),
        npass != null && safe ? tx('web.home.rec_sub', nf(1).format(m), usd(ex * m), usd(ex), npass) : tx('web.home.rec_sub_plain', nf(1).format(m), usd(ex * m), usd(ex)), 'check'));
    } else {
      const W = RB && RB.week, lv = W ? W.sell_level : null;
      cards.push(card(lv === 'ban' ? 'bad' : lv === 'chot' ? 'mid' : 'good', tx('web.home.sell_lab'), lv ? tx('web.rb.level_' + lv) : '—', W ? tx('web.home.sell_sub', W.sell_groups, RB.sell_trusted) : '', 'check'));
    }
    if (SD()) {
      const X = target(), L = refPrice(), gap = cur().pct != null ? cur().pct : Math.abs(X / L - 1), w = beyond(X, L);
      cards.push(card('info', tx(sell ? 'web.home.touch_sell_lab' : 'web.home.touch_lab', pcx(gap), usd(X)), w ? pT(touchP(X, 7)) : pc(1), tx('web.home.touch_sub', w ? pT(touchP(X, 30)) : pc(1)), 'entry'));
      const best = daysAhead().reduce((a, b) => (b.share > a.share ? b : a));
      const k = card('mid', tx(sell ? 'web.home.day_sell_lab' : 'web.home.day_lab'), dayLab(best.date), tx(sell ? 'web.home.day_sell_sub' : 'web.home.day_sub', pc(best.share)), 'entry');
      const cv = el('canvas'); cv.setAttribute('height', '64'); k.insertBefore(cv, k.querySelector('.go')); cards.push(k);
    }
    const CB = KN && KN.calib && KN.calib['4'] ? KN.calib : null, F = KN && KN.forecast && KN.forecast.rows ? KN.forecast : null;
    const r7 = F && F.rows.find((r) => r.k === 7), r30 = F && F.rows.find((r) => r.k === 30);
    if (sell && CB) cards.push(card('mid', tx('web.home.drop_lab'), pc(1 - CB['4'].now.p), tx('web.home.drop_sub', ...['13', '26', '52'].map((h) => (CB[h] ? pc(1 - CB[h].now.p) : '—')))
      + (Object.values(CB).some((x) => x.pick) ? '' : ' ' + tx('web.home.drop_nopick')), 'fc'));
    else if (r7 && r30) cards.push(card('info', tx('web.home.band_lab'), tx('web.home.band_val', kusd(r7.q10), kusd(r7.q90)), tx('web.home.band_sub', usd(r7.q50), usd(r30.q10), usd(r30.q90)), 'fc'));
    $('h-kpis').replaceChildren(...cards);
    requestAnimationFrame(() => document.querySelectorAll('#h-kpis canvas').forEach((cv) => drawDays(cv, true)));
  }

  function redraw() {
    drawFan();
    if (dayData()) { drawDays($('en-days'), false); document.querySelectorAll('#h-kpis canvas').forEach((cv) => drawDays(cv, true)); }
  }
  function redrawAll() { redraw(); if (st.full) drawChart(); if (st.cmp) drawOptCharts(); if (st.mode === 'sell' && st.sdFull) drawSellChart(); if (st.a) drawIndCharts(); }
  for (const id of ['h-fan', 'en-days']) new ResizeObserver(() => requestAnimationFrame(redraw)).observe($(id).parentElement);
  new ResizeObserver(() => requestAnimationFrame(() => document.querySelectorAll('#h-kpis canvas').forEach((cv) => drawDays(cv, true)))).observe($('h-kpis'));
  $('en-target').addEventListener('input', () => { const s = cur(); s.pct = null; s.price = parseAmount($('en-target').value); renderEntry(); renderHome(); requestAnimationFrame(redraw); });
  $('en-target').addEventListener('change', () => { const s = cur(); if (s.price > 0) $('en-target').value = nf(0).format(Math.round(s.price)); });
  // ----- giá thời gian thực: luồng WebSocket Binance (24 giờ: mở, cao, thấp, giá cuối) + đường giá 24 giờ (nến 15 phút) -----
  // Đầu trang đổi theo từng lần giá nhảy; các công cụ tính lại theo giá mới tối đa 10 giây một lần. Mất luồng thì lấy giá REST 15 giây một lần và nối lại.
  const WS_URLS = ['wss://stream.binance.com:9443/ws/btcusdt@miniTicker', 'wss://data-stream.binance.vision/ws/btcusdt@miniTicker'];
  const live = { ws: null, url: 0, lastMsg: 0, retry: 1000, heavyAt: 0, heavyT: null, spark: null, day: null, shown: null };
  const hms = (t) => new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).format(new Date(t));
  const streaming = () => !!live.ws && live.ws.readyState === 1 && Date.now() - live.lastMsg < 15000;
  function renderQuote(flash) {
    const L = st.raw.live && st.raw.live.price; if (!(L > 0)) return;
    const p = $('price'); p.textContent = usd(L);
    if (flash && live.shown != null && L !== live.shown) { p.classList.remove('up', 'down'); void p.offsetWidth; p.classList.add(L > live.shown ? 'up' : 'down'); }
    live.shown = L;
    const c = $('chg'), D = live.day, ref = EN || EX;
    // 24 giờ khi có luồng hoặc nến 15 phút; không thì so với giá đóng ngày gốc (lệch quá 25% là hai nguồn không khớp, nên ẩn)
    const ch = D ? L / D.open - 1 : ref ? L / ref.price - 1 : null;
    c.hidden = ch == null || !(Math.abs(ch) < 0.25);
    if (ch != null) { c.className = 'chg num ' + (ch >= 0 ? 'up' : 'down'); c.textContent = D ? tx('web.home.chg24', spc(ch, 2)) : tx('web.home.chg', spc(ch, 1), dm(ref.anchor)); }
    $('hl').hidden = !D;
    if (D) $('hl').textContent = tx('web.home.hl24', usd(Math.max(D.high, L)), usd(Math.min(D.low, L)));
    const on = streaming();
    $('live-dot').hidden = !on;
    $('when').textContent = on ? tx('web.home.live', hms(live.lastMsg)) : tx('web.home.live_rest', hms(st.raw.live.at || Date.now()));
    drawSpark();
  }
  // tính lại công cụ theo giá mới, không quá một lần mỗi 10 giây
  function heavySoon() {
    const run = () => { live.heavyAt = Date.now(); live.heavyT = null; renderEntry(); renderHome(); requestAnimationFrame(redraw); };
    const wait = 10000 - (Date.now() - live.heavyAt);
    if (wait <= 0) run(); else if (!live.heavyT) live.heavyT = setTimeout(run, wait);
  }
  function onLive() {
    if (!st.raw.live.at) st.raw.live.at = Date.now();
    if (!st.S) $('when').textContent = tx('web.ui.gia_truc_tiep');
    renderQuote(false);
    heavySoon();
  }
  function startStream() {
    if (window.BOT_NO_WS || typeof WebSocket === 'undefined') return;  // bài kiểm tra tắt luồng để số liệu cố định
    let ws;
    try { ws = new WebSocket(WS_URLS[live.url % WS_URLS.length]); } catch (e) { return; }
    live.ws = ws;
    ws.onmessage = (ev) => {
      let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
      const c = Number(m.c); if (!(c > 0)) return;
      live.lastMsg = Date.now(); live.retry = 1000;
      live.day = { open: Number(m.o), high: Number(m.h), low: Number(m.l) };
      st.raw.live = { price: c, at: live.lastMsg };
      if (!st.status.live || !st.status.live.ok) setStatus('live', true, 'Binance');
      if (live.spark && live.spark.length) live.spark[live.spark.length - 1][1] = c;
      renderQuote(true);
      heavySoon();
    };
    ws.onclose = () => {
      if (live.ws !== ws) return;
      live.ws = null; live.url++;
      renderQuote(false);
      setTimeout(startStream, live.retry); live.retry = Math.min(60000, live.retry * 2);
    };
    ws.onerror = () => { try { ws.close(); } catch (e) { /* bỏ qua */ } };
  }
  // đường giá 24 giờ qua (nến 15 phút Binance); dùng cả làm mốc 24 giờ khi chưa có luồng
  async function loadSpark() {
    const start = Date.now() - 86400000;
    for (const base of URLS.kl) {
      try {
        const j = await getJSON(`${base}?symbol=BTCUSDT&interval=15m&startTime=${start}&limit=96`, 15000);
        if (!Array.isArray(j) || !j.length) continue;
        live.spark = j.map((k) => [Number(k[0]), Number(k[4])]);
        if (!streaming()) live.day = { open: Number(j[0][1]), high: Math.max(...j.map((k) => Number(k[2]))), low: Math.min(...j.map((k) => Number(k[3]))) };
        renderQuote(false);
        return;
      } catch (e) { /* thử nguồn kế */ }
    }
  }
  function drawSpark() {
    const cv = $('spark'), S = live.spark;
    cv.hidden = !(S && S.length > 2);
    if (cv.hidden || !cv.clientWidth) return;
    const W = cv.clientWidth, H = baseH(cv), dpr = window.devicePixelRatio || 1;
    cv.style.height = H + 'px'; cv.width = W * dpr; cv.height = H * dpr;
    const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
    const v = S.map((x) => x[1]), lo = Math.min(...v), hi = Math.max(...v), up = v[v.length - 1] >= v[0], col = up ? '#5FD3A5' : '#FF9C86';
    const x = (i) => 2 + (i / (v.length - 1)) * (W - 6), y = (p) => 3 + (hi === lo ? 0.5 : (hi - p) / (hi - lo)) * (H - 6);
    g.beginPath(); v.forEach((p, i) => (i ? g.lineTo(x(i), y(p)) : g.moveTo(x(i), y(p))));
    g.strokeStyle = col; g.lineWidth = 1.6; g.lineJoin = 'round'; g.stroke();
    g.lineTo(x(v.length - 1), H); g.lineTo(x(0), H); g.closePath(); g.fillStyle = col; g.globalAlpha = 0.14; g.fill(); g.globalAlpha = 1;
    g.beginPath(); g.arc(x(v.length - 1), y(v[v.length - 1]), 2.6, 0, Math.PI * 2); g.fillStyle = col; g.fill();
  }

  // ----- điện thoại: mỗi dòng bảng hiện thành một thẻ, mỗi ô kèm tên cột (data-label từ dòng tiêu đề; CSS table.stack ở page.html) -----
  function labelTable(t) {
    const r0 = t.rows[0], hr = t.tHead ? t.tHead.rows[0] : r0 && [...r0.cells].every((c) => c.tagName === 'TH') ? r0 : null;
    if (!hr) return;
    if (!t.tHead) hr.classList.add('hd');  // bảng trong câu trả lời của Claude: dòng đầu là tiêu đề
    const names = [];
    for (const th of hr.cells) {
      const n = [...th.childNodes].filter((x) => !(x.classList && x.classList.contains('sub'))).map((x) => x.textContent).join('').trim();
      for (let k = 0; k < th.colSpan; k++) names.push(n);
    }
    for (const tr of t.rows) {
      if (tr === hr) continue;
      let j = 0;
      for (const td of tr.cells) { if (td.colSpan > 1) td.classList.add('wide'); else td.dataset.label = names[j] || ''; j += td.colSpan; }
    }
    t.classList.add('stack');
  }
  let labelQueued = false;
  new MutationObserver(() => {
    if (labelQueued) return;
    labelQueued = true;
    requestAnimationFrame(() => { labelQueued = false; document.querySelectorAll('#app table').forEach(labelTable); });
  }).observe($('app'), { childList: true, subtree: true });

  // ----- thẻ (tab) và nền sáng / tối -----
  const TABS = [...document.querySelectorAll('#tabs [role=tab]')], TAB_IDS = TABS.map((b) => b.dataset.tab);
  function showTab(name) {
    if (!TAB_IDS.includes(name)) name = 'home';
    TABS.forEach((b) => { const on = b.dataset.tab === name; b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1; });
    document.querySelectorAll('.tabp').forEach((p) => { p.hidden = p.dataset.panel !== name; });
    try { if (location.hash !== '#' + name) history.replaceState(null, '', '#' + name); } catch (e) { /* bỏ qua */ }
    requestAnimationFrame(redraw);
  }
  TABS.forEach((b, i) => {
    b.addEventListener('click', () => showTab(b.dataset.tab));
    b.addEventListener('keydown', (ev) => {
      const j = ev.key === 'ArrowRight' ? (i + 1) % TABS.length : ev.key === 'ArrowLeft' ? (i - 1 + TABS.length) % TABS.length : -1;
      if (j >= 0) { ev.preventDefault(); showTab(TABS[j].dataset.tab); TABS[j].focus(); }
    });
  });
  window.addEventListener('hashchange', () => showTab(location.hash.slice(1)));
  $('theme').addEventListener('click', () => {
    const root = document.documentElement, cur = root.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'), nx = cur === 'dark' ? 'light' : 'dark';
    root.dataset.theme = nx;
    try { localStorage.setItem('btc-bot3-theme', nx); } catch (e) { /* bỏ qua */ }
    requestAnimationFrame(redrawAll);
  });

  function renderStatus() {
    const names ={ live: tx('web.ui.gia_truc_tiep_2'), fng: 'Fear & Greed (Alternative.me)', cm: tx('web.ui.gia_lich_su_mvrv_tho_dao'), kl: tx('web.ui.gia_va_khoi_luong_ngay_binance'), cache: tx('web.ui.du_lieu_luu_tren_may') };
    $('status').replaceChildren(...Object.entries(st.status).map(([k, s]) => el('li', s.ok ? 'ok' : 'err', `${names[k]}: ${s.ok || k === 'cache' ? s.msg : tx('web.ui.loi') + s.msg}`)));
  }


  initPlan();
  initSellPlan();
  if ($('fc-sec')) renderForecast();
  if ($('rb-sec')) renderRebuild();
  renderKN();
  renderEntry();
  applyMode();
  showTab(location.hash.slice(1));
  loadAll();
  startStream();
  loadSpark();
  setInterval(() => { if (!streaming()) loadLive(); }, 15 * 1000);
  setInterval(loadSpark, 15 * 60 * 1000);
})();
