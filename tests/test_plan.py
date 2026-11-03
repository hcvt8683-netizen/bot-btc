# -*- coding: utf-8 -*-
"""Deployment plan tests: the money arithmetic, the use of only the prices inside each one-year window, and the
pre-registered choice (best median; since 04/11/2026, plan.stable: recommended only when every other plan is significantly
worse, else a tie) and the week-by-week stability count (bot/models/plan_stable.py)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import deploy_plan as dp
from bot.models import plan_stable as ps
from bot.models import sell_plan as sp

PC = {"options_weeks": [1, 4, 13, 26, 52], "horizon_weeks": 52}
FEE, SLIP = 0.001, 0.0005


def test_flat_price_costs_only_fees_and_lump_sum_follows_the_price():
    flat = np.full(200, 100.0)
    for n in PC["options_weeks"]:
        roi, mdd = dp.outcomes(flat, np.array([0, 10]), n, 52, FEE, SLIP)
        assert roi == pytest.approx((1 - FEE) / (1 + SLIP) - 1) and (mdd <= 0).all() and mdd.min() > -0.002
    up = 100 * 1.01 ** np.arange(200)
    lump, _ = dp.outcomes(up, np.array([5]), 1, 52, FEE, SLIP)
    assert lump[0] == pytest.approx(up[57] / up[5] * (1 - FEE) / (1 + SLIP) - 1)
    dca, _ = dp.outcomes(up, np.array([5]), 26, 52, FEE, SLIP)
    assert dca[0] < lump[0]  # in a rising market investing at once wins


def test_each_start_reads_only_its_own_year():
    rng = np.random.default_rng(4)
    p = 100 * np.exp(np.cumsum(rng.normal(0.003, 0.08, 300)))
    a, ma = dp.outcomes(p, np.array([20]), 13, 52, FEE, SLIP)
    q = p.copy()
    q[73:] *= 7  # after week 20 + 52
    q[:20] /= 3  # before the start
    b, mb = dp.outcomes(q, np.array([20]), 13, 52, FEE, SLIP)
    assert a[0] == b[0] and ma[0] == mb[0]


def test_choice_follows_the_registered_rule():
    rng = np.random.default_rng(7)
    idx = pd.date_range("2015-01-04", periods=520, freq="W-SUN")
    t = pd.DataFrame({"exec_monday": 100 * np.exp(np.cumsum(rng.normal(0.006, 0.09, len(idx))))}, index=idx)
    r = dp.compute(t, PC, FEE, SLIP, n_boot=300, seed=1, data_from=pd.Timestamp("2016-01-01"))
    o = {x["weeks"]: x for x in r["options"]}
    assert r["best_roi"] == max(o, key=lambda n: o[n]["median"])
    ok = [n for n, x in o.items() if x["not_worse"]]
    assert r["best_roi"] in ok and r["tied"] == ok and r["recommended"] == (r["best_roi"] if ok == [r["best_roi"]] else None)
    assert dp.old_pick(r["options"]) == max(ok, key=lambda n: o[n]["p10"])
    assert r["starts"] == len(dp.start_weeks(t, 52, pd.Timestamp("2016-01-01"))) and r["episodes"] == r["starts"] // 52
    assert o[1]["beat_lump"] is None and all(0 <= o[n]["beat_lump"] <= 1 for n in (4, 13, 26, 52))
    short = dp.compute(t.iloc[:120], PC, FEE, SLIP, n_boot=50, seed=1, data_from=pd.Timestamp("2016-01-01"))
    assert short["options"] == []  # too few start weeks: no plan rather than a guess


def _opt(n, not_worse, p10):
    return {"weeks": n, "not_worse": not_worse, "p10": p10}


def test_recommend_only_when_every_other_plan_is_significantly_worse():
    clear = [_opt(1, False, -0.4), _opt(13, False, -0.3), _opt(52, True, -0.2)]
    assert dp.verdict(clear, 52) == {"tied": [52], "recommended": 52}
    tie = [_opt(1, True, -0.45), _opt(4, False, -0.46), _opt(13, True, -0.48), _opt(52, True, -0.31)]
    assert dp.verdict(tie, 1) == {"tied": [1, 13, 52], "recommended": None}
    assert dp.old_pick(tie) == 52  # the rule used until 03/11/2026 named the safest of the tie


def _weekly_table(seed=11, n=300):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2015-01-04", periods=n, freq="W-SUN")
    return pd.DataFrame({"exec_monday": 100 * np.exp(np.cumsum(rng.normal(0.006, 0.09, n)))}, index=idx)


@pytest.mark.parametrize("mod", [dp, sp])
def test_stability_uses_only_the_weeks_up_to_each_close(mod):
    t = _weekly_table()
    since, start = t.index[200], pd.Timestamp("2015-01-01")
    a = ps.weekly(t, mod, PC, FEE, SLIP, 100, 1, start, since)
    u = t.copy()
    cut = t.index[240]
    u.loc[u.index > cut, "exec_monday"] *= 0.93 ** np.arange(1, int((u.index > cut).sum()) + 1)  # a long fall after week 240
    b = ps.weekly(u, mod, PC, FEE, SLIP, 100, 1, start, since)
    keep = [r for r in a if r["week"] <= cut.strftime("%Y-%m-%d")]
    assert len(keep) == 41 and b[:len(keep)] == keep
    last = mod.compute(t, PC, FEE, SLIP, 100, 1, start)  # the last week of the history is the live report
    assert a[-1]["new"] == last["recommended"] and a[-1]["tied"] == last["tied"]


def test_stability_counts():
    rows = [{"week": f"w{i}", "old": o, "new": n, "tied": t} for i, (o, n, t) in enumerate(
        [(1, None, [1, 13]), (52, None, [1, 13, 52]), (1, None, [1, 13]), (1, 1, [1]), (52, 52, [52]), (52, None, [13, 52])])]
    c = ps.count(rows)
    assert c["weeks"] == 6 and c["old_changes"] == 3 and c["old_flips"] == 3
    assert c["new_changes"] == 3 and c["new_flips"] == 1 and c["tie_changes"] == 2 and c["tie_weeks"] == 4
    assert [g["from"] for g in ps.segments(rows)] == [f"w{i}" for i in range(6)]
