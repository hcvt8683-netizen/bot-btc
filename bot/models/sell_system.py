"""Part E: one sell system (settings in config/candidates.yaml, section sell).

Criteria fire when an indicator is in the most expensive 5% of the previous 4 years (rolling percentile, past data only).
They are counted by GROUP: 0 groups → Giữ, 1–2 → Chốt lời một phần, ≥ 3 → Bán phần lớn. Executable rule: sell X% of
the BTC held once, when an episode of the trigger starts (decision at the Sunday close, fill at the Monday close);
buy everything back when the Sunday close is ≤ 80% of the average sale price or 52 weeks after the first open sale.
Weekly DCA continues throughout; the baseline is the same DCA without selling.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.backtest import measure

LEVEL = {0: "giu", 1: "chot", 2: "chot"}


def flags(t: pd.DataFrame, groups: dict, thr: float) -> pd.DataFrame:
    """On/off per criterion (False where the percentile does not exist yet)."""
    out = pd.DataFrame(index=t.index)
    for feats in groups.values():
        for f in feats:
            out[f] = (t["pct_" + f] >= thr).fillna(False)
    return out


def group_count(fl: pd.DataFrame, groups: dict) -> pd.Series:
    return sum(fl[feats].any(axis=1).astype(int) for feats in groups.values())


def level_of(n: int, levels: dict) -> str:
    return "ban" if n >= levels["ban_phan_lon"] else "chot" if n >= levels["chot_mot_phan"] else "giu"


def episode_starts(mask: np.ndarray, gap: int = 4) -> list[int]:
    return [a for a, _ in measure.episodes(mask, gap)]


def simulate(close: np.ndarray, fill: np.ndarray, starts: list[int], frac: float, ratio: float, max_weeks: int,
             budget: float = 100.0, fee: float = 0.001, slip: float = 0.0005) -> dict:
    """DCA every week plus the sell / buy-back rule. Returns equity paths of the strategy and of plain DCA, and the trades."""
    n = len(fill)
    btc = btc_d = 0.0
    pool = sold_btc = 0.0  # cash from open sales and the BTC sold (for the average sale price)
    opened = None
    eq, eq_d, trades = np.zeros(n), np.zeros(n), []
    start_set = set(starts)
    for t in range(n):
        px = fill[t]
        q = budget * (1 - fee) / (px * (1 + slip))
        btc += q
        btc_d += q
        if t in start_set and btc > 0:
            s = btc * frac
            btc -= s
            pool += s * px * (1 - slip) * (1 - fee)
            sold_btc += s
            opened = t if opened is None else opened
            trades.append({"sell": t, "sell_px": px})
        if pool > 0 and opened is not None and t > opened:
            avg_sale = pool / sold_btc
            if close[t] <= ratio * avg_sale or t - opened >= max_weeks:
                btc += pool * (1 - fee) / (px * (1 + slip))
                for tr in trades:
                    if "buy" not in tr:
                        tr.update({"buy": t, "buy_px": px, "right": px < tr["sell_px"]})
                pool = sold_btc = 0.0
                opened = None
        eq[t], eq_d[t] = btc * px + pool, btc_d * px
    return {"equity": eq, "equity_dca": eq_d, "trades": trades}


def mdd(eq: np.ndarray, budget: float = 100.0) -> float:
    """Max drawdown of the time-weighted index (weekly contributions removed)."""
    r = (eq[1:] - budget) / np.where(eq[:-1] > 0, eq[:-1], np.nan) - 1
    r = r[np.isfinite(r)]
    idx = np.cumprod(1 + r)
    return float((idx / np.maximum.accumulate(idx) - 1).min()) if len(idx) else 0.0
