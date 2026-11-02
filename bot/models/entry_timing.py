"""Picking the buying price and day at lookup time (settings in config/candidates.yaml, section entry).

Not a direction forecast. Three measurements of how low the price may go, on Bitstamp daily candles (they carry the
day's low):
(A) lowest price of the next k days: z = log(min low of candles T+1..T+k / close T) / (30-day daily volatility × √k);
    its 99 percentiles in the 4 years before T (only windows whose last candle is ≤ T) give the band of the lowest
    price and the chance of touching any price (a resting buy order);
(B) wait or buy now: a buy order at close × (1 − x) kept k days, else buy at the close of T + k, against buying at the
    close of T, over every day since check_from, block bootstrap, Holm over the 20 configurations;
(C) which of the next 7 days has the lowest low: share of each position in the 4 years before T, and against 1/7 in
    both halves since check_from.
A daily append-only log lets anyone verify the live bands of (A) when their days come.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml

LOG = DATA / "entry" / "entry_log.csv"
LOG_COLS = ["issued", "target", "k", "price", "sigma", "q10", "q25", "q50", "q75", "q90", "version", "logged_at"]
LEVELS = np.round(np.arange(1, 100) / 100, 2)  # the 99 percentiles shipped to the page
SHOW = (10, 25, 50, 75, 90)
TRUST = (0.75, 0.85)  # the 80% band of the lowest price must cover 75–85% (registered under touch.trust)


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["entry"]


def version(cfg: dict) -> str:
    code = (ROOT / "bot" / "models" / "entry_timing.py").read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def candles(end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Bitstamp daily low and close (row d = candle opening d 00:00 UTC), on a gap-free calendar so shifts are in days.
    A low that is not positive or above the close is treated as missing."""
    from bot.data import pit_store as ps
    b = ps.load_history("bitstamp")
    d = b.assign(date=pd.to_datetime(b["date"])).drop_duplicates("date", keep="last").set_index("date")[["low", "close"]].astype(float).sort_index()
    d.loc[(d["low"] <= 0) | (d["low"] > d["close"]), "low"] = np.nan
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="D"))
    return d if end is None else d[d.index <= end]


def sigma(close: pd.Series, cfg: dict) -> pd.Series:
    return np.log(close).diff().rolling(cfg["vol_days"], min_periods=cfg["vol_days"]).std()


def next_min(low: pd.Series, k: int) -> pd.Series:
    """Lowest low of the candles T+1..T+k, at row T (NaN when one of them is missing or not there yet)."""
    v = low.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    if len(v) > k:
        out[:len(v) - k] = np.lib.stride_tricks.sliding_window_view(v[1:], k).min(axis=1)
    return pd.Series(out, index=low.index)


def z_quantiles(d: pd.DataFrame, k: int, cfg: dict, levels=LEVELS, scaled: bool = True) -> pd.DataFrame:
    """Quantiles of z for every anchor day T, from windows whose last candle is ≤ T (columns = levels)."""
    sig = sigma(d["close"], cfg)
    z = np.log(next_min(d["low"], k) / d["close"])
    if scaled:
        z = z / (sig * np.sqrt(k))
    known = z.shift(k)  # at T: the window of T − k, whose last candle is T
    roll = known.rolling(cfg["window_days"] - k, min_periods=cfg["min_obs"])
    return pd.DataFrame({float(q): roll.quantile(float(q)) for q in levels}, index=d.index)


def touch_prob(thr: np.ndarray, qz: np.ndarray, levels=LEVELS) -> np.ndarray:
    """P(z ≤ thr) by linear interpolation between the quantiles, held at 1% and 99% outside them (row by row)."""
    thr, qz = np.atleast_1d(thr), np.atleast_2d(qz)
    out = np.full(len(thr), np.nan)
    for i in range(len(thr)):
        q = qz[i]
        if np.isfinite(thr[i]) and np.isfinite(q).all():
            out[i] = np.interp(thr[i], q, levels)
    return out


def forecast(d: pd.DataFrame, cfg: dict) -> dict:
    """Today's numbers from the last closed candle of `d`: percentiles of z, band of the lowest price, touch chances."""
    T = d["close"].dropna().index[-1]
    d = d.loc[:T]
    s = float(sigma(d["close"], cfg).loc[T])
    c = float(d["close"].loc[T])
    rows = []
    for k in cfg["horizons_days"]:
        qz = z_quantiles(d, k, cfg).loc[T].to_numpy()
        sk = s * np.sqrt(k)
        band = {f"q{p}": c * float(np.exp(qz[p - 1] * sk)) for p in SHOW}
        probs = {f"{x:.2f}": float(touch_prob(np.array([np.log(1 - x) / sk]), qz[None, :])[0]) for x in cfg["touch"]["show_discounts"]}
        rows.append({"k": int(k), "target": (T + pd.Timedelta(days=k)).strftime("%Y-%m-%d"), "z": [round(float(x), 4) for x in qz], **band, "probs": probs})
    return {"anchor": T.strftime("%Y-%m-%d"), "price": c, "sigma": s, "rows": rows}


def check(d: pd.DataFrame, cfg: dict) -> dict:
    """Walk-forward since check_from, per horizon: coverage of each percentile of the lowest price, the touch chance of
    every shown discount against the touch rate, and Brier against the same method without the volatility scaling."""
    start = pd.Timestamp(str(cfg["check_from"]))
    sig = sigma(d["close"], cfg)
    out = {}
    for k in cfg["horizons_days"]:
        m = next_min(d["low"], k)
        qv, qr = z_quantiles(d, k, cfg), z_quantiles(d, k, cfg, scaled=False)
        ok = (d.index >= start) & m.notna().to_numpy() & qv.notna().all(axis=1).to_numpy() & qr.notna().all(axis=1).to_numpy()
        n = int(ok.sum())
        if not n:
            out[int(k)] = {"n": 0}
            continue
        eff = max(1, n // k)
        sk = (sig * np.sqrt(k))[ok].to_numpy()
        zr = np.log(m[ok] / d["close"][ok]).to_numpy()
        zv = zr / sk
        Qv, Qr = qv[ok].to_numpy(), qr[ok].to_numpy()
        cover = {str(p): float((zv <= Qv[:, p - 1]).mean()) for p in SHOW}
        in80 = (zv >= Qv[:, 9]) & (zv <= Qv[:, 89])
        c80 = float(in80.mean())
        probs = []
        bv = br = 0.0
        for x in cfg["touch"]["show_discounts"]:
            y = (zr <= np.log(1 - x)).astype(float)
            pv = touch_prob(np.log(1 - x) / sk, Qv)
            pr = touch_prob(np.full(n, np.log(1 - x)), Qr)
            hit = float(y.mean())
            probs.append({"x": float(x), "pred": float(pv.mean()), "actual": hit, "ci": list(wilson(round(hit * eff), eff)),
                          "brier": float(((pv - y) ** 2).mean()), "brier_raw": float(((pr - y) ** 2).mean())})
            bv += probs[-1]["brier"]
            br += probs[-1]["brier_raw"]
        lo, hi = TRUST
        out[int(k)] = {"n": n, "n_eff": eff, "from": d.index[ok][0].strftime("%Y-%m-%d"), "to": d.index[ok][-1].strftime("%Y-%m-%d"),
                       "cover": cover, "cover80": c80, "cover80_ci": list(wilson(round(c80 * eff), eff)), "trusted": bool(lo <= c80 <= hi),
                       "probs": probs, "brier": bv / len(probs), "brier_raw": br / len(probs)}
    return out


def _boot_mean(g: np.ndarray, block: float, runs: int, seed: int) -> np.ndarray:
    idx = measure.stationary_indices(len(g), block, runs, np.random.default_rng(seed))
    return g[idx].mean(axis=1)


def wait(d: pd.DataFrame, cfg: dict, n_boot: int = 2000, seed: int = 0) -> dict:
    """(B) every day since check_from: a buy order at close × (1 − x) for k days, else buy at the close of T + k; gain =
    close T / price paid − 1 against buying now. Bootstrap mean, two-sided p, Holm over all configurations, halves."""
    w = cfg["wait"]
    start = pd.Timestamp(str(cfg["check_from"]))
    c = d["close"]
    rows = []
    for k in w["days"]:
        m, later = next_min(d["low"], k), c.shift(-k)
        ok = (d.index >= start) & m.notna().to_numpy() & later.notna().to_numpy() & c.notna().to_numpy()
        for x in w["discounts"]:
            order = (c * (1 - x))[ok].to_numpy()
            filled = m[ok].to_numpy() <= order
            paid = np.where(filled, order, later[ok].to_numpy())
            g = c[ok].to_numpy() / paid - 1
            n, half = len(g), len(g) // 2
            bm = _boot_mean(g, k, n_boot, seed)
            p = min(1.0, max(1.0 / n_boot, 2 * min(float((bm <= 0).mean()), float((bm >= 0).mean()))))
            rows.append({"x": float(x), "k": int(k), "n": n, "n_eff": max(1, n // k), "mean": float(g.mean()),
                         "ci": [float(np.quantile(bm, 0.025)), float(np.quantile(bm, 0.975))], "median": float(np.median(g)),
                         "p10": float(np.quantile(g, 0.10)), "fill": float(filled.mean()), "better": float((g > 0).mean()),
                         "mean_h1": float(g[:half].mean()), "mean_h2": float(g[half:].mean()), "p": p,
                         "from": d.index[ok][0].strftime("%Y-%m-%d"), "split": d.index[ok][half].strftime("%Y-%m-%d"), "to": d.index[ok][-1].strftime("%Y-%m-%d")})
    order_ = np.argsort([r["p"] for r in rows])
    run, M = 0.0, len(rows)
    for i, j in enumerate(order_):  # Holm step-down, kept monotone
        run = max(run, min(1.0, (M - i) * rows[j]["p"]))
        rows[j]["p_holm"] = run
    for r in rows:
        sig_ = r["p_holm"] < 0.05
        r["verdict"] = "cho" if sig_ and r["mean_h1"] > 0 and r["mean_h2"] > 0 else "ngay" if sig_ and r["mean_h1"] < 0 and r["mean_h2"] < 0 else "chua"
    return {"rows": rows, "n_configs": M}


def lowest_day(low: pd.Series, days: int) -> pd.Series:
    """Position 1..days of the candle with the lowest low among T+1..T+days, at row T (NaN when unknown)."""
    v = low.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    if len(v) > days:
        win = np.lib.stride_tricks.sliding_window_view(v[1:], days)
        good = np.isfinite(win).all(axis=1)
        out[:len(v) - days][good] = win[good].argmin(axis=1) + 1
    return pd.Series(out, index=low.index)


def day_shares(low: pd.Series, cfg: dict) -> pd.DataFrame:
    """Share of each position among the windows known at T (last candle ≤ T), over the 4 years before T."""
    days = cfg["cheapest_day"]["days"]
    known = lowest_day(low, days).shift(days)
    out = {}
    for j in range(1, days + 1):
        hit = (known == j).astype(float).where(known.notna())
        out[j] = hit.rolling(cfg["window_days"] - days, min_periods=cfg["min_obs"]).mean()
    return pd.DataFrame(out, index=low.index)


def cheapest(d: pd.DataFrame, cfg: dict, touch_now: dict) -> dict:
    """(C) today's share of each of the next 7 days, and the realised positions in both halves since check_from."""
    days = cfg["cheapest_day"]["days"]
    T = d["close"].dropna().index[-1]
    sh = day_shares(d["low"].loc[:T], cfg).loc[T]
    wd = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    nxt = [{"pos": j, "date": (T + pd.Timedelta(days=j)).strftime("%Y-%m-%d"), "weekday": wd[(T + pd.Timedelta(days=j)).weekday()],
            "share": float(sh[j])} for j in range(1, days + 1)]
    pos = lowest_day(d["low"], days)
    start = pd.Timestamp(str(cfg["check_from"]))
    real = pos[(pos.index >= start) & pos.notna().to_numpy()]
    half = len(real) // 2
    halves = []
    for part in (real.iloc[:half], real.iloc[half:]):
        n = len(part)
        eff = max(1, n // days)
        s = [float((part == j).mean()) for j in range(1, days + 1)]
        halves.append({"from": part.index[0].strftime("%Y-%m-%d"), "to": part.index[-1].strftime("%Y-%m-%d"), "n": n, "n_eff": eff,
                       "shares": s, "ci": [list(wilson(round(x * eff), eff)) for x in s]})
    standout = [j for j in range(1, days + 1) if all(h["ci"][j - 1][0] is not None and h["ci"][j - 1][0] > 1 / days for h in halves)]
    return {"days": nxt, "none_below": 1 - touch_now.get("0.00", np.nan), "halves": halves, "standout": standout}


def read_log(path: Path = LOG) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def log_today(d: pd.DataFrame, cfg: dict, now: pd.Timestamp, path: Path = LOG) -> list[dict]:
    """Append today's band of the lowest price once per anchor day and version, only for horizons whose last candle is
    still open (the candle of day t closes at t + 1 00:00 UTC). Never rewrites or back-fills."""
    path = Path(path)
    v = version(cfg)
    fc = forecast(d, cfg)
    if any(r["issued"] == fc["anchor"] and r["version"] == v for r in read_log(path)):
        return []
    rows = [{"issued": fc["anchor"], "target": r["target"], "k": r["k"], "price": f"{fc['price']:.2f}", "sigma": f"{fc['sigma']:.6f}",
             **{f"q{p}": f"{r[f'q{p}']:.2f}" for p in SHOW}, "version": v, "logged_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
            for r in fc["rows"] if pd.Timestamp(r["target"]) + pd.Timedelta(days=1) > now]
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


def score_log(d: pd.DataFrame, path: Path = LOG, recent: int = 12) -> dict:
    """Live check: rows whose k candles have all closed; did the real lowest price fall in the 80% and 50% bands."""
    rows = read_log(path)
    low = d["low"]
    done = []
    for r in rows:
        a0, t = pd.Timestamp(r["issued"]) + pd.Timedelta(days=1), pd.Timestamp(r["target"])
        seg = low[(low.index >= a0) & (low.index <= t)]
        if len(seg) == int(r["k"]) and seg.notna().all():
            a = float(seg.min())
            done.append({**r, "actual": a, "in80": bool(float(r["q10"]) <= a <= float(r["q90"])), "in50": bool(float(r["q25"]) <= a <= float(r["q75"]))})
    out = {"rows": len(rows), "matured": len(done), "versions": {}}
    for v in sorted({r["version"] for r in done}):
        x = [r for r in done if r["version"] == v]
        out["versions"][v] = {"matured": len(x), "in80": int(sum(r["in80"] for r in x)), "in50": int(sum(r["in50"] for r in x))}
    out["recent"] = [{k: r[k] for k in ("issued", "target", "k", "q10", "q25", "q75", "q90", "actual", "in80", "in50", "version")}
                     for r in sorted(done, key=lambda r: (r["target"], int(r["k"])))[-recent:]]
    out["first_due"] = min((r["target"] for r in rows), default=None) if not done else None
    return out


def run(write: bool = True, end: pd.Timestamp | None = None) -> dict:
    """Everything the page shows (KN.entry); `end` cuts the candles (frozen fixtures for the page tests)."""
    cfg = spec()
    d = candles(end)
    out = forecast(d, cfg)
    by_k = {r["k"]: r for r in out["rows"]}
    out["version"] = version(cfg)
    out["check"] = check(d, cfg)
    out["wait"] = wait(d, cfg)  # 2000 resamples, seed 0 (registered)
    out["cheapest"] = cheapest(d, cfg, by_k[cfg["cheapest_day"]["days"]]["probs"])
    out["log"] = score_log(d)
    if write:
        (DATA / "results" / "entry.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return out


def utc_now() -> pd.Timestamp:
    return pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
