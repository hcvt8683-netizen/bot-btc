// ===== B3 START =====
const B3 = (() => {
  const { IND, FAMILIES } = BOT;
  const { featAt, fitLogit, predLogit, median, quant } = BOT._;
  const wilson = BOT.wilson;
  const DAY = 86400000;

  const HZ = [
    { id: '1m', ten: '1 tháng', w: 4, days: 30 }, { id: '3m', ten: '3 tháng', w: 13, days: 91 },
    { id: '6m', ten: '6 tháng', w: 26, days: 182 }, { id: '1y', ten: '1 năm', w: 52, days: 365 },
  ];
  const SELL_HZ = [{ id: '3m', ten: '3 tháng', w: 13 }, { id: '6m', ten: '6 tháng', w: 26 }];
  const SELL_DROP = -0.10;
  const BUY_Z = [{ id: 'phai', ten: 'Phải mua', min: 80 }, { id: 'cannhac', ten: 'Cân nhắc mua', min: 60 }, { id: 'khong', ten: 'Không nên mua', min: 0 }];
  const SELL_Z = [{ id: 'nen', ten: 'Nên bán', min: 85 }, { id: 'cannhac', ten: 'Cân nhắc bán', min: 70 }, { id: 'khong', ten: 'Không nên bán', min: 0 }];
  const zoneOf = (Z, v) => (v == null ? null : Z.find((z) => v >= z.min));
  const MIN_TRAIN = 78;
  // các phương án theo thứ tự ưu tiên thiết kế; xếp hạng thật do dữ liệu quyết định
  const OPTIONS = [
    { id: 'pa1', ten: 'Phương án 1', ids: ['pi', 'mvrv'], lyDo: 'Xu hướng giá + định giá on-chain: hai nguồn thông tin độc lập.' },
    { id: 'pa2', ten: 'Phương án 2', ids: ['pi', 'mvrvz'], lyDo: 'Như phương án 1 nhưng dùng MVRV Z-Score.' },
    { id: 'pa3', ten: 'Phương án 3', ids: ['pi', 'mvrv', 'fng'], lyDo: 'Ba góc nhìn: xu hướng, định giá, tâm lý. Lịch sử ngắn hơn vì Fear & Greed có từ 2018.' },
    { id: 'pa4', ten: 'Phương án 4', ids: ['pi', 'puell'], lyDo: 'Xu hướng giá + doanh thu thợ đào; Puell bị nhiễu quanh mỗi lần halving.' },
    { id: 'pa5', ten: 'Phương án 5', ids: ['fng', 'mvrv', 'wma'], lyDo: 'Bộ cân bằng không dùng Pi Cycle, để so sánh.' },
    { id: 'pa6', ten: 'Phương án 6', ids: null, lyDo: 'Bộ bot tự tìm có tỷ lệ thắng cao nhất trên dữ liệu.' },
  ];
  const PRESETS = [
    { id: 'all', ten: 'Tất cả chỉ số', ids: IND.map((d) => d.id) },
    { id: 'onchain', ten: 'Định giá on-chain', ids: ['mvrv', 'mvrvz', 'puell'] },
    { id: 'xuhuong', ten: 'Xu hướng giá', ids: ['wma', 'mayer', 'rsiw', 'pi'] },
    { id: 'tamly_dinhgia', ten: 'Tâm lý và định giá', ids: ['fng', 'mvrv', 'wma'] },
  ];

  // các lần kiểm tra theo tuần (Chủ nhật) đến trước ngày phân tích, cộng thêm chính ngày phân tích
  function weekly(S, asOf) {
    const out = [];
    for (let i = 0; i < asOf; i++) if (new Date(S.dates[i] + 'T00:00:00Z').getUTCDay() === 0) out.push(i);
    out.push(asOf);
    return out;
  }
  const featRows = (S, smp, ids) => smp.map((i, j) => { const f = ids.map((id) => featAt(S, id, i)); return { j, i, date: S.dates[i], f, ok: f.every((x) => x != null) }; });

  // dự báo đi tới: tại mỗi lần, chỉ học từ những lần đã biết kết quả trước đó
  function walk(S, smp, R, H, target, refit) {
    const preds = [], X = [], Y = [];
    let model = null, lastFit = -1e9, k = 0, sumY = 0, ref = null;
    const rankIn = (arr, e) => { let lo = 0, hi = arr.length; while (lo < hi) { const m = (lo + hi) >> 1; if (arr[m] < e) lo = m + 1; else hi = m; } let eq = lo; while (eq < arr.length && arr[eq] === e) eq++; return ((lo + 0.5 * (eq - lo)) / arr.length) * 100; };
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
    return { preds, model };
  }

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
    if (!singles.length) throw new Error('Chưa đủ dữ liệu để tìm bộ chỉ số tại ngày này.');
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
    const cands = [{ ten: 'Bộ bot tìm được', ids: chosen }, ...PRESETS.map((p) => ({ ten: p.ten, ids: p.ids.filter((id) => usable.includes(id)) })), ...usable.map((id) => ({ ten: IND.find((d) => d.id === id).ten + ' (riêng)', ids: [id] }))];
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
    if (!ids.length) throw new Error('Hãy chọn ít nhất một chỉ số có dữ liệu.');
    const smp = weekly(S, asOf), R = featRows(S, smp, ids);
    if (!R[R.length - 1].ok) throw new Error('Tại ngày phân tích, một số chỉ số đã chọn chưa có số liệu.');
    const buyW = HZ.map((h) => walk(S, smp, R, h.w, (r) => (r > 0 ? 1 : 0), 4));
    const sellW = SELL_HZ.map((h) => walk(S, smp, R, h.w, (r) => (r < SELL_DROP ? 1 : 0), 4));
    const buyS = combine(buyW), sellS = combine(sellW);
    const nowJ = smp.length - 1;
    const bNow = buyS.find((x) => x.j === nowJ), sNow = sellS.find((x) => x.j === nowJ);
    if (!bNow || !sNow) throw new Error('Chưa đủ lịch sử để chấm điểm tại ngày này. Hãy chọn ngày muộn hơn hoặc bớt các chỉ số mới có dữ liệu gần đây (Fear & Greed, Khối lượng).');
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
      buy: { score: bNow.score, zone: zoneOf(BUY_Z, bNow.score), ev: buyEvidence(buyS, from), series: buyS },
      sell: { score: sNow.score, zone: zoneOf(SELL_Z, sNow.score), ev: sellEvidence(sellS, from), series: sellS },
      hold, weights, feats,
    };
  }

  const P = (x, d = 0) => (x == null || !isFinite(x) ? '—' : (x * 100).toFixed(d).replace('.', ',') + '%');
  const SP = (x) => (x == null || !isFinite(x) ? '—' : (x > 0 ? '+' : '') + (x * 100).toFixed(0) + '%');
  const D = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`;
  const nm = (id) => IND.find((d) => d.id === id).ten;
  function report(S, a, rec, vol, sources, isToday, cmp, sd) {
    const L = [], t = (x) => L.push(x);
    t(`# Báo cáo bot BTC, phân tích tại ngày ${D(a.date)}`); t('');
    t('Bot thống kê, không có trí tuệ AI. Mọi con số tính từ dữ liệu thật tải trên web, bằng kiểm chứng đi tới (chỉ dùng dữ liệu có đến từng thời điểm).'); t('');
    t('## Bối cảnh');
    t(`- Giá BTC tại ngày phân tích: ${Math.round(a.price).toLocaleString('vi-VN')} $` + (isToday ? ' (giá trực tiếp)' : ' (ngày trong quá khứ)'));
    t(`- Nguồn: ${sources}`); t(`- Bộ chỉ số: ${a.ids.map(nm).join(', ')}`); t(`- Giai đoạn chấm điểm: từ ${D(a.from)} đến ${D(a.date)}, kiểm tra mỗi tuần`); t('');
    t('## Kết luận');
    t(`- Tỷ lệ nên mua: **${a.buy.score.toFixed(0)}%**, khung **${a.buy.zone.ten}** (Phải mua từ 80%, Cân nhắc mua 60–80%). Ý nghĩa: điều kiện hôm nay thuận lợi hơn ${a.buy.score.toFixed(0)}% số tuần trước đó.`);
    t(`- Tỷ lệ nên bán: **${a.sell.score.toFixed(0)}%**, khung **${a.sell.zone.ten}** (Nên bán từ 85%, Cân nhắc bán 70–85%). Ý nghĩa: nguy cơ giảm hơn 10% trong 3–6 tháng cao hơn ${a.sell.score.toFixed(0)}% số tuần trước đó.`); t('');
    t('## Xác suất thắng nếu mua tại ngày phân tích');
    t('| Giữ | Xác suất thắng | Khoảng tin cậy 95% | Trung bình mọi lúc | Lãi trung vị | Một nửa số lần trong | Số lần tương tự |' + (isToday ? '' : ' Thực tế sau đó |'));
    t('|---|---|---|---|---|---|---|' + (isToday ? '' : '---|'));
    a.hold.forEach((h) => t(`| ${h.ten} | ${P(h.win)} | ${P(h.lo)}–${P(h.hi)} | ${P(h.base)} | ${SP(h.med)} | ${SP(h.q1)} đến ${SP(h.q3)} | ${h.n} (${h.eps} đợt) |` + (isToday ? '' : ` ${h.thucTe == null ? 'chưa đủ thời gian' : SP(h.thucTe)} |`)));
    t('');
    t('## Bộ tiêu chí: tỷ lệ thắng thực tế theo từng khung mua (từ ' + D(a.from) + ')');
    t('| Khung | Số tuần | ' + HZ.map((h) => 'Thắng sau ' + h.ten).join(' | ') + ' |'); t('|---|---|' + HZ.map(() => '---').join('|') + '|');
    [{ ten: 'Mua bất kỳ lúc nào (mốc)', ...a.buy.ev.base }, ...a.buy.ev.zones].forEach((z) => t(`| ${z.ten} | ${z.n} (${z.eps} đợt) | ` + z.h.map((x) => `${P(x.win)} (${x.n})`).join(' | ') + ' |'));
    t('');
    t('## Khung bán: giá có giảm thật không');
    t('| Khung | Số tuần | ' + SELL_HZ.map((h) => `Giá thấp hơn sau ${h.ten} | Giảm hơn 10% sau ${h.ten}`).join(' | ') + ' |'); t('|---|---|' + SELL_HZ.map(() => '---|---').join('|') + '|');
    [{ ten: 'Bất kỳ lúc nào (mốc)', ...a.sell.ev.base }, ...a.sell.ev.zones].forEach((z) => t(`| ${z.ten} | ${z.n} | ` + z.h.map((x) => `${P(x.giam.win)} | ${P(x.giamManh.win)}`).join(' | ') + ' |'));
    t('');
    if (cmp && cmp.ranked.length) {
      const dt = cmp.dongThuan;
      t(`## So sánh các phương án (chấm trên cùng giai đoạn từ ${D(cmp.from)})`);
      t(`Đồng thuận hôm nay: ${dt.mua.filter((z) => z.n).map((z) => `${z.n}/${dt.tong} ${z.ten.toLowerCase()}`).join(', ')}; trung bình tỷ lệ nên mua ${dt.tbMua.toFixed(0)}%, nên bán ${dt.tbBan.toFixed(0)}%.`);
      t('| Hạng | Phương án | Chỉ số | Nên mua hôm nay | Nên bán hôm nay | Thắng khi Phải mua (1t/3t/6t/1n) | Nửa đầu / nửa sau (6t) | Khi Nên bán, giá thấp hơn sau 6t |'); t('|---|---|---|---|---|---|---|---|');
      cmp.ranked.forEach((x) => t(`| ${x.hang || '—'} | ${x.ten} | ${x.ids.map(nm).join(', ')} | ${x.a.buy.score.toFixed(0)}% ${x.a.buy.zone.ten} | ${x.a.sell.score.toFixed(0)}% ${x.a.sell.zone.ten} | ${x.evB.zones[0].h.map((h) => P(h.win)).join(' / ')} | ${P(x.nua1.win)} / ${P(x.nua2.win)} | ${x.banDung ? P(x.banDung.win) + ' (mốc ' + P(x.banMoc) + ')' : 'ít tín hiệu'} |`));
      t('');
    }
    if (rec) {
      t(`## Bộ chỉ số có tỷ lệ thắng cao nhất (tìm với dữ liệu đến ${D(rec.asOfDate)}, chấm từ ${D(rec.from)})`);
      t('| Bộ | Thắng 1 tháng | Thắng 3 tháng | Thắng 6 tháng | Thắng 1 năm | Nửa đầu 6 tháng | Nửa sau 6 tháng |'); t('|---|---|---|---|---|---|---|');
      rec.ranking.slice(0, 8).forEach((r) => t(`| ${r.ten}: ${r.ids.map(nm).join(', ')} | ` + r.phai.h.map((x) => P(x.win)).join(' | ') + ` | ${P(r.nua1[2].win)} | ${P(r.nua2[2].win)} |`));
      t('');
    }
    if (sd) {
      t(`## Bên bán: nên giữ hay chốt lời (ngày ${D(sd.date)})`);
      t(`- Kết luận: **${sd.verdict.ten}**. ${sd.verdict.goiY}`);
      t(`- Số nhóm tiêu chí đáng tin đang bật: ${sd.nFam}${sd.famNow.length ? ' (' + sd.famNow.map((f) => NHOM_TP[f]).join(', ') + ')' : ''}. Quy tắc: từ 1 nhóm chốt lời một phần, từ 3 nhóm bán phần lớn.`);
      t(`- Mốc: bán vào một tuần bất kỳ thì giá 6 tháng sau thấp hơn ${P(sd.baseDung6)} số lần, 1 năm sau ${P(sd.baseDung12)}.`);
      t('');
      t('| Tiêu chí | Đáng tin | Hôm nay | Số đợt | Giá thấp hơn sau 6 tháng | Khoảng tin cậy | Sau 1 năm | Còn tăng thêm (TV) | Giảm sâu nhất 1 năm (TV) | Giá BTC để bật |'); t('|---|---|---|---|---|---|---|---|---|---|');
      sd.ranked.forEach((c) => t(`| ${c.ten} | ${c.dangTin ? 'có' : ''} | ${c.nowOn ? 'đang bật' : 'chưa'} | ${c.dot} | ${P(c.dung6)} (${c.n6}) | ${P(c.lo6)}–${P(c.hi6)} | ${P(c.dung12)} (${c.n12}) | ${SP(c.up)} | ${SP(c.dn)} | ${c.trigger && c.trigger.gia ? Math.round(c.trigger.gia).toLocaleString('vi-VN') + ' $' : '—'} |`));
      t('');
      if (sd.sims.length) { t('Mô phỏng giữ 1 BTC và chốt lời theo quy tắc (giữ 90/70/50% khi 1/2/3 nhóm bật, mua lại khi bên mua báo từ Cân nhắc mua):'); t('| Bắt đầu | Giữ nguyên | Theo quy tắc | Quy ra BTC | Bán/mua lại | Sụt giảm lớn nhất giữ/quy tắc |'); t('|---|---|---|---|---|---|');
        sd.sims.forEach((x) => t(`| ${D(x.tu)} | ${Math.round(x.giuGT).toLocaleString('vi-VN')} $ | ${Math.round(x.tcGT).toLocaleString('vi-VN')} $ | ${x.tcBTC.toFixed(3)} | ${x.ban}/${x.mua} | ${SP(x.mddH)} / ${SP(x.mdd)} |`)); t(''); }
    }
    t('## Giá trị chỉ số tại ngày phân tích');
    a.feats.forEach((f) => { const d = IND.find((x) => x.id === f.id); t(`- ${d.ten}: ${f.v == null ? '—' : (+f.v).toFixed(d.dec).replace('.', ',') + (d.unit || '')}`); });
    if (a.weights) t('- Trọng số trong mô hình 6 tháng (dương: chỉ số báo rẻ làm tăng xác suất thắng): ' + a.weights.map((w) => `${nm(w.id)} ${w.w >= 0 ? '+' : ''}${w.w.toFixed(2).replace('.', ',')}`).join('; '));
    t('');
    if (vol && vol.last) { t('## Khối lượng giao dịch'); t(`Tuần gần nhất đã đóng (${D(vol.last.date)}): giá ${SP(vol.last.chg)}, khối lượng bằng ${vol.last.rv.toFixed(2).replace('.', ',')} lần trung bình 20 tuần, loại "${BOT.VCLS[vol.last.cls].ten}".`); t(''); }
    t('## Câu hỏi gợi ý cho Claude');
    t('- Kết luận của bot có đáng tin không, xét theo số đợt độc lập và khoảng tin cậy?');
    t('- Bối cảnh vĩ mô và tin tức hiện tại ủng hộ hay mâu thuẫn với kết luận?');
    t('- Nên chia tiền mua thế nào theo các khung trên?');
    return L.join('\n');
  }

  // chạy tất cả phương án tại một ngày và xếp hạng trên cùng một giai đoạn
  async function compareOptions(S, asOf, recIds, tick) {
    const list = [];
    for (const o of OPTIONS) {
      const ids = (o.id === 'pa6' ? recIds || [] : o.ids).filter((id) => S.avail.includes(id));
      const thieu = (o.id === 'pa6' ? [] : o.ids).filter((id) => !S.avail.includes(id));
      const item = { ...o, ids, thieu, a: null, loi: null };
      if (!ids.length) item.loi = o.id === 'pa6' ? 'Chưa tìm được bộ khuyến cáo.' : 'Thiếu dữ liệu cho các chỉ số của phương án này.';
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
      return [x.hang, x.ten, x.ids.map(nm).join(' + '), x.loi || (x.trung ? 'trùng ' + x.trung : x.xepTheo === 'rong' ? 'ít tín hiệu Phải mua, xếp theo khung từ Cân nhắc mua' : ''),
        x.a && x.a.buy.score, x.a && x.a.buy.zone.ten, x.a && x.a.sell.score, x.a && x.a.sell.zone.ten,
        ...HZ.map((h, k) => z && z.h[k].win), z && z.n, z && z.eps, ...HZ.map((h, k) => x.evB && x.evB.base.h[k].win),
        x.nua1 && x.nua1.win, x.nua2 && x.nua2.win, x.banDung && x.banDung.win, x.banMoc, cmp.from]; });
    return csv(head, rows);
  }

  // ================================================================ BÊN BÁN: chốt lời hay giữ
  // nhom: để đếm số nhóm cùng báo, không đếm trùng hai chỉ số đo cùng một thứ
  const TP = [
    { id: 'pi_cat', ind: 'pi', nhom: 'xuhuong', ten: 'Pi Cycle cắt lên (tỉ số ≥ 1)', loai: 'kinh_dien', thr: 1.0 },
    { id: 'mvrvz_7', ind: 'mvrvz', nhom: 'onchain', ten: 'MVRV Z-Score ≥ 7', loai: 'kinh_dien', thr: 7 },
    { id: 'mvrv_3', ind: 'mvrv', nhom: 'onchain', ten: 'MVRV ≥ 3', loai: 'kinh_dien', thr: 3 },
    { id: 'mayer_24', ind: 'mayer', nhom: 'xuhuong', ten: 'Mayer Multiple ≥ 2,4', loai: 'kinh_dien', thr: 2.4 },
    { id: 'rsiw_80', ind: 'rsiw', nhom: 'xuhuong', ten: 'RSI 14 tuần ≥ 80', loai: 'kinh_dien', thr: 80 },
    { id: 'fng_90', ind: 'fng', nhom: 'tamly', ten: 'Fear & Greed ≥ 90', loai: 'kinh_dien', thr: 90 },
    { id: 'puell_4', ind: 'puell', nhom: 'thodao', ten: 'Puell Multiple ≥ 4', loai: 'kinh_dien', thr: 4 },
    { id: 'mvrvz_p', ind: 'mvrvz', nhom: 'onchain', ten: 'MVRV Z-Score thuộc 5% cao nhất 4 năm', loai: 'thich_nghi' },
    { id: 'mvrv_p', ind: 'mvrv', nhom: 'onchain', ten: 'MVRV thuộc 5% cao nhất 4 năm', loai: 'thich_nghi' },
    { id: 'mayer_p', ind: 'mayer', nhom: 'xuhuong', ten: 'Mayer Multiple thuộc 5% cao nhất 4 năm', loai: 'thich_nghi' },
    { id: 'wma_p', ind: 'wma', nhom: 'xuhuong', ten: 'Giá / MA 200 tuần thuộc 5% cao nhất 4 năm', loai: 'thich_nghi' },
    { id: 'puell_p', ind: 'puell', nhom: 'thodao', ten: 'Puell Multiple thuộc 5% cao nhất 4 năm', loai: 'thich_nghi' },
    { id: 'bot_nb', ind: null, nhom: 'mohinh', ten: 'Bot báo Nên bán (tỷ lệ nên bán ≥ 85%)', loai: 'mo_hinh' },
  ];
  const NHOM_TP = { xuhuong: 'Xu hướng giá', onchain: 'Định giá on-chain', tamly: 'Tâm lý', thodao: 'Thợ đào', mohinh: 'Mô hình của bot' };
  const SELL_VERDICT = [
    { id: 'ban', ten: 'Bán phần lớn', min: 3, goiY: 'Chốt khoảng 50% lượng đang giữ, phần còn lại đặt mốc chốt tiếp.' },
    { id: 'chot', ten: 'Chốt lời một phần', min: 1, goiY: 'Chốt khoảng 10–30% để khóa lợi nhuận, giữ phần còn lại.' },
    { id: 'giu', ten: 'Giữ', min: 0, goiY: 'Chưa có tiêu chí chốt lời đáng tin nào bật; tiếp tục giữ.' },
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
    const combos = [1, 2, 3].map((m) => ({ id: 'combo' + m, ten: `Từ ${m} nhóm tiêu chí đáng tin cùng bật`, loai: 'ket_hop', nhom: null, m, ...evalSignal(famCount.map((n) => n >= m)), nowOn: famCount[famCount.length - 1] >= m, coDuLieu: trusted.length > 0 }));
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
    const rows = [...sd.crit, ...sd.combos].map((c) => [c.ten, c.loai, c.nhom ? NHOM_TP[c.nhom] : 'kết hợp', c.dangTin ? 'có' : '', c.nowOn ? 'có' : c.nowOn === false ? 'không' : '', c.nowVal, c.trigger && c.trigger.gia,
      c.dot, c.tuan, c.dung6, c.lo6, c.n6, c.dung12, c.n12, sd.baseDung6, c.med6, c.up, c.dn, (c.ev || []).map((e) => e.date).join(' ')]);
    return csv(head, rows);
  }

  return { HZ, SELL_HZ, BUY_Z, SELL_Z, PRESETS, OPTIONS, TP, NHOM_TP, SELL_VERDICT, zoneOf, analyze, search, report, compareOptions, csvWeekly, csvOptions, sellSide, csvSell };
})();
// ===== B3 END =====
if (typeof module !== 'undefined') module.exports = B3;
