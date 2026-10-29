"""Weekly table at the Sunday close (rebuild, part A).

Every model input is taken at the weekly close: the Coin Metrics row of a Sunday is that Sunday's close (measured:
median 0.13% from Binance and 0.15% from Bitstamp at the same date, 1.5% one day off). A value at week t only uses
daily data up to and including that Sunday; percentiles use only the weekly values up to t (208-week window,
none before 104 weeks). Live prices are for display only and never enter this table.

Publication: Coin Metrics publishes day d about 27 h after 00:00 UTC of d (median of the last 365 days, at most
42 h), so a Sunday-close signal is known on Monday morning (Vietnam time).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.features import catalogue, normalize

PCT_WINDOW, PCT_MIN = 208, 104
FED_LOOKBACK_WEEKS = 26
# cheap_when for the buyer; None = no economic prior (context only)
CHEAP = {"mvrv": "low", "mvrv_z": "low", "pi_ratio": "low", "p_200wma": "low", "mayer": "low", "rsi_14w": "low", "puell": "low",
         "dd_ath": "low", "vol_rel": None, "fng": "low", "rv30": None, "dev_ma20w": "low"}
FEATURES = list(CHEAP)


def rsi_weekly(price: pd.Series, n: int = 14) -> pd.Series:
    """RSI over n weekly steps (price 7 days apart), evaluated every day; causal."""
    d = price - price.shift(7)
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    su = sum(up.shift(7 * k) for k in range(n))
    sd = sum(dn.shift(7 * k) for k in range(n))
    return 100 - 100 / (1 + su / sd.replace(0, np.nan))


def daily_features(cm: pd.DataFrame, ext: pd.DataFrame | None = None, fng: pd.DataFrame | None = None) -> pd.DataFrame:
    """Causal daily values of every candidate feature. cm: date, price, mcap, mvrv, hashrate, iss_usd."""
    a = catalogue.daily_group_a(cm)
    p = a["price"]
    out = a[["price", "mvrv", "mvrv_z", "pi_ratio", "p_200wma", "mayer", "puell", "dd_ath", "hash_ribbon_buy"]].copy()
    out["rsi_14w"] = rsi_weekly(p)
    lr = np.log(p).diff()
    out["rv30"] = lr.rolling(30, min_periods=28).std() * np.sqrt(365)
    out["dev_ma20w"] = p / p.rolling(140, min_periods=140).mean() - 1
    out["vol_rel"] = np.nan
    if ext is not None and len(ext):
        v = ext.set_index("date")["volume_spot_usd"].reindex(out.index)
        v = v.where(v > 0)
        out["vol_rel"] = v.rolling(30, min_periods=25).mean() / v.rolling(365, min_periods=300).mean()
    out["fng"] = np.nan
    if fng is not None and len(fng):
        out["fng"] = fng.set_index("date")["fng"].reindex(out.index)
    return out


def fed_regime(fed: pd.DataFrame | None, sundays: pd.DatetimeIndex, weeks: int = FED_LOOKBACK_WEEKS) -> pd.Series:
    """'tang' / 'giu' / 'giam' from the change of the Fed upper target over the previous `weeks` weeks (data ≤ Sunday)."""
    if fed is None or not len(fed):
        return pd.Series(None, index=sundays, dtype=object)
    f = fed.set_index("date")["fed_upper"].sort_index()
    f = f.reindex(pd.date_range(f.index.min(), max(f.index.max(), sundays.max()), freq="D")).ffill()
    now = f.reindex(sundays)
    before = f.reindex(sundays - pd.Timedelta(weeks=weeks))
    ch = now.to_numpy() - before.to_numpy()
    lab = np.where(np.isnan(ch), None, np.where(ch > 0.1, "tang", np.where(ch < -0.1, "giam", "giu")))
    return pd.Series(lab, index=sundays, dtype=object)


def build(cm: pd.DataFrame, ext: pd.DataFrame | None = None, fng: pd.DataFrame | None = None, fed: pd.DataFrame | None = None,
          end: pd.Timestamp | None = None) -> pd.DataFrame:
    """One row per Sunday: close price, raw features, 4-year percentiles (pct_), buyer cheapness (cheap_), Fed regime.
    Inputs after `end` are dropped first, so the table can never see them."""
    if end is not None:
        cut = lambda df: None if df is None else df[df["date"] <= end]  # noqa: E731
        cm, ext, fng, fed = cut(cm), cut(ext), cut(fng), cut(fed)
    d = daily_features(cm, ext, fng)
    last_full = d.index.max()
    sundays = d.index[(d.index.weekday == 6) & (d.index <= last_full)]
    w = d.reindex(sundays)
    out = pd.DataFrame(index=sundays)
    out.index.name = "date"
    out["close"] = w["price"]
    # execution price for scoring (config rebuild.execution = monday_close): the close of the Monday after the Sunday
    out["exec_monday"] = d["price"].reindex(sundays + pd.Timedelta(days=1)).to_numpy()
    for f in FEATURES:
        out["raw_" + f] = w[f]
        pct = normalize.pit_percentile(w[f], window=PCT_WINDOW, min_hist=PCT_MIN)
        out["pct_" + f] = pct
        if CHEAP[f]:
            out["cheap_" + f] = normalize.cheapness(pct, CHEAP[f])
    out["hash_ribbon_4w"] = d["hash_ribbon_buy"].fillna(0).rolling(28, min_periods=1).max().reindex(sundays)
    out["fed_regime"] = fed_regime(fed, sundays)
    return out


def load(end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Build from the point-in-time store (latest vintage of every source)."""
    from bot.data import pit_store as ps
    fred = ps.load_history("fred_DFEDTARU")
    return build(ps.load_history("coinmetrics"), ps.load_history("coinmetrics_ext"), ps.load_history("fng"),
                 fred if len(fred) else None, end)
