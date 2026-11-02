"""Picking the selling price and day at lookup time (settings in config/candidates.yaml, section exit).

The other face of bot/models/entry_timing.py, on the daily HIGH of the Bitstamp candles. Not a direction forecast:
(A) highest price of the next k days: z = log(max high of candles T+1..T+k / close T) / (30-day daily volatility × √k);
    its 99 percentiles in the 4 years before T (only windows whose last candle is ≤ T) give the band of the highest
    price and the chance of touching any higher price (a resting sell order, taking profit);
(B) wait or sell now: a sell order at close × (1 + x) kept k days, else sell at the close of T + k, against selling at
    the close of T, over every day since check_from, block bootstrap, Holm over the 20 configurations;
(C) which of the next 7 days has the highest high: share of each position in the 4 years before T, and against 1/7
    in both halves since check_from.
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

from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.models.entry_timing import LEVELS, SHOW, TRUST, _boot_mean, sigma, touch_prob

LOG = DATA / "exit" / "exit_log.csv"
LOG_COLS = ["issued", "target", "k", "price", "sigma", "q10", "q25", "q50", "q75", "q90", "version", "logged_at"]


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["exit"]


def version(cfg: dict) -> str:
    """Hash of the settings and of the code that computes the numbers (this module and the helpers it shares)."""
    code = b"".join((ROOT / "bot" / "models" / f).read_bytes().replace(b"\r\n", b"\n") for f in ("exit_timing.py", "entry_timing.py"))
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def candles(end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Bitstamp daily high and close (row d = candle opening d 00:00 UTC), on a gap-free calendar.
    A high that is not positive or below the close is treated as missing."""
    from bot.data import pit_store as ps
    b = ps.load_history("bitstamp")
    d = b.assign(date=pd.to_datetime(b["date"])).drop_duplicates("date", keep="last").set_index("date")[["high", "close"]].astype(float).sort_index()
    d.loc[(d["high"] <= 0) | (d["high"] < d["close"]), "high"] = np.nan
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="D"))
    return d if end is None else d[d.index <= end]


def next_max(high: pd.Series, k: int) -> pd.Series:
    """Highest high of the candles T+1..T+k, at row T (NaN when one of them is missing or not there yet)."""
    v = high.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    if len(v) > k:
        out[:len(v) - k] = np.lib.stride_tricks.sliding_window_view(v[1:], k).max(axis=1)
    return pd.Series(out, index=high.index)


def z_quantiles(d: pd.DataFrame, k: int, cfg: dict, levels=LEVELS, scaled: bool = True) -> pd.DataFrame:
    """Quantiles of z for every anchor day T, from windows whose last candle is ≤ T (columns = levels)."""
    sig = sigma(d["close"], cfg)
    z = np.log(next_max(d["high"], k) / d["close"])
    if scaled:
        z = z / (sig * np.sqrt(k))
    known = z.shift(k)  # at T: the window of T − k, whose last candle is T
    roll = known.rolling(cfg["window_days"] - k, min_periods=cfg["min_obs"])
    return pd.DataFrame({float(q): roll.quantile(float(q)) for q in levels}, index=d.index)


def touch_up(thr: np.ndarray, qz: np.ndarray) -> np.ndarray:
    """P(z ≥ thr) = 1 − P(z ≤ thr); held at 99% below the 1% percentile and at 1% above the 99% one."""
    return 1 - touch_prob(thr, qz)


def forecast(d: pd.DataFrame, cfg: dict) -> dict:
    """Today's numbers from the last closed candle of `d`: percentiles of z, band of the highest price, touch chances."""
    T = d["close"].dropna().index[-1]
    d = d.loc[:T]
    s = float(sigma(d["close"], cfg).loc[T])
    c = float(d["close"].loc[T])
    rows = []
    for k in cfg["horizons_days"]:
        qz = z_quantiles(d, k, cfg).loc[T].to_numpy()
        sk = s * np.sqrt(k)
        band = {f"q{p}": c * float(np.exp(qz[p - 1] * sk)) for p in SHOW}
        probs = {f"{x:.2f}": float(touch_up(np.array([np.log(1 + x) / sk]), qz[None, :])[0]) for x in cfg["touch"]["show_premiums"]}
        rows.append({"k": int(k), "target": (T + pd.Timedelta(days=k)).strftime("%Y-%m-%d"), "z": [round(float(x), 4) for x in qz], **band, "probs": probs})
    return {"anchor": T.strftime("%Y-%m-%d"), "price": c, "sigma": s, "rows": rows}


def check(d: pd.DataFrame, cfg: dict) -> dict:
    """Walk-forward since check_from, per horizon: coverage of each percentile of the highest price, the touch chance of
    every shown premium against the touch rate, and Brier against the same method without the volatility scaling."""
    start = pd.Timestamp(str(cfg["check_from"]))
    sig = sigma(d["close"], cfg)
    out = {}
    for k in cfg["horizons_days"]:
        m = next_max(d["high"], k)
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
        c80 = float(((zv >= Qv[:, 9]) & (zv <= Qv[:, 89])).mean())
        probs = []
        for x in cfg["touch"]["show_premiums"]:
            y = (zr >= np.log(1 + x)).astype(float)
            pv = touch_up(np.log(1 + x) / sk, Qv)
            pr = touch_up(np.full(n, np.log(1 + x)), Qr)
            hit = float(y.mean())
            probs.append({"x": float(x), "pred": float(pv.mean()), "actual": hit, "ci": list(wilson(round(hit * eff), eff)),
                          "brier": float(((pv - y) ** 2).mean()), "brier_raw": float(((pr - y) ** 2).mean())})
        lo, hi = TRUST
        out[int(k)] = {"n": n, "n_eff": eff, "from": d.index[ok][0].strftime("%Y-%m-%d"), "to": d.index[ok][-1].strftime("%Y-%m-%d"),
                       "cover": cover, "cover80": c80, "cover80_ci": list(wilson(round(c80 * eff), eff)), "trusted": bool(lo <= c80 <= hi),
                       "probs": probs, "brier": float(np.mean([p["brier"] for p in probs])), "brier_raw": float(np.mean([p["brier_raw"] for p in probs]))}
    return out


def wait(d: pd.DataFrame, cfg: dict, n_boot: int = 2000, seed: int = 0) -> dict:
    """(B) every day since check_from: a sell order at close × (1 + x) for k days, else sell at the close of T + k; gain =
    price got / close T − 1 against selling now. Bootstrap mean, two-sided p, Holm over all configurations, halves."""
    w = cfg["wait"]
    start = pd.Timestamp(str(cfg["check_from"]))
    c = d["close"]
    rows = []
    for k in w["days"]:
        m, later = next_max(d["high"], k), c.shift(-k)
        ok = (d.index >= start) & m.notna().to_numpy() & later.notna().to_numpy() & c.notna().to_numpy()
        for x in w["premiums"]:
            order = (c * (1 + x))[ok].to_numpy()
            filled = m[ok].to_numpy() >= order
            got = np.where(filled, order, later[ok].to_numpy())
            g = got / c[ok].to_numpy() - 1
            n, half = len(g), len(g) // 2
            bm = _boot_mean(g, k, n_boot, seed)
            p = min(1.0, max(1.0 / n_boot, 2 * min(float((bm <= 0).mean()), float((bm >= 0).mean()))))
            rows.append({"x": float(x), "k": int(k), "n": n, "n_eff": max(1, n // k), "mean": float(g.mean()),
                         "ci": [float(np.quantile(bm, 0.025)), float(np.quantile(bm, 0.975))], "median": float(np.median(g)),
                         "p10": float(np.quantile(g, 0.10)), "fill": float(filled.mean()), "better": float((g > 0).mean()),
                         "mean_h1": float(g[:half].mean()), "mean_h2": float(g[half:].mean()), "p": p,
                         "from": d.index[ok][0].strftime("%Y-%m-%d"), "split": d.index[ok][half].strftime("%Y-%m-%d"), "to": d.index[ok][-1].strftime("%Y-%m-%d")})
    run, M = 0.0, len(rows)
    for i, j in enumerate(np.argsort([r["p"] for r in rows])):  # Holm step-down, kept monotone
        run = max(run, min(1.0, (M - i) * rows[j]["p"]))
        rows[j]["p_holm"] = run
    for r in rows:
        sig_ = r["p_holm"] < 0.05
        r["verdict"] = "cho" if sig_ and r["mean_h1"] > 0 and r["mean_h2"] > 0 else "ngay" if sig_ and r["mean_h1"] < 0 and r["mean_h2"] < 0 else "chua"
    return {"rows": rows, "n_configs": M}


def highest_day(high: pd.Series, days: int) -> pd.Series:
    """Position 1..days of the candle with the highest high among T+1..T+days, at row T (NaN when unknown)."""
    v = high.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    if len(v) > days:
        win = np.lib.stride_tricks.sliding_window_view(v[1:], days)
        good = np.isfinite(win).all(axis=1)
        out[:len(v) - days][good] = win[good].argmax(axis=1) + 1
    return pd.Series(out, index=high.index)


def day_shares(high: pd.Series, cfg: dict) -> pd.DataFrame:
    """Share of each position among the windows known at T (last candle ≤ T), over the 4 years before T."""
    days = cfg["highest_day"]["days"]
    known = highest_day(high, days).shift(days)
    out = {}
    for j in range(1, days + 1):
        hit = (known == j).astype(float).where(known.notna())
        out[j] = hit.rolling(cfg["window_days"] - days, min_periods=cfg["min_obs"]).mean()
    return pd.DataFrame(out, index=high.index)


def highest(d: pd.DataFrame, cfg: dict, touch_now: dict) -> dict:
    """(C) today's share of each of the next 7 days, and the realised positions in both halves since check_from."""
    days = cfg["highest_day"]["days"]
    T = d["close"].dropna().index[-1]
    sh = day_shares(d["high"].loc[:T], cfg).loc[T]
    nxt = [{"pos": j, "date": (T + pd.Timedelta(days=j)).strftime("%Y-%m-%d"), "share": float(sh[j])} for j in range(1, days + 1)]
    pos = highest_day(d["high"], days)
    start = pd.Timestamp(str(cfg["check_from"]))
    real = pos[(pos.index >= start) & pos.notna().to_numpy()]
    half = len(real) // 2
    halves = []
    for part in (real.iloc[:half], real.iloc[half:]):
        eff = max(1, len(part) // days)
        s = [float((part == j).mean()) for j in range(1, days + 1)]
        halves.append({"from": part.index[0].strftime("%Y-%m-%d"), "to": part.index[-1].strftime("%Y-%m-%d"), "n": len(part), "n_eff": eff,
                       "shares": s, "ci": [list(wilson(round(x * eff), eff)) for x in s]})
    standout = [j for j in range(1, days + 1) if all(h["ci"][j - 1][0] is not None and h["ci"][j - 1][0] > 1 / days for h in halves)]
    return {"days": nxt, "none_above": 1 - touch_now.get("0.00", np.nan), "halves": halves, "standout": standout}


def read_log(path: Path = LOG) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def log_today(d: pd.DataFrame, cfg: dict, now: pd.Timestamp, path: Path = LOG) -> list[dict]:
    """Append today's band of the highest price once per anchor day and version, only for horizons whose last candle is
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
    """Live check: rows whose k candles have all closed; did the real highest price fall in the 80% and 50% bands."""
    rows = read_log(path)
    high = d["high"]
    done = []
    for r in rows:
        a0, t = pd.Timestamp(r["issued"]) + pd.Timedelta(days=1), pd.Timestamp(r["target"])
        seg = high[(high.index >= a0) & (high.index <= t)]
        if len(seg) == int(r["k"]) and seg.notna().all():
            a = float(seg.max())
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
    """Everything the page shows (KN.exit); `end` cuts the candles (frozen fixtures for the page tests)."""
    cfg = spec()
    d = candles(end)
    out = forecast(d, cfg)
    by_k = {r["k"]: r for r in out["rows"]}
    out["version"] = version(cfg)
    out["check"] = check(d, cfg)
    out["wait"] = wait(d, cfg)  # 2000 resamples, seed 0 (registered)
    out["highest"] = highest(d, cfg, by_k[cfg["highest_day"]["days"]]["probs"])
    out["log"] = score_log(d)
    if write:
        (DATA / "results" / "exit.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return out


def utc_now() -> pd.Timestamp:
    return pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
