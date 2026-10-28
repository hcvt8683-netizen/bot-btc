"""Weekly feature table on the decision grid, written to data/features.parquet with `available_at` per row.

Each decision (Tuesday 01:00 UTC) uses the daily feature values of the last day whose Coin Metrics row was
published by then. Forward returns are labels for training only (known `h` weeks later).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.config import DATA
from bot.features import catalogue, normalize
from bot.features.panel import daily_cm, decision_dates, decision_time, fill_prices

START = pd.Timestamp("2011-01-01")
HORIZONS = (26, 52)


def weekly(end: pd.Timestamp | None = None, write: bool = False) -> pd.DataFrame:
    """Columns: raw_<f>, pct_<f>, cheap_<f> for Group A, price (fill), fwd_<h> log returns, available_at."""
    cm = daily_cm(end)
    daily = catalogue.daily_group_a(cm)
    avail = cm.set_index("date")["available_at"]
    dates = decision_dates(START, cm["date"].max())
    t = decision_time(dates)
    # last daily row published at decision time t
    pub = pd.DataFrame({"date": avail.index, "available_at": avail.values}).sort_values("available_at")
    j = pd.merge_asof(pd.DataFrame({"t": t}), pub, left_on="t", right_on="available_at", direction="backward")
    src = daily.reindex(j["date"].to_numpy())
    out = pd.DataFrame(index=dates)
    out.index.name = "date"
    out["available_at"] = t
    out["feature_day"] = j["date"].to_numpy()
    out["price"] = fill_prices(cm, dates).to_numpy()
    for f in catalogue.GROUP_A:
        raw = pd.Series(src[f.name].to_numpy(dtype=float), index=dates)
        out["raw_" + f.name] = raw
        if f.norm == "pct208":
            pct = normalize.pit_percentile(raw)
            out["pct_" + f.name] = pct
            out["cheap_" + f.name] = normalize.cheapness(pct, f.cheap_when)
        elif f.norm == "event":
            # event seen in the last EVENT_WEEKS weeks of published days → cheap (1), otherwise neutral (0.5)
            ev = daily[f.name].fillna(0)
            seen = ev.rolling(7 * catalogue.EVENT_WEEKS, min_periods=1).max().reindex(j["date"].to_numpy()).to_numpy()
            out["cheap_" + f.name] = np.where(np.isnan(seen), np.nan, np.where(seen > 0, 1.0, 0.5))
    lp = np.log(out["price"].to_numpy())
    for h in HORIZONS:
        fwd = np.full(len(lp), np.nan)
        fwd[:-h] = lp[h:] - lp[:-h]
        out[f"fwd_{h}"] = fwd
    if write:
        out.reset_index().to_parquet(DATA / "features.parquet", index=False, compression="zstd")
    return out
