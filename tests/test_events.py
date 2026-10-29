# -*- coding: utf-8 -*-
"""Part G tests: events before the data cut-off are never listed; events between the cut-off and the report are flagged
with a re-run suggestion; a calendar that ends too early is reported as stale."""
from __future__ import annotations

import pandas as pd

from bot.report import events as ev

T = pd.Timestamp
CAL = {"fomc": [T("2026-10-21 18:00"), T("2026-10-28 18:00"), T("2026-11-03 19:00"), T("2026-11-20 19:00"), T("2027-01-27 19:00")],
       "cpi": [T("2026-10-25 12:30"), T("2026-10-26 00:00"), T("2026-11-01 13:30")], "pce": []}
SUNDAY = T("2026-10-25")
NOW = T("2026-10-29 09:00")


def test_cutoff_and_next_weekly_close():
    assert ev.cutoff_of(SUNDAY) == T("2026-10-25 23:59:59")
    assert ev.next_weekly_close(NOW) == T("2026-11-01 23:59:59")
    assert ev.next_weekly_close(T("2026-11-01 10:00")) == T("2026-11-01 23:59:59")


def test_only_events_after_cutoff_are_listed_and_the_gap_is_flagged():
    out = ev.listing(ev.cutoff_of(SUNDAY), NOW, 7, CAL, types=("fomc", "cpi", "pce", "opex"))
    times = [e["time"] for e in out["after_cutoff"] + out["upcoming"]]
    assert all(t > T("2026-10-25 23:59:59") for t in times)
    assert T("2026-10-21 18:00") not in times and T("2026-10-25 12:30") not in times  # before the cut-off: never listed
    assert [(e["type"], e["time"]) for e in out["after_cutoff"]] == [("cpi", T("2026-10-26 00:00")), ("fomc", T("2026-10-28 18:00"))]
    assert all(e["flag"] for e in out["after_cutoff"]) and out["rerun"] and out["rerun_after"] == T("2026-11-01 23:59:59")
    up = [(e["type"], e["time"]) for e in out["upcoming"]]
    assert ("opex", T("2026-10-30 08:00")) in up and ("fomc", T("2026-11-03 19:00")) in up and ("fomc", T("2026-11-20 19:00")) not in up
    assert not any(e["flag"] for e in out["upcoming"])


def test_no_gap_means_no_rerun_and_stale_calendars_are_named():
    out = ev.listing(ev.cutoff_of(SUNDAY), T("2026-10-25 23:59:59"), 6, CAL, types=("fomc", "cpi", "pce"))
    assert not out["after_cutoff"] and not out["rerun"] and out["rerun_after"] is None
    assert set(out["stale"]) == {"pce"}  # CPI's last entry (01/11 13:30) is after the window end (31/10 23:59:59)
    late = ev.listing(ev.cutoff_of(SUNDAY), NOW, 7, CAL, types=("fomc", "cpi", "pce"))
    assert set(late["stale"]) == {"cpi", "pce"} and late["stale"]["cpi"] == T("2026-11-01 13:30")
