"""Baselines: plain DCA (m = 1) and the current bot reproduced as a multiplier strategy
(Phải mua → 2.0, Cân nhắc mua → 1.25, Không nên mua → 0.25)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.features.panel import decision_time

CURRENT_MAP = [(80.0, 2.0), (60.0, 1.25), (0.0, 0.25)]
SCORE_LAG = pd.Timedelta(days=2)  # a Sunday score uses Sunday's Coin Metrics row, published at the earliest Tuesday 00:00


def dca(dates: pd.DatetimeIndex) -> np.ndarray:
    return np.ones(len(dates))


def zone_multiplier(score: float) -> float:
    if score is None or not np.isfinite(score):
        return 1.0
    return next(m for thr, m in CURRENT_MAP if score >= thr)


def current_bot(scores: pd.DataFrame, dates: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    """As-of join of weekly buy scores onto decision times. Returns (multiplier, score); m = 1 where no score yet."""
    s = scores[["date", "buy"]].copy()
    s["available_at"] = s["date"] + SCORE_LAG
    s = s.sort_values("available_at")
    t = pd.DataFrame({"t": decision_time(dates)})
    j = pd.merge_asof(t, s, left_on="t", right_on="available_at", direction="backward")
    stale = (j["t"] - j["available_at"]) > pd.Timedelta(days=14)  # never reuse a score older than two weeks
    score = j["buy"].where(~stale).to_numpy(dtype=float)
    return np.array([zone_multiplier(x) for x in score]), score
