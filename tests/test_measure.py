# -*- coding: utf-8 -*-
"""Part B measurement tests: episodes, stationary bootstrap, zone verdicts, calibration, cost basis with leftover cash."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.backtest import measure, metrics
from bot.backtest.engine import SimConfig, simulate


def test_episodes_merge_gaps_up_to_4_weeks():
    m = np.zeros(30, dtype=bool)
    m[[0, 1, 5, 11, 12, 25]] = True  # 1→5 gap 4 (merged), 5→11 gap 6 (new), 12→25 new
    assert measure.episodes(m, 4) == [(0, 5), (11, 12), (25, 25)]


def test_stationary_bootstrap_block_length_and_seed():
    rng = np.random.default_rng(3)
    idx = measure.stationary_indices(500, 13, 200, rng)
    cont = (np.diff(idx, axis=1) == 1) | (np.diff(idx, axis=1) == -499)
    assert abs(1 / (1 - cont.mean()) - 13) < 1.5  # mean block length ≈ 13
    a = measure.stationary_indices(50, 4, 3, np.random.default_rng(9))
    b = measure.stationary_indices(50, 4, 3, np.random.default_rng(9))
    assert (a == b).all()


def _walk(n=600, seed=1):
    rng = np.random.default_rng(seed)
    return 100 * np.exp(np.cumsum(rng.normal(0.002, 0.05, n)))


def test_zone_verdicts():
    p = _walk()
    r, _ = measure.forward(p, 4)
    # a zone that knows the future (only for testing the verdict) must be "better than baseline" with many episodes
    good = pd.Series(np.where(r > 0.05, "phai", "khong"), index=pd.RangeIndex(len(p)), dtype=object)
    t = measure.zone_table(good, p, [4], ["phai", "khong"], n_boot=300, seed=1)
    assert t["zones"]["phai"][4]["verdict"] == "hon_moc" and t["zones"]["phai"][4]["episodes"] >= 3
    rng = np.random.default_rng(2)
    rand = pd.Series(rng.choice(["phai", "khong"], len(p)), index=pd.RangeIndex(len(p)), dtype=object)
    t2 = measure.zone_table(rand, p, [4], ["phai", "khong"], n_boot=300, seed=1)
    assert t2["zones"]["phai"][4]["verdict"] == measure.NO_EDGE
    one = pd.Series(["khong"] * len(p), index=pd.RangeIndex(len(p)), dtype=object)
    one.iloc[100:140] = "phai"  # a single long episode
    t3 = measure.zone_table(one, p, [4], ["phai", "khong"], n_boot=200, seed=1)
    assert t3["zones"]["phai"][4]["episodes"] == 1 and t3["zones"]["phai"][4]["verdict"] == measure.FEW_EPISODES


def test_calibration_shows_probability_only_when_better_than_base_rate():
    rng = np.random.default_rng(4)
    n = 400
    y = (rng.random(n) < 0.5).astype(float)
    good = np.clip(np.where(y == 1, 0.8, 0.2) + rng.normal(0, 0.05, n), 0, 1)
    bad = rng.random(n)
    base = np.full(n, 0.5)
    assert measure.calibration(good, base, y, 4, 300, 1)["show_probability"]
    assert not measure.calibration(bad, base, y, 4, 300, 1)["show_probability"]


def test_cost_basis_with_cash_equals_equity_ratio_minus_one():
    p = _walk(200)
    c = SimConfig(m_min=0.5, m_max=1.5, reserve_cap_weeks=1e9, fee=0.001, slippage=0.0005)
    m = np.where(np.arange(200) % 8 < 4, 0.5, 1.5)
    s, d = simulate(p, m, c), simulate(p, None, c)
    eff_cost_s = s.contributed[0, -1] / (s.btc[0, -1] + s.cash[0, -1] / p[-1])
    cost_d = d.contributed[0, -1] / (d.btc[0, -1] + d.cash[0, -1] / p[-1])
    assert cost_d / eff_cost_s - 1 == pytest.approx(measure.cost_basis_with_cash(float(metrics.equity_ratio(s, d)[0])))
    assert s.cash.min() >= -1e-9  # never borrows
