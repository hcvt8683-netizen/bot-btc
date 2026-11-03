# -*- coding: utf-8 -*-
"""Bands by volatility regime: the method in use is reproduced exactly, no variant looks ahead (prices or groups after the
anchor change nothing), the groups are thirds of past volatility, and a group with too few known windows falls back to the
pooled quantiles."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.models import forecast_regime as fr
from bot.models import price_forecast as pf

F = {"horizons_days": [1, 7, 30], "quantiles": [0.10, 0.25, 0.50, 0.75, 0.90], "vol_days": 30, "window_days": 1461, "min_obs": 365}
R = {"vol_long_days": 365, "groups": 3, "group_min_obs": 120}


def walk(n=3200, seed=5):
    rng = np.random.default_rng(seed)
    vol = 0.03 * np.exp(0.6 * np.sin(np.arange(n) / 150))  # volatility that swings between calm and turbulent
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, vol))), index=pd.date_range("2012-01-01", periods=n, freq="D"))


def test_method_in_use_is_reproduced_exactly():
    p = walk()
    for k in (1, 7, 30):
        lq = fr.log_quantiles(p, k, "hien_tai", F, R)
        b = pf.bands(p, k, F)
        T = p.index[2800]
        assert np.allclose(np.exp(lq.loc[T].to_numpy()), b.loc[T][["q10", "q25", "q50", "q75", "q90"]].to_numpy())


def wild_future(p: pd.Series, T: pd.Timestamp) -> pd.Series:
    """Same past; from the day after T the price jumps ×3 / ÷3 every day (the volatility of tomorrow is extreme)."""
    q = p.copy()
    n = int((q.index > T).sum())
    q[q.index > T] = q[q.index > T] * 3.0 ** np.where(np.arange(n) % 2 == 0, 1, -1)
    return q


def calm_day(p: pd.Series, start: int = 2600) -> pd.Timestamp:
    g = fr.vol_group(p, F, R)
    return next(t for t in p.index[start:] if g.loc[t] == 0)


def test_no_variant_uses_prices_after_the_anchor():
    p = walk()
    T = calm_day(p)  # a calm day: a leak of tomorrow's volatility would move it to another group
    q = wild_future(p, T)
    for v in fr.VARIANTS:
        for k in (1, 7, 30):
            a = fr.log_quantiles(p, k, v, F, R).loc[T].to_numpy()
            b = fr.log_quantiles(q, k, v, F, R).loc[T].to_numpy()
            assert np.allclose(a, b), (v, k)


def test_groups_are_thirds_of_past_volatility():
    p = walk()
    g = fr.vol_group(p, F, R)
    assert set(g.dropna().unique()) <= {0.0, 1.0, 2.0}
    T = calm_day(p)
    assert fr.vol_group(wild_future(p, T), F, R).loc[:T].equals(g.loc[:T])
    s = fr.vol(p, 30)
    i = p.index.get_loc(T)
    rank = (s.iloc[i - 1460:i + 1] <= s.iloc[i]).mean()
    assert g.loc[T] == min(2, int(np.ceil(rank * 3)) - 1)


def test_group_quantiles_match_a_direct_computation():
    p = walk()
    k, T = 7, calm_day(p, 2800)
    i = p.index.get_loc(T)
    s, g = fr.vol(p, 30), fr.vol_group(p, F, R)
    z = [np.log(p.iloc[t + k] / p.iloc[t]) / (s.iloc[t] * np.sqrt(k)) for t in range(i - 1461 + 1, i - k + 1) if g.iloc[t] == g.iloc[i]]
    assert len(z) >= R["group_min_obs"]
    want = np.log(p.iloc[i]) + np.quantile(z, [0.1, 0.5, 0.9]) * s.iloc[i] * np.sqrt(k)
    assert np.allclose(fr.log_quantiles(p, k, "theo_nhom", F, R).loc[T][[0.1, 0.5, 0.9]].to_numpy(), want)


def test_small_group_falls_back_to_pooled_quantiles():
    p = walk()
    lone = pd.Series(0.0, index=p.index)
    lone.iloc[-1] = 2.0  # group 2 exists only today: no known window in it
    k = 7
    a = fr.log_quantiles(p, k, "theo_nhom", F, R, group=lone).iloc[-1]
    b = fr.log_quantiles(p, k, "hien_tai", F, R).iloc[-1]
    assert np.allclose(a.to_numpy(), b.to_numpy())
    same = fr.log_quantiles(p, k, "theo_nhom", F, R, group=pd.Series(0.0, index=p.index)).iloc[-1]  # one group = pooled
    assert np.allclose(same.to_numpy(), b.to_numpy())


def test_blend_uses_both_volatilities():
    p = walk()
    T = p.index[2900]
    same = fr.log_quantiles(p, 7, "tron", F, {**R, "vol_long_days": 30}).loc[T]  # blending a volatility with itself changes nothing
    assert np.allclose(same.to_numpy(), fr.log_quantiles(p, 7, "hien_tai", F, R).loc[T].to_numpy())
    lq = fr.log_quantiles(p, 7, "tron", F, R).loc[T]
    assert lq.notna().all() and lq.is_monotonic_increasing and not np.allclose(lq.to_numpy(), same.to_numpy())


def test_price_forecast_uses_the_registered_blend():
    p = walk()
    Fb = {**F, "vol_long_days": 365}
    T = calm_day(p, 2800)
    for k in (1, 7, 30):
        b = pf.bands(p, k, Fb).loc[T][["q10", "q25", "q50", "q75", "q90"]].to_numpy()
        assert np.allclose(np.exp(fr.log_quantiles(p, k, "tron", F, R).loc[T].to_numpy()), b)
        c = pf.bands(wild_future(p, T), k, Fb).loc[T][["q10", "q25", "q50", "q75", "q90"]].to_numpy()
        assert np.allclose(b, c)  # the blend never reads a price after the anchor
    assert pf.spec().get("vol_long_days") == 365  # the page uses the method that passed (docs/FORECAST_REGIME.md)
