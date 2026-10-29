"""Part G: macro events relative to the data cut-off (settings in config/candidates.yaml, section macro.events).

Only events AFTER the cut-off (the last Sunday close used for the signal) are listed. Events between the cut-off and
the moment the report is published are flagged: the signal does not contain the market's reaction, so the report
suggests running again after the next weekly close. A calendar that does not reach the end of the look-ahead window
is reported as stale instead of silently showing "no events".
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from bot.config import CONFIG, load_yaml
from bot.data.fetchers import events as ev

STORED = ("fomc", "cpi", "pce")


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s.replace("Z", ""))


def calendar(path=None) -> dict[str, list[pd.Timestamp]]:
    """Stored event times (UTC, naive) per type from config/events.yaml."""
    y = load_yaml(path or CONFIG / "events.yaml")
    return {k: sorted(_ts(s) for s in (y.get(k) or [])) for k in STORED}


def cutoff_of(last_sunday: pd.Timestamp) -> pd.Timestamp:
    """The signal uses the Sunday close: data are cut at 23:59:59 UTC that Sunday."""
    return pd.Timestamp(last_sunday).normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)


def next_weekly_close(now: pd.Timestamp) -> pd.Timestamp:
    """End of the next Sunday after `now` (UTC), when a new weekly close exists."""
    d = pd.Timestamp(now).normalize()
    d += pd.Timedelta(days=(6 - d.weekday()) % 7)
    end = d + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return end if end > now else end + pd.Timedelta(weeks=1)


def listing(cutoff: pd.Timestamp, now: pd.Timestamp, ahead_days: int = 7, cal: dict | None = None,
            types=("fomc", "cpi", "pce", "opex")) -> dict:
    """Events in (cutoff, now + ahead]: `after_cutoff` (already happened, flagged) and `upcoming`."""
    cal = calendar() if cal is None else cal
    hi = now + pd.Timedelta(days=ahead_days)
    rows = [(k, t) for k in types if k in cal for t in cal[k]]
    if "opex" in types:
        rows += [("opex", _ts(s)) for s in ev.options_expiry(cutoff.date(), hi.date())]
    keep = sorted((t, k) for k, t in rows if cutoff < t <= hi)
    after = [{"type": k, "time": t, "flag": True} for t, k in keep if t <= now]
    upcoming = [{"type": k, "time": t, "flag": False} for t, k in keep if t > now]
    stale = {k: (max(cal[k]) if cal.get(k) else None) for k in types if k != "opex" and (not cal.get(k) or max(cal[k]) < hi)}
    return {"cutoff": cutoff, "now": now, "until": hi, "after_cutoff": after, "upcoming": upcoming, "stale": stale,
            "rerun": bool(after), "rerun_after": next_weekly_close(now) if after else None}


def utc_now() -> pd.Timestamp:
    return pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
