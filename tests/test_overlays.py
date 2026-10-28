# -*- coding: utf-8 -*-
"""Overlay tests: fixed template, episode gate, combination bounds, event delay, quarterly expiries."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from bot.models import overlays


def test_template_and_gate():
    x = pd.Series(np.r_[np.linspace(0, 1, 60), np.zeros(5), np.ones(5)])
    f = overlays.rule(x, "low")
    assert set(np.unique(f)) <= {0.75, 1.0, 1.25} and (f[:51] == 1.0).all()  # needs 52 weeks of history
    assert f[60] == 1.25 and f[-1] == 0.75  # low value is cheap, high value is expensive
    assert overlays.episodes(np.array([1, 1.25, 1.25, 1, 0.75, 1.25, 1])) == 3
    few = np.array([1.25, 1, 1, 1.25] + [1] * 20)
    assert (overlays.gate(few) == 1).all()


def test_combine_bounds():
    m = overlays.combine(np.array([2.0, 0.25, 1.0]), np.array([1.25, 0.75, 9.0]))
    assert list(m) == [2.0, 0.25, 1.25]


def test_event_delay_moves_fill_never_cancels():
    days = pd.date_range("2026-10-20", "2026-11-05", freq="D")
    close = pd.Series(np.arange(len(days), dtype=float) + 100, index=days)
    dates = pd.DatetimeIndex(["2026-10-27", "2026-11-03"])  # Tuesdays
    fill, delayed = overlays.event_delay(dates, close, [pd.Timestamp("2026-10-28T18:00")])
    assert delayed.tolist() == [True, False]
    assert fill[0] == close[pd.Timestamp("2026-10-29")] and fill[1] == close[pd.Timestamp("2026-11-03")]


def test_quarter_expiries_are_last_fridays():
    q = overlays.quarter_expiries(dt.date(2026, 1, 1), dt.date(2026, 12, 31))
    assert pd.Timestamp("2026-03-27") in q and pd.Timestamp("2026-12-25") in q
