// ===== B3 START =====
const B3 = (() => {
  const tx = typeof I18N !== 'undefined' ? I18N.tx : require('./i18n.js').tx;
  const { IND, FAMILIES } = BOT;
  const { featAt, fitLogit, predLogit, median, quant, computeRaw } = BOT._;
  const wilson = BOT.wilson;
  const DAY = 86400000;

  const HZ = [
    { id: '1m', ten: tx('web.analysis.s_1_thang'), w: 4, days: 30 }, { id: '3m', ten: tx('web.analysis.s_3_thang'), w: 13, days: 91 },
    { id: '6m', ten: tx('web.analysis.s_6_thang'), w: 26, days: 182 }, { id: '1y', ten: tx('web.analysis.s_1_nam'), w: 52, days: 365 },
  ];
  const SELL_HZ = [{ id: '3m', ten: tx('web.analysis.s_3_thang'), w: 13 }, { id: '6m', ten: tx('web.analysis.s_6_thang'), w: 26 }];
  const SELL_DROP = -0.10;
  const BUY_Z = [{ id: 'phai', ten: tx('web.analysis.phai_mua'), min: 80 }, { id: 'cannhac', ten: tx('web.analysis.can_nhac_mua'), min: 60 }, { id: 'khong', ten: tx('web.analysis.khong_nen_mua'), min: 0 }];
  const SELL_Z = [{ id: 'nen', ten: tx('web.analysis.nen_ban'), min: 85 }, { id: 'cannhac', ten: tx('web.analysis.can_nhac_ban'), min: 70 }, { id: 'khong', ten: tx('web.analysis.khong_nen_ban'), min: 0 }];
  const zoneOf = (Z, v) => (v == null ? null : Z.find((z) => v >= z.min));
  const MIN_TRAIN = 78;
  // các phương án theo thứ tự ưu tiên thiết kế; xếp hạng thật do dữ liệu quyết định
  const OPTIONS = [
    { id: 'pa1', ten: tx('web.analysis.phuong_an_1'), ids: ['pi', 'mvrv'], lyDo: tx('web.analysis.xu_huong_gia_dinh_gia_on') },
    { id: 'pa2', ten: tx('web.analysis.phuong_an_2'), ids: ['pi', 'mvrvz'], lyDo: tx('web.analysis.nhu_phuong_an_1_nhung_dung') },
    { id: 'pa3', ten: tx('web.analysis.phuong_an_3'), ids: ['pi', 'mvrv', 'fng'], lyDo: tx('web.analysis.ba_goc_nhin_xu_huong_dinh') },
    { id: 'pa4', ten: tx('web.analysis.phuong_an_4'), ids: ['pi', 'puell'], lyDo: tx('web.analysis.xu_huong_gia_doanh_thu_tho') },
    { id: 'pa5', ten: tx('web.analysis.phuong_an_5'), ids: ['fng', 'mvrv', 'wma'], lyDo: tx('web.analysis.bo_can_bang_khong_dung_pi') },
    { id: 'pa6', ten: tx('web.analysis.phuong_an_6'), ids: null, lyDo: tx('web.analysis.bo_bot_tu_tim_co_ty') },
  ];
  const PRESETS = [
    { id: 'all', ten: tx('web.analysis.tat_ca_chi_so'), ids: IND.map((d) => d.id) },
    { id: 'onchain', ten: tx('web.analysis.dinh_gia_on_chain'), ids: ['mvrv', 'mvrvz', 'puell'] },
    { id: 'xuhuong', ten: tx('web.analysis.xu_huong_gia'), ids: ['wma', 'mayer', 'rsiw', 'pi'] },
    { id: 'tamly_dinhgia', ten: tx('web.analysis.tam_ly_va_dinh_gia'), ids: ['fng', 'mvrv', 'wma'] },
  ];

  // các lần kiểm tra theo tuần (Chủ nhật) đến trước ngày phân tích, cộng thêm chính ngày phân tích
  function weekly(S, asOf) {
    const out = [];
    for (let i = 0; i < asOf; i++) if (new Date(S.dates[i] + 'T00:00:00Z').getUTCDay() === 0) out.push(i);
    out.push(asOf);
    return out;
  }
  const featRows = (S, smp, ids) => smp.map((i, j) => { const f = ids.map((id) => featAt(S, id, i)); return { j, i, date: S.dates[i], f, ok: f.every((x) => x != null) }; });

  // vị trí 0–100 của mức chênh e trong thang so sánh đã sắp xếp
  const rankIn = (arr, e) => { let lo = 0, hi = arr.length; while (lo < hi) { const m = (lo + hi) >> 1; if (arr[m] < e) lo = m + 1; else hi = m; } let eq = lo; while (eq < arr.length && arr[eq] === e) eq++; return ((lo + 0.5 * (eq - lo)) / arr.length) * 100; };
  // dự báo đi tới: tại mỗi lần, chỉ học từ những lần đã biết kết quả trước đó
  function walk(S, smp, R, H, target, refit) {
    const preds = [], X = [], Y = [];
    let model = null, lastFit = -1e9, k = 0, sumY = 0, ref = null;
    for (const r of R) {
      while (k + H <= r.j) { const q = R[k]; if (q.ok) { const ret = S.price[smp[k + H]] / S.price[q.i] - 1; X.push(q.f); Y.push(target(ret)); sumY += Y[Y.length - 1]; } k++; }
      if (!r.ok || X.length < MIN_TRAIN) continue;
      const p0 = sumY / X.length;
      if (!model || r.j - lastFit >= refit) {
        model = fitLogit(X, Y, model && model.w); lastFit = r.j;
        // thang so sánh: mức chênh của mọi lần đã biết kết quả, theo mô hình vừa học (không nhìn trước)
        ref = X.map((x) => predLogit(model, x) - p0).sort((a, b) => a - b);
      }
      const p = predLogit(model, r.f), e = p - p0;
      const ret = r.j + H < smp.length ? S.price[smp[r.j + H]] / S.price[r.i] - 1 : null;
      preds.push({ j: r.j, i: r.i, date: r.date, p, p0, e, r: ret, rank: rankIn(ref, e) });
    }
    return { preds, model, ref };
  }
  // mô hình cuối cùng của từng kỳ giữ, để tính lại tỷ lệ tại ngày phân tích với giá giả định
  const fitOf = (ws) => ws.map((w) => ({ model: w.model, ref: w.ref, p0: w.preds[w.preds.length - 1].p0 }));

  // điểm tổng = trung bình vị trí của các kỳ giữ
  function combine(list) {
    const maps = list.map((w) => new Map(w.preds.map((x) => [x.j, x])));
    const out = [];
    for (const x of list[0].preds) {
      const xs = maps.map((m) => m.get(x.j));
      if (xs.some((y) => !y || y.rank == null)) continue;
      out.push({ j: x.j, i: x.i, date: x.date, score: xs.reduce((a, y) => a + y.rank, 0) / xs.length, rs: xs.map((y) => y.r) });
    }
    return out;
  }

  const winStat = (rets, cond) => { const r = rets.filter((x) => x != null); const k = r.filter(cond).length; const [lo, hi] = wilson(k, r.length); return { n: r.length, win: r.length ? k / r.length : null, lo, hi, med: median(r) }; };
  const eps = (list) => { let e = 0, prev = -9; for (const x of list) { if (x.j - prev > 1) e++; prev = x.j; } return e; };

  function buyEvidence(series, from) {
    const s = series.filter((x) => x.date >= from);
    const rowsOf = (pick) => { const sel = s.filter(pick); return { n: sel.length, eps: eps(sel), h: HZ.map((h, k) => winStat(sel.map((x) => x.rs[k]), (r) => r > 0)) }; };
    return { base: rowsOf(() => true), zones: BUY_Z.map((z) => ({ ...z, ...rowsOf((x) => zoneOf(BUY_Z, x.score) === z) })) };
  }
  function sellEvidence(series, from) {
    const s = series.filter((x) => x.date >= from);
    const rowsOf = (pick) => { const sel = s.filter(pick); return { n: sel.length, eps: eps(sel), h: SELL_HZ.map((h, k) => ({ giam: winStat(sel.map((x) => x.rs[k]), (r) => r < 0), giamManh: winStat(sel.map((x) => x.rs[k]), (r) => r < SELL_DROP) })) }; };
    return { base: rowsOf(() => true), zones: SELL_Z.map((z) => ({ ...z, ...rowsOf((x) => zoneOf(SELL_Z, x.score) === z) })) };
  }

  // đánh giá nhanh một bộ chỉ số (chỉ chiều mua), dùng khi tìm bộ tốt nhất
  function quickBuy(S, asOf, ids, refit = 8) {
    const smp = weekly(S, asOf), R = featRows(S, smp, ids);
    const ws = HZ.map((h) => walk(S, smp, R, h.w, (r) => (r > 0 ? 1 : 0), refit));
    return combine(ws);
  }
  function objective(series, from) {
    const ev = buyEvidence(series, from), z = ev.zones[0];
    if (z.n < 20 || z.eps < 2) return { score: -Infinity, ev };
    const lbs = z.h.map((x) => (x.n >= 10 ? x.lo : null)).filter((x) => x != null);
    if (!lbs.length) return { score: -Infinity, ev };
    return { score: lbs.reduce((a, b) => a + b, 0) / lbs.length, ev };
  }

  async function search(S, asOf, cand, tick) {
    cand = cand.filter((id) => S.avail.includes(id));
    const cache = new Map();
    const run = async (ids) => { const key = [...ids].sort().join(','); if (!cache.has(key)) { cache.set(key, quickBuy(S, asOf, ids)); if (tick) await tick(); } return cache.get(key); };
    const singles = [];
    for (const id of cand) { const s = await run([id]); if (s.length) singles.push({ id, first: s[0].date }); }
    if (!singles.length) throw new Error(tx('web.analysis.chua_du_du_lieu_de_tim'));
    const from = singles.map((x) => x.first).sort().pop() > '2021-01-01' ? singles.map((x) => x.first).sort().pop() : '2021-01-01';
    const usable = singles.map((x) => x.id);
    const evalIds = async (ids) => objective(await run(ids), from);
    let chosen = [], best = -Infinity; const steps = [];
    while (chosen.length < 6) {
      let pick = null, ps = -Infinity;
      for (const id of usable) { if (chosen.includes(id)) continue; const o = await evalIds([...chosen, id]); if (o.score > ps) { ps = o.score; pick = id; } }
      if (!pick) break;
      if (chosen.length && ps - best < 0.005) { steps.push({ them: pick, score: ps, dung: true }); break; }
      chosen = [...chosen, pick]; best = ps; steps.push({ them: pick, score: ps });
    }
    const cands = [{ ten: tx('web.analysis.bo_bot_tim_duoc'), ids: chosen }, ...PRESETS.map((p) => ({ ten: p.ten, ids: p.ids.filter((id) => usable.includes(id)) })), ...usable.map((id) => ({ ten: IND.find((d) => d.id === id).ten + tx('web.analysis.rieng'), ids: [id] }))];
    const ranking = [];
    for (const c of cands) {
      if (!c.ids.length) continue;
      const series = await run(c.ids), o = objective(series, from);
      const mid = series.filter((x) => x.date >= from); const midDate = mid.length ? mid[Math.floor(mid.length / 2)].date : from;
      const half = (a, b) => { const z = buyEvidence(series.filter((x) => x.date >= a && (!b || x.date < b)), a).zones[0]; return z.h; };
      ranking.push({ ...c, score: o.score, phai: o.ev.zones[0], base: o.ev.base, nua1: half(from, midDate), nua2: half(midDate) });
    }
    ranking.sort((a, b) => b.score - a.score);
    const seen = new Set(), uniq = ranking.filter((r) => { const k = [...r.ids].sort().join(','); if (seen.has(k)) return false; seen.add(k); return true; });
    return { ids: chosen, from, steps, ranking: uniq, asOfDate: S.dates[asOf], midNote: true };
  }

  // phân tích đầy đủ một bộ chỉ số tại một ngày
  function analyze(S, asOf, ids) {
    ids = ids.filter((id) => S.avail.includes(id));
    if (!ids.length) throw new Error(tx('web.analysis.hay_chon_it_nhat_mot_chi'));
    const smp = weekly(S, asOf), R = featRows(S, smp, ids);
    if (!R[R.length - 1].ok) throw new Error(tx('web.analysis.tai_ngay_phan_tich_mot_so'));
    const buyW = HZ.map((h) => walk(S, smp, R, h.w, (r) => (r > 0 ? 1 : 0), 4));
    const sellW = SELL_HZ.map((h) => walk(S, smp, R, h.w, (r) => (r < SELL_DROP ? 1 : 0), 4));
    const buyS = combine(buyW), sellS = combine(sellW);
    const nowJ = smp.length - 1;
    const bNow = buyS.find((x) => x.j === nowJ), sNow = sellS.find((x) => x.j === nowJ);
    if (!bNow || !sNow) throw new Error(tx('web.analysis.chua_du_lich_su_de_cham'));
    const from = buyS[0].date;
    // xác suất thắng hôm nay cho từng kỳ giữ: tỉ lệ thực tế của những lần trước có điều kiện gần giống
    const hold = HZ.map((h, k) => {
      const w = buyW[k], now = w.preds[w.preds.length - 1], past = w.preds.filter((x) => x.r != null);
      let band = 0.03, near = [];
      while (band <= 0.3) { near = past.filter((x) => Math.abs(x.e - now.e) <= band); if (near.length >= 25) break; band += 0.03; }
      const st = winStat(near.map((x) => x.r), (r) => r > 0), base = winStat(past.map((x) => x.r), (r) => r > 0);
      const act = asOf + h.days < S.price.length ? S.price[asOf + h.days] / S.price[asOf] - 1 : null;
      return { ...h, ...st, eps: eps(near), base: base.win, q1: quant(near.map((x) => x.r), 0.25), q3: quant(near.map((x) => x.r), 0.75), thucTe: act };
    });
    const weights = buyW[2].model ? ids.map((id, k) => ({ id, w: buyW[2].model.w[k + 1] * IND.find((d) => d.id === id).dir })) : null;
    const feats = ids.map((id) => ({ id, v: S.v[id][smp[nowJ]] }));
    return {
      date: S.dates[asOf], asOf, price: S.price[asOf], ids, from,
      buy: { score: bNow.score, zone: zoneOf(BUY_Z, bNow.score), ev: buyEvidence(buyS, from), series: buyS, fit: fitOf(buyW) },
      sell: { score: sNow.score, zone: zoneOf(SELL_Z, sNow.score), ev: sellEvidence(sellS, from), series: sellS, fit: fitOf(sellW) },
      hold, weights, feats,
    };
  }

  // ---- giá đề xuất mua, bán: giá BTC tại ngày phân tích để bot chuyển khung
  // tỷ lệ nên mua, nên bán nếu giá ngày phân tích là X: tính lại chỉ số trên chuỗi cắt tại ngày đó (không thấy dữ liệu sau),
  // giữ nguyên mô hình đã học và các yếu tố không phụ thuộc giá (Fear & Greed, khối lượng); vốn hóa, MVRV, Puell đổi theo giá
  function scoreAtPrice(S, asOf, a, X) {
    const n = asOf + 1, k = X / S.price[asOf], cut = (arr) => arr.slice(0, n);
    const T = { dates: cut(S.dates), price: cut(S.price), mc: cut(S.mc), mv: cut(S.mv), iss: cut(S.iss), fng: cut(S.fng), qv: cut(S.qv), has: S.has };
    T.price[asOf] = X;
    for (const key of ['mc', 'mv', 'iss']) if (T[key][asOf] != null) T[key][asOf] *= k;
    computeRaw(T);
    if (S.iss[asOf] == null && T.v.puell[asOf] != null) T.v.puell[asOf] *= k; // Puell hôm nay mượn từ hôm trước: cho đổi theo giá
    const f = a.ids.map((id) => featAt(T, id, asOf));
    if (f.some((x) => x == null)) return null;
    const sc = (fits) => fits.reduce((s, m) => s + rankIn(m.ref, predLogit(m.model, f) - m.p0), 0) / fits.length;
    return { buy: sc(a.buy.fit), sell: sc(a.sell.fit) };
  }
  // các ngưỡng khung xếp theo giá từ cao xuống thấp: Nên bán, Cân nhắc bán, Cân nhắc mua, Phải mua
  const LV = [...SELL_Z.filter((z) => z.min > 0).map((z) => ({ id: z.id, ten: z.ten, kind: 'sell', thr: z.min })),
    ...BUY_Z.filter((z) => z.min > 0).reverse().map((z) => ({ id: z.id, ten: z.ten, kind: 'buy', thr: z.min }))];
  const LV_STEP = 1.01, LV_LO = 0.25, LV_HI = 4, LV_LADDER = [0.7, 0.8, 0.9, 0.95, 1, 1.05, 1.1, 1.2, 1.3, 1.5];
  // lời giải thích khi mốc giá ít ý nghĩa
  function levelNotes(lv) {
    const out = [];
    if (lv.phang) out.push(tx('web.analysis.voi_bo_chi_so_nay_ty'));
    if (lv.nguocMua) out.push(tx('web.analysis.mo_hinh_cua_bo_chi_so'));
    if (lv.nguocBan) out.push(tx('web.analysis.mo_hinh_cua_bo_chi_so_2'));
    return out;
  }
  // dò từ giá p mỗi bước 1% rồi chia đôi, tìm mốc mà tại đó điều kiện ok(X) đổi so với hôm nay;
  // giá giảm làm tỷ lệ nên mua tăng, giá tăng làm tỷ lệ nên bán tăng; đang đạt thì dò ngược lại để tìm chỗ hết đạt
  function findLevel(p, kind, ok) {
    const dat = ok(p), go = (kind === 'buy' ? -1 : 1) * (dat ? -1 : 1);
    let a0 = p, b0 = null;
    for (let s = 1; ; s++) { const X = p * LV_STEP ** (go * s); if (X < p * LV_LO || X > p * LV_HI) break; if (ok(X) !== dat) { b0 = X; break; } a0 = X; }
    if (b0 == null) return { dat, gia: null };
    for (let it = 0; it < 12; it++) { const m = Math.sqrt(a0 * b0); if (ok(m) === dat) a0 = m; else b0 = m; }
    return { dat, gia: dat ? a0 : b0 };
  }
  function priceLevels(S, asOf, a) {
    const p = S.price[asOf], memo = new Map();
    const at = (X) => { if (!memo.has(X)) memo.set(X, scoreAtPrice(S, asOf, a, X)); return memo.get(X); };
    const levels = LV.map((L) => ({ ...L, ...findLevel(p, L.kind, (X) => { const s = at(X); return s != null && s[L.kind] >= L.thr; }) }));
    // bảng "nếu giá là X": cho thấy tỷ lệ đổi theo giá thế nào, kể cả khi mô hình chạy ngược hoặc gần như không đổi
    const ladder = LV_LADDER.map((f) => { const s = at(p * f); return { f, gia: p * f, buy: s ? s.buy : null, sell: s ? s.sell : null }; });
    const now = ladder.find((r) => r.f === 1), dn = ladder.find((r) => r.f === 0.8), up = ladder.find((r) => r.f === 1.2);
    const phang = ladder.every((r) => r.buy != null && Math.abs(r.buy - now.buy) < 3 && Math.abs(r.sell - now.sell) < 3);
    return { date: S.dates[asOf], price: p, lo: p * LV_LO, hi: p * LV_HI, levels, ladder, phang,
      nguocMua: !phang && dn.buy != null && dn.buy < now.buy - 1, nguocBan: !phang && up.sell != null && up.sell < now.sell - 1 };
  }
  const usdT = (x) => Math.round(x).toLocaleString('vi-VN') + ' $';
  function levelText(lv, L) {
    if (L.gia != null) return tx('web.analysis.khi_gia_0_1', L.kind === 'buy' ? '≤' : '≥', usdT(L.gia));
    if (!L.dat) return L.kind === 'buy' ? tx('web.analysis.chua_dat_du_gia_giam_toi', usdT(lv.lo)) : tx('web.analysis.chua_dat_du_gia_tang_toi', usdT(lv.hi));
    return L.kind === 'buy' ? tx('web.analysis.o_moi_muc_gia_den_0', usdT(lv.hi)) : tx('web.analysis.o_moi_muc_gia_tu_0', usdT(lv.lo));
  }

  const vnTime = typeof I18N !== 'undefined' ? I18N.vnTime : require('./i18n.js').vnTime;
  // ⚠ for an indicator set with fewer than 10 independent episodes or two halves more than 20 points apart (6 months)
  const warnMd = (eps, h1, h2) => (eps < 10 || (h1 && h2 && h1.n && h2.n && Math.abs(h1.win - h2.win) > 0.2) ? tx('web.kn.warn_mark') : '');
  const P = (x, d = 0) => (x == null || !isFinite(x) ? '—' : (x * 100).toFixed(d).replace('.', ',') + '%');
  const SP = (x) => (x == null || !isFinite(x) ? '—' : (x > 0 ? '+' : '') + (x * 100).toFixed(0) + '%');
  const D = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`;
  const nm = (id) => IND.find((d) => d.id === id).ten;
  function report(S, a, rec, vol, sources, isToday, cmp, sd, lv, kn) {
    const L = [], t = (x) => L.push(x);
    t(tx('web.analysis.bao_cao_bot_btc_phan_tich', D(a.date))); t('');
    t(tx('web.analysis.bot_thong_ke_khong_co_tri')); t('');
    t(tx('web.analysis.boi_canh'));
    t(tx('web.analysis.gia_btc_tai_ngay_phan_tich', Math.round(a.price).toLocaleString('vi-VN')) + (isToday ? tx('web.analysis.gia_truc_tiep') : tx('web.analysis.ngay_trong_qua_khu')));
    t(tx('web.analysis.nguon_0', sources)); t(tx('web.analysis.bo_chi_so_0', a.ids.map(nm).join(', '))); t(tx('web.analysis.giai_doan_cham_diem_tu_0', D(a.from), D(a.date))); t('');
    t(tx('web.analysis.ket_luan'));
    t(tx('web.analysis.ty_le_nen_mua_0_khung', a.buy.score.toFixed(0), a.buy.zone.ten, a.buy.score.toFixed(0)));
    t(tx('web.analysis.ty_le_nen_ban_0_khung', a.sell.score.toFixed(0), a.sell.zone.ten, a.sell.score.toFixed(0))); t('');
    if (kn) {
      const stale = (Date.now() - Date.parse(kn.generated_at)) / 86400000 > kn.stale_data_days, m = stale ? 1 : kn.multiplier, ev = kn.evidence;
      const d3 = (x) => (x == null ? '—' : x.toFixed(3).replace('.', ','));
      t(tx('web.kn.md_title'));
      t(tx('web.kn.md_m', m.toFixed(1).replace('.', ','), stale || kn.mode === 'safe' ? tx('web.kn.mode_safe') : tx('web.kn.mode_model', tx('web.kn.layer_' + kn.layer)),
        usdT(kn.amount_example_usd * m), usdT(kn.amount_example_usd)));
      if (stale || kn.reasons.includes('data_stale')) t(tx('web.kn.md_why', tx('web.kn.reason_data_stale')));
      const rb = kn.rebuild && kn.rebuild.acceptance ? kn.rebuild : null;
      if (rb) {
        const A = rb.acceptance, W = rb.week, zn = (z) => (z ? tx('web.rb.zone_' + z) : '—'), r0 = (x) => (x == null ? '—' : Math.round(x).toString());
        if (kn.reasons.includes('model_failed')) t(tx('web.kn.md_why', tx('web.kn.why_rb', Object.values(A.criteria).filter((c) => c.pass).length, D(A.holdout_start), D(A.last_week), A.holdout_weeks, D(A.run_at.slice(0, 10)))));
        t(tx('web.kn.md_rb_week', D(W.date), r0(W.rank), zn(W.zone), r0(W.rank_mvrv), zn(W.zone_mvrv), r0(W.rank_200w), zn(W.zone_200w)));
      } else {
        if (kn.reasons.includes('model_failed')) t(tx('web.kn.md_why', tx('web.kn.reason_model_failed')));
        if (ev) { const c = ev.candidate.holdout, b = ev.current_bot.holdout; t(tx('web.kn.md_cmp', d3(c.median), d3(c.p10), d3(b.median), d3(b.p10), P(b.cba, 1), P(b.mdd), P(b.mdd_dca))); }
      }
      t(tx('web.kn.md_events', kn.events.length ? kn.events.map((e) => (e.flag ? '⚑ ' : '') + tx('web.kn.event_line', vnTime(e.time), tx('web.kn.ev_' + e.type))).join('; ') : tx('web.kn.events_none')));
      t(tx('web.kn.md_fresh', vnTime(kn.generated_at))); t('');
    }
    if (lv) {
      t(tx('web.analysis.gia_de_xuat_mua_va_ban', D(lv.date), usdT(lv.price)));
      t(tx('web.analysis.gia_btc_de_bot_chuyen_khung'));
      t(tx('web.analysis.khuyen_cao_dieu_kien_gia_cach')); t('|---|---|---|---|');
      lv.levels.forEach((L) => t(`| ${L.ten} | ${levelText(lv, L)} | ${L.gia != null ? SP(L.gia / lv.price - 1) : '—'} | ${L.dat ? tx('web.analysis.dang_dat') : tx('web.analysis.chua_dat')} |`));
      levelNotes(lv).forEach((s) => t(`- ${s}`));
      t(tx('web.analysis.neu_gia_ngay_phan_tich_la') + lv.ladder.map((r) => tx('web.analysis.s_0_1_nen_mua_2_nen', usdT(r.gia), r.f === 1 ? tx('web.analysis.hien_tai') : SP(r.f - 1), r.buy == null ? '—' : r.buy.toFixed(0) + '%', r.sell == null ? '—' : r.sell.toFixed(0) + '%')).join('; ') + '.');
      t('');
    }
    t(tx('web.analysis.xac_suat_thang_neu_mua_tai'));
    t(tx('web.analysis.giu_xac_suat_thang_khoang_tin') + (isToday ? '' : tx('web.analysis.thuc_te_sau_do')));
    t('|---|---|---|---|---|---|---|' + (isToday ? '' : '---|'));
    a.hold.forEach((h) => t(tx('web.analysis.s_0_1_2_3_4_5', h.ten, P(h.win), P(h.lo), P(h.hi), P(h.base), SP(h.med), SP(h.q1), SP(h.q3), h.n, h.eps) + (isToday ? '' : ` ${h.thucTe == null ? tx('web.analysis.chua_du_thoi_gian') : SP(h.thucTe)} |`)));
    t('');
    t(tx('web.analysis.bo_tieu_chi_ty_le_thang') + D(a.from) + ')');
    t(tx('web.analysis.khung_so_tuan') + HZ.map((h) => tx('web.analysis.thang_sau') + h.ten).join(' | ') + ' |'); t('|---|---|' + HZ.map(() => '---').join('|') + '|');
    [{ ten: tx('web.analysis.mua_bat_ky_luc_nao_moc'), ...a.buy.ev.base }, ...a.buy.ev.zones].forEach((z) => t(tx('web.analysis.s_0_1_2_dot', z.ten, z.n, z.eps) + z.h.map((x) => `${P(x.win)} (${x.n})`).join(' | ') + ' |'));
    t('');
    t(tx('web.analysis.khung_ban_gia_co_giam_that'));
    t(tx('web.analysis.khung_so_tuan') + SELL_HZ.map((h) => tx('web.analysis.gia_thap_hon_sau_0_giam', h.ten, h.ten)).join(' | ') + ' |'); t('|---|---|' + SELL_HZ.map(() => '---|---').join('|') + '|');
    [{ ten: tx('web.analysis.bat_ky_luc_nao_moc'), ...a.sell.ev.base }, ...a.sell.ev.zones].forEach((z) => t(`| ${z.ten} | ${z.n} | ` + z.h.map((x) => `${P(x.giam.win)} | ${P(x.giamManh.win)}`).join(' | ') + ' |'));
    t('');
    if (cmp && cmp.ranked.length) {
      const dt = cmp.dongThuan;
      t(tx('web.analysis.so_sanh_cac_phuong_an_cham', D(cmp.from)));
      t(tx('web.analysis.dong_thuan_hom_nay_0_trung', dt.mua.filter((z) => z.n).map((z) => `${z.n}/${dt.tong} ${z.ten.toLowerCase()}`).join(', '), dt.tbMua.toFixed(0), dt.tbBan.toFixed(0)));
      t(tx('web.analysis.hang_phuong_an_chi_so_nen')); t('|---|---|---|---|---|---|---|---|');
      cmp.ranked.forEach((x) => t(`| ${x.hang || '—'} | ${warnMd((x.xepTheo === 'rong' ? x.rong : x.evB.zones[0]).eps, x.nua1, x.nua2)}${x.ten} | ${x.ids.map(nm).join(', ')} | ${x.a.buy.score.toFixed(0)}% ${x.a.buy.zone.ten} | ${x.a.sell.score.toFixed(0)}% ${x.a.sell.zone.ten} | ${x.evB.zones[0].h.map((h) => P(h.win)).join(' / ')} | ${P(x.nua1.win)} / ${P(x.nua2.win)} | ${x.banDung ? P(x.banDung.win) + tx('web.analysis.moc') + P(x.banMoc) + ')' : tx('web.analysis.it_tin_hieu')} |`));
      t('');
    }
    if (rec) {
      t(tx('web.analysis.bo_chi_so_co_ty_le', D(rec.asOfDate), D(rec.from)));
      t(tx('web.analysis.bo_thang_1_thang_thang_3')); t('|---|---|---|---|---|---|---|');
      rec.ranking.slice(0, 8).forEach((r) => t(`| ${warnMd(r.phai.eps, r.nua1[2], r.nua2[2])}${r.ten}: ${r.ids.map(nm).join(', ')} | ` + r.phai.h.map((x) => P(x.win)).join(' | ') + ` | ${P(r.nua1[2].win)} | ${P(r.nua2[2].win)} |`));
      t('');
    }
    if (sd) {
      t(tx('web.analysis.ben_ban_nen_giu_hay_chot', D(sd.date)));
      t(tx('web.analysis.ket_luan_0_1', sd.verdict.ten, sd.verdict.goiY));
      t(tx('web.analysis.so_nhom_tieu_chi_dang_tin', sd.nFam, sd.famNow.length ? ' (' + sd.famNow.map((f) => NHOM_TP[f]).join(', ') + ')' : ''));
      t(tx('web.analysis.moc_ban_vao_mot_tuan_bat', P(sd.baseDung6), P(sd.baseDung12)));
      t('');
      t(tx('web.analysis.tieu_chi_dang_tin_hom_nay')); t('|---|---|---|---|---|---|---|---|---|---|');
      sd.ranked.forEach((c) => t(`| ${c.ten} | ${c.dangTin ? tx('web.analysis.co') : ''} | ${c.nowOn ? tx('web.analysis.dang_bat') : tx('web.analysis.chua')} | ${c.dot} | ${P(c.dung6)} (${c.n6}) | ${P(c.lo6)}–${P(c.hi6)} | ${P(c.dung12)} (${c.n12}) | ${SP(c.up)} | ${SP(c.dn)} | ${c.trigger && c.trigger.gia ? Math.round(c.trigger.gia).toLocaleString('vi-VN') + ' $' : '—'} |`));
      t('');
      if (sd.sims.length) { t(tx('web.analysis.mo_phong_giu_1_btc_va')); t(tx('web.analysis.bat_dau_giu_nguyen_theo_quy')); t('|---|---|---|---|---|---|');
        sd.sims.forEach((x) => t(`| ${D(x.tu)} | ${Math.round(x.giuGT).toLocaleString('vi-VN')} $ | ${Math.round(x.tcGT).toLocaleString('vi-VN')} $ | ${x.tcBTC.toFixed(3).replace('.', ',')} | ${x.ban}/${x.mua} | ${SP(x.mddH)} / ${SP(x.mdd)} |`)); t(''); }
    }
    t(tx('web.analysis.gia_tri_chi_so_tai_ngay'));
    a.feats.forEach((f) => { const d = IND.find((x) => x.id === f.id); t(`- ${d.ten}: ${f.v == null ? '—' : (+f.v).toFixed(d.dec).replace('.', ',') + (d.unit || '')}`); });
    if (a.weights) t(tx('web.analysis.trong_so_trong_mo_hinh_6') + a.weights.map((w) => `${nm(w.id)} ${w.w >= 0 ? '+' : ''}${w.w.toFixed(2).replace('.', ',')}`).join('; '));
    t('');
    if (vol && vol.last) { t(tx('web.analysis.khoi_luong_giao_dich')); t(tx('web.analysis.tuan_gan_nhat_da_dong_0', D(vol.last.date), SP(vol.last.chg), vol.last.rv.toFixed(2).replace('.', ','), BOT.VCLS[vol.last.cls].ten)); t(''); }
    t(tx('web.analysis.cau_hoi_goi_y_cho_claude'));
    t(tx('web.analysis.ket_luan_cua_bot_co_dang'));
    t(tx('web.analysis.boi_canh_vi_mo_va_tin'));
    t(tx('web.analysis.nen_chia_tien_mua_the_nao'));
    return L.join('\n');
  }

  // chạy tất cả phương án tại một ngày và xếp hạng trên cùng một giai đoạn
  async function compareOptions(S, asOf, recIds, tick) {
    const list = [];
    for (const o of OPTIONS) {
      const ids = (o.id === 'pa6' ? recIds || [] : o.ids).filter((id) => S.avail.includes(id));
      const thieu = (o.id === 'pa6' ? [] : o.ids).filter((id) => !S.avail.includes(id));
      const item = { ...o, ids, thieu, a: null, loi: null };
      if (!ids.length) item.loi = o.id === 'pa6' ? tx('web.analysis.chua_tim_duoc_bo_khuyen_cao') : tx('web.analysis.thieu_du_lieu_cho_cac_chi');
      else { try { item.a = analyze(S, asOf, ids); } catch (e) { item.loi = e.message; } }
      list.push(item);
      if (tick) await tick();
    }
    const okList = list.filter((x) => x.a);
    if (!okList.length) return { list, from: null, ranked: [] };
    let from = okList.map((x) => x.a.from).sort().pop(); if (from < '2021-01-01') from = '2021-01-01';
    for (const x of okList) {
      const bs = x.a.buy.series.filter((p) => p.date >= from), ss = x.a.sell.series.filter((p) => p.date >= from);
      x.evB = buyEvidence(bs, from); x.evS = sellEvidence(ss, from);
      x.obj = objective(bs, from).score;
      // phương án ít tín hiệu Phải mua: xếp theo khung từ Cân nhắc mua trở lên
      const wide = buyEvidence(bs.map((p) => ({ ...p, score: p.score >= 60 ? 100 : 0 })), from).zones[0];
      const lbs = wide.n >= 20 && wide.eps >= 2 ? wide.h.map((h) => (h.n >= 10 ? h.lo : null)).filter((v) => v != null) : [];
      x.obj2 = lbs.length ? lbs.reduce((a, b) => a + b, 0) / lbs.length : -Infinity;
      x.rong = wide;
      const mid = bs.length ? bs[Math.floor(bs.length / 2)].date : from;
      x.nua1 = buyEvidence(bs.filter((p) => p.date < mid), from).zones[0].h[2];
      x.nua2 = buyEvidence(bs.filter((p) => p.date >= mid), mid).zones[0].h[2];
      const nb = x.evS.zones[0];
      x.banDung = nb.n >= 10 ? nb.h[1].giam : null;
      x.banMoc = x.evS.base.h[1].giam.win;
      const same = list.find((y) => y !== x && y.id < x.id && y.a && [...y.ids].sort().join() === [...x.ids].sort().join());
      x.trung = same ? same.ten : null;
    }
    const key = (x) => (isFinite(x.obj) ? [2, x.obj] : isFinite(x.obj2) ? [1, x.obj2] : [0, 0]);
    const ranked = okList.filter((x) => !x.trung).sort((p, q) => { const a = key(p), b = key(q); return b[0] - a[0] || b[1] - a[1]; });
    ranked.forEach((x, k) => { x.hang = key(x)[0] ? k + 1 : null; x.xepTheo = key(x)[0] === 2 ? 'phai' : key(x)[0] === 1 ? 'rong' : null; });
    const cnt = (Z, key) => Z.map((z) => ({ ...z, n: okList.filter((x) => !x.trung && x.a[key].zone.id === z.id).length }));
    const uniq = okList.filter((x) => !x.trung);
    return { list, from, ranked, dongThuan: { mua: cnt(BUY_Z, 'buy'), ban: cnt(SELL_Z, 'sell'), tbMua: uniq.reduce((a, x) => a + x.a.buy.score, 0) / uniq.length, tbBan: uniq.reduce((a, x) => a + x.a.sell.score, 0) / uniq.length, tong: uniq.length } };
  }

  // ---- xuất dữ liệu cho Claude hoặc Excel (UTF-8 có BOM, dấu phẩy ngăn cột, dấu chấm thập phân)
  const cell = (v) => (v == null ? '' : typeof v === 'number' ? (isFinite(v) ? String(Math.round(v * 1e6) / 1e6) : '') : /[",\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v));
  const csv = (head, rows) => '\ufeff' + [head, ...rows].map((r) => r.map(cell).join(',')).join('\n');
  function csvWeekly(S, a) {
    const sell = new Map(a.sell.series.map((x) => [x.j, x]));
    const head = ['ngay', 'gia_usd', 'ty_le_nen_mua_pct', 'khung_mua', 'ty_le_nen_ban_pct', 'khung_ban', ...a.ids.map((id) => id + '_' + nm(id)),
      'thuc_te_sau_1_thang', 'thuc_te_sau_3_thang', 'thuc_te_sau_6_thang', 'thuc_te_sau_1_nam'];
    const rows = a.buy.series.map((x) => { const sv = sell.get(x.j);
      return [x.date, S.price[x.i], x.score, zoneOf(BUY_Z, x.score).ten, sv ? sv.score : null, sv ? zoneOf(SELL_Z, sv.score).ten : null,
        ...a.ids.map((id) => S.v[id][x.i]), ...HZ.map((h) => (x.i + h.days < S.price.length ? S.price[x.i + h.days] / S.price[x.i] - 1 : null))]; });
    return csv(head, rows);
  }
  function csvOptions(cmp) {
    const head = ['hang', 'phuong_an', 'chi_so', 'ghi_chu', 'nen_mua_hom_nay_pct', 'khung_mua', 'nen_ban_hom_nay_pct', 'khung_ban',
      ...HZ.map((h) => 'phai_mua_thang_' + h.id), 'phai_mua_so_lan', 'phai_mua_so_dot', ...HZ.map((h) => 'moc_thang_' + h.id),
      'nua_dau_thang_6m', 'nua_sau_thang_6m', 'nen_ban_gia_thap_hon_6m', 'moc_gia_thap_hon_6m', 'cham_tu'];
    const rows = cmp.list.map((x) => { const z = x.evB && x.evB.zones[0];
      return [x.hang, x.ten, x.ids.map(nm).join(' + '), x.loi || (x.trung ? tx('web.analysis.trung') + x.trung : x.xepTheo === 'rong' ? tx('web.analysis.it_tin_hieu_phai_mua_xep') : ''),
        x.a && x.a.buy.score, x.a && x.a.buy.zone.ten, x.a && x.a.sell.score, x.a && x.a.sell.zone.ten,
        ...HZ.map((h, k) => z && z.h[k].win), z && z.n, z && z.eps, ...HZ.map((h, k) => x.evB && x.evB.base.h[k].win),
        x.nua1 && x.nua1.win, x.nua2 && x.nua2.win, x.banDung && x.banDung.win, x.banMoc, cmp.from]; });
    return csv(head, rows);
  }

  // ================================================================ BÊN BÁN: chốt lời hay giữ
  // nhom: để đếm số nhóm cùng báo, không đếm trùng hai chỉ số đo cùng một thứ
  const TP = [
    { id: 'pi_cat', ind: 'pi', nhom: 'xuhuong', ten: tx('web.analysis.pi_cycle_cat_len_ti_so'), loai: 'kinh_dien', thr: 1.0 },
    { id: 'mvrvz_7', ind: 'mvrvz', nhom: 'onchain', ten: 'MVRV Z-Score ≥ 7', loai: 'kinh_dien', thr: 7 },
    { id: 'mvrv_3', ind: 'mvrv', nhom: 'onchain', ten: 'MVRV ≥ 3', loai: 'kinh_dien', thr: 3 },
    { id: 'mayer_24', ind: 'mayer', nhom: 'xuhuong', ten: 'Mayer Multiple ≥ 2,4', loai: 'kinh_dien', thr: 2.4 },
    { id: 'rsiw_80', ind: 'rsiw', nhom: 'xuhuong', ten: tx('web.analysis.rsi_14_tuan_80'), loai: 'kinh_dien', thr: 80 },
    { id: 'fng_90', ind: 'fng', nhom: 'tamly', ten: 'Fear & Greed ≥ 90', loai: 'kinh_dien', thr: 90 },
    { id: 'puell_4', ind: 'puell', nhom: 'thodao', ten: 'Puell Multiple ≥ 4', loai: 'kinh_dien', thr: 4 },
    { id: 'mvrvz_p', ind: 'mvrvz', nhom: 'onchain', ten: tx('web.analysis.mvrv_z_score_thuoc_5_cao'), loai: 'thich_nghi' },
    { id: 'mvrv_p', ind: 'mvrv', nhom: 'onchain', ten: tx('web.analysis.mvrv_thuoc_5_cao_nhat_4'), loai: 'thich_nghi' },
    { id: 'mayer_p', ind: 'mayer', nhom: 'xuhuong', ten: tx('web.analysis.mayer_multiple_thuoc_5_cao_nhat'), loai: 'thich_nghi' },
    { id: 'wma_p', ind: 'wma', nhom: 'xuhuong', ten: tx('web.analysis.gia_ma_200_tuan_thuoc_5'), loai: 'thich_nghi' },
    { id: 'puell_p', ind: 'puell', nhom: 'thodao', ten: tx('web.analysis.puell_multiple_thuoc_5_cao_nhat'), loai: 'thich_nghi' },
    { id: 'bot_nb', ind: null, nhom: 'mohinh', ten: tx('web.analysis.bot_bao_nen_ban_ty_le'), loai: 'mo_hinh' },
  ];
  const NHOM_TP = { xuhuong: tx('web.analysis.xu_huong_gia'), onchain: tx('web.analysis.dinh_gia_on_chain'), tamly: tx('web.analysis.tam_ly'), thodao: tx('web.analysis.tho_dao'), mohinh: tx('web.analysis.mo_hinh_cua_bot') };
  const SELL_VERDICT = [
    { id: 'ban', ten: tx('web.analysis.ban_phan_lon'), min: 3, goiY: tx('web.analysis.chot_khoang_50_luong_dang_giu') },
    { id: 'chot', ten: tx('web.analysis.chot_loi_mot_phan'), min: 1, goiY: tx('web.analysis.chot_khoang_10_30_de_khoa') },
    { id: 'giu', ten: tx('web.analysis.giu'), min: 0, goiY: tx('web.analysis.chua_co_tieu_chi_chot_loi') },
  ];
  const tpOn = (S, c, i, sellScoreAt) => {
    if (c.loai === 'mo_hinh') { const s = sellScoreAt(i); return s == null ? null : s >= 85; }
    if (!S.avail.includes(c.ind)) return null;
    if (c.loai === 'kinh_dien') { const v = S.v[c.ind][i]; return v == null ? null : v >= c.thr; }
    const f = featAt(S, c.ind, i); return f == null ? null : f >= 0.95;
  };
  // giá BTC cần đạt để tiêu chí bật (với chỉ số tăng theo giá)
  function triggerPrice(S, c, i) {
    const p = S.price[i], v = c.ind ? S.v[c.ind][i] : null; if (v == null || (c.ind !== 'mvrvz' && !(v > 0))) return null;
    let thr = c.thr;
    if (c.loai === 'thich_nghi') { const w = []; for (let j = Math.max(0, i - 1460); j <= i; j++) { const x = S.v[c.ind][j]; if (x != null) w.push(x); } if (w.length < 365) return null; w.sort((a, b) => a - b); thr = w[Math.floor(0.95 * (w.length - 1))]; }
    if (['mvrv', 'mayer', 'wma', 'puell'].includes(c.ind)) return { gia: p * thr / v, thr };
    if (c.ind === 'mvrvz' && S.mc[i] && S.mv[i] && S.zsd && S.zsd[i]) { const mc = S.mc[i], rc = mc / S.mv[i]; return { gia: p * (rc + thr * S.zsd[i]) / mc, thr }; }
    return { gia: null, thr };
  }

  function sellSide(S, asOf, a) {
    const smp = weekly(S, asOf), sellMap = new Map(a.sell.series.map((x) => [x.i, x.score]));
    const sellScoreAt = (i) => (sellMap.has(i) ? sellMap.get(i) : null);
    const fwd = (i, days) => (i + days <= asOf ? S.price[i + days] / S.price[i] - 1 : null);
    const maxUp = (i, days) => { if (i + days > asOf) return null; let m = S.price[i]; for (let k = i; k <= i + days; k++) m = Math.max(m, S.price[k]); return m / S.price[i] - 1; };
    const maxDn = (i, days) => { if (i + days > asOf) return null; let m = S.price[i]; for (let k = i; k <= i + days; k++) m = Math.min(m, S.price[k]); return m / S.price[i] - 1; };
    const on = TP.map((c) => smp.map((i) => tpOn(S, c, i, sellScoreAt)));
    // đánh giá từng tiêu chí theo từng đợt bật (tuần đầu tiên của mỗi đợt, các tuần cách nhau tối đa 8 tuần gộp một đợt)
    const evalSignal = (flags) => {
      const starts = []; let last = -99, weeksOn = 0;
      flags.forEach((f, j) => { if (f) { weeksOn++; if (j - last > 8) starts.push(j); last = j; } });
      const ev = starts.map((j) => { const i = smp[j]; return { date: S.dates[i], i, r6: fwd(i, 182), r12: fwd(i, 365), up: maxUp(i, 182), dn: maxDn(i, 365) }; });
      const done6 = ev.filter((e) => e.r6 != null), k6 = done6.filter((e) => e.r6 < 0).length, [lo6, hi6] = wilson(k6, done6.length);
      const done12 = ev.filter((e) => e.r12 != null), k12 = done12.filter((e) => e.r12 < 0).length, [lo12, hi12] = wilson(k12, done12.length);
      return { dot: ev.length, tuan: weeksOn, ev, n6: done6.length, dung6: done6.length ? k6 / done6.length : null, lo6, hi6, n12: done12.length, dung12: done12.length ? k12 / done12.length : null, lo12, hi12,
        med6: median(done6.map((e) => e.r6)), up: median(ev.filter((e) => e.up != null).map((e) => e.up)), dn: median(ev.filter((e) => e.dn != null).map((e) => e.dn)) };
    };
    // mốc so sánh: giá thấp hơn sau 6 tháng nếu bán vào một tuần bất kỳ
    const all6 = smp.map((i) => fwd(i, 182)).filter((x) => x != null), baseDung6 = all6.length ? all6.filter((x) => x < 0).length / all6.length : null;
    const all12 = smp.map((i) => fwd(i, 365)).filter((x) => x != null), baseDung12 = all12.length ? all12.filter((x) => x < 0).length / all12.length : null;
    const crit = TP.map((c, k) => {
      const flags = on[k], st = evalSignal(flags), nowOn = flags[flags.length - 1];
      const tg = c.ind ? triggerPrice(S, c, asOf) : null;
      return { ...c, ...st, coDuLieu: flags.some((f) => f != null), nowOn, nowVal: c.ind ? S.v[c.ind][asOf] : sellScoreAt(asOf), trigger: tg,
        dangTin: st.n6 >= 3 && st.lo6 != null && st.lo6 > baseDung6 };
    });
    // tiêu chí kết hợp: số nhóm cùng bật (chỉ tính tiêu chí đáng tin)
    const trusted = crit.filter((c) => c.dangTin);
    const famAt = (j) => { const f = new Set(); trusted.forEach((c) => { const k = TP.findIndex((t) => t.id === c.id); if (on[k][j]) f.add(c.nhom); }); return f; };
    const famCount = smp.map((_, j) => famAt(j).size);
    const combos = [1, 2, 3].map((m) => ({ id: 'combo' + m, ten: tx('web.analysis.tu_0_nhom_tieu_chi_dang', m), loai: 'ket_hop', nhom: null, m, ...evalSignal(famCount.map((n) => n >= m)), nowOn: famCount[famCount.length - 1] >= m, coDuLieu: trusted.length > 0 }));
    const ranked = [...crit, ...combos].filter((c) => c.coDuLieu && c.n6 >= 3).sort((x, y) => (y.lo6 ?? -1) - (x.lo6 ?? -1));
    const famNow = famAt(smp.length - 1), nFam = famNow.size;
    const verdict = SELL_VERDICT.find((v) => nFam >= v.min);
    // mô phỏng: giữ 1 BTC; khi các nhóm đáng tin bật thì bán bớt về tỷ trọng mục tiêu; mua lại khi bên mua báo từ Cân nhắc mua
    const buyMap = new Map(a.buy.series.map((x) => [x.i, x.score]));
    const simFrom = (startDate) => {
      const js = smp.map((i, j) => j).filter((j) => S.dates[smp[j]] >= startDate && buyMap.has(smp[j]) && j < smp.length - 1);
      if (js.length < 52) return null;
      const p0 = S.price[smp[js[0]]]; let btc = 1, cash = 0, ban = 0, mua = 0, peak = p0, mdd = 0, peakH = p0, mddH = 0;
      for (const j of js) {
        const i = smp[j], px = S.price[i], target = famCount[j] >= 3 ? 0.5 : famCount[j] === 2 ? 0.7 : famCount[j] === 1 ? 0.9 : null;
        const val = btc * px + cash, expo = (btc * px) / val;
        if (target != null && expo > target + 0.01) { const sellBtc = (expo - target) * val / px; btc -= sellBtc; cash += sellBtc * px; ban++; }
        else if (target == null && cash > 0 && (buyMap.get(i) ?? 0) >= 60) { btc += cash / px; cash = 0; mua++; }
        const v2 = btc * px + cash; peak = Math.max(peak, v2); mdd = Math.min(mdd, v2 / peak - 1); peakH = Math.max(peakH, px); mddH = Math.min(mddH, px / peakH - 1);
      }
      const pe = S.price[smp[js[js.length - 1]]], val = btc * pe + cash;
      return { tu: S.dates[smp[js[0]]], den: S.dates[smp[js[js.length - 1]]], giuGT: pe, giuBTC: 1, tcGT: val, tcBTC: val / pe, ban, mua, mdd, mddH, tienMat: cash };
    };
    const simStarts = ['2014-01-01', '2018-01-01', '2021-01-01'].map(simFrom).filter(Boolean);
    const seen = new Set(), sims = simStarts.filter((x) => (seen.has(x.tu) ? false : seen.add(x.tu)));
    return { date: S.dates[asOf], price: S.price[asOf], crit, combos, ranked, trusted: trusted.map((c) => c.id), baseDung6, baseDung12, famNow: [...famNow], nFam, verdict,
      series: smp.map((i, j) => ({ i, date: S.dates[i], n: famCount[j], on: TP.map((c, k) => on[k][j]) })), sims };
  }

  function csvSell(sd) {
    const head = ['tieu_chi', 'loai', 'nhom', 'dang_tin', 'hom_nay_bat', 'gia_tri_hom_nay', 'gia_kich_hoat_usd', 'so_dot', 'so_tuan_bat',
      'gia_thap_hon_sau_6t', 'can_duoi_6t', 'so_dot_du_6t', 'gia_thap_hon_sau_1n', 'so_dot_du_1n', 'moc_gia_thap_hon_6t', 'lai_trung_vi_6t_sau_tin_hieu', 'con_tang_them_toi_da_trung_vi', 'giam_sau_nhat_1n_trung_vi', 'cac_dot'];
    const rows = [...sd.crit, ...sd.combos].map((c) => [c.ten, c.loai, c.nhom ? NHOM_TP[c.nhom] : tx('web.analysis.ket_hop'), c.dangTin ? tx('web.analysis.co') : '', c.nowOn ? tx('web.analysis.co') : c.nowOn === false ? tx('web.analysis.khong') : '', c.nowVal, c.trigger && c.trigger.gia,
      c.dot, c.tuan, c.dung6, c.lo6, c.n6, c.dung12, c.n12, sd.baseDung6, c.med6, c.up, c.dn, (c.ev || []).map((e) => e.date).join(' ')]);
    return csv(head, rows);
  }

  // research access for the rebuild (bot/report/measure_b.py): walk-forward predictions per horizon
  const walkPreds = (S, asOf, ids) => { const smp = weekly(S, asOf), R = featRows(S, smp, ids); return HZ.map((h) => ({ h: h.w, preds: walk(S, smp, R, h.w, (r) => (r > 0 ? 1 : 0), 4).preds.map((x) => [x.date, x.p, x.p0]) })); };
  return { HZ, SELL_HZ, BUY_Z, SELL_Z, PRESETS, OPTIONS, TP, NHOM_TP, SELL_VERDICT, LV, zoneOf, analyze, search, report, walkPreds, compareOptions, csvWeekly, csvOptions, sellSide, csvSell, scoreAtPrice, findLevel, priceLevels, levelText, levelNotes };
})();
// ===== B3 END =====
if (typeof module !== 'undefined') module.exports = B3;
