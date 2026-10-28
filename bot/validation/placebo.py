"""Placebo test: shuffle the multiplier series in 26-week blocks and compare equity ratios on the real price path.

The real strategy must beat at least 95% of placebo runs (acceptance criterion 4). The block shuffle keeps the
share of weeks at each multiplier and its local persistence, and only destroys the timing.
"""
from __future__ import annotations

import numpy as np

from bot.backtest import metrics
from bot.backtest.engine import SimConfig, simulate


def shuffled(mult: np.ndarray, block: int, rng: np.random.Generator, runs: int) -> np.ndarray:
    n = len(mult)
    blocks = [mult[k:k + block] for k in range(0, n, block)]
    out = np.empty((runs, n))
    for j in range(runs):
        order = rng.permutation(len(blocks))
        out[j] = np.concatenate([blocks[i] for i in order])[:n]
    return out


def placebo(price: np.ndarray, mult: np.ndarray, n: int = 1000, block: int = 26, seed: int = 0,
            cfg_: SimConfig | None = None) -> dict:
    """Percentile of the real equity ratio among block-shuffled placebos (ties count half)."""
    rng = np.random.default_rng(seed)
    M = shuffled(np.asarray(mult, dtype=float), block, rng, n)
    P = np.broadcast_to(price, M.shape)
    d = simulate(P, None, cfg_)
    pl = metrics.equity_ratio(simulate(P, M, cfg_), d)
    real = metrics.summary(price, mult, cfg_)["equity_ratio"]
    pct = float((np.sum(pl < real - 1e-12) + 0.5 * np.sum(np.abs(pl - real) <= 1e-12)) / n)
    return {"er": real, "percentile": pct, "placebo_median": float(np.median(pl)), "placebo_p95": float(np.quantile(pl, 0.95)), "n": n}
