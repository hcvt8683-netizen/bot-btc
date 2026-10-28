# -*- coding: utf-8 -*-
"""Sell-side tests: episodes, action rule, 50%-in-26-weeks cap, sells in the simulator."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.backtest.engine import SimConfig, simulate
from bot.models import sell


def test_episodes_merge_weeks_closer_than_8():
    on = np.array([1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])
    assert sell.episode_starts(on) == [0, 15]


def test_action_rule_needs_valuation_plus_momentum_and_caps_at_half():
    n = 40
    fl = pd.DataFrame({c.id: np.zeros(n) for c in sell.CRITERIA})
    fl["rsiw_80"] = 1.0                     # momentum alone → no sale
    frac, _ = sell.sell_fractions(fl, ["rsiw_80", "mvrv_3", "fng_90"])
    assert frac.sum() == 0
    fl["mvrv_3"] = 1.0                      # valuation + momentum → 10% weekly
    frac, g = sell.sell_fractions(fl, ["rsiw_80", "mvrv_3", "fng_90"])
    assert frac[0] == pytest.approx(0.10) and g[0] == 2
    kept = np.prod(1 - frac[:26])
    assert kept >= 0.5 - 1e-9 and np.prod(1 - frac[:27]) < 1  # never more than 50% within 26 weeks
    fl["fng_90"] = 1.0                      # 3 groups → 30%
    frac, _ = sell.sell_fractions(fl, ["rsiw_80", "mvrv_3", "fng_90"])
    assert frac[0] == pytest.approx(0.30)


def test_simulator_sells_fraction_into_reserve():
    p = np.array([100.0, 100, 200, 200])
    c = SimConfig(fee=0, slippage=0)
    s = simulate(p, np.ones(4), c, sell=np.array([0, 0, 0.5, 0]))
    # week 3: +100 cash, sell 1 of 2 BTC at 200 (+200), buy 100 → 1.5 BTC and 200 cash left in the reserve
    assert s.btc[0, 2] == pytest.approx(1.0 + 0.5) and s.cash[0, 2] == pytest.approx(200)
