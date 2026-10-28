# -*- coding: utf-8 -*-
"""Validation toolkit tests: folds with purge/embargo, bootstrap, placebo, registry, Deflated Sharpe Ratio."""
from __future__ import annotations

import numpy as np
import pytest

from bot.validation import bootstrap, dsr, placebo, registry, walkforward


def test_folds_purge_overlapping_labels():
    fs = walkforward.folds(400, first_test=200, refit=13, horizon=26, embargo=26)
    assert fs and all(walkforward.check_no_overlap(f, 26) for f in fs)
    assert all(len(b.train) >= len(a.train) for a, b in zip(fs, fs[1:]))  # expanding
    assert all(len(f.test) == 13 for f in fs[:-1]) and fs[0].test[0] == 200 and fs[0].train.max() == 200 - 26 - 1
    f52 = walkforward.folds(400, first_test=200, horizon=52, embargo=26)
    assert f52[0].train.max() == 200 - 52 - 1  # the longer of horizon and embargo wins


def path(n=312, seed=1):
    rng = np.random.default_rng(seed)
    return 10000 * np.exp(np.cumsum(rng.normal(0.004, 0.08, n)))


def test_bootstrap_is_deterministic_and_dca_is_exactly_one():
    p = path()
    b1 = bootstrap.bootstrap(p, np.ones(len(p)), n=200, seed=3)
    assert b1["er_ci"] == pytest.approx((1.0, 1.0)) and b1["cba_ci"] == pytest.approx((0.0, 0.0), abs=1e-12)
    m = np.where(np.arange(len(p)) % 20 < 10, 2.0, 0.5)
    a, b = bootstrap.bootstrap(p, m, n=200, seed=3), bootstrap.bootstrap(p, m, n=200, seed=3)
    assert a == b and a["er_ci"][0] <= a["er_median"] <= a["er_ci"][1]


def test_placebo_ranks_good_timing_high():
    p = path()
    trend = np.exp(np.convolve(np.log(p), np.ones(26) / 26, mode="same"))
    good = np.where(p < trend, 2.0, 0.25)
    assert placebo.placebo(p, good, n=300, seed=1)["percentile"] > 0.9
    flat = placebo.placebo(p, np.ones(len(p)), n=50, seed=1)
    assert flat["percentile"] == pytest.approx(0.5)  # all placebos tie with the real series


def test_registry_counts_trials(tmp_path):
    f = tmp_path / "reg.csv"
    registry.log("a", "dev", ["mvrv"], {"k": 1}, {"er": 1.01, "sr_active": 0.05}, path=f)
    registry.log("b", "dev", "pi+mvrv", {"k": 2}, {"er": 0.99, "sr_active": -0.02}, path=f)
    assert registry.n_trials(f) == 2 and registry.sharpes(f) == [0.05, -0.02]
    assert registry.rows(f)[1]["features"] == "pi+mvrv"


def test_deflated_sharpe_penalises_many_trials():
    rng = np.random.default_rng(0)
    r = rng.normal(0.002, 0.01, 520)
    one = dsr.deflated_sharpe(r, 1, 0.0)
    many = dsr.deflated_sharpe(r, 100, 0.01 ** 2 * 4)
    assert one["sr0"] == 0 and 0.5 < one["dsr"] <= 1 and many["dsr"] < one["dsr"]
    assert dsr.expected_max_sr(100, 0.04) == pytest.approx(0.2 * ((1 - dsr.EULER) * 2.326348 + dsr.EULER * 2.680210), rel=1e-3)
