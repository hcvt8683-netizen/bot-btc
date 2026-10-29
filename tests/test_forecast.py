# -*- coding: utf-8 -*-
"""Price-band forecast tests: no look-ahead, the rolling window equals a direct computation, bands are calibrated on a
synthetic random walk, and the log only appends genuine (future-target) forecasts once per anchor day."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.models import price_forecast as pf

CFG = {"horizons_days": [1, 7, 30], "quantiles": [0.10, 0.25, 0.50, 0.75, 0.90], "vol_days": 30, "window_days": 1461, "min_obs": 365, "check_from": "2016-01-01"}


def walk(n=3000, seed=3):
    rng = np.random.default_rng(seed)
    vol = 0.03 * np.exp(0.5 * np.sin(np.arange(n) / 200))  # slowly changing volatility
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0005, vol))), index=pd.date_range("2012-01-01", periods=n, freq="D"))


def test_bands_use_only_prices_up_to_the_anchor():
    p = walk()
    T = p.index[2500]
    a = {k: pf.bands(p, k, CFG).loc[T] for k in CFG["horizons_days"]}
    q = p.copy()
    q[q.index > T] *= 4
    b = {k: pf.bands(q, k, CFG).loc[T] for k in CFG["horizons_days"]}
    for k in a:
        pd.testing.assert_series_equal(a[k], b[k])


def test_rolling_window_matches_a_direct_computation():
    p = walk()
    k, T = 7, p.index[2600]
    i = p.index.get_loc(T)
    lr = np.log(p).diff()
    sig = lr.rolling(30).std()
    z = [np.log(p.iloc[t + k] / p.iloc[t]) / (sig.iloc[t] * np.sqrt(k)) for t in range(i - 1461 + 1, i - k + 1)]
    want = p.iloc[i] * np.exp(np.quantile(z, [0.1, 0.5, 0.9]) * sig.iloc[i] * np.sqrt(k))
    got = pf.bands(p, k, CFG).loc[T][["q10", "q50", "q90"]].to_numpy()
    assert np.allclose(got, want)


def test_bands_are_calibrated_on_a_random_walk():
    res = pf.check(walk(4000, seed=11), CFG)
    for k in (1, 7):
        assert 0.75 < res[k]["vol"]["cover80"] < 0.85 and 0.44 < res[k]["vol"]["cover50"] < 0.56


def test_log_appends_once_per_anchor_and_only_future_targets(tmp_path):
    p = walk(2000)
    log = tmp_path / "f.csv"
    T = p.index[-1]
    now = T + pd.Timedelta(days=1, hours=1)  # the day after the anchor: the 1-day target closes at T + 2 days 00:00
    rows = pf.log_today(p, CFG, now, log)
    assert [int(r["k"]) for r in rows] == [1, 7, 30]
    first = log.read_bytes()
    assert pf.log_today(p, CFG, now, log) == [] and log.read_bytes() == first  # same anchor: nothing new
    late = pf.log_today(p.iloc[:-1], CFG, p.index[-1] + pd.Timedelta(days=1), log)  # an older anchor run late: its 1-day target already closed
    assert [int(r["k"]) for r in late] == [7, 30] and log.read_bytes().startswith(first)
    q = pd.concat([p, pd.Series([p.iloc[-1] * 1.01], index=[T + pd.Timedelta(days=1)])])
    s = pf.score_log(q, log)
    assert s["rows"] == 5 and s["matured"] >= 1 and all(isinstance(r["in80"], bool) for r in s["recent"])


def test_search_reproduces_the_method_in_use_and_never_looks_ahead():
    from bot.models import forecast_search as fs
    p = walk()
    cur = {"vol": "std30", "window": 1461, "center": "empirical", "dist": "empirical"}
    lq = fs.log_quantiles(p, 7, cur, CFG["min_obs"])
    b = pf.bands(p, 7, CFG)
    T = p.index[2600]
    assert np.allclose(np.exp(lq.loc[T].to_numpy()), b.loc[T][["q10", "q25", "q50", "q75", "q90"]].to_numpy())
    q = p.copy()
    q[q.index > T] *= 3
    for v in ({"vol": "ewma94", "window": "all", "center": "zero", "dist": "empirical"}, {"vol": "none", "window": 730, "center": "empirical", "dist": "empirical"},
              {"vol": "std60", "window": None, "center": "zero", "dist": "normal"}):
        assert np.allclose(fs.log_quantiles(p, 30, v).loc[T].to_numpy(), fs.log_quantiles(q, 30, v).loc[T].to_numpy())
