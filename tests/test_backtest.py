# -*- coding: utf-8 -*-
"""Backtest engine and metrics tests on synthetic paths (no network, deterministic)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.backtest import baselines, metrics
from bot.backtest.engine import SimConfig, simulate
from bot.validation import splits

C = SimConfig(budget=100, m_min=0.25, m_max=2.0, reserve_cap_weeks=12, fee=0.001, slippage=0.0005)


def sine_path(n: int = 208) -> np.ndarray:
    t = np.arange(n)
    return 20000 * np.exp(0.004 * t + 0.5 * np.sin(2 * np.pi * t / 104))


def test_dca_equals_itself_and_costs_are_applied():
    p = sine_path()
    r = metrics.summary(p, np.ones(len(p)), C)
    assert r["equity_ratio"] == pytest.approx(1.0) and r["cba"] == pytest.approx(0.0) and r["idle_avg"] == 0
    d = simulate(p, None, C)
    assert d.btc[0, -1] == pytest.approx(np.sum(100 * (1 - 0.001) / (p * 1.0005)))
    assert d.contributed[0, -1] == 100 * len(p) and d.cash[0, -1] == pytest.approx(0)


def test_multiplier_clipped_never_zero_and_reserve_capped():
    p = sine_path()
    s = simulate(p, np.zeros(len(p)), C)  # asks for 0 → clipped to 0.25
    assert s.mult.min() == pytest.approx(0.25) and s.amount.min() > 0
    assert s.reserve_before.max() <= (12 + 0.75) * 100 + 1e-9  # forced m ≥ 1 once reserve > 12 B
    s2 = simulate(p, np.full(len(p), 5.0), C)  # asks for 5 → 2.0, limited by cash
    assert s2.mult.max() == pytest.approx(2.0) and (s2.cash >= -1e-9).all()


def test_buying_more_when_cheap_beats_dca():
    p = sine_path()
    trend = np.exp(0.004 * np.arange(len(p))) * 20000
    m = np.where(p < trend, 2.0, 0.25)  # cheap vs trend → buy more
    r = metrics.summary(p, m, C)
    assert r["equity_ratio"] > 1.01 and r["cba"] > 0.01  # all cash deployed, so ratio ≈ 1 + CBA
    bad = metrics.summary(p, np.where(p < trend, 0.25, 2.0), C)
    assert bad["equity_ratio"] < 1 and bad["cba"] < 0


def test_rolling_windows_are_independent_simulations():
    p = sine_path(300)
    dates = pd.date_range("2015-01-06", periods=300, freq="7D")
    m = np.where(np.arange(300) % 10 < 5, 2.0, 0.5)
    df = metrics.rolling(dates, p, m, dates[0], dates[-1], window=104, step=4, cfg_=C)
    assert len(df) == len(range(0, 300 - 104 + 1, 4))
    first = metrics.summary(p[:104], m[:104], C)
    assert df["equity_ratio"].iloc[0] == pytest.approx(first["equity_ratio"])
    s = metrics.roll_summary(df)
    assert s["er_p10"] <= s["er_median"]


def test_twr_drawdown_matches_price_for_dca():
    p = np.array([100, 50, 100, 25, 50, 100.0])
    r = metrics.twr(simulate(p, None, SimConfig(fee=0, slippage=0)))[0]
    assert r[0] == pytest.approx(-0.5) and metrics.drawdown_stats(np.r_[r, r])["mdd"] == pytest.approx(-0.75)


def test_win_rate_counts_episodes_and_wilson():
    p = np.array([1, 2, 3, 2, 1, 2, 3, 4.0])
    mask = np.array([1, 1, 0, 0, 1, 1, 0, 0], dtype=bool)
    w = metrics.win_rate(p, mask, 1)
    assert w["n"] == 4 and w["episodes"] == 2 and w["win"] == 1.0 and w["lo"] < 1


def test_current_bot_join_is_point_in_time():
    dates = pd.DatetimeIndex(["2022-06-21", "2022-06-28", "2022-07-26"])  # Tuesdays
    scores = pd.DataFrame({"date": pd.to_datetime(["2022-06-19", "2022-06-26"]), "buy": [85.0, 65.0]})
    m, s = baselines.current_bot(scores, dates)
    assert list(s[:2]) == [85.0, 65.0] and list(m) == [2.0, 1.25, 1.0]  # last one: score too old → DCA
    late = pd.DataFrame({"date": pd.to_datetime(["2022-06-20"]), "buy": [90.0]})  # Monday score → available Wed
    assert np.isnan(baselines.current_bot(late, dates[:1])[1][0])


def test_holdout_is_locked():
    assert splits.dev_end() == pd.Timestamp("2022-12-31")
    with pytest.raises(splits.HoldoutLocked):
        splits.guard(pd.Timestamp("2023-01-03"))
    splits.guard(pd.Timestamp("2023-01-03"), final=True)
    cyc = splits.cycles(pd.Timestamp("2022-12-31"))
    assert [c[3] for c in cyc] == [True, True, True, False] and cyc[-1][2] == pd.Timestamp("2022-12-31")
