# -*- coding: utf-8 -*-
"""Candlestick patterns (bot/models/candles.py) and the learned model of the Trend view (bot/models/trend.py, ml_*):
patterns are recognised from their registered definitions, use only candles up to T (a planted look-ahead is caught),
independent occurrences are spaced k days apart; the learned model only trains on days whose outcome is known (a planted
look-ahead is caught) and the 9-out-of-10 band is wider than the 8-out-of-10 one."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import candles as cd
from bot.models import trend as tr


def frame(rows: list[tuple[float, float, float, float]], start: str = "2020-01-01") -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=pd.date_range(start, periods=len(rows), freq="D"))


def falling(n: int = 12, p: float = 120.0) -> list[tuple]:
    out = []
    for _ in range(n):
        out.append((p, p + 0.5, p - 1.5, p - 1.0))
        p -= 1.0
    return out


def rising(n: int = 12, p: float = 100.0) -> list[tuple]:
    out = []
    for _ in range(n):
        out.append((p, p + 1.5, p - 0.5, p + 1.0))
        p += 1.0
    return out


def test_patterns_follow_their_definitions():
    d = falling() + [(108.0, 108.5, 104.0, 105.0), (104.5, 110.0, 104.0, 109.0)]      # bearish, then a bullish body engulfing it
    f = cd.detect(frame(d))
    assert f["nhan_chim_tang"].iloc[-1] and not f["nhan_chim_giam"].iloc[-1]
    d = falling() + [(106.0, 108.5, 101.5, 108.0)]                                     # body 2, lower shadow 4,5, upper 0,5
    f = cd.detect(frame(d))
    assert f["bua"].iloc[-1] and not f["doji_sau_giam"].iloc[-1]
    d = rising() + [(112.0, 113.0, 111.0, 112.05)]                                     # body ≤ 10% of the range after a rise
    f = cd.detect(frame(d))
    assert f["doji_sau_tang"].iloc[-1] and not f["doji_sau_giam"].iloc[-1]
    d = falling(10) + [(100.0, 101.2, 99.8, 101.0), (100.5, 102.2, 100.3, 102.0), (101.5, 103.3, 101.3, 103.0)]
    assert cd.detect(frame(d))["ba_chang_trang"].iloc[-1]


def test_patterns_use_only_candles_up_to_t():
    rng = np.random.default_rng(2)
    n = 600
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    o = np.r_[c[0], c[:-1]] * np.exp(rng.normal(0, 0.005, n))
    h, lo = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.01, n))), np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.01, n)))
    d = frame(list(zip(o, h, lo, c)))
    T = d.index[400]
    a = cd.detect(d).loc[:T]
    for crash in (0.5, 2.0):
        e = d.copy()
        e.loc[e.index > T] *= crash
        pd.testing.assert_frame_equal(a, cd.detect(e).loc[:T])
    assert a.to_numpy().sum() > 20


def test_a_planted_look_ahead_in_a_pattern_is_caught(monkeypatch):
    real = cd.detect
    monkeypatch.setattr(cd, "detect", lambda d: real(d).shift(-1, fill_value=False))   # flags known one day early
    with pytest.raises(AssertionError):
        test_patterns_use_only_candles_up_to_t()


def test_independent_occurrences_are_spaced():
    assert cd._spaced(np.array([1, 2, 3, 8, 9, 20]), 3).tolist() == [1, 8, 20]
    assert cd._spaced(np.array([5, 6]), 1).tolist() == [5, 6]


def _ml_inputs(days: int = 1600, seed: int = 9):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2016-01-01", periods=days, freq="D")
    p = pd.Series(1000 * np.exp(np.cumsum(rng.normal(0.0005, 0.03, days))), index=idx)
    X = pd.DataFrame(rng.normal(0, 1, (days, 4)), index=idx, columns=list("abcd"))
    X["a"] = np.log(p / p.shift(5))                                                   # partly informative, known at T
    k = 5
    r = np.log(p.shift(-k) / p)
    up = pd.Series(np.where(r.notna(), (r > 0).astype(float), np.nan), index=idx)
    return X, up, k


def test_learned_model_uses_only_known_outcomes():
    """Right after each refit day T (where a leak would show), flipping every outcome not known at T changes nothing up to T."""
    X, up, k = _ml_inputs()
    a = tr.ml_predict(X, up, k)
    lab = np.flatnonzero(np.isfinite(X.to_numpy()).all(axis=1) & up.notna().to_numpy())
    refits = range(lab[tr.ML_MIN] + k, len(up) - 60, tr.ML_REFIT)
    for j in list(refits)[::4]:
        T = X.index[j + 1]
        b_up = up.copy()
        late = b_up.index > T - pd.Timedelta(days=k)
        b_up[late] = 1 - b_up[late]
        pd.testing.assert_series_equal(a.loc[:T], tr.ml_predict(X, b_up, k).loc[:T])
    assert a.notna().sum() > 300


def test_a_planted_look_ahead_in_the_learned_model_is_caught(monkeypatch):
    """Training on days whose outcome ends after the refit day must make the check above fail."""
    monkeypatch.setattr(tr, "ML_MIN", tr.ML_MIN)
    real = tr.ml_predict
    monkeypatch.setattr(tr, "ml_predict", lambda X, up, k: real(X, up.shift(-k), 0) if k else real(X, up, k))
    with pytest.raises(AssertionError):
        test_learned_model_uses_only_known_outcomes()


def test_nine_out_of_ten_band_is_wider_than_eight():
    rng = np.random.default_rng(4)
    days = 2400
    p = 1000 * np.exp(np.cumsum(rng.normal(0.0008, 0.03, days)))
    d = pd.DataFrame({"p": p, "mvrv": 1.5 + 0.1 * rng.normal(size=days)}, index=pd.date_range("2015-01-01", periods=days, freq="D"))
    cfg = tr.spec()
    pr = tr.predict(d, tr.base_states(d, cfg), 7, cfg)
    g = pr["models"]["goc"].dropna()
    assert (g[0.05] < g[0.1]).all() and (g[0.95] > g[0.9]).all()
    e = tr.evaluate(pr, 7, {**cfg, "eval_from": "2018-01-01"})
    assert e["models"]["goc"]["cover90"] > e["models"]["goc"]["cover80"]
