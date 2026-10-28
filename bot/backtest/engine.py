"""Weekly contribution simulation (section 2.1), vectorised over many runs for bootstrap and placebo tests.

Each week: budget B is added to cash; the strategy buys clip(m × B, 0, cash) with m clipped to [m_min, m_max];
unspent money stays in the reserve (optional yield). If the reserve before the contribution exceeds
reserve_cap_weeks × B, m is raised to at least 1. Costs: fee on the amount and slippage on the price.
"""
from __future__ import annotations

import dataclasses

import numpy as np

from bot.config import cfg


@dataclasses.dataclass(frozen=True)
class SimConfig:
    budget: float = 100.0
    m_min: float = 0.25
    m_max: float = 2.0
    reserve_cap_weeks: float = 12.0
    fee: float = 0.001
    slippage: float = 0.0005
    reserve_yield: float = 0.0

    @staticmethod
    def from_config() -> "SimConfig":
        b, c = cfg()["budget"], cfg()["costs"]
        return SimConfig(b["weekly_usd"], b["multiplier_min"], b["multiplier_max"], b["reserve_cap_weeks"],
                         c["fee"], c["slippage"], b.get("reserve_yield", 0.0))


@dataclasses.dataclass
class SimResult:
    """Arrays of shape (runs, weeks). Values are after the week's contribution and purchase, at that week's price."""
    price: np.ndarray
    mult: np.ndarray
    amount: np.ndarray
    btc: np.ndarray
    cash: np.ndarray
    reserve_before: np.ndarray
    contributed: np.ndarray
    spent: np.ndarray

    @property
    def equity(self) -> np.ndarray:
        return self.btc * self.price + self.cash


def simulate(price: np.ndarray, mult: np.ndarray | None, cfg_: SimConfig | None = None) -> SimResult:
    """price: (weeks,) or (runs, weeks); mult: same shape, or None for plain DCA (m = 1, no reserve)."""
    c = cfg_ or SimConfig.from_config()
    P = np.atleast_2d(np.asarray(price, dtype=float))
    M = np.ones_like(P) if mult is None else np.broadcast_to(np.atleast_2d(np.asarray(mult, dtype=float)), P.shape).copy()
    if mult is None:
        M[:] = 1.0
    R, N = P.shape
    out = {k: np.zeros((R, N)) for k in ("mult", "amount", "btc", "cash", "reserve_before", "contributed", "spent")}
    btc, cash, contrib, spent = np.zeros(R), np.zeros(R), np.zeros(R), np.zeros(R)
    wy = (1 + c.reserve_yield) ** (1 / 52) - 1
    for t in range(N):
        cash = cash * (1 + wy)
        reserve = cash.copy()
        m = np.clip(np.nan_to_num(M[:, t], nan=1.0), c.m_min, c.m_max) if mult is not None else np.ones(R)
        m = np.where(reserve > c.reserve_cap_weeks * c.budget, np.maximum(m, 1.0), m)
        cash = cash + c.budget
        contrib = contrib + c.budget
        amt = np.clip(m * c.budget, 0, cash)
        btc = btc + amt * (1 - c.fee) / (P[:, t] * (1 + c.slippage))
        cash = cash - amt
        spent = spent + amt
        for k, v in (("mult", m), ("amount", amt), ("btc", btc), ("cash", cash), ("reserve_before", reserve),
                     ("contributed", contrib), ("spent", spent)):
            out[k][:, t] = v
    return SimResult(price=P, **out)
