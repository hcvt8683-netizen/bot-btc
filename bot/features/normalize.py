"""Point-in-time normalization: percentile rank of the current weekly value within the trailing 208 weekly
values (current included). NaN until 104 weekly values exist. Sign adjustment turns every feature into
"cheapness" in [0, 1] (1 = cheapest for a buyer) using its `cheap_when` prior.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def pit_percentile(x: pd.Series, window: int = 208, min_hist: int = 104) -> pd.Series:
    """Ties count half; NaN inputs stay NaN and are not counted in the history."""
    v = x.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    for t in range(len(v)):
        if not np.isfinite(v[t]):
            continue
        h = v[max(0, t - window + 1):t + 1]
        h = h[np.isfinite(h)]
        if len(h) < min_hist:
            continue
        out[t] = (np.sum(h < v[t]) + 0.5 * (np.sum(h == v[t]) - 1)) / (len(h) - 1)
    return pd.Series(out, index=x.index)


def cheapness(pct: pd.Series, cheap_when: str) -> pd.Series:
    if cheap_when == "low":
        return 1 - pct
    if cheap_when == "high":
        return pct
    raise ValueError(cheap_when)
