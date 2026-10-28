# -*- coding: utf-8 -*-
"""Feature and layer A tests: point-in-time normalization, causal daily features, decision-time join, models."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.features import catalogue, normalize
from bot.models import core


def test_percentile_is_point_in_time_and_needs_history():
    rng = np.random.default_rng(0)
    x = pd.Series(rng.normal(size=400))
    p = normalize.pit_percentile(x)
    assert p.iloc[:103].isna().all() and p.iloc[103:].between(0, 1).all()
    p_cut = normalize.pit_percentile(x.iloc[:250])
    assert np.allclose(p.iloc[:250].to_numpy(), p_cut.to_numpy(), equal_nan=True)  # adding future values changes nothing
    up = normalize.pit_percentile(pd.Series(np.arange(300.0)))
    assert up.iloc[-1] == pytest.approx(1.0) and normalize.cheapness(up, "low").iloc[-1] == pytest.approx(0.0)


def synthetic_cm(n=2000, seed=1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    d = pd.date_range("2012-01-01", periods=n, freq="D")
    p = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, n)))
    mvrv = 1.5 + 0.5 * np.sin(np.arange(n) / 200)
    hashrate = np.exp(np.arange(n) / 500) * (1 + 0.2 * np.sin(np.arange(n) / 40))
    return pd.DataFrame({"date": d, "price": p, "mcap": p * 1e7, "mvrv": mvrv, "hashrate": hashrate, "iss_usd": p * 900})


def test_daily_features_are_causal():
    cm = synthetic_cm()
    full = catalogue.daily_group_a(cm)
    cut = catalogue.daily_group_a(cm.iloc[:1500])
    cols = ["mvrv", "mvrv_z", "pi_ratio", "p_200wma", "mayer", "puell", "dd_ath", "hash_ribbon_buy"]
    assert np.allclose(full[cols].iloc[:1500].to_numpy(), cut[cols].to_numpy(), equal_nan=True)
    assert full["p_200wma"].iloc[:1399].isna().all() and np.isfinite(full["p_200wma"].iloc[1399])
    assert full["hash_ribbon_buy"].sum() >= 1


def test_halving_phase_quarters():
    ph = catalogue.halving_phase(pd.DatetimeIndex(["2020-05-11", "2021-06-01", "2024-04-19", "2024-04-20"]))
    assert list(ph) == [0, 1, 3, 0]


def test_composite_and_step_map():
    f = pd.DataFrame({"cheap_a": [0.9, 0.5, np.nan, 0.1], "cheap_b": [0.9, 0.7, 0.5, 0.1]})
    s = core.composite(f, ["a", "b"])
    assert s.iloc[0] == pytest.approx(0.9) and np.isnan(s.iloc[2])
    assert list(core.step_map(s.to_numpy())) == [2.0, 1.25, 1.0, 0.25]


def test_ridge_drops_features_with_unstable_sign():
    rng = np.random.default_rng(3)
    n = 400
    good = rng.uniform(size=n)
    noise = rng.uniform(size=n)
    y = np.r_[0.5 * good[: n - 26] + rng.normal(0, 0.05, n - 26), np.full(26, np.nan)]
    feat = pd.DataFrame({"cheap_good": good, "cheap_noise": noise, "fwd_26": y})
    sc, info = core.ridge_signed(feat, ["good", "noise"], horizons=(26,))
    assert "good" in info["kept"] and info["signs"]["good"] == 1.0
    ok = np.isfinite(sc.to_numpy())
    assert ok.sum() > 100 and np.corrcoef(sc.to_numpy()[ok], good[ok])[0, 1] > 0.5
