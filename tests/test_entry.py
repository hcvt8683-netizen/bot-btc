# -*- coding: utf-8 -*-
"""Entry-timing tests (bot/models/entry_timing.py): no look-ahead in the lowest-price percentiles nor in the cheapest-day
shares, the rolling window equals a direct computation, touch chances are calibrated on a synthetic random walk, the
wait-or-buy-now rule is computed as registered, and the log only appends genuine forecasts once per anchor day."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.models import entry_timing as et

CFG = {"horizons_days": [1, 7, 30], "vol_days": 30, "window_days": 1461, "min_obs": 365, "check_from": "2016-01-01",
       "touch": {"show_discounts": [0.0, 0.02, 0.05]}, "wait": {"discounts": [0.02, 0.05], "days": [1, 7]}, "cheapest_day": {"days": 7}}


def walk(n=3000, seed=3):
    """Daily closes of a random walk with slowly changing volatility, and a low below each close inside the day."""
    rng = np.random.default_rng(seed)
    vol = 0.03 * np.exp(0.5 * np.sin(np.arange(n) / 200))
    close = 100 * np.exp(np.cumsum(rng.normal(0.0005, vol)))
    prev = np.r_[close[0], close[:-1]]
    low = np.minimum(prev, close) * np.exp(-np.abs(rng.normal(0, vol * 0.6)))
    return pd.DataFrame({"low": low, "close": close}, index=pd.date_range("2012-01-01", periods=n, freq="D"))


def test_next_min_and_lowest_day_look_only_at_the_next_candles():
    d = walk(60)
    m, pos = et.next_min(d["low"], 7), et.lowest_day(d["low"], 7)
    for i in (0, 10, 52):
        seg = d["low"].iloc[i + 1:i + 8].to_numpy()
        assert np.isclose(m.iloc[i], seg.min()) and pos.iloc[i] == seg.argmin() + 1
    assert m.iloc[-7:].isna().all() and pos.iloc[-7:].isna().all()


def test_percentiles_and_shares_use_only_candles_up_to_the_anchor():
    d = walk()
    T = d.index[2500]
    a = {k: et.z_quantiles(d, k, CFG).loc[T] for k in CFG["horizons_days"]}
    sa = et.day_shares(d["low"], CFG).loc[T]
    e = d.copy()
    e.loc[e.index > T] *= 0.25  # crash every later candle
    e.loc[e.index > T, "low"] *= 0.5
    for k in a:
        pd.testing.assert_series_equal(a[k], et.z_quantiles(e, k, CFG).loc[T])
    pd.testing.assert_series_equal(sa, et.day_shares(e["low"], CFG).loc[T])
    f = et.forecast(d.loc[:T], CFG)
    assert f["anchor"] == T.strftime("%Y-%m-%d") and f == et.forecast(e.loc[:T], CFG)


def test_rolling_window_matches_a_direct_computation():
    d = walk()
    k, T = 7, d.index[2600]
    i = d.index.get_loc(T)
    sig = np.log(d["close"]).diff().rolling(30).std()
    lo, c = d["low"].to_numpy(), d["close"].to_numpy()
    z = [np.log(lo[t + 1:t + k + 1].min() / c[t]) / (sig.iloc[t] * np.sqrt(k)) for t in range(i - 1461 + 1, i - k + 1)]
    want = np.quantile(z, [0.01, 0.1, 0.5, 0.9, 0.99])
    got = et.z_quantiles(d, k, CFG).loc[T][[0.01, 0.1, 0.5, 0.9, 0.99]].to_numpy()
    assert np.allclose(got, want)
    pos = [lo[t + 1:t + 8].argmin() + 1 for t in range(i - 1461 + 1, i - 7 + 1)]
    sh = et.day_shares(d["low"], CFG).loc[T]
    assert np.allclose(sh.to_numpy(), [np.mean(np.array(pos) == j) for j in range(1, 8)])


def test_touch_chances_are_calibrated_on_a_random_walk():
    res = et.check(walk(4000, seed=11), CFG)
    for k in (1, 7):
        r = res[k]
        assert 0.75 < r["cover80"] < 0.85 and abs(r["cover"]["50"] - 0.5) < 0.06
        for p in r["probs"]:
            assert abs(p["pred"] - p["actual"]) < 0.05
        assert r["brier"] <= r["brier_raw"] + 0.01


def test_touch_prob_interpolates_and_holds_at_the_ends():
    q = np.linspace(-2, 2, 99)[None, :]
    assert np.isclose(et.touch_prob(np.array([0.0]), q)[0], 0.5)
    assert et.touch_prob(np.array([-9.0]), q)[0] == 0.01 and et.touch_prob(np.array([9.0]), q)[0] == 0.99


def test_wait_rule_as_registered():
    d = walk(3000)
    res = et.wait(d, CFG, n_boot=200)
    r = next(x for x in res["rows"] if x["k"] == 1 and x["x"] == 0.02)
    start = pd.Timestamp("2016-01-01")
    c, lo = d["close"], d["low"]
    g = []
    for t in range(len(d) - 1):
        if d.index[t] < start:
            continue
        order = c.iloc[t] * 0.98
        paid = order if lo.iloc[t + 1] <= order else c.iloc[t + 1]
        g.append(c.iloc[t] / paid - 1)
    assert r["n"] == len(g) and np.isclose(r["mean"], np.mean(g)) and r["ci"][0] <= r["mean"] <= r["ci"][1]
    assert res["n_configs"] == 4 and all(x["p_holm"] >= x["p"] for x in res["rows"]) and {x["verdict"] for x in res["rows"]} <= {"cho", "ngay", "chua"}


def test_log_appends_once_per_anchor_and_only_open_horizons(tmp_path):
    d = walk(2000)
    log = tmp_path / "e.csv"
    T = d.index[-1]
    now = T + pd.Timedelta(days=1, hours=1)  # the day after the anchor: the 1-day candle closes at T + 2 days 00:00
    rows = et.log_today(d, CFG, now, log)
    assert [int(r["k"]) for r in rows] == [1, 7, 30]
    first = log.read_bytes()
    assert et.log_today(d, CFG, now, log) == [] and log.read_bytes() == first
    late = et.log_today(d.iloc[:-1], CFG, d.index[-1] + pd.Timedelta(days=1), log)  # an older anchor run late: its 1-day candle already closed
    assert [int(r["k"]) for r in late] == [7, 30] and log.read_bytes().startswith(first)
    e = pd.concat([d, pd.DataFrame({"low": [d["close"].iloc[-1] * 0.99], "close": [d["close"].iloc[-1]]}, index=[T + pd.Timedelta(days=1)])])
    s = et.score_log(e, log)
    assert s["rows"] == 5 and s["matured"] == 1 and isinstance(s["recent"][0]["in80"], bool)
