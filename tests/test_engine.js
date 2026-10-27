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
  const sd = B3.sellSide(S, last, a);
  assert(['giu', 'chot', 'ban'].includes(sd.verdict.id), 'bên bán có kết luận hợp lệ');
  const rec = await B3.search(S, last, S.avail);
  assert(Array.isArray(rec.ids), 'tìm bộ chỉ số chạy được');
  const cmp = await B3.compareOptions(S, last, rec.ids);
  assert(cmp.list.length >= 5, 'so sánh các phương án chạy được');
  assert(B3.csvWeekly(S, a).startsWith('\ufeffngay,'), 'xuất CSV từng tuần đúng định dạng');
  assert(B3.report(S, a, rec, null, 'thử', true, cmp, sd).includes('## Bên bán'), 'báo cáo có phần bên bán');
})();
