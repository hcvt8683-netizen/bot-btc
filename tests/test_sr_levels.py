# -*- coding: utf-8 -*-
"""Support / resistance by frame (bot/models/sr_levels.py): levels and touches use only candles up to the touch (a
planted look-ahead is caught), outcomes match a plain candle-by-candle loop of the registered rules (a candle that both
bounces and breaks is a break), episodes follow the registered rule, the placebo only looks back, and the verdict."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import sr_levels as sr

CFG = sr.spec()


def walk(n=3000, seed=4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    prev = np.r_[c[0], c[:-1]]
    hi = np.maximum(prev, c) * np.exp(np.abs(rng.normal(0, 0.006, n)))
    lo = np.minimum(prev, c) * np.exp(-np.abs(rng.normal(0, 0.006, n)))
    return pd.DataFrame({"high": hi, "low": lo, "close": c}, index=pd.date_range("2016-01-01", periods=n, freq="D"))


def test_frames_are_the_registered_ones():
    fr = sr.frames(CFG)
    assert len(fr) * 2 == 102
    assert fr[0] == {"unit": "gio", "n": 1, "candles": "1h", "W": 1, "H": 6}
    assert [f["W"] for f in fr if f["unit"] == "ngay"][-1] == 168 and [f["H"] for f in fr if f["unit"] == "thang"][-1] == 60


@pytest.mark.parametrize("W", [5, 20])
def test_levels_and_touches_use_only_candles_up_to_the_touch(W):
    d = walk()
    T = 1800
    a = d.copy()
    for factor in (0.5, 2.0):                         # every later candle falls, or jumps
        b = d.copy()
        b.iloc[T + 1:] *= factor
        for x, y in zip(sr.levels(a, W), sr.levels(b, W)):
            pd.testing.assert_series_equal(x.iloc[:T + 1], y.iloc[:T + 1])
        for side in sr.SIDES:
            ua = sr.touches(a, sr.levels(a, W)[0 if side == "R" else 1].to_numpy(), sr.levels(a, W)[2].to_numpy(), side, CFG)
            ub = sr.touches(b, sr.levels(b, W)[0 if side == "R" else 1].to_numpy(), sr.levels(b, W)[2].to_numpy(), side, CFG)
            assert list(ua[ua <= T]) == list(ub[ub <= T]) and (ua <= T).sum() > 10


def test_a_planted_look_ahead_is_caught(monkeypatch):
    """Levels from a window centred on t (it sees later candles) must make the check above fail."""
    monkeypatch.setattr(sr, "levels", lambda d, W: (d["high"].rolling(W, center=True).max(), d["low"].rolling(W, center=True).min(),
                                                    sr.pa.atr(d, sr.ATR_N)))
    with pytest.raises(AssertionError):
        test_levels_and_touches_use_only_candles_up_to_the_touch(20)


def brute(d: pd.DataFrame, u: int, lvl: float, a: float, side: str, H: int) -> float:
    lo, hi, c = (d[k].to_numpy() for k in ("low", "high", "close"))
    g = 1 if side == "R" else -1
    for v in range(u, u + H + 1):
        if v >= len(c):
            return np.nan
        if g * (c[v] - lvl) >= CFG["break_atr"] * a:
            return sr.BREAK
        far = lo[v] if side == "R" else hi[v]
        if v >= u + 1 and g * (lvl - far) >= CFG["bounce_atr"] * a:
            return sr.BOUNCE
    return sr.OPEN


@pytest.mark.parametrize("side", sr.SIDES)
def test_outcomes_match_a_plain_loop(side):
    d = walk(n=1500, seed=9)
    R, S, A = sr.levels(d, 10)
    L = (R if side == "R" else S).to_numpy()
    u = sr.touches(d, L, A.to_numpy(), side, CFG)
    o = sr.outcomes(d, u, L, A.to_numpy(), side, 10, CFG)
    seen = set()
    for x, y in zip(u, o):
        z = brute(d, x, L[x - 1], A.to_numpy()[x - 1], side, 10)
        assert (np.isnan(y) and np.isnan(z)) or y == z, (x, y, z)
        seen.add(None if np.isnan(z) else int(z))
    assert {sr.BOUNCE, sr.BREAK} <= seen


def test_a_candle_that_bounces_and_breaks_counts_as_a_break():
    idx = pd.date_range("2016-01-01", periods=30, freq="D")
    d = pd.DataFrame({"high": 101.0, "low": 99.0, "close": 100.0}, index=idx)
    d.iloc[20] = [104.0, 95.0, 103.5]                  # wicks far down and closes well above
    u = np.array([19])
    L, A = np.full(30, 100.5), np.full(30, 2.0)
    assert sr.outcomes(d, u, L, A, "R", 5, CFG)[0] == sr.BREAK


def test_episodes_start_again_only_after_the_horizon():
    assert list(sr.episode_starts(np.array([10, 11, 15, 16, 30, 31]), 5)) == [0, 3, 4]


def test_placebo_only_looks_back():
    d = walk()
    R, _, _ = sr.levels(d, 10)
    p = sr.placebo(d, R, 25)
    e = d.copy()
    e.iloc[2001:] *= 3
    pd.testing.assert_series_equal(p.iloc[:2001], sr.placebo(e, sr.levels(e, 10)[0], 25).iloc[:2001])


def test_verdict_rule():
    r = {"real": {"n": 200}, "diff": 0.1, "p_holm": 0.01, "halves": [{"real": {"n": 90}, "diff": 0.05}, {"real": {"n": 110}, "diff": 0.12}]}
    assert sr.verdict(r) == "manh_hon"
    assert sr.verdict({**r, "diff": -0.1, "halves": [{"real": {"n": 90}, "diff": -0.05}, {"real": {"n": 110}, "diff": -0.1}]}) == "yeu_hon"
    assert sr.verdict({**r, "p_holm": 0.2}) == "nhu_bat_ky"
    assert sr.verdict({**r, "real": {"n": 29}}) == "it_du_lieu"
    assert sr.verdict({**r, "halves": [{"real": {"n": 4}, "diff": 0.05}, {"real": {"n": 110}, "diff": 0.12}]}) == "it_du_lieu"


@pytest.mark.parametrize("side", sr.SIDES)
def test_touches_match_the_registered_definition(side):
    """A touch at u uses the level and ATR set at t = u − 1 (not the touching candle) and must come from beyond the zone."""
    d = walk(n=1200, seed=2)
    R, S, A = sr.levels(d, 7)
    L, a = (R if side == "R" else S).to_numpy(), A.to_numpy()
    hi, lo, c = (d[k].to_numpy() for k in ("high", "low", "close"))
    want = []
    for u in range(1, len(d)):
        t, w = u - 1, CFG["zone_atr"] * a[u - 1]
        if not (np.isfinite(L[t]) and np.isfinite(w)):
            continue
        if (side == "R" and hi[u] >= L[t] - w and c[t] < L[t] - w) or (side == "S" and lo[u] <= L[t] + w and c[t] > L[t] + w):
            want.append(u)
    got = list(sr.touches(d, L, a, side, CFG))
    assert got == want and len(got) > 20
