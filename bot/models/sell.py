"""Sell side (section 4.3), conservative.

The 13 existing take-profit criteria of the web bot are rebuilt on the weekly decision grid. A criterion with fewer
than 10 independent episodes (weeks less than 8 weeks apart form one episode, as in the web bot) is display only.
Action rule on the active criteria: sell 10% of BTC when the valuation group and the momentum or positioning group
trigger together, 30% when 3 or more groups trigger; never more than 50% within any 26 weeks; buying back happens
only through the buy layer. The sell side becomes an action only if, compared with holding, it improves both the
P10 equity ratio and the max drawdown in at least 3 of 4 halving cycles; otherwise it stays advisory text.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from bot.backtest import metrics
from bot.backtest.engine import SimConfig, simulate
from bot.backtest.metrics import wilson
from bot.validation import splits

MIN_EPISODES = 10
GAP_WEEKS = 8
WINDOW = 52


@dataclasses.dataclass(frozen=True)
class Criterion:
    id: str
    feature: str        # weekly column
    group: str          # valuation / momentum / positioning / model
    kind: str           # classic (raw ≥ thr), adaptive (4-year percentile ≥ 0.95), model (bot sell score ≥ 85)
    thr: float


CRITERIA = [
    Criterion("pi_cat", "raw_pi_ratio", "momentum", "classic", 1.0),
    Criterion("mvrvz_7", "raw_mvrv_z", "valuation", "classic", 7.0),
    Criterion("mvrv_3", "raw_mvrv", "valuation", "classic", 3.0),
    Criterion("mayer_24", "raw_mayer", "momentum", "classic", 2.4),
    Criterion("rsiw_80", "rsi_14w", "momentum", "classic", 80.0),
    Criterion("fng_90", "fng", "positioning", "classic", 90.0),
    Criterion("puell_4", "raw_puell", "valuation", "classic", 4.0),
    Criterion("mvrvz_p", "pct_mvrv_z", "valuation", "adaptive", 0.95),
    Criterion("mvrv_p", "pct_mvrv", "valuation", "adaptive", 0.95),
    Criterion("mayer_p", "pct_mayer", "momentum", "adaptive", 0.95),
    Criterion("wma_p", "pct_p_200wma", "momentum", "adaptive", 0.95),
    Criterion("puell_p", "pct_puell", "valuation", "adaptive", 0.95),
    Criterion("bot_nb", "bot_sell", "model", "model", 85.0),
]


def flags(table: pd.DataFrame) -> pd.DataFrame:
    """Weekly on/off (NaN when the input is missing) for every criterion."""
    out = pd.DataFrame(index=table.index)
    for c in CRITERIA:
        v = table[c.feature] if c.feature in table else pd.Series(np.nan, index=table.index)
        out[c.id] = np.where(v.isna(), np.nan, (v >= c.thr).astype(float))
    return out


def episode_starts(on: np.ndarray) -> list[int]:
    starts, last = [], -10**9
    for j, f in enumerate(on):
        if f == 1:
            if j - last > GAP_WEEKS:
                starts.append(j)
            last = j
    return starts


def criterion_stats(on: np.ndarray, price: np.ndarray, h: int = 26) -> dict:
    """Episodes and the share of episodes after which the price was lower h weeks later (diagnostic, with Wilson)."""
    st = episode_starts(on)
    done = [j for j in st if j + h < len(price)]
    k = sum(price[j + h] < price[j] for j in done)
    lo, hi = wilson(k, len(done))
    return {"episodes": len(st), "weeks_on": int(np.nansum(on == 1)), "n": len(done), "right": k / len(done) if done else None, "lo": lo, "hi": hi}


def sell_fractions(fl: pd.DataFrame, active: list[str], cap: float = 0.5, window: int = 26) -> tuple[np.ndarray, np.ndarray]:
    """Weekly sell fraction from the action rule, with the 50%-in-26-weeks cap. Returns (fractions, groups on)."""
    groups = {c.id: c.group for c in CRITERIA}
    n = len(fl)
    on_g = np.zeros(n, dtype=int)
    frac = np.zeros(n)
    hist: list[tuple[int, float]] = []
    for t in range(n):
        g = {groups[i] for i in active if fl[i].iloc[t] == 1}
        on_g[t] = len(g)
        want = 0.30 if len(g) >= 3 else 0.10 if ("valuation" in g and ({"momentum", "positioning"} & g)) else 0.0
        hist = [(k, f) for k, f in hist if t - k < window]
        kept = float(np.prod([1 - f for _, f in hist])) if hist else 1.0
        allow = max(0.0, 1 - (1 - cap) / kept) if kept > 0 else 0.0
        f = min(want, allow)
        if f > 1e-9:
            frac[t] = f
            hist.append((t, f))
    return frac, on_g


def compare(dates: pd.DatetimeIndex, price: np.ndarray, mult: np.ndarray, frac: np.ndarray, cfg_: SimConfig | None = None) -> dict:
    """Per halving cycle: P10 of 52-week rolling equity ratio vs DCA and max drawdown, for buy+sell vs buy only."""
    c = cfg_ or SimConfig.from_config()
    out = {}
    for name, a, b, complete in splits.cycles(dates[-1]):
        sel = np.where((dates >= a) & (dates <= b))[0]
        if len(sel) < WINDOW:
            continue
        starts = list(range(sel[0], sel[-1] - WINDOW + 2, 4))
        P = np.stack([price[k:k + WINDOW] for k in starts])
        M = np.stack([mult[k:k + WINDOW] for k in starts])
        F = np.stack([frac[k:k + WINDOW] for k in starts])
        d = simulate(P, None, c)
        er_hold = metrics.equity_ratio(simulate(P, M, c), d)
        er_sell = metrics.equity_ratio(simulate(P, M, c, sell=F), d)
        full_hold = simulate(price[sel], mult[sel], c)
        full_sell = simulate(price[sel], mult[sel], c, sell=frac[sel])
        mdd_h = metrics.drawdown_stats(metrics.twr(full_hold)[0])["mdd"]
        mdd_s = metrics.drawdown_stats(metrics.twr(full_sell)[0])["mdd"]
        p10_h, p10_s = float(np.quantile(er_hold, 0.1)), float(np.quantile(er_sell, 0.1))
        out[name] = {"complete": complete, "p10_hold": p10_h, "p10_sell": p10_s, "med_hold": float(np.median(er_hold)), "med_sell": float(np.median(er_sell)),
                     "mdd_hold": mdd_h, "mdd_sell": mdd_s, "sells": int((frac[sel] > 0).sum()),
                     "er_cycle_hold": float(full_hold.equity[0, -1] / simulate(price[sel], None, c).equity[0, -1]),
                     "er_cycle_sell": float(full_sell.equity[0, -1] / simulate(price[sel], None, c).equity[0, -1]),
                     "better": p10_s > p10_h + 1e-9 and mdd_s > mdd_h + 1e-9}
    return out
