# -*- coding: utf-8 -*-
"""Calibrated probability tests: a week's probability uses only labels known at that week (changing prices or features
from that week on changes nothing), and the bins method is shrunk toward the base rate."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.models import calib_prob as cp


def table(n=420, seed=5):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2015-01-04", periods=n, freq="W-SUN")
    t = pd.DataFrame({"exec_monday": 100 * np.exp(np.cumsum(rng.normal(0.004, 0.08, n)))}, index=idx)
    for f in cp.FEATS:
        t[f] = rng.random(n)
    return t


def test_probabilities_never_use_data_from_their_week_on():
    t = table()
    for h in (4, 26):
        a = cp.predictions(t, h)
        for j in (250, 300, 380):
            u = t.copy()
            u.iloc[j:, 0] *= np.linspace(0.2, 5, len(u) - j)  # prices from week j on (the Monday after week j decides labels of week j - h)
            u.iloc[j + 1:, 1:] = 0.99
            b = cp.predictions(u, h)
            pd.testing.assert_series_equal(a.iloc[j][["base", "bins", "logit"]], b.iloc[j][["base", "bins", "logit"]], check_names=False)


def test_bins_are_shrunk_toward_the_base_rate():
    p = cp.predictions(table(), 13).dropna(subset=["base", "bins"])
    assert ((p["bins"] - p["base"]).abs() < 0.5).all() and p["bins"].between(0, 1).all()


def test_return_quantiles_never_use_data_from_their_week_on():
    t = table()
    for h in (4, 52):
        a = cp.ret_predictions(t, h)
        for j in (250, 300, 380):
            u = t.copy()
            u.iloc[j:, 0] *= np.linspace(0.2, 5, len(u) - j)
            u.iloc[j + 1:, 1:] = 0.99
            b = cp.ret_predictions(u, h)
            cols = [c for c in a.columns if c != "r"]
            pd.testing.assert_series_equal(a.iloc[j][cols], b.iloc[j][cols], check_names=False)


def test_pinball_loss_is_lowest_at_the_true_quantiles():
    r = np.random.default_rng(1).normal(0, 1, 20000)
    true = np.quantile(r, cp.QS)
    best = cp.pinball(np.tile(true, (len(r), 1)), r).mean()
    for shift in (-0.3, 0.3):
        assert cp.pinball(np.tile(true + shift, (len(r), 1)), r).mean() > best
