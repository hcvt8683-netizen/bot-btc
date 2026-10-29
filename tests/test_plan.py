# -*- coding: utf-8 -*-
"""Deployment plan tests: the money arithmetic, the use of only the prices inside each one-year window, and the
pre-registered choice (best median; recommended = highest 10th percentile among plans not significantly worse)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import deploy_plan as dp

PC = {"options_weeks": [1, 4, 13, 26, 52], "horizon_weeks": 52}
FEE, SLIP = 0.001, 0.0005


def test_flat_price_costs_only_fees_and_lump_sum_follows_the_price():
    flat = np.full(200, 100.0)
    for n in PC["options_weeks"]:
        roi, mdd = dp.outcomes(flat, np.array([0, 10]), n, 52, FEE, SLIP)
        assert roi == pytest.approx((1 - FEE) / (1 + SLIP) - 1) and (mdd <= 0).all() and mdd.min() > -0.002
    up = 100 * 1.01 ** np.arange(200)
    lump, _ = dp.outcomes(up, np.array([5]), 1, 52, FEE, SLIP)
    assert lump[0] == pytest.approx(up[57] / up[5] * (1 - FEE) / (1 + SLIP) - 1)
    dca, _ = dp.outcomes(up, np.array([5]), 26, 52, FEE, SLIP)
    assert dca[0] < lump[0]  # in a rising market investing at once wins


def test_each_start_reads_only_its_own_year():
    rng = np.random.default_rng(4)
    p = 100 * np.exp(np.cumsum(rng.normal(0.003, 0.08, 300)))
    a, ma = dp.outcomes(p, np.array([20]), 13, 52, FEE, SLIP)
    q = p.copy()
    q[73:] *= 7  # after week 20 + 52
    q[:20] /= 3  # before the start
    b, mb = dp.outcomes(q, np.array([20]), 13, 52, FEE, SLIP)
    assert a[0] == b[0] and ma[0] == mb[0]


def test_choice_follows_the_registered_rule():
    rng = np.random.default_rng(7)
    idx = pd.date_range("2015-01-04", periods=520, freq="W-SUN")
    t = pd.DataFrame({"exec_monday": 100 * np.exp(np.cumsum(rng.normal(0.006, 0.09, len(idx))))}, index=idx)
    r = dp.compute(t, PC, FEE, SLIP, n_boot=300, seed=1, data_from=pd.Timestamp("2016-01-01"))
    o = {x["weeks"]: x for x in r["options"]}
    assert r["best_roi"] == max(o, key=lambda n: o[n]["median"])
    ok = [n for n, x in o.items() if x["not_worse"]]
    assert r["best_roi"] in ok and r["recommended"] == max(ok, key=lambda n: o[n]["p10"])
    assert r["starts"] == len(dp.start_weeks(t, 52, pd.Timestamp("2016-01-01"))) and r["episodes"] == r["starts"] // 52
    assert o[1]["beat_lump"] is None and all(0 <= o[n]["beat_lump"] <= 1 for n in (4, 13, 26, 52))
    short = dp.compute(t.iloc[:120], PC, FEE, SLIP, n_boot=50, seed=1, data_from=pd.Timestamp("2016-01-01"))
    assert short["options"] == []  # too few start weeks: no plan rather than a guess
