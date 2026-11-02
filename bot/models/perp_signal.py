"""Long/Short on the BTCUSDT perpetual at lookup time (settings in config/candidates.yaml, section perp).

For each horizon (1–24 hours on hourly candles, 1–7 days on daily candles) and each decision time t (a candle close):
the net gain of a long and of a short opened at the close of t and closed at the close of t + horizon, after taker fee,
slippage and the funding paid or received in (t, t + horizon]. Five pre-registered states, all known at t: trend (close
against the 20-candle mean), funding (24-hour mean against its percentiles of the previous 365 days), stretch (return of
the last horizon against its percentiles), volatility (20-candle std against its percentiles). Per cell and side: share
of profitable trades, Wilson on non-overlapping trades, both halves, Bonferroni over every cell-side, and liquidation
curves so the page can read any leverage. A cell is only called an edge when it passes the registered rule.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml

LOG = DATA / "perp" / "perp_log.csv"
LOG_COLS = ["issued", "unit", "h", "target", "price", "cells", "p_long", "p_short", "verdict", "version", "logged_at"]
HOUR = pd.Timedelta(hours=1)
FUNDING_EVERY = pd.Timedelta(hours=8)
SIDES = ("long", "short")
CELLS = {"moc": None, "trend_tren": ("trend", "tren"), "trend_duoi": ("trend", "duoi"), "funding_cao": ("funding", "cao"),
         "funding_thap": ("funding", "thap"), "stretch_tang_manh": ("stretch", "tang_manh"), "stretch_giam_manh": ("stretch", "giam_manh"),
         "vol_cao": ("vol", "cao"), "vol_binh_thuong": ("vol", "binh_thuong")}
STATES = ("trend", "funding", "stretch", "vol")


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["perp"]


def version(cfg: dict) -> str:
    """Hash of the settings and of this module."""
    code = (ROOT / "bot" / "models" / "perp_signal.py").read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def horizons(cfg: dict) -> list[tuple[str, int]]:
    return [("h", int(h)) for h in cfg["horizons_hours"]] + [("d", int(k)) for k in cfg["horizons_days"]]


def z_bonferroni(cfg: dict) -> tuple[float, int]:
    m = len(horizons(cfg)) * len(cfg["cells"]) * len(SIDES)
    return float(norm.ppf(1 - 0.05 / m)), m


# ----- data -----
def hourly(cfg: dict, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Hourly high, low, close indexed by the candle CLOSE time t (open + 1 hour), gap-free grid from `start`."""
    from bot.data import pit_store as ps
    h = ps.load_history("binance_perp_1h")
    d = h.assign(time=pd.to_datetime(h["time"])).drop_duplicates("time", keep="last").set_index("time")[["high", "low", "close"]]
    d = d.astype(float).sort_index()
    d.index = d.index + HOUR
    d = d[d.index > pd.Timestamp(str(cfg["start"]))]
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="h"))
    return d if end is None else d[d.index <= end]


def funding(index: pd.DatetimeIndex, end: pd.Timestamp | None = None) -> tuple[pd.Series, pd.Series, pd.Timestamp | None]:
    """Funding rate on the hourly grid (0 between funding times), a 0/1 marker of funding times, and the last known one."""
    from bot.data import pit_store as ps
    f = ps.load_history("binance_funding")
    if f.empty:
        return pd.Series(0.0, index=index), pd.Series(0.0, index=index), None
    s = f.assign(t=pd.to_datetime(f["time"]).dt.floor("h")).groupby("t")["funding_rate"].last().astype(float)
    if end is not None:
        s = s[s.index <= end]
    return s.reindex(index).fillna(0.0), s.reindex(index).notna().astype(float), (s.index.max() if len(s) else None)


def daily(h: pd.DataFrame) -> pd.DataFrame:
    """Daily candles from the 24 hourly ones of each UTC day, indexed by their close (next 00:00); an hour missing → NaN."""
    day = (h.index - HOUR).normalize()
    g = h.groupby(day)
    out = pd.DataFrame({"high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last()})
    full = h.notna().all(axis=1).groupby(day).sum() == 24
    out[~full.reindex(out.index).fillna(False).to_numpy()] = np.nan
    out.index = out.index + pd.Timedelta(days=1)
    return out


def funding_24h(rate: pd.Series, mark: pd.Series, last: pd.Timestamp | None) -> pd.Series:
    """Mean of the funding rates in (t − 24 h, t] on the hourly grid; unknown once a funding time is missing at the end."""
    cnt = mark.rolling(24, min_periods=24).sum()
    f = (rate.rolling(24, min_periods=24).sum() / cnt).where(cnt > 0)
    if last is None:
        return f * np.nan
    return f.where(f.index < last + FUNDING_EVERY)


# ----- states (only data up to t) -----
def _past_q(x: pd.Series, q: float, w: int, minp: int) -> pd.Series:
    """q-quantile of x over the w rows before each row (the row itself excluded)."""
    return x.shift(1).rolling(w, min_periods=minp).quantile(q)


def _label(cond: list[tuple[np.ndarray, str]], other: str, known: np.ndarray) -> pd.Series:
    out = np.select([c for c, _ in cond], [lab for _, lab in cond], default=other).astype(object)
    out[~known] = None
    return out


def funding_state(f24: pd.Series, cfg: dict) -> pd.Series:
    """'cao' / 'thap' / 'giua' on the hourly grid, thresholds from the previous 365 days of the hourly series."""
    st = cfg["states"]
    w, mn = st["lookback_days"] * 24, st["min_days"] * 24
    q20, q80 = _past_q(f24, 0.2, w, mn), _past_q(f24, 0.8, w, mn)
    known = (f24.notna() & q20.notna()).to_numpy()
    return pd.Series(_label([((f24 >= q80).to_numpy(), "cao"), ((f24 <= q20).to_numpy(), "thap")], "giua", known), index=f24.index)


def base_states(c: pd.Series, per_day: int, cfg: dict) -> pd.DataFrame:
    """Trend and volatility at every close t of `c` (per_day = 24 for hourly candles, 1 for daily ones)."""
    st = cfg["states"]
    n, w, mn = int(st["window"]), st["lookback_days"] * per_day, st["min_days"] * per_day
    mean = c.rolling(n, min_periods=n).mean()
    trend = _label([((c > mean).to_numpy(), "tren")], "duoi", (c.notna() & mean.notna()).to_numpy())
    vol = np.log(c).diff().rolling(n, min_periods=n).std()
    v80 = _past_q(vol, 0.8, w, mn)
    vol_s = _label([((vol >= v80).to_numpy(), "cao")], "binh_thuong", (vol.notna() & v80.notna()).to_numpy())
    return pd.DataFrame({"trend": trend, "vol": vol_s}, index=c.index)


def stretch_state(c: pd.Series, H: int, per_day: int, cfg: dict) -> pd.Series:
    """Return of the last H candles against its 10% / 90% percentiles of the previous 365 days."""
    st = cfg["states"]
    w, mn = st["lookback_days"] * per_day, st["min_days"] * per_day
    past = c / c.shift(H) - 1
    p10, p90 = _past_q(past, 0.1, w, mn), _past_q(past, 0.9, w, mn)
    return pd.Series(_label([((past >= p90).to_numpy(), "tang_manh"), ((past <= p10).to_numpy(), "giam_manh")], "giua",
                            (past.notna() & p10.notna()).to_numpy()), index=c.index)


def candle_states(c: pd.Series, H: int, per_day: int, cfg: dict) -> pd.DataFrame:
    """Trend, stretch (return of the last H candles) and volatility at every close t of `c`."""
    return base_states(c, per_day, cfg).assign(stretch=stretch_state(c, H, per_day, cfg))


def thresholds(c: pd.Series, f24: pd.Series, hs: list[int], per_day: int, cfg: dict) -> dict:
    """Percentile thresholds from the 365 days up to the last row (inclusive), for the live state on the page."""
    st = cfg["states"]
    n, w, mn = int(st["window"]), st["lookback_days"] * per_day, st["min_days"] * per_day
    wf, mf = st["lookback_days"] * 24, st["min_days"] * 24
    last = lambda s, q, ww, mm: float(s.rolling(ww, min_periods=mm).quantile(q).iloc[-1])  # noqa: E731
    vol = np.log(c).diff().rolling(n, min_periods=n).std()
    out = {"funding": [last(f24, 0.2, wf, mf), last(f24, 0.8, wf, mf)], "vol80": last(vol, 0.8, w, mn), "stretch": {}}
    for H in hs:
        past = c / c.shift(H) - 1
        out["stretch"][str(H)] = [last(past, 0.1, w, mn), last(past, 0.9, w, mn)]
    return out


# ----- outcomes -----
def _next(v: np.ndarray, k: int, fn) -> np.ndarray:
    """fn over the values at t+1..t+k, at row t (NaN when one of them is missing or not there yet)."""
    out = np.full(len(v), np.nan)
    if len(v) > k:
        out[:len(v) - k] = fn(np.lib.stride_tricks.sliding_window_view(v[1:], k), axis=1)
    return out


def outcomes(d: pd.DataFrame, H: int, hours: int, rate: pd.Series, last_f: pd.Timestamp | None, cfg: dict) -> pd.DataFrame:
    """Net gain of a long and a short opened at the close of t and closed at the close H candles later, and how far the
    price went against each side meanwhile (for liquidation)."""
    c = d["close"].to_numpy(dtype=float)
    later = np.r_[c[H:], np.full(H, np.nan)]
    r = later / c - 1
    cum = rate.cumsum()
    f = cum.reindex(d.index + hours * HOUR).to_numpy() - cum.reindex(d.index).to_numpy()
    if last_f is None:
        f[:] = np.nan
    else:
        f[~((d.index + hours * HOUR) < last_f + FUNDING_EVERY)] = np.nan
    cost = 2 * (cfg["costs"]["fee"] + cfg["costs"]["slippage"])
    lo, hi = _next(d["low"].to_numpy(dtype=float), H, np.min), _next(d["high"].to_numpy(dtype=float), H, np.max)
    return pd.DataFrame({"long": r - cost - f, "short": -r - cost + f, "mae_long": 1 - lo / c, "mae_short": hi / c - 1}, index=d.index)


# ----- statistics -----
def non_overlap(pos: np.ndarray, H: int) -> int:
    """Trades whose windows (t, t + H] do not overlap: take the earliest, skip those inside its horizon, repeat."""
    n, i = 0, 0
    while i < len(pos):
        n += 1
        i = int(np.searchsorted(pos, pos[i] + H, side="left"))
    return n


def side_stats(net: np.ndarray, mae: np.ndarray, pos: np.ndarray, first: np.ndarray, H: int, z_b: float, grid: list[float]) -> dict:
    n = len(net)
    if not n:
        return {"n": 0, "edge": False}
    win = net > 0
    p, eff = float(win.mean()), non_overlap(pos, H)
    k = round(p * eff)
    ci, lb = wilson(k, eff), wilson(k, eff, z_b)[0]
    halves = []
    for m in (first, ~first):
        halves.append({"n": int(m.sum()), "p": float(win[m].mean()) if m.any() else None, "mean": float(net[m].mean()) if m.any() else None})
    mean = float(net.mean())
    edge = bool(lb is not None and lb > 0.5 and mean > 0 and all(h["p"] is not None and h["p"] > 0.5 and h["mean"] > 0 for h in halves))
    liq = [mae >= g / 100 for g in grid]
    return {"n": n, "n_eff": eff, "p": p, "ci": list(ci), "lb_bonf": lb, "mean": mean, "median": float(np.median(net)),
            "p10": float(np.quantile(net, 0.10)), "halves": halves, "edge": edge,
            "lev": {"liq": [float(x.mean()) for x in liq], "win": [float((~x & win).mean()) for x in liq],
                    "mean": [float(np.where(x, 0.0, net).mean()) for x in liq]}}


def cell_masks(s: pd.DataFrame) -> dict[str, np.ndarray]:
    return {c: (np.ones(len(s), dtype=bool) if spec_ is None else (s[spec_[0]] == spec_[1]).to_numpy())
            for c, spec_ in CELLS.items()}


def evaluate(s: pd.DataFrame, o: pd.DataFrame, H: int, cfg: dict) -> dict:
    """Every cell-side of one horizon over the decision times with all states and a known outcome."""
    z_b, _ = z_bonferroni(cfg)
    grid = cfg["leverage"]["grid_pct"]
    ok = s[list(STATES)].notna().all(axis=1).to_numpy() & o[["long", "short", "mae_long", "mae_short"]].notna().all(axis=1).to_numpy()
    pos_all = np.arange(len(s))[ok]
    if not len(pos_all):
        return {"n": 0, "cells": {}}
    times = s.index[ok]
    split = times[len(times) // 2]
    first_all = times < split
    sv = s[ok]
    cells = {}
    for name, m in cell_masks(sv).items():
        if name not in cfg["cells"]:
            continue
        cells[name] = {side: side_stats(o[side].to_numpy()[ok][m], o[f"mae_{side}"].to_numpy()[ok][m], pos_all[m], first_all[m], H, z_b, grid)
                       for side in SIDES}
    return {"n": int(ok.sum()), "from": times[0].strftime("%Y-%m-%d %H:%M"), "split": split.strftime("%Y-%m-%d %H:%M"),
            "to": times[-1].strftime("%Y-%m-%d %H:%M"), "cells": cells}


def matched(row: pd.Series) -> list[str]:
    """Cells whose condition holds in one row of states (moc always; none when a state is unknown)."""
    return ["moc"] + [c for c, sp in CELLS.items() if sp is not None and row.get(sp[0]) == sp[1]]


def decide(cells: dict, names: list[str]) -> dict:
    """Registered verdict from the matching cells: an edge on exactly one side → that side, else no trade. The shown chance
    is the matching cell with the highest Bonferroni lower bound (moc when none of the condition cells matches)."""
    out = {"cells": names}
    for side in SIDES:
        cand = [(cells[c][side].get("lb_bonf") or 0.0, c) for c in names if c in cells and cells[c][side].get("n")]
        best = max(cand)[1] if cand else None
        out[side] = {"cell": best, "p": cells[best][side]["p"] if best else None, "ci": cells[best][side]["ci"] if best else None,
                     "edge": [c for c in names if c in cells and cells[c][side].get("edge")]}
    lo, sh = bool(out["long"]["edge"]), bool(out["short"]["edge"])
    out["verdict"] = "nen_long" if lo and not sh else "nen_short" if sh and not lo else "khong"
    return out


# ----- everything at once -----
def build(cfg: dict, end: pd.Timestamp | None = None) -> dict:
    """Candles, funding, states and outcomes for both units (hourly / daily)."""
    h = hourly(cfg, end)
    rate, mark, last_f = funding(h.index, end)
    f24 = funding_24h(rate, mark, last_f)
    fst = funding_state(f24, cfg)
    d = daily(h)
    return {"h": h, "d": d, "rate": rate, "last_f": last_f, "f24": f24, "fstate": fst}


def unit_frames(b: dict, unit: str, H: int, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """States and outcomes of one horizon on its own candles."""
    d, per_day, hours = (b["h"], 24, H) if unit == "h" else (b["d"], 1, 24 * H)
    cache = b.setdefault("_base", {})
    if unit not in cache:
        cache[unit] = base_states(d["close"], per_day, cfg).assign(funding=b["fstate"].reindex(d.index).to_numpy())
    s = cache[unit].assign(stretch=stretch_state(d["close"], H, per_day, cfg))
    return s, outcomes(d, H, hours, b["rate"], b["last_f"], cfg)


def run(write: bool = True, end: pd.Timestamp | None = None) -> dict:
    """Everything the page shows (KN.perp); `end` cuts the data (frozen fixtures for the page tests)."""
    cfg = spec()
    b = build(cfg, end)
    z_b, m = z_bonferroni(cfg)
    out = {"version": version(cfg), "z_bonf": z_b, "tests": m, "costs": cfg["costs"], "mmr": cfg["leverage"]["mmr"],
           "grid_pct": cfg["leverage"]["grid_pct"], "funding_last": b["last_f"].strftime("%Y-%m-%d %H:%M") if b["last_f"] is not None else None,
           "horizons": [], "now": {}, "thresholds": {}}
    for unit in ("h", "d"):
        d = b["h"] if unit == "h" else b["d"]
        c = d["close"]
        T = c.dropna().index[-1]
        hs = [H for u, H in horizons(cfg) if u == unit]
        out["thresholds"][unit] = thresholds(c.loc[:T], b["f24"].loc[:T], hs, 24 if unit == "h" else 1, cfg)
        out["now"][unit] = {"anchor": T.strftime("%Y-%m-%d %H:%M"), "close": float(c.loc[T]), "states": {}}
        for H in hs:
            s, o = unit_frames(b, unit, H, cfg)
            ev = evaluate(s, o, H, cfg)
            out["horizons"].append({"unit": unit, "h": H, **ev})
            now = s.loc[T]
            out["now"][unit]["states"][str(H)] = {"state": {k: now[k] for k in STATES}, **decide(ev["cells"], matched(now))}
    out["log"] = score_log(b, cfg)
    if write:
        (DATA / "results").mkdir(exist_ok=True)
        (DATA / "results" / "perp.json").write_text(json.dumps(compact(out), ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    return out


def compact(out: dict) -> dict:
    """What the page embeds: 4 decimals (0,01%), thresholds 8 (funding rates are around 0,0001)."""
    return {**_round({k: v for k, v in out.items() if k != "thresholds"}), "thresholds": _round(out["thresholds"], 8)}


def _round(x, nd: int = 4):
    if isinstance(x, float):
        return None if not np.isfinite(x) else round(x, nd)
    if isinstance(x, dict):
        return {k: _round(v, nd) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v, nd) for v in x]
    return x


# ----- forward log (new final test period from 03/11/2026) -----
def read_log(path: Path = LOG) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def log_today(res: dict, b: dict, cfg: dict, now: pd.Timestamp, path: Path = LOG) -> list[dict]:
    """Append once per day anchor and version, at the last daily close, every horizon whose end is still ahead.
    Never rewrites or back-fills."""
    path = Path(path)
    v = res["version"]
    T = b["d"]["close"].dropna().index[-1]
    if any(r["issued"] == T.strftime("%Y-%m-%d %H:%M") and r["version"] == v for r in read_log(path)):
        return []
    ev = {(e["unit"], e["h"]): e for e in res["horizons"]}
    rows = []
    for unit, H in horizons(cfg):
        target = T + (H * HOUR if unit == "h" else pd.Timedelta(days=H))
        if target <= now:
            continue
        s, _ = unit_frames(b, unit, H, cfg)
        if T not in s.index:
            continue
        dec = decide(ev[(unit, H)]["cells"], matched(s.loc[T]))
        rows.append({"issued": T.strftime("%Y-%m-%d %H:%M"), "unit": unit, "h": H, "target": target.strftime("%Y-%m-%d %H:%M"),
                     "price": f"{float(b['h']['close'].loc[T]):.2f}", "cells": "|".join(dec["cells"]),
                     "p_long": "" if dec["long"]["p"] is None else f"{dec['long']['p']:.4f}",
                     "p_short": "" if dec["short"]["p"] is None else f"{dec['short']['p']:.4f}",
                     "verdict": dec["verdict"], "version": v, "logged_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")})
    if not rows:
        return []
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLS)
        if new:
            w.writeheader()
        w.writerows(rows)
    return rows


def score_log(b: dict, cfg: dict, path: Path = LOG) -> dict:
    """Live check: logged rows whose horizon has passed and whose funding is known; was the long / short profitable."""
    rows = read_log(path)
    h, rate, last_f = b["h"], b["rate"], b["last_f"]
    cost = 2 * (cfg["costs"]["fee"] + cfg["costs"]["slippage"])
    cum = rate.cumsum()
    done = []
    for r in rows:
        t0, t1 = pd.Timestamp(r["issued"]), pd.Timestamp(r["target"])
        if t1 not in h.index or t0 not in h.index or pd.isna(h["close"].loc[t1]) or last_f is None or t1 >= last_f + FUNDING_EVERY:
            continue
        ret = float(h["close"].loc[t1]) / float(r["price"]) - 1
        f = float(cum.loc[t1] - cum.loc[t0])
        done.append({**r, "long_net": ret - cost - f, "short_net": -ret - cost + f})
    out = {"rows": len(rows), "matured": len(done), "versions": {}}
    for v in sorted({r["version"] for r in done}):
        x = [r for r in done if r["version"] == v]
        called = [r for r in x if r["verdict"] in ("nen_long", "nen_short")]
        hit = sum((r["long_net"] if r["verdict"] == "nen_long" else r["short_net"]) > 0 for r in called)
        out["versions"][v] = {"matured": len(x), "called": len(called), "called_hit": int(hit),
                              "long_win": float(np.mean([r["long_net"] > 0 for r in x])), "short_win": float(np.mean([r["short_net"] > 0 for r in x]))}
    out["first_due"] = min((r["target"] for r in rows), default=None) if not done else None
    return out


def utc_now() -> pd.Timestamp:
    return pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
