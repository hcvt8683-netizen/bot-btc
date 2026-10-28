// Regression snapshot of every text the bot exports (report .md and the three CSV files),
// computed on a frozen synthetic data set, so any change in numbers or wording shows up as a diff.
// Check:  node tests/snapshot_report.js          (exit code 1 and a diff summary on mismatch)
// Update: node tests/snapshot_report.js --update (only after reviewing the change)
const fs = require('fs'), path = require('path');
global.BOT = require('../src/engine.js');
const B3 = require('../src/analysis.js');
const { make } = require('./gen_data.js');

const END = Date.parse('2026-10-27T00:00:00Z');
const NOW = Date.parse('2026-10-28T03:00:00Z');
Date.now = () => NOW; // the report checks data freshness against the clock
const KN = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'recommendation.json'), 'utf8'));
const DIR = path.join(__dirname, 'snapshots');

async function produce() {
  const { cm, kl, fng } = make(END);
  const S = BOT.buildSeries({ cm, kl, fng, live: null }), last = S.price.length - 1;
  const vol = BOT.volumeStudy(S);
  const rec = await B3.search(S, last, S.avail);
  const cmp = await B3.compareOptions(S, last, rec.ids);
  const top = cmp.ranked.find((x) => x.hang);
  const ids = top ? top.ids : rec.ids;
  const a = B3.analyze(S, last, ids);
  const lv = B3.priceLevels(S, last, a);
  const sd = B3.sellSide(S, last, a);
  const volLast = vol && { last: vol.weeks.filter((x) => x.cls && x.date <= a.date).pop() };
  const sources = 'Fear & Greed Alternative.me, Coin Metrics, Binance (giá, khối lượng ngày)';
  return {
    'report.md': B3.report(S, a, rec, volLast, sources, true, cmp, sd, lv, KN) + '\n',
    'weekly.csv': B3.csvWeekly(S, a) + '\n',
    'options.csv': B3.csvOptions(cmp) + '\n',
    'sell.csv': B3.csvSell(sd) + '\n',
  };
}

(async () => {
  const out = await produce(), update = process.argv.includes('--update');
  fs.mkdirSync(DIR, { recursive: true });
  let bad = 0;
  for (const [name, text] of Object.entries(out)) {
    const f = path.join(DIR, name);
    if (update) { fs.writeFileSync(f, text, 'utf8'); console.log('updated', name, text.length, 'chars'); continue; }
    const old = fs.existsSync(f) ? fs.readFileSync(f, 'utf8') : null;
    if (old === text) { console.log('same:', name); continue; }
    bad++;
    const a = (old || '').split('\n'), b = text.split('\n');
    const k = a.findIndex((x, i) => x !== b[i]);
    console.error(`DIFF: ${name} (first differing line ${k + 1})\n  - ${(a[k] || '').slice(0, 300)}\n  + ${(b[k] || '').slice(0, 300)}`);
    fs.writeFileSync(f + '.new', text, 'utf8');
  }
  if (bad) { console.error(`${bad} snapshot(s) changed; new versions written as *.new for review.`); process.exitCode = 1; }
})();
