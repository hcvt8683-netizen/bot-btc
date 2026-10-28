// ===== CORE START =====
const BOT = (() => {
  const tx = typeof I18N !== 'undefined' ? I18N.tx : require('./i18n.js').tx;
  const DAY = 86400000;
  const iso = (t) => new Date(t).toISOString().slice(0, 10);
  const num = (x) => { const v = Number(x); return x == null || x === '' || !isFinite(v) ? null : v; };
  const WIN = 1461;
  const MAX_UOC = 3; // số ngày cuối tối đa được ước tính vốn hóa và MVRV khi Coin Metrics chưa công bố

  const FAMILIES = { tamly: tx('web.engine.tam_ly'), onchain: tx('web.engine.dinh_gia_on_chain'), xuhuong: tx('web.engine.xu_huong_gia'), thodao: tx('web.engine.tho_dao'), chuky: tx('web.engine.chu_ky'), khoiluong: tx('web.engine.khoi_luong') };
  // dir -1: giá trị thấp là rẻ; +1: giá trị cao là rẻ. feat: 'pct' = vị trí trong 4 năm gần nhất, 'raw' = giá trị gốc × scale
  // vote: ngưỡng cho phương pháp biểu quyết [ngưỡng +1, ngưỡng +2, ngưỡng nóng]
  const IND = [
    { id: 'fng', ten: 'Fear & Greed', nhom: 'tamly', dir: -1, feat: 'raw', scale: 0.01, dec: 0, vote: [24, 9, 75], need: 'fng',
      y: tx('web.engine.tam_ly_dam_dong_0_100') },
    { id: 'mvrv', ten: 'MVRV', nhom: 'onchain', dir: -1, feat: 'pct', dec: 2, vote: [1.3, 1.0, 2.4], need: 'cm',
      y: tx('web.engine.gia_chia_cho_gia_von_trung') },
    { id: 'mvrvz', ten: 'MVRV Z-Score', nhom: 'onchain', dir: -1, feat: 'pct', dec: 2, vote: [0.5, 0, 3], need: 'cm',
      y: tx('web.engine.chenh_lech_von_hoa_thi_truong') },
    { id: 'wma', ten: tx('web.engine.gia_ma_200_tuan'), nhom: 'xuhuong', dir: -1, feat: 'pct', dec: 2, vote: [1.15, 1.0, 2.5],
      y: tx('web.engine.gia_so_voi_trung_binh_khoang') },
    { id: 'mayer', ten: 'Mayer Multiple', nhom: 'xuhuong', dir: -1, feat: 'pct', dec: 2, vote: [0.8, 0.65, 2.4],
      y: tx('web.engine.gia_so_voi_trung_binh_200') },
    { id: 'rsiw', ten: tx('web.engine.rsi_14_tuan'), nhom: 'xuhuong', dir: -1, feat: 'raw', scale: 0.01, dec: 0, vote: [35, 30, 80],
      y: tx('web.engine.suc_manh_gia_tren_khung_tuan') },
    { id: 'pi', ten: tx('web.engine.ti_so_pi_cycle'), nhom: 'xuhuong', dir: -1, feat: 'raw', scale: 1, dec: 2, vote: [0.4, 0.33, 0.95],
      y: tx('web.engine.ma_111_ngay_chia_cho_2') },
    { id: 'puell', ten: 'Puell Multiple', nhom: 'thodao', dir: -1, feat: 'pct', dec: 2, vote: [0.6, 0.5, 3.5], need: 'iss',
      y: tx('web.engine.gia_tri_btc_moi_phat_hanh') },
    { id: 'dd', ten: tx('web.engine.giam_tu_dinh'), nhom: 'chuky', dir: 1, feat: 'raw', scale: 0.01, dec: 1, unit: '%', vote: [45, 60, 15], high: true,
      y: tx('web.engine.gia_thap_hon_dinh_cao_nhat') },
    { id: 'vol', ten: tx('web.engine.khoi_luong_tuong_doi'), nhom: 'khoiluong', dir: 1, feat: 'raw', scale: 1, dec: 2, vote: null, need: 'vol',
      y: tx('web.engine.khoi_luong_giao_dich_trung_binh') },
  ];

  // ---------------------------------------------------------------- dữ liệu
  function buildSeries({ cm, kl, fng, live }) {
    const rows = new Map();
    if (cm && cm.length) {
      for (const r of cm) { const p = Number(r.PriceUSD); if (p > 0) rows.set(String(r.time).slice(0, 10), { p, mc: num(r.CapMrktCurUSD), mv: num(r.CapMVRVCur), iss: num(r.IssTotUSD) }); }
    } else if (kl && kl.length) {
      for (const k of kl) { const p = Number(k[4]); if (p > 0) rows.set(iso(Number(k[0])), { p, mc: null, mv: null, iss: null }); }
    }
    const qvMap = new Map();
    if (kl && kl.length) for (const k of kl) { const q = Number(k[7]); if (q > 0) qvMap.set(iso(Number(k[0])), q); }
    const keys = [...rows.keys()].sort();
    if (!keys.length) throw new Error(tx('web.engine.khong_co_du_lieu_gia_lich'));
    const full = []; let last = null;
    for (let t = Date.parse(keys[0] + 'T00:00:00Z'), e = Date.parse(keys[keys.length - 1] + 'T00:00:00Z'); t <= e; t += DAY) {
      const d = iso(t), r = rows.get(d); if (r) last = r; full.push([d, r || { ...last, iss: null }]);
    }
    // Coin Metrics có thể công bố giá trước, vốn hóa và MVRV sau: các ngày cuối còn thiếu (tối đa MAX_UOC ngày)
    // được ước tính từ ngày gần nhất có đủ số liệu, theo tỉ lệ giá. Chỉ dùng số liệu đến chính ngày đó.
    let k0 = full.length - 1, uocTinh = null;
    while (k0 >= 0 && (full[k0][1].mc == null || full[k0][1].mv == null)) k0--;
    if (k0 >= 0 && k0 < full.length - 1 && full.length - 1 - k0 <= MAX_UOC) {
      const b = full[k0][1];
      for (let k = k0 + 1; k < full.length; k++) { const r = full[k][1], f = r.p / b.p; full[k] = [full[k][0], { ...r, mc: b.mc * f, mv: b.mv * f }]; }
      uocTinh = { tu: full[k0][0], den: full[full.length - 1][0], ngay: full.length - 1 - k0 };
    }
    const today = iso(Date.now());
    if (live && live.price > 0) {
      const lr = full[full.length - 1][1], k = live.price / lr.p;
      const mk = () => ({ p: live.price, mc: lr.mc != null ? lr.mc * k : null, mv: lr.mv != null ? lr.mv * k : null, iss: null });
      if (full[full.length - 1][0] === today) full[full.length - 1] = [today, mk()];
      else if (full[full.length - 1][0] < today) {
        for (let t = Date.parse(full[full.length - 1][0] + 'T00:00:00Z') + DAY; iso(t) < today; t += DAY) full.push([iso(t), { ...lr, iss: null }]);
        full.push([today, mk()]);
      }
    }
    const n = full.length;
    const S = { dates: full.map((x) => x[0]), price: new Float64Array(n), mc: [], mv: [], iss: [], fng: new Array(n).fill(null),
      has: { cm: !!(cm && cm.length) && full.some((x) => x[1].mv != null), iss: full.some((x) => x[1].iss != null), fng: !!(fng && fng.length), vol: qvMap.size > 400 } };
    full.forEach(([, r], i) => { S.price[i] = r.p; S.mc.push(r.mc); S.mv.push(r.mv); S.iss.push(r.iss); });
    S.uocTinh = uocTinh;
    S.qv = S.dates.map((d) => qvMap.get(d) ?? null);
    if (S.qv[n - 1] != null) S.qv[n - 1] = null; // ngày hôm nay chưa đóng, khối lượng chưa đủ
    if (fng && fng.length) {
      const m = new Map(fng.map((f) => [iso(Number(f.timestamp) * 1000), Number(f.value)])); let lf = null;
      for (let i = 0; i < n; i++) { const v = m.get(S.dates[i]); if (v != null) lf = v; S.fng[i] = v != null ? v : (i === n - 1 ? lf : null); }
    }
    computeRaw(S);
    return S;
  }

  function computeRaw(S) {
    const n = S.price.length, P = new Float64Array(n + 1);
    for (let i = 0; i < n; i++) P[i + 1] = P[i] + S.price[i];
    const sma = (i, w) => (i + 1 >= w ? (P[i + 1] - P[i + 1 - w]) / w : null);
    const IS = new Float64Array(n + 1), IC = new Int32Array(n + 1);
    for (let i = 0; i < n; i++) { const v = S.iss[i]; IS[i + 1] = IS[i] + (v ?? 0); IC[i + 1] = IC[i] + (v != null ? 1 : 0); }
    const QS = new Float64Array(n + 1), QC = new Int32Array(n + 1);
    for (let i = 0; i < n; i++) { const q = S.qv ? S.qv[i] : null; QS[i + 1] = QS[i] + (q ?? 0); QC[i + 1] = QC[i] + (q != null ? 1 : 0); }
    const qavg = (i, w, minc) => { const a = Math.max(0, i + 1 - w), c = QC[i + 1] - QC[a]; return c >= minc ? (QS[i + 1] - QS[a]) / c : null; };
    S.qavg = qavg;
    const V = {}; IND.forEach((d) => { V[d.id] = new Array(n).fill(null); });
    let ath = 0, cnt = 0, mean = 0, m2 = 0, lastPuell = null;
    for (let i = 0; i < n; i++) {
      const p = S.price[i]; ath = Math.max(ath, p);
      V.dd[i] = (1 - p / ath) * 100;
      V.fng[i] = S.fng[i];
      const a200 = sma(i, 200), a1400 = sma(i, 1400), a111 = sma(i, 111), a350 = sma(i, 350);
      if (a200) V.mayer[i] = p / a200;
      if (a1400) V.wma[i] = p / a1400;
      if (a111 && a350) V.pi[i] = a111 / (2 * a350);
      if (i >= 7 * 14) { // RSI 14 tuần, tính trên giá cách nhau 7 ngày
        let up = 0, dn = 0; for (let k = 0; k < 14; k++) { const d = S.price[i - 7 * k] - S.price[i - 7 * (k + 1)]; if (d > 0) up += d; else dn -= d; }
        V.rsiw[i] = dn === 0 ? 100 : 100 - 100 / (1 + up / dn);
      }
      const mc = S.mc[i], mv = S.mv[i];
      if (mc != null) { cnt++; const d = mc - mean; mean += d / cnt; m2 += d * (mc - mean); }
      if (mc != null && mv != null && mv > 0 && cnt > 30) { V.mvrv[i] = mv; V.mvrvz[i] = (mc - mc / mv) / Math.sqrt(m2 / cnt); (S.zsd = S.zsd || [])[i] = Math.sqrt(m2 / cnt); }
      { const s30 = qavg(i, 30, 25), s365 = qavg(i, 365, 300); if (s30 && s365) V.vol[i] = s30 / s365; else if (i === n - 1 && V.vol[i - 1] != null) V.vol[i] = V.vol[i - 1]; }
      const a = Math.max(0, i + 1 - 365), c = IC[i + 1] - IC[a];
      if (S.iss[i] != null && c >= 300) { lastPuell = S.iss[i] / ((IS[i + 1] - IS[a]) / c); V.puell[i] = lastPuell; }
      else if (i === n - 1 && lastPuell != null) V.puell[i] = lastPuell;
    }
    S.v = V; S.pctMemo = {};
    S.avail = IND.filter((d) => !d.need || S.has[d.need]).map((d) => d.id);
  }

  function pctAt(S, id, i) {
    const key = id + ':' + i; if (key in S.pctMemo) return S.pctMemo[key];
    const v = S.v[id], x = v[i]; let r = null;
    if (x != null) {
      let less = 0, eq = 0, tot = 0;
      for (let j = Math.max(0, i - WIN + 1); j <= i; j++) { const y = v[j]; if (y == null) continue; tot++; if (y < x) less++; else if (y === x) eq++; }
      if (tot >= 365) r = (less + 0.5 * eq) / tot;
    }
    S.pctMemo[key] = r; return r;
  }
  function featAt(S, id, i) {
    const d = IND.find((x) => x.id === id);
    if (d.feat === 'pct') return pctAt(S, id, i);
    const v = S.v[id][i]; return v == null ? null : v * d.scale;
  }
  // ---------------------------------------------------------------- hồi quy logistic có điều chuẩn
  function solve(A, b) {
    const n = b.length, M = A.map((r, i) => [...r, b[i]]);
    for (let c = 0; c < n; c++) {
      let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
      [M[c], M[p]] = [M[p], M[c]];
      const pv = M[c][c] || 1e-12;
      for (let r = 0; r < n; r++) { if (r === c) continue; const f = M[r][c] / pv; if (!f) continue; for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
    }
    return M.map((r, i) => r[n] / (r[i] || 1e-12));
  }
  function fitLogit(X, y, init, lambda = 2) {
    const n = X.length, d = X[0].length, mu = new Array(d).fill(0), sd = new Array(d).fill(0);
    for (const x of X) for (let k = 0; k < d; k++) mu[k] += x[k] / n;
    for (const x of X) for (let k = 0; k < d; k++) sd[k] += (x[k] - mu[k]) ** 2 / n;
    for (let k = 0; k < d; k++) sd[k] = Math.sqrt(sd[k]) || 1;
    const Z = X.map((x) => [1, ...x.map((v, k) => (v - mu[k]) / sd[k])]);
    let w = init && init.length === d + 1 ? [...init] : new Array(d + 1).fill(0);
    if (!init) { const m = y.reduce((a, b) => a + b, 0) / n; w[0] = Math.log((m + 1e-3) / (1 - m + 1e-3)); }
    for (let it = 0; it < 30; it++) {
      const g = new Array(d + 1).fill(0), Hm = Array.from({ length: d + 1 }, () => new Array(d + 1).fill(0));
      for (let s = 0; s < n; s++) {
        const z = Z[s]; let e = 0; for (let k = 0; k <= d; k++) e += w[k] * z[k];
        const p = 1 / (1 + Math.exp(-e)), q = p * (1 - p), res = y[s] - p;
        for (let a = 0; a <= d; a++) { g[a] += res * z[a]; const qa = q * z[a]; for (let b = a; b <= d; b++) Hm[a][b] += qa * z[b]; }
      }
      for (let a = 0; a <= d; a++) for (let b = 0; b < a; b++) Hm[a][b] = Hm[b][a];
      for (let k = 1; k <= d; k++) { g[k] -= lambda * w[k]; Hm[k][k] += lambda; }
      const delta = solve(Hm, g); let mx = 0;
      for (let k = 0; k <= d; k++) { w[k] += delta[k]; mx = Math.max(mx, Math.abs(delta[k])); }
      if (mx < 1e-6) break;
    }
    return { w, mu, sd };
  }
  const predLogit = (m, x) => { let e = m.w[0]; for (let k = 0; k < x.length; k++) e += m.w[k + 1] * (x[k] - m.mu[k]) / m.sd[k]; return 1 / (1 + Math.exp(-e)); };

  // ---------------------------------------------------------------- đo lường
  function wilson(k, n) { if (!n) return [null, null]; const z = 1.96, p = k / n, d = 1 + z * z / n, c = p + z * z / (2 * n), m = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return [Math.max(0, (c - m) / d), Math.min(1, (c + m) / d)]; }
  const median = (a) => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const quant = (a, q) => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.max(0, Math.round(q * (s.length - 1))))]; };

  // ---------------------------------------------------------------- khối lượng giao dịch
  const VCLS = {
    tang_xn: { ten: tx('web.engine.tang_co_khoi_luong_xac_nhan'), tone: 'good' },
    tang_yeu: { ten: tx('web.engine.tang_nhung_khoi_luong_thap'), tone: 'mid' },
    giam_manh: { ten: tx('web.engine.giam_kem_khoi_luong_lon'), tone: 'bad' },
    giam_yeu: { ten: tx('web.engine.giam_voi_khoi_luong_thap'), tone: 'mid' },
    thuong: { ten: tx('web.engine.khoi_luong_va_gia_binh_thuong'), tone: '' },
  };
  function volumeStudy(S) {
    if (!S.has.vol) return null;
    const n = S.price.length, weeks = [];
    for (let i = 7; i < n - 1; i++) {
      if (new Date(S.dates[i] + 'T00:00:00Z').getUTCDay() !== 0) continue;
      let v = 0, c = 0; for (let k = 0; k < 7; k++) { const q = S.qv[i - k]; if (q != null) { v += q; c++; } }
      if (c < 6) continue;
      weeks.push({ i, date: S.dates[i], vol: v * 7 / c, chg: S.price[i] / S.price[i - 7] - 1 });
    }
    weeks.forEach((w, k) => {
      const prev = weeks.slice(Math.max(0, k - 20), k);
      w.rv = prev.length >= 10 ? w.vol / (prev.reduce((a, x) => a + x.vol, 0) / prev.length) : null;
      const up = w.chg > 0.02, dn = w.chg < -0.02, hi = w.rv != null && w.rv >= 1.25, lo = w.rv != null && w.rv <= 0.8;
      w.cls = w.rv == null ? null : up && hi ? 'tang_xn' : up && lo ? 'tang_yeu' : dn && hi ? 'giam_manh' : dn && lo ? 'giam_yeu' : 'thuong';
      w.f4 = k + 4 < weeks.length ? S.price[weeks[k + 4].i] / S.price[w.i] - 1 : null;
      w.f13 = k + 13 < weeks.length ? S.price[weeks[k + 13].i] / S.price[w.i] - 1 : null;
    });
    // kiểm chứng: sau mỗi loại tuần, giá đi tiếp thế nào
    const testOf = (pick) => {
      const sel = weeks.filter(pick), out = { n: sel.length };
      for (const h of ['f4', 'f13']) {
        const r = sel.map((w) => w[h]).filter((x) => x != null), k = r.filter((x) => x > 0).length, [lo, hi] = wilson(k, r.length);
        out[h] = { n: r.length, win: r.length ? k / r.length : null, lo, hi, med: median(r) };
      }
      return out;
    };
    const test = [{ id: 'all', ten: tx('web.engine.moi_tuan_moc_so_sanh'), ...testOf((w) => w.cls != null) }]
      .concat(Object.entries(VCLS).map(([id, c]) => ({ id, ten: c.ten, tone: c.tone, ...testOf((w) => w.cls === id) })));
    // các đợt tăng/giảm từ 20% trở lên (zigzag trên giá đóng cửa ngày)
    const start = S.qv.findIndex((q) => q != null), thr = 0.2, piv = [];
    if (start >= 0) {
      let dir = 0, ext = start, base = start;
      for (let i = start + 1; i < n; i++) {
        const p = S.price[i];
        if (dir >= 0 && p > S.price[ext]) ext = i;
        if (dir <= 0 && p < S.price[ext]) ext = i;
        if (dir === 0) { if (p >= S.price[base] * (1 + thr)) { dir = 1; piv.push(base); ext = i; } else if (p <= S.price[base] * (1 - thr)) { dir = -1; piv.push(base); ext = i; } continue; }
        if (dir === 1 && p <= S.price[ext] * (1 - thr)) { piv.push(ext); dir = -1; ext = i; }
        else if (dir === -1 && p >= S.price[ext] * (1 + thr)) { piv.push(ext); dir = 1; ext = i; }
      }
      piv.push(n - 1);
    }
    const waves = [];
    for (let k = 0; k + 1 < piv.length; k++) {
      const a = piv[k], b = piv[k + 1]; if (b - a < 3) continue;
      const qs = []; for (let i = a + 1; i <= b; i++) if (S.qv[i] != null) qs.push(S.qv[i]);
      if (qs.length < 3) continue;
      const avg = qs.reduce((x, y) => x + y, 0) / qs.length, ref = S.qavg(a, 365, 200);
      const h1 = qs.slice(0, qs.length >> 1), h2 = qs.slice(qs.length >> 1);
      const trend = h1.length && h2.length ? (h2.reduce((x, y) => x + y, 0) / h2.length) / (h1.reduce((x, y) => x + y, 0) / h1.length) : null;
      const chg = S.price[b] / S.price[a] - 1, rel = ref ? avg / ref : null, up = chg > 0;
      let note;
      if (rel == null) note = tx('web.engine.chua_du_lich_su_khoi_luong');
      else if (up) note = rel >= 1.2 && trend >= 1 ? tx('web.engine.tang_kem_khoi_luong_lon_va')
        : rel >= 1.2 ? tx('web.engine.khoi_luong_lon_nhung_giam_dan')
        : rel < 0.9 ? tx('web.engine.tang_voi_khoi_luong_thap_thieu') : tx('web.engine.khoi_luong_binh_thuong');
      else note = trend != null && trend >= 1.3 && rel >= 1 ? tx('web.engine.khoi_luong_don_manh_ve_cuoi')
        : rel >= 1.2 ? tx('web.engine.giam_kem_khoi_luong_lon_ap')
        : rel < 0.9 ? tx('web.engine.giam_voi_khoi_luong_thap_chu') : tx('web.engine.khoi_luong_binh_thuong');
      waves.push({ from: S.dates[a], to: S.dates[b], open: b === n - 1, chg, days: b - a, rel, trend, note });
    }
    const done = weeks.filter((w) => w.cls != null);
    return { weeks, test, waves, last: done[done.length - 1] || null, recent: done.slice(-8) };
  }

  return { IND, FAMILIES, VCLS, buildSeries, wilson, volumeStudy,
    _: { featAt, fitLogit, predLogit, median, quant, computeRaw } };
})();
// ===== CORE END =====
if (typeof module !== 'undefined') module.exports = BOT;
