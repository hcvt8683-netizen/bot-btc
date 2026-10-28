// Export the current bot's weekly walk-forward scores (no look-ahead) for the multiplier backtest.
// Input: JSON {cm, kl, fng} in the browser format. Output: JSON with fixed option series and the
// "Tự động: phương án tốt nhất" choice re-made every `every` weeks using only data up to that week.
// Run: node tools/export_current_bot.js <input.json> <output.json> [every=4] [autoFrom=2021-01-03]
const fs = require('fs');
global.BOT = require('../src/engine.js');
const B3 = require('../src/analysis.js');
const [, , inp, outp, everyArg, fromArg] = process.argv;
const every = Number(everyArg || 4), autoFrom = fromArg || '2021-01-03';

(async () => {
  const raw = JSON.parse(fs.readFileSync(inp, 'utf8'));
  const S = BOT.buildSeries({ cm: raw.cm, kl: raw.kl, fng: raw.fng, live: null }), last = S.price.length - 1;
  const avail = BOT.IND.filter((d) => S.avail.includes(d.id)).map((d) => d.id);
  const cache = new Map();
  const seriesOf = (ids) => {
    const key = [...ids].sort().join(',');
    if (!cache.has(key)) {
      const a = B3.analyze(S, last, ids), sell = new Map(a.sell.series.map((x) => [x.j, x.score]));
      cache.set(key, { ids, buy: a.buy.series.map((x) => [x.date, x.score, sell.get(x.j) ?? null]) });
    }
    return cache.get(key);
  };
  const fixed = {};
  for (const o of B3.OPTIONS) if (o.ids) fixed[o.id] = seriesOf(o.ids.filter((id) => S.avail.includes(id)));
  fixed.all = seriesOf(avail);
  // re-select the top option every `every` weeks, exactly like the UI button "Tự động" would have at that date
  const sundays = []; for (let i = 0; i <= last; i++) if (new Date(S.dates[i] + 'T00:00:00Z').getUTCDay() === 0 && S.dates[i] >= autoFrom) sundays.push(i);
  const auto = [], t0 = Date.now();
  for (let k = 0; k < sundays.length; k += every) {
    const i = sundays[k];
    let rec = null, cmp = null;
    try { rec = await B3.search(S, i, avail); } catch (e) { rec = null; }
    try { cmp = await B3.compareOptions(S, i, rec ? rec.ids : null); } catch (e) { cmp = null; }
    const top = cmp ? cmp.ranked.find((x) => x.hang) : null;
    const ids = top ? top.ids : rec && rec.ids.length ? rec.ids : avail;
    seriesOf(ids);
    auto.push({ date: S.dates[i], option: top ? top.id : rec && rec.ids.length ? 'pa6' : 'all', ids, rec: rec ? rec.ids : [] });
    if (k % (every * 10) === 0) console.error(`auto ${S.dates[i]} -> ${top ? top.id : '-'} [${ids}] (${Math.round((Date.now() - t0) / 1000)} s)`);
  }
  fs.writeFileSync(outp, JSON.stringify({ last: S.dates[last], fixed, auto, sets: [...cache.values()] }));
  console.error(`done: ${Object.keys(fixed).length} fixed, ${auto.length} auto choices, ${cache.size} distinct sets`);
})();
