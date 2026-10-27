// ===== CORE START =====
const BOT = (() => {
  const DAY = 86400000;
  const iso = (t) => new Date(t).toISOString().slice(0, 10);
  const num = (x) => { const v = Number(x); return x == null || x === '' || !isFinite(v) ? null : v; };
  const WIN = 1461;
  const MAX_UOC = 3; // số ngày cuối tối đa được ước tính vốn hóa và MVRV khi Coin Metrics chưa công bố

  const FAMILIES = { tamly: 'Tâm lý', onchain: 'Định giá on-chain', xuhuong: 'Xu hướng giá', thodao: 'Thợ đào', chuky: 'Chu kỳ', khoiluong: 'Khối lượng' };
  // dir -1: giá trị thấp là rẻ; +1: giá trị cao là rẻ. feat: 'pct' = vị trí trong 4 năm gần nhất, 'raw' = giá trị gốc × scale
  // vote: ngưỡng cho phương pháp biểu quyết [ngưỡng +1, ngưỡng +2, ngưỡng nóng]
  const IND = [
    { id: 'fng', ten: 'Fear & Greed', nhom: 'tamly', dir: -1, feat: 'raw', scale: 0.01, dec: 0, vote: [24, 9, 75], need: 'fng',
      y: 'Tâm lý đám đông 0–100 của Alternative.me, có từ 02/2018. Thấp là sợ hãi.' },
    { id: 'mvrv', ten: 'MVRV', nhom: 'onchain', dir: -1, feat: 'pct', dec: 2, vote: [1.3, 1.0, 2.4], need: 'cm',
      y: 'Giá chia cho giá vốn trung bình của toàn bộ BTC đang lưu hành. Dưới 1 là người giữ trung bình đang lỗ.' },
    { id: 'mvrvz', ten: 'MVRV Z-Score', nhom: 'onchain', dir: -1, feat: 'pct', dec: 2, vote: [0.5, 0, 3], need: 'cm',
      y: 'Chênh lệch vốn hóa thị trường và vốn hóa thực, chia cho độ lệch chuẩn lịch sử.' },
    { id: 'wma', ten: 'Giá / MA 200 tuần', nhom: 'xuhuong', dir: -1, feat: 'pct', dec: 2, vote: [1.15, 1.0, 2.5],
      y: 'Giá so với trung bình khoảng 4 năm; đường này từng là đáy của nhiều chu kỳ.' },
    { id: 'mayer', ten: 'Mayer Multiple', nhom: 'xuhuong', dir: -1, feat: 'pct', dec: 2, vote: [0.8, 0.65, 2.4],
      y: 'Giá so với trung bình 200 ngày.' },
    { id: 'rsiw', ten: 'RSI 14 tuần', nhom: 'xuhuong', dir: -1, feat: 'raw', scale: 0.01, dec: 0, vote: [35, 30, 80],
      y: 'Sức mạnh giá trên khung tuần, 0–100. Dưới 30 là bán quá đà, trên 80 là mua quá đà.' },
    { id: 'pi', ten: 'Tỉ số Pi Cycle', nhom: 'xuhuong', dir: -1, feat: 'raw', scale: 1, dec: 2, vote: [0.4, 0.33, 0.95],
      y: 'MA 111 ngày chia cho 2 lần MA 350 ngày. Chạm 1 từng báo đỉnh 2013, 2017, 4/2021, nhưng không chạm ở đỉnh 2025.' },
    { id: 'puell', ten: 'Puell Multiple', nhom: 'thodao', dir: -1, feat: 'pct', dec: 2, vote: [0.6, 0.5, 3.5], need: 'iss',
      y: 'Giá trị BTC mới phát hành cho thợ đào so với trung bình 365 ngày. Halving làm chỉ số tụt cơ học.' },
    { id: 'dd', ten: 'Giảm từ đỉnh', nhom: 'chuky', dir: 1, feat: 'raw', scale: 0.01, dec: 1, unit: '%', vote: [45, 60, 15], high: true,
      y: 'Giá thấp hơn đỉnh cao nhất bao nhiêu phần trăm. Đáy các chu kỳ trước giảm 77–84%, chu kỳ 2026 khoảng 54%.' },
    { id: 'vol', ten: 'Khối lượng tương đối', nhom: 'khoiluong', dir: 1, feat: 'raw', scale: 1, dec: 2, vote: null, need: 'vol',
      y: 'Khối lượng giao dịch trung bình 30 ngày chia cho trung bình 365 ngày, cặp BTC/USDT trên Binance (có từ 08/2017). Trên 1 là sôi động hơn bình thường. Không dùng trong biểu quyết vì khối lượng cao xuất hiện cả ở đỉnh lẫn đáy; để mô hình tự học chiều tác động.' },
  ];
  const HOLD = { '1m': { ten: '1 tháng', tuan: 4, thang: 1 }, '3m': { ten: '3 tháng', tuan: 13, thang: 3 }, '6m': { ten: '6 tháng', tuan: 26, thang: 6 }, '12m': { ten: '1 năm', tuan: 52, thang: 12 } };
  const FRAMES = { tuan: { ten: 'Mua theo tuần', unit: 'tuần', minTrain: 104, refit: 4 }, thang: { ten: 'Mua theo tháng', unit: 'tháng', minTrain: 30, refit: 1 } };
  const LEVELS = { 2: 'Nên mua', 1: 'Cân nhắc mua', 0: 'Không mua thêm', '-1': 'Cân nhắc bán', '-2': 'Nên bán' };

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
    if (!keys.length) throw new Error('Không có dữ liệu giá lịch sử');
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
  function voteAt(d, v) {
    if (v == null || !d.vote) return null;
    const [b1, b2, hot] = d.vote;
    if (d.high) return v >= b2 ? 2 : v >= b1 ? 1 : v < hot ? -1 : 0;
    return v <= b2 ? 2 : v <= b1 ? 1 : v >= hot ? -1 : 0;
  }

  function samples(S, frame) {
    const out = [];
    for (let i = 0; i < S.dates.length; i++) {
      const d = S.dates[i];
      if (frame === 'tuan') { if (new Date(d + 'T00:00:00Z').getUTCDay() === 0) out.push(i); }
      else if (i + 1 < S.dates.length && S.dates[i + 1].slice(5, 7) !== d.slice(5, 7)) out.push(i);
    }
    if (out[out.length - 1] !== S.dates.length - 1) out.push(S.dates.length - 1);
    return out;
  }

  // bảng mẫu theo khung: mỗi dòng là một lần kiểm tra, kèm kết quả nếu giữ H kỳ
  function rows(S, frame, H, ids) {
    const smp = samples(S, frame);
    return smp.map((i, j) => {
      const f = {}; ids.forEach((id) => { f[id] = featAt(S, id, i); });
      const r = j + H < smp.length ? S.price[smp[j + H]] / S.price[i] - 1 : null;
      return { j, i, date: S.dates[i], f, r, y: r == null ? null : r > 0 ? 1 : 0, known: j + H };
    });
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

  // ---------------------------------------------------------------- dự báo đi tới (không nhìn trước)
  // kind: 'base' | 'logit' | 'vote'
  function walkForward(S, R, ids, kind, frame, fromDate, toDate) {
    const F = FRAMES[frame], preds = [], fits = [];
    let model = null, lastFit = -1e9, vtab = null;
    const ok = (r) => ids.every((id) => r.f[id] != null);
    for (const r of R) {
      if (r.date < fromDate || (toDate && r.date > toDate)) continue;
      if (!ok(r)) continue;
      const train = R.filter((t) => t.known <= r.j && t.y != null && ok(t));
      if (train.length < F.minTrain) continue;
      const p0 = train.reduce((a, t) => a + t.y, 0) / train.length;
      let p = p0;
      if (kind === 'logit' && ids.length) {
        if (r.j - lastFit >= F.refit || !model) {
          model = fitLogit(train.map((t) => ids.map((id) => t.f[id])), train.map((t) => t.y), model && model.w);
          lastFit = r.j; fits.push({ date: r.date, w: model.w.slice(1), n: train.length });
        }
        p = predLogit(model, ids.map((id) => r.f[id]));
      } else if (kind === 'vote' && ids.length) {
        if (r.j - lastFit >= F.refit || !vtab) { vtab = voteTable(S, train, ids, p0); lastFit = r.j; }
        p = vtab.lookup(voteScore(S, r.i, ids));
      }
      preds.push({ j: r.j, i: r.i, date: r.date, p, p0, y: r.y, r: r.r });
    }
    return { preds, fits };
  }
  function voteScore(S, i, ids) {
    const fam = {};
    for (const id of ids) { const d = IND.find((x) => x.id === id); if (!d.vote) continue; const s = voteAt(d, S.v[id][i]); if (s == null) return null; (fam[d.nhom] = fam[d.nhom] || []).push(s); }
    if (!Object.keys(fam).length) return null;
    const av = Object.values(fam).map((a) => a.reduce((x, y) => x + y, 0) / a.length);
    return av.reduce((x, y) => x + y, 0) / av.length;
  }
  function voteTable(S, train, ids, p0) {
    const bin = (t) => (t == null ? null : Math.max(-2, Math.min(4, Math.round(t * 2))));
    const agg = {};
    for (const t of train) { const b = bin(voteScore(S, t.i, ids)); if (b == null) continue; (agg[b] = agg[b] || [0, 0]); agg[b][0] += t.y; agg[b][1]++; }
    return { lookup: (s) => { const b = bin(s); const a = agg[b] || [0, 0]; return (a[0] + 8 * p0) / (a[1] + 8); } };
  }

  // ---------------------------------------------------------------- đo lường
  function wilson(k, n) { if (!n) return [null, null]; const z = 1.96, p = k / n, d = 1 + z * z / n, c = p + z * z / (2 * n), m = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return [Math.max(0, (c - m) / d), Math.min(1, (c + m) / d)]; }
  const median = (a) => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const quant = (a, q) => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.max(0, Math.round(q * (s.length - 1))))]; };
  function auc(ps) {
    const pos = ps.filter((x) => x.y === 1).length, neg = ps.length - pos; if (!pos || !neg) return null;
    const s = [...ps].sort((a, b) => a.p - b.p); let rank = 0, sum = 0, i = 0;
    while (i < s.length) { let j = i; while (j + 1 < s.length && s[j + 1].p === s[i].p) j++; const r = (i + j + 2) / 2; for (let k = i; k <= j; k++) if (s[k].y === 1) sum += r; i = j + 1; }
    return (sum - pos * (pos + 1) / 2) / (pos * neg);
  }
  const levelOf = (p, p0) => (p >= p0 + 0.10 ? 2 : p >= p0 + 0.04 ? 1 : p <= p0 - 0.15 ? -2 : p <= p0 - 0.08 ? -1 : 0);
  function episodes(list) { let e = 0, prev = -9; for (const x of list) { if (x.j - prev > 1) e++; prev = x.j; } return e; }
  function metrics(preds, a, b) {
    const ps = preds.filter((x) => x.y != null && (!a || x.date >= a) && (!b || x.date <= b));
    if (!ps.length) return { n: 0 };
    const br = ps.reduce((s, x) => s + (x.p - x.y) ** 2, 0) / ps.length, br0 = ps.reduce((s, x) => s + (x.p0 - x.y) ** 2, 0) / ps.length;
    const lv = {};
    for (const L of [2, 1, 0, -1, -2]) {
      const sel = ps.filter((x) => levelOf(x.p, x.p0) === L), k = sel.filter((x) => x.y === 1).length;
      const [lo, hi] = wilson(k, sel.length);
      lv[L] = { n: sel.length, eps: episodes(sel), win: sel.length ? k / sel.length : null, lo, hi, med: median(sel.map((x) => x.r)) };
    }
    const allK = ps.filter((x) => x.y === 1).length;
    return { n: ps.length, eps: episodes(ps), brier: br, brier0: br0, bss: 1 - br / br0, auc: auc(ps), base: allK / ps.length, lv, from: ps[0].date, to: ps[ps.length - 1].date };
  }
  function calibration(preds) {
    const ps = preds.filter((x) => x.y != null), bins = [];
    for (let b = 0; b < 10; b++) {
      const sel = ps.filter((x) => Math.min(9, Math.floor(x.p * 10)) === b); if (!sel.length) continue;
      const k = sel.filter((x) => x.y === 1).length, [lo, hi] = wilson(k, sel.length);
      bins.push({ b, pred: sel.reduce((s, x) => s + x.p, 0) / sel.length, act: k / sel.length, n: sel.length, lo, hi });
    }
    return bins;
  }

  // ---------------------------------------------------------------- phối hợp tối ưu: thêm dần từng chỉ số
  async function greedy(S, R, cand, frame, fromDate, toDate, tick) {
    let chosen = [], best = -Infinity; const steps = [];
    const evalSet = (ids) => metrics(walkForward(S, R, ids, 'logit', frame, fromDate, toDate).preds).bss;
    while (chosen.length < 6) {
      let pick = null, pickScore = -Infinity; const tried = [];
      for (const id of cand) {
        if (chosen.includes(id)) continue;
        const sc = evalSet([...chosen, id]); tried.push({ id, bss: sc });
        if (sc > pickScore) { pickScore = sc; pick = id; }
        if (tick) await tick();
      }
      if (!pick) break;
      const gain = pickScore - (chosen.length ? best : 0);
      steps.push({ them: pick, bss: pickScore, tang: gain, thu: tried.sort((a, b) => b.bss - a.bss) });
      if (gain < 0.005) { steps[steps.length - 1].dung = true; break; }
      chosen = [...chosen, pick]; best = pickScore;
    }
    return { ids: chosen, steps };
  }

  // giai đoạn theo chu kỳ halving
  const ERAS = [['2014-01-01', '2016-07-08', '2014–2016'], ['2016-07-09', '2020-05-10', '2016–2020'], ['2020-05-11', '2024-04-19', '2020–2024'], ['2024-04-20', '2099-12-31', '2024–nay']];
  function eraAUC(R, ids) {
    const out = {};
    for (const id of ids) {
      const d = IND.find((x) => x.id === id);
      out[id] = ERAS.map(([a, b, ten]) => {
        const sel = R.filter((r) => r.date >= a && r.date <= b && r.y != null && r.f[id] != null).map((r) => ({ p: r.f[id] * d.dir, y: r.y }));
        return { ten, n: sel.length, auc: sel.length >= 20 ? auc(sel) : null };
      });
    }
    return out;
  }

  // mô phỏng: cùng ngân sách 100 $/tuần, mua đều so với mua theo mức của bot
  const MULT = { 2: 2.5, 1: 1.5, 0: 0.6, '-1': 0.4, '-2': 0.2 };
  const SELL = { '-2': 0.05, '-1': 0 };
  function simulate(S, preds, frame) {
    const amt = frame === 'tuan' ? 100 : 100 * 52 / 12, lastP = S.price[S.price.length - 1];
    const run = (bot) => {
      let cash = 0, btc = 0, inv = 0, spent = 0, buys = [];
      for (const x of preds) {
        if (x.i === S.price.length - 1) continue;
        const px = S.price[x.i]; cash += amt; inv += amt;
        const L = bot ? levelOf(x.p, x.p0) : 0;
        if (bot && SELL[L] && btc > 0) { const q = btc * SELL[L]; btc -= q; cash += q * px; }
        const b = Math.min(cash, amt * (bot ? MULT[L] : 1)); if (b > 0) { btc += b / px; cash -= b; spent += b; buys.push(px); }
      }
      const value = btc * lastP + cash;
      return { inv, value, cash, btc, roi: inv ? value / inv - 1 : 0, avg: btc ? spent / btc : null, lan: buys.length, dangLai: buys.length ? buys.filter((p) => p < lastP).length / buys.length : null };
    };
    return { deu: run(false), bot: run(true) };
  }

  // ---------------------------------------------------------------- chạy toàn bộ cho một khung
  async function analyze(S, cfg, frame, tick = null) {
    const H = HOLD[cfg.hold][frame], ids = cfg.ids.filter((id) => S.avail.includes(id));
    const R = rows(S, frame, H, ids);
    const allOk = (r) => ids.every((id) => r.f[id] != null);
    const firstAll = R.find(allOk);
    if (!firstAll) throw new Error('Các chỉ số đã chọn chưa có đủ dữ liệu chung.');
    // mốc đánh giá chung: từ lúc mọi chỉ số đã chọn có số liệu và đủ dữ liệu huấn luyện
    const pre = walkForward(S, R, ids, 'base', frame, firstAll.date);
    const evalFrom = pre.preds.length ? pre.preds[0].date : firstAll.date;
    const known = pre.preds.filter((x) => x.y != null);
    const mid = known.length ? known[Math.floor(known.length / 2)].date : evalFrom;
    const methods = [];
    const add = (id, ten, kind, use, note) => { const wf = walkForward(S, R, use, kind, frame, evalFrom); methods.push({ id, ten, kind, ids: use, note, wf, m: metrics(wf.preds), m1: metrics(wf.preds, null, mid), m2: metrics(wf.preds, mid) }); };
    add('base', 'Mốc: chỉ dựa vào tỉ lệ có lãi trung bình trước đó', 'base', []);
    for (const id of ids) { add('one:' + id, IND.find((d) => d.id === id).ten + ' (riêng)', 'logit', [id]); if (tick) await tick(); }
    add('vote', 'Biểu quyết theo nhóm (ngưỡng cố định)', 'vote', ids); if (tick) await tick();
    add('logit', 'Hồi quy logistic, mọi chỉ số đã chọn', 'logit', ids); if (tick) await tick();
    const g = await greedy(S, R, ids, frame, evalFrom, mid, tick);
    if (g.ids.length) add('auto', 'Tổ hợp tự chọn: ' + g.ids.map((id) => IND.find((d) => d.id === id).ten).join(' + '), 'logit', g.ids, 'chọn trên nửa đầu');
    // chọn phương pháp: tự động = tốt nhất ở nửa đầu; người dùng có thể chỉ định
    let chosen;
    if (cfg.method === 'auto') {
      chosen = methods.filter((x) => x.id !== 'base' && x.m1.n).sort((a, b) => b.m1.bss - a.m1.bss)[0] || methods[0];
    } else chosen = methods.find((x) => x.id === cfg.method) || methods.find((x) => x.id === 'logit');
    // dự báo hôm nay: huấn luyện trên toàn bộ dữ liệu đã biết kết quả
    const last = R[R.length - 1], train = R.filter((t) => t.y != null && chosen.ids.every((id) => t.f[id] != null));
    const p0 = train.reduce((a, t) => a + t.y, 0) / train.length;
    let pNow = p0, model = null;
    if (chosen.kind === 'logit' && chosen.ids.every((id) => last.f[id] != null)) { model = fitLogit(train.map((t) => chosen.ids.map((id) => t.f[id])), train.map((t) => t.y)); pNow = predLogit(model, chosen.ids.map((id) => last.f[id])); }
    else if (chosen.kind === 'vote') pNow = voteTable(S, train, chosen.ids, p0).lookup(voteScore(S, last.i, chosen.ids));
    // xác suất đã hiệu chỉnh: lịch sử những lần bot dự báo gần bằng hôm nay
    const known2 = chosen.wf.preds.filter((x) => x.y != null);
    let band = 0.04, near = [];
    while (band <= 0.2) { near = known2.filter((x) => Math.abs(x.p - pNow) <= band); if (near.length >= 20) break; band += 0.04; }
    const k = near.filter((x) => x.y === 1).length, [lo, hi] = wilson(k, near.length);
    const lvNow = levelOf(pNow, p0);
    const out = {
      frame, H, holdTen: HOLD[cfg.hold].ten, ids, evalFrom, mid, R, methods, chosen, greedy: g,
      today: { date: last.date, price: S.price[last.i], pNow, p0, level: lvNow, hist: { n: near.length, eps: episodes(near), win: near.length ? k / near.length : null, lo, hi, band,
        med: median(near.map((x) => x.r)), q1: quant(near.map((x) => x.r), 0.25), q3: quant(near.map((x) => x.r), 0.75) },
        weights: model ? chosen.ids.map((id, kx) => ({ id, w: model.w[kx + 1] * IND.find((d) => d.id === id).dir })) : null,
        feats: ids.map((id) => ({ id, v: S.v[id][last.i], f: last.f[id], vote: voteAt(IND.find((d) => d.id === id), S.v[id][last.i]) })) },
      eras: eraAUC(R, ids), calib: calibration(chosen.wf.preds), sim: simulate(S, chosen.wf.preds, frame),
    };
    out.log = buildLog(S, out, cfg);
    return out;
  }

  // ---------------------------------------------------------------- nhật ký tư duy (sinh từ số liệu đã tính)
  const P = (x, d = 0) => (x == null || !isFinite(x) ? '—' : (x * 100).toFixed(d).replace('.', ',') + '%');
  const D = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`;
  const nameOf = (id) => IND.find((d) => d.id === id).ten;
  function buildLog(S, o, cfg) {
    const F = FRAMES[o.frame], base = o.methods.find((m) => m.id === 'base'), L = [];
    const missing = cfg.ids.filter((id) => !S.avail.includes(id));
    L.push({ t: 'Đặt câu hỏi', s: [`Nếu ${F.ten.toLowerCase()} và giữ ${o.holdTen}, xác suất lần mua đó có lãi là bao nhiêu? "Thành công" được định nghĩa cứng: giá sau ${o.H} ${F.unit} cao hơn giá lúc mua. Không dùng định nghĩa nào khác để số liệu không bị uốn theo ý muốn.`] });
    L.push({ t: 'Kiểm tra dữ liệu', s: [`Giá từ ${D(S.dates[0])} đến ${D(S.dates[S.dates.length - 1])}, ${S.dates.length.toLocaleString('vi-VN')} ngày.`,
      `Chỉ số đang dùng: ${o.ids.map(nameOf).join(', ')}.` + (missing.length ? ` Không dùng được vì thiếu nguồn: ${missing.map(nameOf).join(', ')}.` : ''),
      `Mọi chỉ số đã chọn cùng có số liệu và đủ ${F.minTrain} ${F.unit} để học từ ${D(o.evalFrom)}, nên mọi phương pháp được chấm trên cùng khoảng này để so sánh công bằng.`] });
    L.push({ t: 'Đặt mốc so sánh', s: [`Trong khoảng chấm điểm, mua bất kỳ ${F.unit} nào rồi giữ ${o.holdTen} có lãi ${P(base.m.base)} số lần (${base.m.n} lần). Bitcoin tăng dài hạn nên mốc này đã cao; một chỉ số chỉ có ích nếu vượt được nó.`,
      `Thước đo chính là điểm kỹ năng Brier: 0 nghĩa là không hơn mốc, dương là tốt hơn, âm là tệ hơn. Kèm theo là AUC: 0,5 là đoán bừa, càng gần 1 càng phân biệt tốt lần lãi với lần lỗ.`] });
    const singles = o.methods.filter((m) => m.id.startsWith('one:')).sort((a, b) => b.m.bss - a.m.bss);
    const helpful = singles.filter((m) => m.m.bss > 0.005), useless = singles.filter((m) => m.m.bss <= 0.005);
    L.push({ t: 'Thử từng chỉ số riêng lẻ', s: [helpful.length ? `Tốt hơn mốc: ${helpful.map((m) => `${m.ten.replace(' (riêng)', '')} (${m.m.bss >= 0 ? '+' : ''}${m.m.bss.toFixed(3).replace('.', ',')})`).join(', ')}.` : 'Không chỉ số riêng lẻ nào vượt mốc rõ rệt.',
      useless.length ? `Không hơn mốc: ${useless.map((m) => m.ten.replace(' (riêng)', '')).join(', ')}.` : ''].filter(Boolean) });
    const eraLines = o.ids.map((id) => { const e = o.eras[id].filter((x) => x.auc != null); if (!e.length) return null;
      const good = e.filter((x) => x.auc >= 0.58).map((x) => x.ten), bad = e.filter((x) => x.auc <= 0.48).map((x) => x.ten);
      return `${nameOf(id)}: ` + (good.length ? `khớp ở ${good.join(', ')}` : 'không khớp rõ ở giai đoạn nào') + (bad.length ? `; ngược ở ${bad.join(', ')}` : '') + '.'; }).filter(Boolean);
    L.push({ t: 'Xem từng giai đoạn chu kỳ', s: ['Mỗi chỉ số được chấm riêng trong từng chu kỳ halving, vì một chỉ số có thể đúng ở chu kỳ này mà sai ở chu kỳ khác.', ...eraLines] });
    const lg = o.methods.find((m) => m.id === 'logit'), vt = o.methods.find((m) => m.id === 'vote');
    L.push({ t: 'Phối hợp các chỉ số', s: [`Biểu quyết theo nhóm (đếm phiếu, ngưỡng cố định): điểm kỹ năng ${vt.m.bss.toFixed(3).replace('.', ',')}.`,
      `Hồi quy logistic dùng mọi chỉ số: điểm kỹ năng ${lg.m.bss.toFixed(3).replace('.', ',')}. Mô hình tự học trọng số từ dữ liệu quá khứ và học lại mỗi ${F.refit} ${F.unit}, nên khi một chỉ số hết hiệu quả, trọng số của nó tự giảm.`,
      'Thêm chỉ số không tự động làm kết quả đáng tin hơn: các chỉ số cùng nhóm (MVRV và MVRV Z-Score, MA 200 tuần và Mayer) gần như đo cùng một thứ. Vì vậy bot thử thêm từng chỉ số và chỉ giữ lại chỉ số làm điểm kỹ năng tăng thật.'] });
    if (o.greedy.steps.length) L.push({ t: 'Chọn tổ hợp tốt nhất trên nửa đầu dữ liệu', s: o.greedy.steps.map((s, k) => s.dung ? `Bước ${k + 1}: thêm ${nameOf(s.them)} chỉ tăng ${s.tang.toFixed(3).replace('.', ',')}, dưới ngưỡng 0,005, nên dừng.` : `Bước ${k + 1}: thêm ${nameOf(s.them)}, điểm kỹ năng ${s.bss.toFixed(3).replace('.', ',')} (tăng ${s.tang.toFixed(3).replace('.', ',')}).`) });
    const c = o.chosen;
    L.push({ t: 'Kiểm tra trên dữ liệu chưa dùng để chọn', s: [`Phương pháp được chọn: ${c.ten}.`,
      `Nửa đầu (${D(c.m1.from || o.evalFrom)}–${D(o.mid)}): điểm kỹ năng ${c.m1.bss != null ? c.m1.bss.toFixed(3).replace('.', ',') : '—'}. Nửa sau (${D(o.mid)}–${D(c.m2.to || o.mid)}), phần bot không dùng để chọn: ${c.m2.n ? c.m2.bss.toFixed(3).replace('.', ',') : 'chưa đủ dữ liệu'}.`,
      c.m2.n && c.m2.bss < 0 ? 'Ở nửa sau, phương pháp này kém hơn mốc. Đây là dấu hiệu quá khớp hoặc thị trường đã đổi tính chất; không nên tin mạnh vào kết luận.' : c.m2.n && c.m2.bss > 0 ? 'Phương pháp vẫn tốt hơn mốc ở nửa sau, nên kết quả có cơ sở hơn.' : ''].filter(Boolean) });
    const t = o.today, h = t.hist, lv = c.m.lv[2];
    L.push({ t: 'Kết luận hôm nay', s: [`Mô hình cho xác suất có lãi ${P(t.pNow)} so với mức trung bình ${P(t.p0)}, nên mức là "${LEVELS[t.level]}".`,
      h.n ? `Trong quá khứ có ${h.n} lần bot dự báo gần như vậy (thuộc ${h.eps} đợt); thực tế ${P(h.win)} số lần có lãi, khoảng tin cậy ${P(h.lo)}–${P(h.hi)}. Lãi trung vị ${P(h.med)}, một nửa số lần nằm trong ${P(h.q1)} đến ${P(h.q3)}.` : 'Chưa có đủ lần dự báo tương tự trong quá khứ để đối chiếu.',
      lv.n ? `Khi bot báo "Nên mua" trong quá khứ, ${P(lv.win)} số lần có lãi sau ${o.holdTen} (${lv.n} lần, ${lv.eps} đợt).` : 'Trong khoảng chấm điểm, bot chưa từng báo "Nên mua".'] });
    L.push({ t: 'Giới hạn', s: ['Bitcoin mới có khoảng 4 chu kỳ đầy đủ, nên số đợt độc lập ít; khoảng tin cậy rộng là bình thường.', 'Từ khi có quỹ ETF (2024), đỉnh và đáy nông hơn trước; mô hình học lại liên tục nhưng vẫn có thể chậm thích nghi.', 'Mọi con số trên trang đều tính từ dữ liệu tải về, không có số nào được đặt tay.'] });
    return L;
  }


  // ---------------------------------------------------------------- khối lượng giao dịch
  const VCLS = {
    tang_xn: { ten: 'Tăng có khối lượng xác nhận', tone: 'good' },
    tang_yeu: { ten: 'Tăng nhưng khối lượng thấp', tone: 'mid' },
    giam_manh: { ten: 'Giảm kèm khối lượng lớn', tone: 'bad' },
    giam_yeu: { ten: 'Giảm với khối lượng thấp', tone: 'mid' },
    thuong: { ten: 'Khối lượng và giá bình thường', tone: '' },
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
    const test = [{ id: 'all', ten: 'Mọi tuần (mốc so sánh)', ...testOf((w) => w.cls != null) }]
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
      if (rel == null) note = 'Chưa đủ lịch sử khối lượng để so sánh.';
      else if (up) note = rel >= 1.2 && trend >= 1 ? 'Tăng kèm khối lượng lớn và tăng dần: có lực mua thật.'
        : rel >= 1.2 ? 'Khối lượng lớn nhưng giảm dần về cuối đợt: lực mua yếu đi.'
        : rel < 0.9 ? 'Tăng với khối lượng thấp: thiếu xác nhận, dễ bị đảo chiều.' : 'Khối lượng bình thường.';
      else note = trend != null && trend >= 1.3 && rel >= 1 ? 'Khối lượng dồn mạnh về cuối đợt: dấu hiệu bán tháo đầu hàng, thường gần đáy.'
        : rel >= 1.2 ? 'Giảm kèm khối lượng lớn: áp lực bán thật.'
        : rel < 0.9 ? 'Giảm với khối lượng thấp: chủ yếu do cạn lực mua.' : 'Khối lượng bình thường.';
      waves.push({ from: S.dates[a], to: S.dates[b], open: b === n - 1, chg, days: b - a, rel, trend, note });
    }
    const done = weeks.filter((w) => w.cls != null);
    return { weeks, test, waves, last: done[done.length - 1] || null, recent: done.slice(-8) };
  }

  // ---------------------------------------------------------------- bộ chỉ số khuyến cáo (suy ra từ kết quả vừa chạy)
  function recommend(res) {
    const ids = res.tuan.ids, rows = [];
    for (const id of ids) {
      const d = IND.find((x) => x.id === id); let score = 0; const why = [];
      for (const fr of ['tuan', 'thang']) {
        const o = res[fr], m = o.methods.find((x) => x.id === 'one:' + id), lab = fr === 'tuan' ? 'khung tuần' : 'khung tháng';
        if (!m || !m.m1.n || !m.m2.n) { why.push(`${lab}: chưa đủ dữ liệu`); continue; }
        const a = m.m1.bss > 0.005, b = m.m2.bss > 0.005;
        if (a && b) { score += 2; why.push(`${lab}: tốt hơn mốc ở cả hai nửa`); }
        else if (a || b) { score += 1; why.push(`${lab}: tốt hơn mốc ở ${a ? 'nửa đầu' : 'nửa sau'}`); }
        else if (m.m1.bss < -0.005 && m.m2.bss < -0.005) { score -= 1; why.push(`${lab}: kém hơn mốc ở cả hai nửa`); }
        else why.push(`${lab}: không hơn mốc`);
        if (o.greedy.ids.includes(id)) { score += 1; why.push(`được chọn vào tổ hợp tối ưu ${lab}`); }
      }
      const e = res.tuan.eras[id].filter((x) => x.auc != null), good = e.filter((x) => x.auc >= 0.58).length, bad = e.filter((x) => x.auc <= 0.45).length;
      if (good >= 2) { score += 1; why.push(`khớp ở ${good} chu kỳ halving`); }
      if (bad >= 2) { score -= 1; why.push(`chạy ngược cách hiểu thông thường ở ${bad} chu kỳ`); }
      rows.push({ id, ten: d.ten, nhom: d.nhom, score, why });
    }
    rows.sort((a, b) => b.score - a.score);
    const picks = [], perFam = {};
    for (const r of rows) {
      if (r.score < 3 || picks.length >= 6 || (perFam[r.nhom] || 0) >= 2) continue;
      picks.push(r.id); perFam[r.nhom] = (perFam[r.nhom] || 0) + 1;
    }
    let weak = false;
    if (picks.length < 2) { weak = true; for (const r of rows) if (r.score >= 1 && !picks.includes(r.id) && picks.length < 3) picks.push(r.id); }
    rows.forEach((r) => { r.pick = picks.includes(r.id); });
    return { picks, rows, weak, xetDu: ids.length === IND.length };
  }

  // ---------------------------------------------------------------- báo cáo để đưa cho Claude
  const PC = (x, d = 0) => (x == null || !isFinite(x) ? '—' : (x * 100).toFixed(d).replace('.', ',') + '%');
  const SPC = (x) => (x == null || !isFinite(x) ? '—' : (x > 0 ? '+' : '') + (x * 100).toFixed(0) + '%');
  const SK = (x) => (x == null || !isFinite(x) ? '—' : (x > 0 ? '+' : '') + x.toFixed(3).replace('.', ','));
  const USD = (x) => (x == null || !isFinite(x) ? '—' : Math.round(x).toLocaleString('vi-VN') + ' $');
  function buildReport(S, res, vol, rec, sources) {
    const L = [], t = (x) => L.push(x), last = S.dates.length - 1;
    t(`# Báo cáo bot xác suất mua BTC, ngày ${D(S.dates[last])}`);
    t('');
    t('Báo cáo do bot thống kê tạo ra từ dữ liệu tải trực tiếp trên web. Mọi con số đều tính từ dữ liệu; bot không có khả năng suy luận ngoài các phép tính này.');
    t('');
    t('## Bối cảnh');
    t(`- Giá BTC lúc chạy: ${USD(S.price[last])}`);
    t(`- Dữ liệu giá từ ${D(S.dates[0])} đến ${D(S.dates[last])}`);
    t(`- Nguồn: ${sources}`);
    t(`- Chỉ số dùng: ${res.tuan.ids.map(nameOf).join(', ')}`);
    t(`- Thời gian giữ để tính "thành công": ${res.tuan.holdTen} (thành công = giá sau kỳ giữ cao hơn giá mua)`);
    t(`- Cách kết hợp: ${res.cfg.method === 'auto' ? 'tự chọn cách tốt nhất trên nửa đầu dữ liệu' : res.cfg.method === 'logit' ? 'hồi quy logistic' : 'biểu quyết theo nhóm'}`);
    t('');
    t('## Kết luận hôm nay');
    for (const fr of ['tuan', 'thang']) {
      const o = res[fr], td = o.today, h = td.hist, nm = o.chosen.m.lv[2];
      t(`### ${FRAMES[fr].ten}`);
      t(`- Mức: **${LEVELS[td.level > 0 ? td.level : 0]}**; chiều bán: ${td.level < 0 ? LEVELS[td.level] : 'Không bán'}`);
      t(`- Xác suất mô hình: ${PC(td.pNow)}; tỉ lệ có lãi trung bình: ${PC(td.p0)}`);
      t(`- Xác suất đã hiệu chỉnh (theo ${h.n} lần dự báo tương tự, ${h.eps} đợt): ${PC(h.win)}, khoảng tin cậy 95% ${PC(h.lo)}–${PC(h.hi)}`);
      t(`- Lãi trung vị của các lần tương tự: ${SPC(h.med)}; một nửa số lần trong ${SPC(h.q1)} đến ${SPC(h.q3)}`);
      t(`- Khi bot từng báo "Nên mua": ${nm.n ? `${PC(nm.win)} có lãi (${nm.n} lần, ${nm.eps} đợt, khoảng tin cậy ${PC(nm.lo)}–${PC(nm.hi)})` : 'chưa từng báo'}`);
      t(`- Cách kết hợp được dùng: ${o.chosen.ten}; điểm kỹ năng Brier toàn bộ ${SK(o.chosen.m.bss)}, nửa đầu ${SK(o.chosen.m1.bss)}, nửa sau ${SK(o.chosen.m2.bss)}; AUC ${o.chosen.m.auc == null ? '—' : o.chosen.m.auc.toFixed(2).replace('.', ',')}`);
      t(`- Chấm điểm từ ${D(o.evalFrom)}, ${o.chosen.m.n} lần kiểm tra; chia đôi tại ${D(o.mid)}`);
      t('- Giá trị chỉ số hôm nay: ' + td.feats.map((f) => `${nameOf(f.id)} ${f.v == null ? '—' : (+f.v).toFixed(IND.find((d) => d.id === f.id).dec).replace('.', ',')}`).join('; '));
      t('');
    }
    if (rec) {
      t('## Bộ chỉ số khuyến cáo');
      t(rec.picks.length ? `Khuyến cáo: ${rec.picks.map(nameOf).join(', ')}${rec.weak ? ' (tín hiệu yếu, ít chỉ số đạt chuẩn)' : ''}.` : 'Chưa có chỉ số nào đạt chuẩn khuyến cáo.');
      t('');
      t('| Chỉ số | Điểm | Lý do |'); t('|---|---|---|');
      rec.rows.forEach((r) => t(`| ${r.ten}${r.pick ? ' (khuyến cáo)' : ''} | ${r.score} | ${r.why.join('; ')} |`));
      t('');
    }
    for (const fr of ['tuan', 'thang']) {
      const o = res[fr];
      t(`## Bảng xếp hạng cách dự báo, ${FRAMES[fr].ten.toLowerCase()}`);
      t('| Cách dự báo | Điểm kỹ năng | Nửa đầu | Nửa sau | AUC | Khi báo Nên mua |'); t('|---|---|---|---|---|---|');
      o.methods.forEach((m) => { const nm = m.m.lv[2]; t(`| ${m.ten}${m === o.chosen ? ' (đang dùng)' : ''} | ${SK(m.m.bss)} | ${SK(m.m1.bss)} | ${SK(m.m2.bss)} | ${m.m.auc == null || m.id === 'base' ? '—' : m.m.auc.toFixed(2).replace('.', ',')} | ${nm.n ? `${PC(nm.win)} (${nm.n} lần, ${nm.eps} đợt)` : '—'} |`); });
      t('');
      t(`Kết quả thực tế theo mức bot đưa ra (${FRAMES[fr].ten.toLowerCase()}):`);
      t('| Mức | Số lần | Có lãi | Khoảng tin cậy | Lãi trung vị |'); t('|---|---|---|---|---|');
      [2, 1, 0, -1, -2].forEach((Lv) => { const x = o.chosen.m.lv[Lv]; t(`| ${LEVELS[Lv]} | ${x.n} (${x.eps} đợt) | ${PC(x.win)} | ${PC(x.lo)}–${PC(x.hi)} | ${SPC(x.med)} |`); });
      t('');
    }
    t('## AUC từng chỉ số theo chu kỳ halving (khung tuần)');
    t('| Chỉ số | ' + ERAS.map((e) => e[2]).join(' | ') + ' |'); t('|---|' + ERAS.map(() => '---').join('|') + '|');
    res.tuan.ids.forEach((id) => t(`| ${nameOf(id)} | ` + res.tuan.eras[id].map((e) => (e.auc == null ? '—' : e.auc.toFixed(2).replace('.', ','))).join(' | ') + ' |'));
    t('');
    if (vol) {
      t('## Khối lượng giao dịch (BTC/USDT Binance)');
      if (vol.last) t(`Tuần gần nhất đã đóng (${D(vol.last.date)}): giá ${SPC(vol.last.chg)}, khối lượng bằng ${vol.last.rv.toFixed(2).replace('.', ',')} lần trung bình 20 tuần, loại "${VCLS[vol.last.cls].ten}".`);
      t('');
      t('| Loại tuần | Số tuần | Có lãi sau 4 tuần | Có lãi sau 13 tuần | Lãi trung vị 13 tuần |'); t('|---|---|---|---|---|');
      vol.test.forEach((r) => t(`| ${r.ten} | ${r.n} | ${PC(r.f4.win)} | ${PC(r.f13.win)} | ${SPC(r.f13.med)} |`));
      t('');
      t('Các đợt tăng/giảm từ 20% trở lên gần nhất:');
      t('| Từ | Đến | Giá | Số ngày | Khối lượng so với TB năm | Nhận xét |'); t('|---|---|---|---|---|---|');
      vol.waves.slice(-10).forEach((w) => t(`| ${D(w.from)} | ${w.open ? 'đang diễn ra' : D(w.to)} | ${SPC(w.chg)} | ${w.days} | ${w.rel == null ? '—' : w.rel.toFixed(2).replace('.', ',') + ' lần'} | ${w.note} |`));
      t('');
    }
    t('## Mô phỏng 100 $/tuần (chỉ dùng dự báo đi tới)');
    t('| Cách mua | Tổng nạp | Giá vốn TB | Giá trị hôm nay | Lời/lỗ | Số lần mua đang lãi |'); t('|---|---|---|---|---|---|');
    for (const fr of ['tuan', 'thang']) for (const k of ['deu', 'bot']) { const r = res[fr].sim[k]; t(`| ${fr === 'tuan' ? 'Mỗi tuần' : 'Mỗi tháng'}, ${k === 'deu' ? 'đều tay' : 'theo bot'} | ${USD(r.inv)} | ${USD(r.avg)} | ${USD(r.value)} | ${SPC(r.roi)} | ${PC(r.dangLai)} |`); }
    t('');
    t('## Nhật ký tư duy của bot (khung tuần)');
    res.tuan.log.forEach((l, k) => { t(`${k + 1}. **${l.t}.** ${l.s.join(' ')}`); });
    t('');
    t('## Phương pháp');
    t('- Kiểm chứng đi tới: mỗi lần dự báo chỉ học từ những lần mua đã biết kết quả tại thời điểm đó.');
    t('- Mốc so sánh là tỉ lệ có lãi trung bình trước đó; điểm kỹ năng Brier 0 nghĩa là không hơn mốc.');
    t('- MVRV, MVRV Z-Score, MA 200 tuần, Mayer, Puell được chuẩn hóa thành vị trí trong 4 năm gần nhất.');
    t('- Mức: Nên mua khi xác suất cao hơn trung bình ≥ 10 điểm %, Cân nhắc mua ≥ 4; Cân nhắc bán khi thấp hơn ≥ 8, Nên bán ≥ 15. Ngưỡng cố định.');
    t('');
    t('## Gợi ý câu hỏi cho Claude');
    t('- Nhận định của bot có đáng tin không, xét theo điểm kỹ năng nửa sau, số đợt độc lập và khoảng tin cậy?');
    t('- Bối cảnh vĩ mô và tin tức hiện tại có ủng hộ hay mâu thuẫn với kết luận của bot?');
    t('- Nên mua theo tuần hay theo tháng với số liệu này, và vì sao?');
    t('- Khối lượng giao dịch hiện tại xác nhận hay làm yếu xu hướng giá?');
    return L.join('\n');
  }
  function exportJSON(S, res, vol, rec) {
    const last = S.dates.length - 1, pick = (o) => ({ frame: o.frame, hold: o.holdTen, evalFrom: o.evalFrom, mid: o.mid, chosen: o.chosen.ten, today: { ...o.today, level: LEVELS[o.today.level] },
      methods: o.methods.map((m) => ({ ten: m.ten, bss: m.m.bss, bss1: m.m1.bss, bss2: m.m2.bss, auc: m.m.auc, nenMua: m.m.lv[2] })), levels: o.chosen.m.lv, eras: o.eras, sim: o.sim, log: o.log });
    return JSON.stringify({ ngay: S.dates[last], gia: S.price[last], chiSo: res.tuan.ids, tuan: pick(res.tuan), thang: pick(res.thang), khuyenCao: rec, khoiLuong: vol && { last: vol.last, test: vol.test, waves: vol.waves.slice(-15) } }, null, 1);
  }

  return { IND, FAMILIES, HOLD, FRAMES, LEVELS, ERAS, MULT, SELL, VCLS, buildSeries, analyze, levelOf, samples, wilson, volumeStudy, recommend, buildReport, exportJSON,
    _: { featAt, fitLogit, predLogit, median, quant, episodes, auc, computeRaw } };
})();
// ===== CORE END =====
if (typeof module !== 'undefined') module.exports = BOT;
