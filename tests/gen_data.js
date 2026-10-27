

const DAY = 86400000;
let t = Date.parse('2010-07-18T00:00:00Z'), end = Date.now() - DAY, cm = [], fng = [], kl = [], p = 0.08, rp = 0.08, seed = 11, prevP = p;
const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
for (let i = 0; t <= end; t += DAY, i++) {
  const cyc = Math.sin(i / 1461 * 2 * Math.PI);
  p *= Math.exp(0.0016 + 0.004 * cyc + (rnd() - 0.5) * 0.07 - 0.0008 * Math.log(p / rp)); rp += (p - rp) / 500;
  const issue = i < 800 ? 7200 : i < 2300 ? 3600 : i < 3700 ? 1800 : i < 5100 ? 900 : 450;
  const ds = new Date(t).toISOString().slice(0, 10);
  cm.push({ time: ds + 'T00:00:00.000000000Z', PriceUSD: String(p), CapMrktCurUSD: String(p * (3e6 + i * 4000)), CapMVRVCur: String(p / rp), IssTotUSD: String(issue * p) });
  if (t >= Date.parse('2018-02-01')) fng.push({ value: String(Math.max(1, Math.min(99, Math.round(50 + 30 * cyc + (rnd() - 0.5) * 40)))), timestamp: String(t / 1000) });
  if (t >= Date.parse('2017-08-17')) { const mv = Math.abs(Math.log(p / prevP)); kl.push([t, '0', '0', '0', String(p), '0', 0, String(1e9 * (1 + i / 3000) * (0.6 + rnd() * 0.8 + mv * 20))]); }
  prevP = p;
}

module.exports = { cm, kl, fng, p };
