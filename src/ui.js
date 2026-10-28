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
      $('loading').hidden = false; $('loading').textContent = e.message + tx('web.ui.kiem_tra_mang_hoac_mo_bang');
      $('progress').textContent = '';
    } finally { /* xong */ }
  }
  async function loadLive() {
    for (const u of URLS.live) { try { const j = await getJSON(u, 15000); if (Number(j.price) > 0) { st.raw.live = { price: Number(j.price) }; setStatus('live', true, 'Binance'); return; } } catch (e) { /* tiếp */ } }
    try { const j = await getJSON(URLS.gecko, 15000); st.raw.live = { price: j.bitcoin.usd }; setStatus('live', true, 'CoinGecko'); } catch (e) { setStatus('live', false, e.message); }
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
    $('price').textContent = usd(S.price[last]);
    $('when').textContent = st.raw.live ? tx('web.ui.gia_truc_tiep') : tx('web.ui.gia_dong_cua_0', fmtDate(S.dates[last]));
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
      $('loading').hidden = true; $('app').hidden = false;
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
  const report = () => B3.report(st.S, st.a, st.rec, st.vol && { last: st.vol.weeks.filter((x) => x.cls && x.date <= st.a.date).pop() }, sourcesText(), st.asOf === st.S.price.length - 1, st.cmp, st.sd, st.lv, KN);
  function download(name, text, type) { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000); }
  $('dl-md').addEventListener('click', () => download(`bao-cao-bot-btc-${st.a.date}.md`, report(), 'text/markdown;charset=utf-8'));
  $('dl-csv').addEventListener('click', () => download(`du-lieu-tuan-bot-btc-${st.a.date}.csv`, B3.csvWeekly(st.S, st.a), 'text/csv;charset=utf-8'));
  $('dl-pa').addEventListener('click', () => { if (!st.cmp) { $('copy-msg').textContent = tx('web.ui.chua_co_ket_qua_so_sanh'); return; } download(`so-sanh-phuong-an-bot-btc-${st.a.date}.csv`, B3.csvOptions(st.cmp), 'text/csv;charset=utf-8'); });


  // ================================================================ BÊN BÁN
  try { const md = localStorage.getItem('btc-bot3-mode'); if (md === 'sell' || md === 'buy') st.mode = md; } catch (e) { /* bỏ qua */ }
  st.mode = st.mode || 'buy';
  function applyMode() {
    const sell = st.mode === 'sell';
    $('mode-buy').setAttribute('aria-pressed', String(!sell)); $('mode-sell').setAttribute('aria-pressed', String(sell));
    $('buy-view').hidden = sell; $('sell-view').hidden = !sell;
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
    try { await navigator.clipboard.writeText(report()); } catch (e) { const ta = el('textarea'); ta.value = report(); document.body.append(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
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
  function addMsg(role, text, srcs) {
    const m = el('div', 'msg ' + role);
    if (role === 'assistant') { m.append(mdToNodes(text)); if (srcs && srcs.length) { const ol = el('ol', 'srcs'); srcs.forEach((x) => { const li = el('li'); const a = el('a', null, x.title); a.href = x.url; a.target = '_blank'; a.rel = 'noopener'; li.append(a); ol.append(li); }); m.append(el('div', 'sub', tx('web.ui.nguon_claude_da_doc')), ol); } }
    else m.textContent = text;
    $('chat').append(m); m.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }
  async function callClaude() {
    const key = $('ck').value.trim(); if (!key) throw new Error(tx('web.ui.hay_dan_khoa_api_cua_claude'));
    const body = { model: $('cmodel').value, max_tokens: 4000, system: SYS, messages: chat.map((x) => ({ role: x.role, content: x.content })) };
    if ($('cweb').checked) body.tools = [{ type: 'web_search_20250305', name: 'web_search', max_uses: 5 }];
    let text = '', srcs = [];
    for (let k = 0; k < 6; k++) {
      let r;
      try {
        r = await fetch('https://api.anthropic.com/v1/messages', { method: 'POST', headers: { 'content-type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true' }, body: JSON.stringify(body) });
      } catch (e) { throw new Error(tx('web.ui.khong_ket_noi_duoc_claude_api')); }
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(r.status === 401 ? tx('web.ui.khoa_api_khong_hop_le') : r.status === 429 ? tx('web.ui.claude_dang_gioi_han_so_luot') : tx('web.ui.claude_api_bao_loi_0_1', r.status, (j.error && j.error.message) || ''));
      for (const b of j.content || []) {
        if (b.type === 'text') { text += b.text; (b.citations || []).forEach((c) => c.url && srcs.push({ title: c.title || c.url, url: c.url })); }
        if (b.type === 'web_search_tool_result' && Array.isArray(b.content)) b.content.forEach((x) => x.url && srcs.push({ title: x.title || x.url, url: x.url }));
      }
      if (j.stop_reason === 'pause_turn') { body.messages = [...body.messages, { role: 'assistant', content: j.content }]; continue; }
      break;
    }
    const seen = new Set(); srcs = srcs.filter((x) => !seen.has(x.url) && seen.add(x.url)).slice(0, 12);
    return { text: text.trim(), srcs };
  }
  async function sendToClaude(q, first) {
    const btns = [$('ai-first'), $('ai-send')]; btns.forEach((b) => { b.disabled = true; }); $('ai-busy').hidden = false; $('ai-err').hidden = true;
    const content = first ? tx('web.ui.day_la_bao_cao_moi_nhat', report(), q) : q;
    chat.push({ role: 'user', content }); addMsg('user', q);
    try { const r = await callClaude(); chat.push({ role: 'assistant', content: r.text || tx('web.ui.claude_khong_tra_loi_noi_dung') }); addMsg('assistant', r.text, r.srcs); }
    catch (e) { chat.pop(); $('ai-err').textContent = e.message; $('ai-err').hidden = false; }
    finally { btns.forEach((b) => { b.disabled = false; }); $('ai-busy').hidden = true; }
  }
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
      if (KN.reasons.includes('model_failed')) { const p = el('p', 'lead'); p.append(el('b', null, tx('web.kn.why')), tx('web.kn.reason_model_failed'), ' ', tx('web.kn.current_zone_note')); notes.push(p); }
    }
    $('kn-notes').replaceChildren(...notes);
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
    const evs = KN ? KN.events.map((e) => el('li', null, tx('web.kn.event_line', vnTime(e.time), tx('web.kn.ev_' + e.type)))) : [];
    $('kn-events').replaceChildren(...(evs.length ? evs : [el('li', null, tx('web.kn.events_none'))]), ...(KN && !KN.event_delay ? [el('li', null, tx('web.kn.no_delay'))] : []));
    $('kn-fresh').replaceChildren(...(KN ? Object.entries(KN.freshness).map(([k, s]) => el('li', s.ok ? 'ok' : 'err',
      s.ok ? tx('web.kn.fresh_ok', tx('sources.' + k), fmtDate(s.last)) : tx('web.kn.fresh_err', tx('sources.' + k), s.error))) : []));
    if (KN) { $('updated').textContent = tx('web.kn.updated', vnTime(KN.generated_at)); $('updated').hidden = false; }
    $('stale').hidden = !stale;
    if (stale) $('stale').textContent = tx('web.kn.stale_banner', vnTime(KN.generated_at));
  }

  function renderStatus() {
    const names = { live: tx('web.ui.gia_truc_tiep_2'), fng: 'Fear & Greed (Alternative.me)', cm: tx('web.ui.gia_lich_su_mvrv_tho_dao'), kl: tx('web.ui.gia_va_khoi_luong_ngay_binance'), cache: tx('web.ui.du_lieu_luu_tren_may') };
    $('status').replaceChildren(...Object.entries(st.status).map(([k, s]) => el('li', s.ok ? 'ok' : 'err', `${names[k]}: ${s.ok || k === 'cache' ? s.msg : tx('web.ui.loi') + s.msg}`)));
  }


  loadAll();
  setInterval(async () => { if (!st.S) return; await loadLive(); if (st.raw.live) $('price').textContent = usd(st.raw.live.price); }, 60 * 1000);
})();
