"""Metrics of section 2.2: equity ratio vs DCA (primary), cost-basis advantage, idle cash, drawdown, Sortino,
Calmar, plus win rate as a diagnostic with episode count and Wilson interval."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from bot.backtest.engine import SimConfig, SimResult, simulate


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if not n:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - m) / d), min(1.0, (c + m) / d)


def episodes(mask: np.ndarray) -> int:
    """Number of runs of consecutive True values (one episode per run)."""
    m = np.asarray(mask, dtype=bool)
    return int(np.sum(m & ~np.r_[False, m[:-1]]))


def equity_ratio(s: SimResult, d: SimResult) -> np.ndarray:
    """(BTC_s × P_T + cash_s) / (BTC_d × P_T + cash_d) at the last week, per run."""
    return s.equity[:, -1] / d.equity[:, -1]


def cba(s: SimResult, d: SimResult) -> np.ndarray:
    """Cost-basis advantage: avg cost of DCA / avg cost of strategy − 1, on deployed USD (costs included)."""
    return (d.spent[:, -1] / d.btc[:, -1]) / (s.spent[:, -1] / s.btc[:, -1]) - 1


def twr(s: SimResult) -> np.ndarray:
    """Time-weighted weekly returns (contributions removed): r_t = (V_t − B) / V_{t−1} − 1, from week 2 on."""
    V = s.equity
    flow = np.diff(s.contributed, axis=1, prepend=0)
    prev = np.roll(V, 1, axis=1)
    r = np.where(prev > 0, (V - flow) / np.where(prev > 0, prev, 1) - 1, np.nan)
    return r[:, 1:]


def drawdown_stats(r: np.ndarray) -> dict:
    """Max drawdown, longest time under water (weeks), Sortino and Calmar of one weekly return series."""
    r = r[np.isfinite(r)]
    if len(r) < 4:
        return {"mdd": None, "tuw": None, "sortino": None, "calmar": None}
    idx = np.cumprod(1 + r)
    peak = np.maximum.accumulate(idx)
    dd = idx / peak - 1
    under, run, tuw = dd < -1e-12, 0, 0
    for u in under:
        run = run + 1 if u else 0
        tuw = max(tuw, run)
    down = np.sqrt(np.mean(np.minimum(r, 0) ** 2))
    cagr = idx[-1] ** (52 / len(r)) - 1
    mdd = float(dd.min())
    return {"mdd": mdd, "tuw": int(tuw), "sortino": float(np.mean(r) * 52 / (down * math.sqrt(52))) if down > 0 else None,
            "calmar": float(cagr / abs(mdd)) if mdd < 0 else None}


def idle_cash(s: SimResult, budget: float) -> dict:
    """Average reserve as share of contributions so far, and share of weeks with reserve > 3 × B."""
    res = s.cash
    return {"idle_avg": float(np.mean(res / s.contributed)), "idle_weeks_3b": float(np.mean(res > 3 * budget))}


def summary(price: np.ndarray, mult: np.ndarray, cfg_: SimConfig | None = None) -> dict:
    """Full metric set for one path: strategy vs DCA with the same contributions."""
    c = cfg_ or SimConfig.from_config()
    s, d = simulate(price, mult, c), simulate(price, None, c)
    ds, dd = drawdown_stats(twr(s)[0]), drawdown_stats(twr(d)[0])
    return {"equity_ratio": float(equity_ratio(s, d)[0]), "cba": float(cba(s, d)[0]), **idle_cash(s, c.budget),
            "mdd": ds["mdd"], "mdd_dca": dd["mdd"], "tuw": ds["tuw"], "tuw_dca": dd["tuw"], "sortino": ds["sortino"],
            "sortino_dca": dd["sortino"], "calmar": ds["calmar"], "calmar_dca": dd["calmar"], "weeks": len(price),
            "avg_mult": float(np.mean(s.mult))}


def rolling(dates: pd.DatetimeIndex, price: np.ndarray, mult: np.ndarray, start: pd.Timestamp, end: pd.Timestamp,
            window: int = 104, step: int = 4, cfg_: SimConfig | None = None) -> pd.DataFrame:
    """Independent simulations on every `window`-week window fully inside [start, end], starting every `step` weeks."""
    c = cfg_ or SimConfig.from_config()
    idx = np.where((dates >= start) & (dates <= end))[0]
    starts = [k for k in idx[::step] if k + window - 1 <= idx[-1]] if len(idx) else []
    if not starts:
        return pd.DataFrame()
    P = np.stack([price[k:k + window] for k in starts])
    M = np.stack([mult[k:k + window] for k in starts])
    s, d = simulate(P, M, c), simulate(P, None, c)
    ts, td = twr(s), twr(d)
    rows = []
    for j, k in enumerate(starts):
        a, b = drawdown_stats(ts[j]), drawdown_stats(td[j])
        rows.append({"start": dates[k], "end": dates[k + window - 1], "equity_ratio": float(s.equity[j, -1] / d.equity[j, -1]),
                     "cba": float((d.spent[j, -1] / d.btc[j, -1]) / (s.spent[j, -1] / s.btc[j, -1]) - 1),
                     "idle_avg": float(np.mean(s.cash[j] / s.contributed[j])), "mdd": a["mdd"], "mdd_dca": b["mdd"]})
    return pd.DataFrame(rows)


def roll_summary(df: pd.DataFrame) -> dict:
    """Median and P10 (the bad case) of the rolling equity ratio and CBA."""
    if df.empty:
        return {"n": 0}
    er = df["equity_ratio"].to_numpy()
    return {"n": len(df), "er_median": float(np.median(er)), "er_p10": float(np.quantile(er, 0.10)),
            "er_min": float(er.min()), "cba_median": float(df["cba"].median()), "idle_avg": float(df["idle_avg"].mean()),
            "share_above_1": float(np.mean(er > 1))}


def win_rate(price: np.ndarray, mask: np.ndarray, h: int) -> dict:
    """Diagnostic: share of flagged weeks whose price h weeks later is higher; with episodes and Wilson 95%."""
    n_all = len(price)
    sel = [t for t in np.where(mask)[0] if t + h < n_all]
    k = sum(price[t + h] > price[t] for t in sel)
    lo, hi = wilson(k, len(sel))
    m = np.zeros(n_all, dtype=bool)
    m[sel] = True
    return {"n": len(sel), "episodes": episodes(m), "win": k / len(sel) if sel else None, "lo": lo, "hi": hi}


def active_returns(price: np.ndarray, mult: np.ndarray, cfg_: SimConfig | None = None) -> np.ndarray:
    """Weekly time-weighted return of the strategy minus that of DCA (the series used for Sharpe and DSR)."""
    return twr(simulate(price, mult, cfg_))[0] - twr(simulate(price, None, cfg_))[0]


def sharpe(r: np.ndarray) -> float | None:
    r = r[np.isfinite(r)]
    return float(r.mean() / r.std(ddof=1)) if len(r) > 2 and r.std(ddof=1) > 0 else None
