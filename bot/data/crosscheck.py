"""Price cross-check between sources on their overlap (same calendar day = same daily close)."""
from __future__ import annotations

import pandas as pd

from bot.data import pit_store as ps

ERAS = [("2010–2013", "2010-01-01", "2013-12-31"), ("2014–2016", "2014-01-01", "2016-12-31"),
        ("2017–2020", "2017-01-01", "2020-12-31"), ("2021–nay", "2021-01-01", "2100-01-01")]


def series() -> dict[str, pd.Series]:
    out = {"coinmetrics": ps.load_history("coinmetrics").set_index("date")["price"]}
    for name, col in (("bitstamp", "close"), ("binance_spot", "close"), ("coingecko", "price")):
        h = ps.load_history(name)
        if len(h):
            out[name] = h.set_index("date")[col]
    return out


def compare(primary: str = "coinmetrics", threshold: float = 0.02) -> dict:
    """For every other source: overlap, median / 99th percentile / max of |price difference|, days above threshold,
    split by era, and the five largest gaps."""
    s = series()
    base = s[primary]
    res = {}
    for name, other in s.items():
        if name == primary:
            continue
        j = pd.concat([base, other], axis=1, keys=["a", "b"]).dropna()
        j = j[(j["a"] > 0) & (j["b"] > 0)]
        d = (j["b"] / j["a"] - 1)
        ad = d.abs()
        eras = []
        for label, a, b in ERAS:
            x = ad[(ad.index >= a) & (ad.index <= b)]
            if len(x):
                eras.append({"era": label, "days": int(len(x)), "median": float(x.median()), "p99": float(x.quantile(0.99)),
                             "above": int((x > threshold).sum())})
        worst = ad.sort_values(ascending=False).head(5)
        res[name] = {"from": j.index.min().strftime("%Y-%m-%d"), "to": j.index.max().strftime("%Y-%m-%d"), "days": int(len(j)),
                     "median": float(ad.median()), "p99": float(ad.quantile(0.99)), "max": float(ad.max()), "above": int((ad > threshold).sum()),
                     "eras": eras, "worst": [{"date": t.strftime("%Y-%m-%d"), "primary": float(j.loc[t, "a"]), "other": float(j.loc[t, "b"]),
                                              "diff": float(d.loc[t])} for t in worst.index]}
    return res
