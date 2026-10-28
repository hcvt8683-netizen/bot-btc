// Kiểm tra nhanh phần tính toán bằng dữ liệu giả lập (không cần mạng).
// Chạy: node tests/test_engine.js
global.BOT = require('../src/engine.js');
const B3 = require('../src/analysis.js');
const { cm, kl, fng, p } = require('./gen_data.js');
const assert = (ok, msg) => { if (!ok) { console.error('SAI:', msg); process.exitCode = 1; } else console.log('đúng:', msg); };
(async () => {
  const S = BOT.buildSeries({ cm, kl, fng, live: { price: p } }), last = S.price.length - 1;
  assert(S.avail.length === BOT.IND.length, 'đủ 10 chỉ số có dữ liệu');
  const a = B3.analyze(S, last, ['pi', 'mvrv']);
  assert(a.buy.score >= 0 && a.buy.score <= 100, 'tỷ lệ nên mua nằm trong 0–100');
  assert(a.sell.score >= 0 && a.sell.score <= 100, 'tỷ lệ nên bán nằm trong 0–100');
  assert(a.hold.length === 4 && a.hold.every((h) => h.win == null || (h.win >= 0 && h.win <= 1)), 'xác suất thắng 4 kỳ giữ hợp lệ');
  // không nhìn trước tương lai: phân tích tại ngày quá khứ không được đổi khi thêm dữ liệu sau ngày đó
  const d = S.dates.indexOf('2022-06-19');
  const S2 = BOT.buildSeries({ cm: cm.filter((r) => r.time.slice(0, 10) <= '2023-12-31'), kl, fng, live: null });
  const x1 = B3.analyze(S, d, ['pi', 'mvrv']), x2 = B3.analyze(S2, S2.dates.indexOf('2022-06-19'), ['pi', 'mvrv']);
  assert(Math.abs(x1.buy.score - x2.buy.score) < 1e-9 && Math.abs(x1.sell.score - x2.sell.score) < 1e-9, 'kết quả tại 19/06/2022 không phụ thuộc dữ liệu sau ngày đó');
  // Coin Metrics chưa công bố vốn hóa và MVRV của n ngày cuối (đã gặp với dữ liệu thật 26/10/2026)
  const thieu = (n) => cm.map((r, k) => (k >= cm.length - n ? { ...r, CapMrktCurUSD: null, CapMVRVCur: null } : r));
  const S0 = BOT.buildSeries({ cm, kl, fng, live: null }), S3 = BOT.buildSeries({ cm: thieu(1), kl, fng, live: null }), e = S3.dates.length - 1;
  assert(S3.uocTinh && S3.uocTinh.ngay === 1 && S3.v.mvrv[e] != null && S3.v.mvrvz[e] != null, 'thiếu MVRV ngày cuối: bot ước tính và ghi lại để báo trên giao diện');
  const ky = Number(cm[cm.length - 2].CapMVRVCur) * Number(cm[cm.length - 1].PriceUSD) / Number(cm[cm.length - 2].PriceUSD);
  assert(Math.abs(S3.v.mvrv[e] / ky - 1) < 1e-12, 'MVRV ước tính = MVRV hôm trước × tỉ lệ giá, chỉ dùng số liệu đến chính ngày đó');
  assert(S3.v.mvrv.slice(0, e).every((v, i) => v === S0.v.mvrv[i]) && S3.v.mvrvz.slice(0, e).every((v, i) => v === S0.v.mvrvz[i]), 'ước tính ngày cuối không làm đổi MVRV, MVRV Z-Score của mọi ngày trước');
  const d0 = S0.dates.indexOf('2022-06-19'), y1 = B3.analyze(S0, d0, ['pi', 'mvrv']), y2 = B3.analyze(S3, d0, ['pi', 'mvrv']);
  assert(y1.buy.score === y2.buy.score && y1.sell.score === y2.sell.score, 'ước tính ngày cuối không làm đổi kết quả tại 19/06/2022');
  const S5 = BOT.buildSeries({ cm: thieu(1), kl, fng, live: { price: p } });
  let loi = null; try { B3.analyze(S5, S5.dates.length - 1, ['pi', 'mvrv']); } catch (err) { loi = err.message; }
  assert(loi === null, 'thiếu MVRV ngày cuối, có giá trực tiếp: phương án Pi + MVRV vẫn phân tích được hôm nay' + (loi ? ' (' + loi + ')' : ''));
  const S6 = BOT.buildSeries({ cm: thieu(3), kl, fng, live: null }), S7 = BOT.buildSeries({ cm: thieu(4), kl, fng, live: null });
  assert(S6.uocTinh && S6.uocTinh.ngay === 3 && !S7.uocTinh && S7.v.mvrv[S7.dates.length - 1] == null, 'chỉ ước tính khi thiếu tối đa 3 ngày; thiếu 4 ngày thì không đoán');
  // giá đề xuất mua, bán
  const sNow = B3.scoreAtPrice(S, last, a, S.price[last]);
  assert(Math.abs(sNow.buy - a.buy.score) < 1e-9 && Math.abs(sNow.sell - a.sell.score) < 1e-9, 'giá đề xuất: tại giá hiện tại, tỷ lệ tính lại đúng bằng tỷ lệ nên mua, nên bán');
  const f1 = B3.findLevel(100, 'buy', (X) => X <= 87.3), f2 = B3.findLevel(100, 'sell', (X) => X >= 131.7), f3 = B3.findLevel(100, 'buy', (X) => X <= 140), f4 = B3.findLevel(100, 'buy', () => false);
  assert(!f1.dat && Math.abs(f1.gia - 87.3) < 0.01 && !f2.dat && Math.abs(f2.gia - 131.7) < 0.01 && f3.dat && Math.abs(f3.gia - 140) < 0.01 && f4.gia == null,
    'dò mốc giá tìm đúng ranh giới: mốc dưới giá, mốc trên giá, hôm nay đã đạt, không bao giờ đạt');
  // dữ liệu giả lập có giá chạy theo đà nên mô hình thường ngược chiều và mốc có thể trống; mốc nào có thì phải đúng ranh giới
  const lv = B3.priceLevels(S, last, a);
  const bien = (L) => { const s1 = B3.scoreAtPrice(S, last, a, L.gia), s2 = B3.scoreAtPrice(S, last, a, L.gia * (L.kind === 'buy' ? 1.002 : 0.998)); return s1[L.kind] >= L.thr && s2[L.kind] < L.thr; };
  assert(lv.levels.length === 4 && lv.ladder.length === 10 && lv.levels.every((L) => L.gia == null || bien(L)), 'giá đề xuất của bot nằm đúng ranh giới khung');
  const g1 = B3.priceLevels(S, d, x1), g2 = B3.priceLevels(S2, S2.dates.indexOf('2022-06-19'), x2);
  assert(g1.levels.every((L, k) => L.dat === g2.levels[k].dat && (L.gia == null ? g2.levels[k].gia == null : Math.abs(L.gia / g2.levels[k].gia - 1) < 1e-9)) && g1.ladder.every((r, k) => Math.abs(r.buy - g2.ladder[k].buy) < 1e-9 && Math.abs(r.sell - g2.ladder[k].sell) < 1e-9), 'giá đề xuất tại 19/06/2022 không phụ thuộc dữ liệu sau ngày đó');
  const sd = B3.sellSide(S, last, a);
  assert(['giu', 'chot', 'ban'].includes(sd.verdict.id), 'bên bán có kết luận hợp lệ');
  const rec = await B3.search(S, last, S.avail);
  assert(Array.isArray(rec.ids), 'tìm bộ chỉ số chạy được');
  const cmp = await B3.compareOptions(S, last, rec.ids);
  assert(cmp.list.length >= 5, 'so sánh các phương án chạy được');
  assert(B3.csvWeekly(S, a).startsWith('\ufeffngay,'), 'xuất CSV từng tuần đúng định dạng');
  assert(B3.report(S, a, rec, null, 'thử', true, cmp, sd).includes('## Bên bán'), 'báo cáo có phần bên bán');
  assert(B3.report(S, a, rec, null, 'thử', true, cmp, sd, lv).includes('## Giá đề xuất mua và bán'), 'báo cáo có phần giá đề xuất');
})();
