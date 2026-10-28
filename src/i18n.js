// ===== I18N START =====
// User-facing text lookup for the web page. Source of truth: bot/i18n/vi.yaml (build.py writes src/vi.json and
// inlines it into the page). Usage: tx('web.ui.key', arg0, arg1) fills {0}, {1} exactly like a template literal.
const I18N = (() => {
  const VI = typeof window === 'undefined' && typeof require !== 'undefined' ? require('./vi.json') : /*VI_JSON*/null;
  function tx(key, ...args) {
    let v = VI;
    for (const k of key.split('.')) v = v == null ? undefined : v[k];
    if (v == null) throw new Error('missing text for key ' + key);
    return args.length ? String(v).replace(/\{(\d+)\}/g, (m, i) => (+i < args.length ? String(args[+i]) : m)) : String(v);
  }
  // 'HH:mm dd/mm/yyyy' in Vietnam time (Asia/Ho_Chi_Minh) from an ISO UTC string
  function vnTime(iso) {
    const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric', hourCycle: 'h23' })
      .formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
    return `${p.hour}:${p.minute} ${p.day}/${p.month}/${p.year}`;
  }
  return { tx, vnTime, VI };
})();
// ===== I18N END =====
if (typeof module !== 'undefined') module.exports = I18N;
