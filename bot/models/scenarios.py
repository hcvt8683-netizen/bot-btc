"""Part F: dynamic price scenarios (settings in config/candidates.yaml, section scenarios).

For a hypothetical price change Δ reached after k weeks (even path on a log scale), synthetic days are appended after
the analysis Sunday and EVERY indicator is recomputed with the same weekly-close builder as the real table:
price-based indicators follow the path exactly; realized cap, supply, daily issuance in BTC and hash rate stay at their
last value (realized cap can instead drift by `rc_change`, used for the band from its past 4-year changes); Fear & Greed
follows a response model estimated on past data only (ΔF&G = a + b·r_k + c·(F&G − 50)), with a 10–90% band from its
residuals. Nothing after the analysis date is used.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.features import weekly_close as wc


def fng_response(t: pd.DataFrame, k: int, until: pd.Timestamp | None = None, band=(0.10, 0.90)) -> dict:
    """OLS of the k-week change of Fear & Greed on the k-week log return and the distance of F&G from 50."""
    d = t if until is None else t[t.index <= until]
    f, p = d["raw_fng"], d["close"]
    df = pd.DataFrame({"dF": f.shift(-k) - f, "r": np.log(p.shift(-k) / p), "lvl": f - 50}).dropna()
    if until is not None:  # the k-week change must be fully known by `until`
        df = df[df.index <= until - pd.Timedelta(weeks=k)]
    X = np.column_stack([np.ones(len(df)), df["r"], df["lvl"]])
    coef, *_ = np.linalg.lstsq(X, df["dF"].to_numpy(), rcond=None)
    res = df["dF"].to_numpy() - X @ coef
    ss = np.sum((df["dF"] - df["dF"].mean()) ** 2)
    return {"k": k, "n": int(len(df)), "a": float(coef[0]), "b": float(coef[1]), "c": float(coef[2]),
            "r2": float(1 - np.sum(res ** 2) / ss) if ss else None, "q": [float(np.quantile(res, band[0])), float(np.quantile(res, band[1]))]}


def fng_predict(model: dict, fng_now: float, r: float) -> tuple[float, float, float]:
    mid = fng_now + model["a"] + model["b"] * r + model["c"] * (fng_now - 50)
    return tuple(float(np.clip(x, 0, 100)) for x in (mid + model["q"][0], mid, mid + model["q"][1]))


def fng_check(t: pd.DataFrame, k: int, fit_until: pd.Timestamp, test: tuple[pd.Timestamp, pd.Timestamp], band=(0.10, 0.90)) -> dict:
    """Out-of-sample coverage of the band: fit up to fit_until, test on weeks in `test` whose k-week outcome is known."""
    m = fng_response(t, k, fit_until, band)
    f, p = t["raw_fng"], t["close"]
    rows = []
    for d in t.index[(t.index >= test[0]) & (t.index <= test[1] - pd.Timedelta(weeks=k))]:
        j = t.index.get_loc(d)
        if j + k >= len(t) or not np.isfinite(f.iloc[j]) or not np.isfinite(f.iloc[j + k]):
            continue
        lo, mid, hi = fng_predict(m, f.iloc[j], np.log(p.iloc[j + k] / p.iloc[j]))
        rows.append((f.iloc[j + k], lo, mid, hi, f.iloc[j]))
    a = np.array(rows)
    if not len(a):
        return {"k": k, "weeks": 0}
    naive_err = np.abs(a[:, 0] - a[:, 4]).mean()  # "F&G stays where it is"
    return {"k": k, "weeks": int(len(a)), "coverage": float(np.mean((a[:, 0] >= a[:, 1]) & (a[:, 0] <= a[:, 3]))),
            "mae_model": float(np.abs(a[:, 0] - a[:, 2]).mean()), "mae_constant": float(naive_err), "model": m}


def rc_drift(cm: pd.DataFrame, k: int, until: pd.Timestamp, window_weeks: int = 208, band=(0.10, 0.90)) -> dict:
    """10–90% of the k-week change of realized cap (market cap / MVRV) over the `window_weeks` before `until`."""
    d = cm[cm["date"] <= until].set_index("date")
    rc = (d["mcap"] / d["mvrv"]).dropna()
    rc = rc[rc.index > until - pd.Timedelta(weeks=window_weeks)]
    ch = (rc / rc.shift(7 * k, freq="D").reindex(rc.index) - 1).dropna()
    return {"k": k, "n": int(len(ch)), "q": [float(np.quantile(ch, band[0])), float(np.quantile(ch, band[1]))]}


def synthetic(inputs: dict, asof: pd.Timestamp, delta: float, k: int, fng_end: float | None = None,
              price_path: np.ndarray | None = None, fng_path: np.ndarray | None = None, rc_change: float = 0.0) -> dict:
    """Inputs cut at `asof` plus 7k synthetic days ending at asof + k weeks with price × (1 + delta)."""
    cut = {n: (None if df is None else df[df["date"] <= asof].copy()) for n, df in inputs.items()}
    cm, ext, fng, fed = cut["cm"], cut["ext"], cut["fng"], cut["fed"]
    days = pd.date_range(asof + pd.Timedelta(days=1), periods=7 * k, freq="D")
    last = cm.iloc[-1]
    p0 = float(last["price"])
    steps = np.arange(1, len(days) + 1) / len(days)
    path = price_path if price_path is not None else p0 * np.exp(np.log(1 + delta) * steps)
    rc = float(last["mcap"] / last["mvrv"]) * np.exp(np.log(1 + rc_change) * steps)  # realized cap held (or drifting)
    supply = float(last["mcap"] / last["price"])      # supply held
    iss_btc = float(last["iss_usd"] / last["price"])  # daily issuance in BTC held
    new_cm = pd.DataFrame({"date": days, "price": path, "mcap": path * supply, "mvrv": path * supply / rc,
                           "hashrate": float(last["hashrate"]), "iss_usd": iss_btc * path})
    out = {"cm": pd.concat([cm, new_cm], ignore_index=True)}
    if ext is not None and len(ext):
        v = float(ext["volume_spot_usd"].tail(30).mean())
        out["ext"] = pd.concat([ext, pd.DataFrame({"date": days, "volume_spot_usd": v, "supply": ext["supply"].iloc[-1], "iss_btc": ext["iss_btc"].iloc[-1]})],
                               ignore_index=True)
    else:
        out["ext"] = ext
    if fng is not None and len(fng):
        f0 = float(fng["fng"].iloc[-1])
        fp = fng_path if fng_path is not None else (f0 + (fng_end - f0) * np.arange(1, len(days) + 1) / len(days) if fng_end is not None else np.full(len(days), f0))
        out["fng"] = pd.concat([fng, pd.DataFrame({"date": days, "fng": fp})], ignore_index=True)
    else:
        out["fng"] = fng
    if fed is not None and len(fed):
        out["fed"] = pd.concat([fed, pd.DataFrame({"date": days, "fed_upper": fed["fed_upper"].iloc[-1]})], ignore_index=True)
    else:
        out["fed"] = fed
    return out


def scenario_row(inputs: dict, asof: pd.Timestamp, delta: float, k: int, fng_end: float | None = None, **kw) -> pd.Series:
    s = synthetic(inputs, asof, delta, k, fng_end, **kw)
    t = wc.build(s["cm"], s["ext"], s["fng"], s["fed"])
    return t.loc[asof + pd.Timedelta(weeks=k)]


def rank_among(history: pd.Series, x: float) -> float | None:
    """0–100 rank of x among earlier values of the same score (the "Tỷ lệ nên mua" scale)."""
    h = history.dropna().to_numpy()
    if not np.isfinite(x) or len(h) < 52:
        return None
    return float((np.sum(h < x) + 0.5 * np.sum(h == x)) / len(h) * 100)
