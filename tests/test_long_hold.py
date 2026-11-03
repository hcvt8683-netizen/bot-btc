# -*- coding: utf-8 -*-
"""Buy and hold (bot/models/long_hold.py): the gain after costs, the stats only use days whose outcome is known, the
registered 'hold at least' rule, and the buying price is read back from the entry module (nothing recomputed)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from bot.models import long_hold as lh

CFG = lh.spec()


def test_gain_counts_costs_on_both_sides():
    p = pd.Series([100.0, 110.0, 99.0], index=pd.date_range("2020-01-01", periods=3, freq="D"))
    g = lh.gains(p, 1, 0.0015)
    assert g.iloc[0] == pytest.approx(110 * 0.9985 / (100 * 1.0015) - 1)
    assert np.isnan(g.iloc[-1])                                  # the last day has no outcome yet


def test_table_uses_known_outcomes_and_independent_counts():
    idx = pd.date_range("2015-12-01", periods=900, freq="D")
    p = pd.Series(100 * 1.001 ** np.arange(900), index=idx)    # a steady rise: every holding period gains
    rows = lh.table(p, {**CFG, "horizons_days": [7, 365]})
    r7, r365 = rows
    assert r7["from"] == "2016-01-01" and r7["n"] == (idx[-1] - pd.Timestamp("2016-01-01")).days + 1 - 7
    assert r7["p"] == 1.0 and r7["n_eff"] == round(r7["n"] / 7) and r365["n_eff"] == max(1, round(r365["n"] / 365))
    assert pd.Timestamp(r365["to"]) + pd.Timedelta(days=365) <= idx[-1]


def test_hold_at_least_rule():
    def row(h, p, lo, h1, h2):
        return {"h": h, "n": 100, "p": p, "ci": [lo, 0.99], "halves": [{"n": 50, "p": h1}, {"n": 50, "p": h2}]}
    assert lh.hold_at_least([row(30, 0.6, 0.45, 0.6, 0.6), row(365, 0.85, 0.55, 0.9, 0.8), row(730, 0.9, 0.6, 0.9, 0.9)]) == 365
    assert lh.hold_at_least([row(365, 0.85, 0.40, 0.9, 0.8)]) is None          # too few independent periods
    assert lh.hold_at_least([row(730, 0.85, 0.60, 0.95, 0.70)]) is None        # one half below 80%


def test_buying_price_is_read_back_from_entry(tmp_path):
    e = {"anchor": "2026-11-01", "price": 77000.0, "rows": [{"k": 7, "probs": {x: 0.5 for x in lh.DISCOUNTS}, "q10": 1, "q50": 2, "q90": 3},
                                                             {"k": 30, "probs": {x: 0.7 for x in lh.DISCOUNTS}, "q10": 70000, "q50": 74000, "q90": 76500}],
         "wait": {"rows": [{"verdict": "chua"}] * 14 + [{"verdict": "ngay"}] * 6}}
    p = tmp_path / "entry.json"
    p.write_text(json.dumps(e), encoding="utf-8")
    b = lh.buy_price(p)
    assert b["wait"] == {"configs": 20, "better": 0, "worse": 6} and b["fills"]["30"]["0.03"] == 0.7 and b["low30"]["q50"] == 74000
