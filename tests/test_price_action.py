# -*- coding: utf-8 -*-
"""Price action (bot/models/price_action.py): criteria follow their registered definitions, swings are only used once
the 5 candles on their right have closed, nothing at day T depends on candles after T (planted look-ahead bugs are
caught), episodes are spaced k days apart, the statistics find an engineered edge and the final test is guarded."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from bot.models import price_action as pa


def ohlc(n: int = 900, seed: int = 3, start: str = "2018-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    o = np.r_[c[0], c[:-1]] * np.exp(rng.normal(0, 0.004, n))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.012, n)))
    lo = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.012, n)))
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c}, index=pd.date_range(start, periods=n, freq="D"))


def two(prev: tuple, now: tuple, S=np.nan, R=np.nan, w=1.0, up=False, down=False) -> pd.Series:
    """Criteria of candle `now` after candle `prev` (open, high, low, close) with the levels fixed before it."""
    x = pd.DataFrame([prev, now], columns=["open", "high", "low", "close"]).assign(S=S, R=R, w=w, up=up, down=down)
    return pa.rules(x, pa.spec()["params"]).iloc[-1]


def test_criteria_follow_their_definitions():
    f = two((104, 106, 104, 105), (103, 104, 100.2, 102), S=100)       # dips into the support zone, closes above it
    assert f["ho_tro"] and not f["pha_vo_gia_duoi"] and not f["pin_bar_ho_tro"]
    f = two((104, 106, 104, 105), (101, 102, 98, 101.5), S=100)        # pierces beyond the zone, closes back above
    assert f["pha_vo_gia_duoi"] and not f["ho_tro"] and f["pin_bar_ho_tro"]     # lower shadow 3 of a range of 4
    f = two((104, 105, 100.5, 104), (103, 104, 101.5, 103.5), S=100)   # inside a mother bar that touched the zone
    assert f["inside_bar_ho_tro"] and not f["ho_tro"]
    f = two((96, 96, 94, 95), (97, 99.8, 96, 98), R=100)               # rejected at resistance
    assert f["khang_cu"] and not f["pha_vo_gia_tren"]
    f = two((96, 96, 94, 95), (99, 102, 98.5, 99), R=100)              # false breakout above, long upper shadow
    assert f["pha_vo_gia_tren"] and f["pin_bar_khang_cu"] and not f["khang_cu"]
    f = two((104, 106, 104, 105), (101, 102, 98, 101.5))               # no support known → nothing at support fires
    assert not f[["ho_tro", "pha_vo_gia_duoi", "pin_bar_ho_tro", "inside_bar_ho_tro"]].any()
    f = two((104, 106, 104, 105), (103, 104, 100.2, 102), S=100, w=np.nan)   # no ATR yet → no zone
    assert not f["ho_tro"]


def vee(n_down: int = 10, n_up: int = 25) -> pd.DataFrame:
    """Falling then rising candles: the only swing low is the bottom (day n_down), no swing high."""
    c = np.r_[np.linspace(100, 91, n_down), 90, np.linspace(91, 91 + n_up - 1, n_up)]
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + 0.5, "low": np.minimum(o, c) - 0.5, "close": c},
                        index=pd.date_range("2020-01-01", periods=len(c), freq="D"))


def test_a_swing_is_used_only_after_the_fifth_candle_on_its_right():
    d, n = vee(), 5
    hi, lo = pa.swings(d, n)
    assert lo.tolist().index(True) == 10 and lo.sum() == 1 and hi.sum() == 0
    S, R = pa.levels(d, hi, lo, n, 365)
    assert np.isnan(S[: 10 + n + 1]).all()                     # known at the close of day 15, so a level from day 16 on
    assert S[10 + n + 1] == d["low"].iloc[10] and np.isnan(R).all()


def test_structure_waits_for_the_second_swing():
    m, n = 60, 5
    d = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0}, index=pd.date_range("2020-01-01", periods=m, freq="D"))
    hi, lo = np.zeros(m, bool), np.zeros(m, bool)
    hi[[10, 30]], lo[[20, 40]] = True, True
    d.iloc[[10, 30], 1] = [101.0, 110.0]
    d.iloc[[20, 40], 2] = [90.0, 95.0]
    up, down = pa.structure(d, hi, lo, n)
    assert not up[: 40 + n].any() and up[40 + n] and not down.any()   # higher high, higher low once day 40 is known
    d.iloc[50:, 3] = 94.0                                               # close below the last swing low: structure broken
    up, _ = pa.structure(d, hi, lo, n)
    assert up[45:50].all() and not up[50:].any()


def _parts(d: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    p = cfg["params"]
    hi, lo = pa.swings(d, p["swing_n"])
    S, R = pa.levels(d, hi, lo, p["swing_n"], p["level_lookback_days"])
    up, down = pa.structure(d, hi, lo, p["swing_n"])
    return pd.DataFrame({"S": S, "R": R, "up": up, "down": down}, index=d.index)


def test_criteria_use_only_candles_up_to_t():
    cfg, d = pa.spec(), ohlc()
    a, fa = _parts(d, cfg), pa.flags(d, cfg)
    for j in range(150, 850, 20):
        T = d.index[j]
        for mult in (0.5, 2.0):
            e = d.copy()
            e.loc[e.index > T] *= mult
            pd.testing.assert_frame_equal(a.loc[:T], _parts(e, cfg).loc[:T])
            pd.testing.assert_frame_equal(fa.loc[:T], pa.flags(e, cfg).loc[:T])
    assert a["S"].notna().mean() > 0.5 and a["R"].notna().mean() > 0.5 and a["up"].any() and a["down"].any()
    assert fa[list(cfg["criteria"])].to_numpy().sum() > 100 and fa["bo_tang"].any() and fa["bo_giam"].any()


def test_a_planted_look_ahead_in_the_swings_is_caught(monkeypatch):
    monkeypatch.setattr(pa, "known_after", lambda n: 0)          # a swing used before the candles on its right have closed
    with pytest.raises(AssertionError):
        test_criteria_use_only_candles_up_to_t()


def test_a_planted_look_ahead_in_the_criteria_is_caught(monkeypatch):
    real = pa.flags
    monkeypatch.setattr(pa, "flags", lambda d, cfg: real(d, cfg).shift(-1, fill_value=False))   # known one day early
    with pytest.raises(AssertionError):
        test_criteria_use_only_candles_up_to_t()


def test_episodes_are_spaced():
    dates = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-04", "2020-01-09", "2020-01-10", "2020-01-30"])
    assert pa.episodes(dates, 3).tolist() == [0, 3, 5]
    assert pa.episodes(dates, 1).tolist() == [0, 2, 3, 5]
    assert pa.episodes(pd.DatetimeIndex([]), 3).tolist() == []


def test_statistics_find_an_engineered_edge_and_not_a_random_one():
    rng = np.random.default_rng(11)
    n = 1500
    r = rng.normal(0, 0.03, n)
    sig = rng.random(n) < 0.06
    r[1:][sig[:-1]] = np.abs(r[1:][sig[:-1]])                 # the day after a signal always closes higher
    c = 100 * np.exp(np.cumsum(r))
    d = pd.DataFrame({"open": c, "high": c, "low": c, "close": c}, index=pd.date_range("2016-01-01", periods=n, freq="D"))
    f = pd.DataFrame({"ho_tro": sig, "khang_cu": rng.random(n) < 0.06}, index=d.index)
    cfg = {"criteria": {"ho_tro": "tăng; x", "khang_cu": "giảm; x"}, "combo": {}, "horizons_days": [1]}
    rows = {x["crit"]: x for x in pa.table(d, f, cfg, d.index[0], None, n_boot=500)}
    assert rows["ho_tro"]["verdict"] == "hon" and rows["ho_tro"]["hit"] == 1.0
    assert rows["khang_cu"]["verdict"] == "chua" and rows["khang_cu"]["p_holm"] > 0.05
    assert rows["ho_tro"]["episodes"] <= rows["ho_tro"]["n"] and len(rows["ho_tro"]["halves"]) == 2
    f["ho_tro"] = False
    f.iloc[[100, 900], 0] = True                               # two signals: too few episodes, no conclusion
    assert {x["crit"]: x for x in pa.table(d, f, cfg, d.index[0], None, n_boot=200)}["ho_tro"]["verdict"] == "it_dot"


def test_holm_is_monotone():
    rows = [{"p": 0.01}, {"p": 0.04}, {"p": 0.03}]
    pa.holm(rows)
    assert [x["p_holm"] for x in rows] == pytest.approx([0.03, 0.06, 0.06])


def test_the_final_test_is_guarded(tmp_path):
    cfg = pa.spec()
    d = ohlc(n=3300, start="2018-01-01")                       # ends 01/2027: not a year of outcomes after 03/11/2026
    log = tmp_path / "final_runs.log"
    with pytest.raises(pa.NotReady):
        pa.run_final(d, cfg, log_path=log, out_path=tmp_path / "out.json")
    assert not log.exists()
    log.write_text(json.dumps({"phase": pa.PHASE, "status": "done"}) + "\n", encoding="utf-8")
    with pytest.raises(pa.AlreadyRun):
        pa.run_final(d, cfg, log_path=log, out_path=tmp_path / "out.json")
