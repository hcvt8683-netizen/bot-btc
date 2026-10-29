# -*- coding: utf-8 -*-
"""Part E tests: group counting, the sell / buy-back rule, and no look-ahead in the simulation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import sell_system as ss

GROUPS = {"g1": ["a", "b"], "g2": ["c"]}


def test_flags_and_group_count():
    t = pd.DataFrame({"pct_a": [0.96, 0.5, np.nan], "pct_b": [0.97, 0.99, 0.1], "pct_c": [0.2, 0.95, 0.99]})
    fl = ss.flags(t, GROUPS, 0.95)
    assert list(ss.group_count(fl, GROUPS)) == [1, 2, 1]  # a and b in one group count once
    assert ss.level_of(0, {"chot_mot_phan": 1, "ban_phan_lon": 3}) == "giu" and ss.level_of(3, {"chot_mot_phan": 1, "ban_phan_lon": 3}) == "ban"


def test_sell_once_per_episode_and_buy_back_rules():
    close = np.array([100, 120, 130, 100, 90, 95, 110, 120.0])
    fill = close.copy()
    r = ss.simulate(close, fill, [1], 0.2, 0.8, 52, fee=0, slip=0)
    tr = r["trades"]
    assert len(tr) == 1 and tr[0]["sell"] == 1 and tr[0]["buy"] == 4 and tr[0]["right"]  # 90 ≤ 0.8 × 120 = 96
    late = ss.simulate(close, fill, [1], 0.2, 0.5, 3, fee=0, slip=0)["trades"]
    assert late[0]["buy"] == 4  # time stop after 3 weeks
    assert r["equity"][-1] > r["equity_dca"][-1]  # sold high, bought back lower


def test_simulation_has_no_look_ahead():
    """Prices after week T crash (so the buy-back condition would fire if it could see them); every cut-off from 60 to 139
    is checked so the test also catches a one-week look-ahead."""
    rng = np.random.default_rng(1)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.06, 200)))
    fill = close * 1.01
    starts = [20, 60, 120]
    a = ss.simulate(close, fill, starts, 0.3, 0.8, 52)
    for T in range(60, 140):
        c2, f2 = close.copy(), fill.copy()
        c2[T + 1:] *= 0.3
        f2[T + 1:] *= 0.3
        b = ss.simulate(c2, f2, starts, 0.3, 0.8, 52)
        assert np.allclose(a["equity"][:T + 1], b["equity"][:T + 1]), T
        assert [x for x in a["trades"] if x.get("buy", 999) <= T] == [x for x in b["trades"] if x.get("buy", 999) <= T]
