# -*- coding: utf-8 -*-
"""Price action panel data (bot/models/pa_sheet.py): first touches match a plain loop, counts add up and fall as the
level moves away, the state shows only what is known at the last candle, and the entry check follows section
pa_sheet (suggested stop / target, break-even share, Wilson, verdict)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import pa_sheet as ps
from bot.models import price_action as pa


def candles(n: int = 900, seed: int = 5, start: str = "2015-06-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.03, n)))
    o = np.r_[c[0], c[:-1]] * np.exp(rng.normal(0, 0.004, n))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.012, n)))
    lo = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.012, n)))
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c}, index=pd.date_range(start, periods=n, freq="D"))


def test_first_touch_matches_a_plain_loop():
    d, H, since = candles(300), 7, pd.Timestamp("2015-07-01")
    tu, td, n = ps.first_touch(d, H, since)
    C, Hi, Lo, a = d["close"].to_numpy(), d["high"].to_numpy(), d["low"].to_numpy(), pa.atr(d, 14).to_numpy()
    ts = [t for t in range(len(d)) if d.index[t] >= since and np.isfinite(a[t]) and t + H < len(d)]
    assert n == len(ts) > 200
    for k, t in enumerate(ts):
        for gi, g in enumerate(ps.grid()):
            assert tu[k, gi] == next((j for j in range(H) if Hi[t + 1 + j] >= C[t] + g * a[t]), H)
            assert td[k, gi] == next((j for j in range(H) if Lo[t + 1 + j] <= C[t] - g * a[t]), H)


def test_touch_counts_add_up_and_fall_with_distance():
    t = ps.touch(candles(), 30, pd.Timestamp("2016-01-01"))
    up, down, same = (np.array(t[k]) for k in ("up", "down", "same"))
    assert ((up + down + same) <= t["N"]).all() and t["N"] > 0
    assert (np.diff(up, axis=0) <= 0).all() and (np.diff(down, axis=1) <= 0).all()   # farther target → touched first less often
    assert (np.diff(up, axis=1) >= 0).all()                                          # farther stop → target first more often


def test_state_shows_only_what_is_known_at_the_last_candle():
    d, cfg = candles(), pa.spec()
    for cut in (500, 700, 899):
        e = d.iloc[: cut + 1]
        s = ps.state(e, cfg)
        L = e.index[-1]
        assert s["anchor"] == L.strftime("%Y-%m-%d")
        for x in s["lows"] + s["highs"]:
            day = pd.Timestamp(x["date"])
            assert L - pd.Timedelta(days=365) <= day <= L - pd.Timedelta(days=5)
        f = pa.flags(d, cfg)                                                          # criteria on the full history, same day
        assert s["active"] == [c for c in f.columns if f.loc[L, c]]
        assert s["w"] == pytest.approx(0.5 * pa.atr(e, 14).iloc[-1])


def panel(H: int = 7, N: int = 700, up=None, down=None, same=None) -> dict:
    z = lambda: [[0] * ps.LEVELS for _ in range(ps.LEVELS)]  # noqa: E731
    t = {"N": N, "up": up or z(), "down": down or z(), "same": same or z()}
    return {"step": ps.STEP, "levels": ps.LEVELS, "state": {"atr": 100.0, "w": 50.0, "close": 1000.0,
            "lows": [{"date": "x", "price": 900.0}, {"date": "x", "price": 950.0}], "highs": [{"date": "x", "price": 1080.0}]},
            "touch": {str(H): t}}


def test_suggested_stop_and_target_follow_the_registration():
    o = panel()
    s = ps.suggest(o, "long", 1000.0)
    assert (s["S"], s["R"], s["SL"], s["TP"]) == (950.0, 1080.0, 900.0, 1030.0)       # below support zone, before resistance zone
    s = ps.suggest(o, "short", 1000.0)
    assert s["SL"] == 1130.0 and s["TP"] == pytest.approx(1000.0 - 2 * 130.0)          # support + w = 1000 is not below the entry
    assert ps.suggest(o, "short", 1040.0)["TP"] == 1000.0                               # support + w below the entry
    assert ps.suggest(o, "long", 1100.0)["TP"] == pytest.approx(1100.0 + 2 * (1100.0 - 900.0))    # no resistance above: 2 × the stop
    assert ps.suggest(o, "long", 890.0)["SL"] == pytest.approx(790.0)                   # no support below: 1 ATR


def test_entry_check_verdict():
    up, down, same = ([[0] * ps.LEVELS for _ in range(ps.LEVELS)] for _ in range(3))
    # long, stop 1 ATR (level 4 → index 3), target 2 ATR (level 8 → index 7)
    up[7][3], down[7][3], same[7][3] = 420, 260, 20
    o = panel(up=up, down=down, same=same)
    r = ps.check(o, "long", 1000.0, 900.0, 1200.0, 7)
    assert r["valid"] and r["q"] == pytest.approx(1 / 3) and r["rr"] == pytest.approx(2)
    assert r["Pt"] == pytest.approx(420 / 700) and r["Ps"] == pytest.approx(280 / 700) and r["p"] == pytest.approx(0.6)
    assert r["n_eff"] == pytest.approx(100) and r["ci"][0] > 1 / 3 and r["verdict"] == "loi" and r["exp_r"] == pytest.approx(0.8)
    # short: stop 2 ATR up is the row, target 1 ATR down the column (same cell); a candle touching both counts as the stop
    rs = ps.check(o, "short", 1000.0, 1200.0, 900.0, 7)
    assert rs["Pt"] == pytest.approx(260 / 700) and rs["Ps"] == pytest.approx(440 / 700) and rs["verdict"] == "bat_loi"
    assert not ps.check(o, "long", 1000.0, 1100.0, 1200.0, 7)["valid"]
    assert ps.check(o, "long", 1000.0, 999.0, 3000.0, 7)["clamped"]                      # 20 ATR target is outside the grid
