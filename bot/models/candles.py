"""Classic candlestick patterns on Bitstamp daily candles (config/candidates.yaml, section candles; registered before any
number was computed).

Twelve textbook patterns (engulfing, hammer, shooting star, doji after a fall / rise, morning / evening star, three white
soldiers / black crows, piercing line, dark cloud cover) with fixed thresholds, each with the direction it is said to
announce. A pattern seen at day T uses only the candles up to T. For 1, 3 and 7 days: how often the move went the
announced way on independent occurrences (at least k days apart), against the same share on any day of the period
(one-sided binomial test), Holm over 12 patterns × 3 horizons, both halves, at least 30 occurrences.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import binom

from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, load_yaml

MIN_N = 30


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["candles"]


def direction(cfg: dict) -> dict[str, int]:
    """+1 for a pattern said to announce a rise, −1 for a fall (first word of its registered definition)."""
    return {name: (1 if text.strip().startswith("tăng") else -1) for name, text in cfg["patterns"].items()}


def load(end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Bitstamp daily open, high, low, close on a gap-free calendar (a missing day stays NaN)."""
    from bot.data import pit_store as ps
    b = ps.load_history("bitstamp")
    d = b.assign(date=pd.to_datetime(b["date"])).drop_duplicates("date", keep="last").set_index("date")[["open", "high", "low", "close"]]
    d = d.astype(float).sort_index()
    d = d[(d > 0).all(axis=1)]
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="D"))
    return d if end is None else d[d.index <= end]


def detect(d: pd.DataFrame) -> pd.DataFrame:
    """True at T when the pattern is complete at the close of T (candles up to T only; a missing candle → False)."""
    O, H, L, C = (d[k] for k in ("open", "high", "low", "close"))
    body, rng = (C - O).abs(), H - L
    up_sh, lo_sh = H - np.maximum(O, C), np.minimum(O, C) - L
    bull, bear = C > O, C < O
    sma = C.shift(1).rolling(10, min_periods=10).mean()
    down, upt = C.shift(1) < sma, C.shift(1) > sma
    s = lambda x, n: x.shift(n)  # noqa: E731
    sb = lambda x, n: x.shift(n, fill_value=False).astype(bool)  # noqa: E731
    O1, C1, H1, L1, O2, C2 = s(O, 1), s(C, 1), s(H, 1), s(L, 1), s(O, 2), s(C, 2)
    body1, body2, rng2 = s(body, 1), s(body, 2), s(rng, 2)
    bull1, bear1, bull2, bear2 = sb(bull, 1), sb(bear, 1), sb(bull, 2), sb(bear, 2)
    doji = (rng > 0) & (body <= 0.1 * rng)
    out = {
        "nhan_chim_tang": down & bear1 & bull & (O <= C1) & (C >= O1),
        "nhan_chim_giam": upt & bull1 & bear & (O >= C1) & (C <= O1),
        "bua": down & (body > 0) & (lo_sh >= 2 * body) & (up_sh <= 0.5 * body),
        "sao_bang": upt & (body > 0) & (up_sh >= 2 * body) & (lo_sh <= 0.5 * body),
        "doji_sau_giam": down & doji,
        "doji_sau_tang": upt & doji,
        "sao_mai": sb(down, 2) & bear2 & (body2 >= 0.6 * rng2) & (body1 <= 0.3 * body2) & bull & (C > (O2 + C2) / 2),
        "sao_hom": sb(upt, 2) & bull2 & (body2 >= 0.6 * rng2) & (body1 <= 0.3 * body2) & bear & (C < (O2 + C2) / 2),
        "ba_chang_trang": bull2 & bull1 & bull & (C1 > C2) & (C > C1) & (O1 >= O2) & (O1 <= C2) & (O >= O1) & (O <= C1),
        "ba_qua_den": bear2 & bear1 & bear & (C1 < C2) & (C < C1) & (O1 <= O2) & (O1 >= C2) & (O <= O1) & (O >= C1),
        "xuyen_tang": down & bear1 & (O < L1) & (C > (O1 + C1) / 2) & (C < O1),
        "may_den": upt & bull1 & (O > H1) & (C < (O1 + C1) / 2) & (C > O1),
    }
    return pd.DataFrame({k: v.fillna(False).astype(bool) for k, v in out.items()}, index=d.index)


def _spaced(pos: np.ndarray, k: int) -> np.ndarray:
    """Occurrences at least k days apart: take the earliest, skip those within k days after it, repeat."""
    keep, nxt = [], -10 ** 9
    for p in pos:
        if p >= nxt:
            keep.append(p)
            nxt = p + k
    return np.asarray(keep, dtype=int)


def holm(pvals: dict) -> dict:
    keys = sorted(pvals, key=lambda x: pvals[x])
    m, run, out = len(keys), 0.0, {}
    for i, key in enumerate(keys):
        run = max(run, min(1.0, (m - i) * pvals[key]))
        out[key] = run
    return out


def evaluate(d: pd.DataFrame, flags: pd.DataFrame, cfg: dict) -> dict:
    """Every pattern and horizon: hits on independent occurrences against the share of any day, halves, Holm."""
    dirs, C = direction(cfg), d["close"]
    start = pd.Timestamp(str(cfg["eval_from"]))
    res, pv = {}, {}
    for k in [int(x) for x in cfg["horizons_days"]]:
        r = (C.shift(-k) / C - 1).to_numpy()
        known = np.isfinite(r) & (d.index >= start)
        idx = np.flatnonzero(known)
        if not len(idx):
            continue
        half = idx[len(idx) // 2]
        base = {1: float((r[known] > 0).mean()), -1: float((r[known] < 0).mean())}
        base_h = [{s: float(((r[idx[idx < half]] * s) > 0).mean()) for s in (1, -1)},
                  {s: float(((r[idx[idx >= half]] * s) > 0).mean()) for s in (1, -1)}]
        for name, sgn in dirs.items():
            pos = _spaced(np.flatnonzero(flags[name].to_numpy() & known), k)
            hit = (r[pos] * sgn) > 0
            n, h = len(pos), int(hit.sum())
            p = float(binom.sf(h - 1, n, base[sgn])) if n else 1.0
            first, second = hit[pos < half], hit[pos >= half]
            res.setdefault(name, {"dir": sgn, "per_k": {}})["per_k"][str(k)] = {
                "n": n, "hits": h, "rate": h / n if n else None, "ci": list(wilson(h, n)) if n else [None, None], "base": base[sgn], "p": p,
                "halves": [float(first.mean()) if len(first) else None, base_h[0][sgn], float(second.mean()) if len(second) else None, base_h[1][sgn]]}
            pv[(name, str(k))] = p
    adj = holm(pv)
    for (name, k), a in adj.items():
        x = res[name]["per_k"][k]
        h = x["halves"]
        x["holm"] = a
        x["few"] = x["n"] < MIN_N
        x["edge"] = bool(not x["few"] and a < 0.05 and h[0] is not None and h[2] is not None and h[0] > h[1] and h[2] > h[3])
    return res


def run(write: bool = False, end: pd.Timestamp | None = None) -> dict:
    """Patterns today (last closed Bitstamp candle), their history and the registered verdict."""
    cfg = spec()
    d = load(end)
    f = detect(d)
    T = d["close"].dropna().index[-1]
    ev = evaluate(d, f, cfg)
    for name in ev:
        ev[name]["count"] = int(f[name].sum())
    out = {"anchor": T.strftime("%Y-%m-%d"), "today": [n for n in f.columns if bool(f.loc[T, n])], "patterns": ev,
           "tests": len(cfg["patterns"]) * len(cfg["horizons_days"]), "from": str(cfg["eval_from"]),
           "edges": sorted({n for n, x in ev.items() for v in x["per_k"].values() if v.get("edge")})}
    if write:
        (DATA / "results").mkdir(exist_ok=True)
        (DATA / "results" / "candles.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    return out


def ml_flags(f: pd.DataFrame) -> pd.DataFrame:
    """The 11 pattern flags the learned model uses (both doji merged into one), as 0/1."""
    g = f.drop(columns=["doji_sau_giam", "doji_sau_tang"]).astype(float)
    g["doji"] = (f["doji_sau_giam"] | f["doji_sau_tang"]).astype(float)
    return g
