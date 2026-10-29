"""Daily BTC price bands for the next 1–7 days and 30 days (settings in config/candidates.yaml, section forecast).

Not a direction forecast: the k-day log return, divided by (30-day daily volatility × √k), has a distribution that is
read from the 4 years before the anchor day (only windows whose outcome is already known), and is scaled back with the
current volatility. Quantiles 10/25/50/75/90 give the 80% band, the 50% band and the middle. The same rolling
computation gives the walk-forward check since 2018 (how often the real close fell inside each band), and a daily
append-only log lets anyone verify the live forecasts when their day comes.
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

LOG = DATA / "forecast" / "forecast_log.csv"
LOG_COLS = ["issued", "target", "k", "price", "q10", "q25", "q50", "q75", "q90", "version", "logged_at"]


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["forecast"]


def version(cfg: dict) -> str:
    code = (ROOT / "bot" / "models" / "price_forecast.py").read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def daily_prices(end: pd.Timestamp | None = None) -> pd.Series:
    """Coin Metrics daily close (row d = close of day d), on a gap-free calendar so shifts are in days."""
    from bot.data import pit_store as ps
    cm = ps.load_history("coinmetrics")
    s = cm.assign(date=pd.to_datetime(cm["date"])).drop_duplicates("date", keep="last").set_index("date")["price"].astype(float).sort_index().dropna()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))
    return s if end is None else s[s.index <= end]


def bands(p: pd.Series, k: int, cfg: dict, scaled: bool = True) -> pd.DataFrame:
    """Price quantiles for day T + k, for every anchor day T, using prices up to T only."""
    lr = np.log(p).diff()
    sig = lr.rolling(cfg["vol_days"], min_periods=cfg["vol_days"]).std()
    rk = np.log(p.shift(-k) / p)
    z = rk / (sig * np.sqrt(k)) if scaled else rk
    known = z.shift(k)  # at T: the standardised return of T − k, whose outcome is the price of T
    out = {}
    for q in cfg["quantiles"]:
        qz = known.rolling(cfg["window_days"] - k, min_periods=cfg["min_obs"]).quantile(q)
        out[f"q{int(round(q * 100))}"] = p * np.exp(qz * sig * np.sqrt(k) if scaled else qz)
    return pd.DataFrame(out, index=p.index)


def forecast(p: pd.Series, cfg: dict) -> dict:
    """Bands from the last anchor day of `p`."""
    T = p.dropna().index[-1]
    rows = []
    for k in cfg["horizons_days"]:
        b = bands(p.loc[:T], k, cfg).loc[T]
        rows.append({"k": int(k), "target": (T + pd.Timedelta(days=k)).strftime("%Y-%m-%d"), **{c: float(b[c]) for c in b.index}})
    return {"anchor": T.strftime("%Y-%m-%d"), "price": float(p.loc[T]), "rows": rows}


def check(p: pd.Series, cfg: dict) -> dict:
    """Walk-forward coverage of the 50% and 80% bands since check_from, per horizon; Wilson by independent windows."""
    start = pd.Timestamp(str(cfg["check_from"]))
    out = {}
    for k in cfg["horizons_days"]:
        actual = p.shift(-k)
        res = {}
        for name, scaled in (("vol", True), ("raw", False)):
            b = bands(p, k, cfg, scaled)
            m = (p.index >= start) & actual.notna().to_numpy() & b["q10"].notna().to_numpy()
            a, bb = actual[m], b[m]
            in80, in50 = ((a >= bb["q10"]) & (a <= bb["q90"])), ((a >= bb["q25"]) & (a <= bb["q75"]))
            n = int(m.sum())
            eff = max(1, n // k)
            res[name] = {"n": n, "n_eff": eff, "cover80": float(in80.mean()), "cover50": float(in50.mean()),
                         "cover80_ci": list(wilson(round(float(in80.mean()) * eff), eff)), "cover50_ci": list(wilson(round(float(in50.mean()) * eff), eff)),
                         "above_median": float((a > bb["q50"]).mean()), "width80": float(((bb["q90"] - bb["q10"]) / p[m]).median()),
                         "from": a.index[0].strftime("%Y-%m-%d") if n else None, "to": a.index[-1].strftime("%Y-%m-%d") if n else None}
        out[int(k)] = res
    return out


def read_log(path: Path = LOG) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def log_today(p: pd.Series, cfg: dict, now: pd.Timestamp, path: Path = LOG) -> list[dict]:
    """Append today's forecast once per anchor day and version, only for target days whose close is still ahead
    (the close of day d is known at d + 1 00:00 UTC). Never rewrites or back-fills."""
    path = Path(path)
    v = version(cfg)
    fc = forecast(p, cfg)
    if any(r["issued"] == fc["anchor"] and r["version"] == v for r in read_log(path)):
        return []
    rows = [{"issued": fc["anchor"], "target": r["target"], "k": r["k"], "price": f"{fc['price']:.2f}",
             **{q: f"{r[q]:.2f}" for q in ("q10", "q25", "q50", "q75", "q90")}, "version": v, "logged_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
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


def score_log(p: pd.Series, path: Path = LOG, recent: int = 12) -> dict:
    """Live verification: rows whose target close is known, hits of the 50% and 80% bands, per version."""
    rows = read_log(path)
    done = []
    for r in rows:
        t = pd.Timestamp(r["target"])
        a = p.get(t, np.nan) if t in p.index else np.nan
        if np.isfinite(a):
            done.append({**r, "actual": float(a), "in80": bool(float(r["q10"]) <= a <= float(r["q90"])), "in50": bool(float(r["q25"]) <= a <= float(r["q75"]))})
    out = {"rows": len(rows), "matured": len(done), "versions": {}}
    for v in sorted({r["version"] for r in done}):
        d = [r for r in done if r["version"] == v]
        out["versions"][v] = {"matured": len(d), "in80": int(sum(r["in80"] for r in d)), "in50": int(sum(r["in50"] for r in d))}
    out["recent"] = [{k: r[k] for k in ("issued", "target", "k", "q10", "q25", "q75", "q90", "actual", "in80", "in50", "version")}
                     for r in sorted(done, key=lambda r: (r["target"], int(r["k"])))[-recent:]]
    out["first_due"] = min((r["target"] for r in rows), default=None) if not done else None
    return out


def for_report(now: pd.Timestamp | None = None) -> dict:
    cfg = spec()
    p = daily_prices()
    out = forecast(p, cfg)
    out["version"] = version(cfg)
    out["check"] = check(p, cfg)
    out["log"] = score_log(p)
    return out


def utc_now() -> pd.Timestamp:
    return pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
