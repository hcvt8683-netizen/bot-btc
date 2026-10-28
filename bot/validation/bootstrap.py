"""Moving-block bootstrap of the weekly price path with the multiplier paired to each week (26-week blocks).

Each resample rebuilds a price path from resampled weekly log returns and keeps the multiplier that was used in
those weeks, then simulates strategy and DCA with the same contributions. Gives 95% intervals for the equity
ratio and the cost-basis advantage.
"""
from __future__ import annotations

import numpy as np

from bot.backtest import metrics
from bot.backtest.engine import SimConfig, simulate


def block_indices(n: int, block: int, rng: np.random.Generator, runs: int) -> np.ndarray:
    """(runs, n) indices made of consecutive blocks with random starts (circular)."""
    k = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(runs, k))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    return idx.reshape(runs, -1)[:, :n]


def bootstrap(price: np.ndarray, mult: np.ndarray, n: int = 2000, block: int = 26, seed: int = 0,
              cfg_: SimConfig | None = None) -> dict:
    """Equity ratio and CBA: point estimate, median and 95% interval over `n` block resamples."""
    rng = np.random.default_rng(seed)
    r = np.diff(np.log(price))
    m = np.asarray(mult, dtype=float)[1:]
    idx = block_indices(len(r), block, rng, n)
    P = price[0] * np.exp(np.cumsum(r[idx], axis=1))
    P = np.concatenate([np.full((n, 1), price[0]), P], axis=1)
    M = np.concatenate([np.full((n, 1), mult[0]), m[idx]], axis=1)
    s, d = simulate(P, M, cfg_), simulate(P, None, cfg_)
    er, cb = metrics.equity_ratio(s, d), metrics.cba(s, d)
    point = metrics.summary(price, mult, cfg_)
    q = lambda x: (float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975)))  # noqa: E731
    return {"er": point["equity_ratio"], "er_ci": q(er), "er_median": float(np.median(er)), "er_p10": float(np.quantile(er, 0.10)),
            "cba": point["cba"], "cba_ci": q(cb), "n": n, "block": block}
