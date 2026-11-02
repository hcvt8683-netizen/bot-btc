# -*- coding: utf-8 -*-
"""Long/Short tests (bot/models/perp_signal.py): states use only data up to t (and a planted look-ahead is caught), the
net gain counts fee, slippage and only the funding inside (t, t + horizon], non-overlapping counts, daily candles from
hourly ones, and the registered verdict."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import perp_signal as ps

CFG = {**ps.spec(), "states": {**ps.spec()["states"], "lookback_days": 20, "min_days": 10}}


def walk(days=60, seed=5) -> pd.DataFrame:
    """Hourly candles of a random walk (index = candle close time)."""
    rng = np.random.default_rng(seed)
    n = days * 24
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    prev = np.r_[close[0], close[:-1]]
    hi = np.maximum(prev, close) * np.exp(np.abs(rng.normal(0, 0.002, n)))
    lo = np.minimum(prev, close) * np.exp(-np.abs(rng.normal(0, 0.002, n)))
    return pd.DataFrame({"high": hi, "low": lo, "close": close}, index=pd.date_range("2024-01-01 01:00", periods=n, freq="h"))


def fund(index: pd.DatetimeIndex, seed=7) -> tuple[pd.Series, pd.Series]:
    rng = np.random.default_rng(seed)
    mark = pd.Series((index.hour % 8 == 0).astype(float), index=index)
    return pd.Series(np.where(mark > 0, rng.normal(1e-4, 1e-4, len(index)), 0.0), index=index), mark


def all_states(h: pd.DataFrame, rate: pd.Series, mark: pd.Series, H: int = 6) -> pd.DataFrame:
    f24 = ps.funding_24h(rate, mark, rate.index[-1])
    return ps.candle_states(h["close"], H, 24, CFG).assign(funding=ps.funding_state(f24, CFG))


def test_states_use_only_data_up_to_t():
    h = walk()
    rate, mark = fund(h.index)
    T = h.index[1000]
    a = all_states(h, rate, mark).loc[:T]
    e, r2 = h.copy(), rate.copy()
    e.loc[e.index > T] *= 0.3            # crash every later candle
    r2.loc[r2.index > T] *= -50          # and flip the later funding
    b = all_states(e, r2, mark).loc[:T]
    pd.testing.assert_frame_equal(a, b)
    assert a.iloc[-1].notna().all()


def test_a_planted_look_ahead_is_caught(monkeypatch):
    """Thresholds from a window centred on t (it sees the future) must make the check above fail."""
    monkeypatch.setattr(ps, "_past_q", lambda x, q, w, minp: x.rolling(w, min_periods=minp, center=True).quantile(q))
    h = walk()
    rate, mark = fund(h.index)
    T = h.index[1000]
    e = h.copy()
    e.loc[e.index > T] *= 0.3
    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(all_states(h, rate, mark).loc[:T], all_states(e, rate, mark).loc[:T])


def test_net_gain_as_registered():
    idx = pd.date_range("2024-01-01 01:00", periods=6, freq="h")
    d = pd.DataFrame({"close": [100, 101, 103, 102, 104, 105], "high": [100, 102, 104, 103, 105, 106],
                      "low": [99, 100, 98, 101, 103, 104]}, index=idx, dtype=float)
    rate = pd.Series(0.0, index=idx)
    rate.iloc[2] = 0.001   # inside (t, t + 2] for t = idx[0]
    rate.iloc[0] = 0.5     # at t itself: not paid by a trade opened at t
    o = ps.outcomes(d, 2, 2, rate, idx[-1], CFG)
    cost = 2 * (CFG["costs"]["fee"] + CFG["costs"]["slippage"])
    assert o["long"].iloc[0] == pytest.approx(103 / 100 - 1 - cost - 0.001)
    assert o["short"].iloc[0] == pytest.approx(-(103 / 100 - 1) - cost + 0.001)
    assert o["mae_long"].iloc[0] == pytest.approx(1 - 98 / 100) and o["mae_short"].iloc[0] == pytest.approx(104 / 100 - 1)
    assert o[["long", "short"]].iloc[-2:].isna().all().all()  # outcome not known yet
    o2 = ps.outcomes(d, 2, 2, rate, idx[0], CFG)  # funding known only up to idx[0] + 8 h: still fine for these windows
    assert o2["long"].iloc[0] == pytest.approx(o["long"].iloc[0])
    o3 = ps.outcomes(d, 2, 2, rate, None, CFG)
    assert o3["long"].isna().all()


def test_funding_mean_and_unknown_after_the_last_funding_time():
    idx = pd.date_range("2024-01-01 01:00", periods=72, freq="h")
    mark = pd.Series((idx.hour % 8 == 0).astype(float), index=idx)
    rate = pd.Series(np.where(mark > 0, 0.0003, 0.0), index=idx)
    last = idx[mark.to_numpy() > 0][-3]
    f = ps.funding_24h(rate, mark, last)
    assert f.iloc[30] == pytest.approx(0.0003)
    assert f[f.index >= last + pd.Timedelta(hours=8)].isna().all() and f[f.index < last + pd.Timedelta(hours=8)].iloc[-1] == pytest.approx(0.0003)


def test_non_overlapping_count():
    assert ps.non_overlap(np.array([0, 1, 2, 5, 6, 10]), 3) == 3
    assert ps.non_overlap(np.array([0, 1, 2, 3]), 1) == 4
    assert ps.non_overlap(np.array([], dtype=int), 4) == 0


def test_daily_candles_need_all_24_hours():
    h = walk(3)
    d = ps.daily(h.iloc[23:])   # the first close is 2024-01-02 00:00: day 1 complete only from its first hour
    first = ps.daily(h)
    assert first.index[0] == pd.Timestamp("2024-01-02") and first["close"].iloc[0] == h["close"].iloc[23]
    assert first["low"].iloc[0] == h["low"].iloc[:24].min()
    g = h.copy()
    g.iloc[30, 2] = np.nan
    assert np.isnan(ps.daily(g)["close"].iloc[1]) and not np.isnan(ps.daily(g)["close"].iloc[0])
    assert len(d)


def _cell(edge_long=False, edge_short=False, lb=0.4):
    side = lambda e: {"n": 10, "p": 0.6, "ci": [0.5, 0.7], "lb_bonf": lb, "edge": e}  # noqa: E731
    return {"long": side(edge_long), "short": side(edge_short)}


def test_registered_verdict():
    cells = {"moc": _cell(), "trend_tren": _cell(edge_long=True, lb=0.55), "vol_cao": _cell(edge_short=True)}
    assert ps.decide(cells, ["moc", "trend_tren"])["verdict"] == "nen_long"
    assert ps.decide(cells, ["moc", "trend_tren"])["long"]["cell"] == "trend_tren"
    assert ps.decide(cells, ["moc"])["verdict"] == "khong"             # the edge is in a cell that does not match now
    assert ps.decide(cells, ["moc", "trend_tren", "vol_cao"])["verdict"] == "khong"   # both sides: no trade
    assert ps.matched(pd.Series({"trend": "tren", "funding": "giua", "stretch": "giam_manh", "vol": "binh_thuong"})) == \
        ["moc", "trend_tren", "stretch_giam_manh", "vol_binh_thuong"]


def test_edge_needs_bonferroni_and_both_halves():
    z, m = ps.z_bonferroni(ps.spec())
    assert m == 558 and z == pytest.approx(3.745, abs=0.01)
    rng = np.random.default_rng(1)
    pos = np.arange(4000)
    good = rng.normal(0.01, 0.01, 4000)          # wins 84%
    first = pos < 2000
    s = ps.side_stats(good, np.zeros(4000), pos, first, 1, z, [1, 5])
    assert s["edge"] and s["n_eff"] == 4000 and s["lev"]["liq"] == [0.0, 0.0]
    bad_half = good.copy()
    bad_half[2000:] *= -1                        # second half loses
    assert not ps.side_stats(bad_half, np.zeros(4000), pos, first, 1, z, [1])["edge"]
    coin = rng.normal(0.0, 0.01, 4000)
    assert not ps.side_stats(coin, np.zeros(4000), pos, first, 1, z, [1])["edge"]
    few = ps.side_stats(good[:30], np.full(30, 0.02), pos[:30] * 10, first[:30], 24, z, [1, 5])
    assert few["n_eff"] == 10 and few["lev"]["liq"] == [1.0, 0.0] and few["lev"]["mean"][0] == 0.0  # 0, 30, 60, …, 270
