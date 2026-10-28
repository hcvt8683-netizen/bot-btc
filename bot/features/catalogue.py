"""Feature catalogue (section 4.1). Every feature: name, group, formula, minimum raw history, `cheap_when`
(economic prior for a buyer) and normalization. Daily series are causal (value at day d uses data ≤ d).
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from bot.validation.splits import HALVINGS


@dataclasses.dataclass(frozen=True)
class Feature:
    name: str
    group: str          # A cycle/valuation, B positioning/short term, C macro/event
    formula: str
    min_days: int       # raw daily history needed before the first value
    cheap_when: str | None  # "low", "high", "event" or None (no prior)
    norm: str = "pct208"    # point-in-time percentile over 208 weeks (NaN before 104 weeks)
    source: str = "coinmetrics"


GROUP_A = [
    Feature("mvrv", "A", "market cap / realized cap", 1, "low"),
    Feature("mvrv_z", "A", "(MC − RC) / std(MC, expanding)", 30, "low"),
    Feature("pi_ratio", "A", "SMA111(P) / (2 × SMA350(P))", 350, "low"),
    Feature("p_200wma", "A", "P / SMA(P, 200 weeks)", 1400, "low"),
    Feature("mayer", "A", "P / SMA200d(P)", 200, "low"),
    Feature("puell", "A", "IssTotUSD / SMA365(IssTotUSD)", 365, "low"),
    Feature("dd_ath", "A", "P / running ATH − 1", 1, "low"),
    Feature("nupl", "A", "1 − 1 / MVRV", 1, "low"),
    Feature("halving_phase", "A", "days since halving / days in cycle, quarters", 1, None, norm="raw"),
    Feature("hash_ribbon_buy", "A", "SMA30(hash) crosses above SMA60 after ≥ 10 days below; cheap for 8 weeks", 60, "event", norm="event"),
]
CATALOGUE = {f.name: f for f in GROUP_A}
EVENT_WEEKS = 8


def daily_group_a(cm: pd.DataFrame) -> pd.DataFrame:
    """Daily causal values of every Group A feature from Coin Metrics rows (date, price, mcap, mvrv, hashrate, iss_usd)."""
    d = cm.set_index("date").sort_index().asfreq("D")
    p = d["price"].ffill()
    sma = lambda s, w: s.rolling(w, min_periods=w).mean()  # noqa: E731
    out = pd.DataFrame(index=d.index)
    out["mvrv"] = d["mvrv"]
    mc = d["mcap"]
    rc = mc / d["mvrv"]
    out["mvrv_z"] = (mc - rc) / mc.expanding(min_periods=30).std(ddof=0)
    out["pi_ratio"] = sma(p, 111) / (2 * sma(p, 350))
    out["p_200wma"] = p / sma(p, 1400)
    out["mayer"] = p / sma(p, 200)
    iss = d["iss_usd"]
    out["puell"] = iss / iss.rolling(365, min_periods=300).mean()
    out["dd_ath"] = p / p.cummax() - 1
    out["nupl"] = 1 - 1 / d["mvrv"]
    out["halving_phase"] = halving_phase(out.index)
    out["hash_ribbon_buy"] = hash_ribbon_events(d["hashrate"]).astype(float)
    out["price"] = p
    return out


def halving_phase(idx: pd.DatetimeIndex) -> np.ndarray:
    """Quarter (0–3) of the current halving cycle; cycle length taken as the previous cycle's (known in advance)."""
    edges = [pd.Timestamp("2009-01-03"), *HALVINGS]
    out = np.full(len(idx), np.nan)
    for k, t in enumerate(idx):
        prev = max(e for e in edges if e <= t)
        j = edges.index(prev)
        length = (edges[j] - edges[j - 1]).days if j > 0 else 1400
        out[k] = min(3, int(4 * (t - prev).days / length))
    return out


def hash_ribbon_events(hashrate: pd.Series, below_days: int = 10) -> pd.Series:
    """True on the day SMA30 crosses back above SMA60 after at least `below_days` consecutive days below."""
    h = hashrate.ffill()
    s30, s60 = h.rolling(30, min_periods=30).mean(), h.rolling(60, min_periods=60).mean()
    below = (s30 < s60).astype(int)
    run = below.groupby((below != below.shift()).cumsum()).cumsum() * below
    prev_run = run.shift(1).fillna(0)
    return (below == 0) & (prev_run >= below_days) & s60.notna()
