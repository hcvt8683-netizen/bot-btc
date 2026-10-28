"""Daily base data and the weekly decision grid.

Decision time: every Tuesday 01:00 UTC (Coin Metrics publishes day d at the earliest on d+1, so Sunday's
on-chain values are known on Tuesday). The buy is filled at that Tuesday's daily close (Coin Metrics PriceUSD).
"""
from __future__ import annotations

import pandas as pd

from bot.config import cfg
from bot.data import pit_store

DECISION_HOUR = 1


def daily_cm(end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Coin Metrics daily rows with available_at, optionally cut at `end` (inclusive)."""
    df = pit_store.with_available_at(pit_store.load_history("coinmetrics"), "coinmetrics")
    return df[df["date"] <= end].reset_index(drop=True) if end is not None else df


def decision_dates(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """Decision days (dates at 00:00) on the configured weekday between start and end inclusive."""
    wd = int((cfg().get("backtest") or {}).get("decision_weekday", 1))
    days = pd.date_range(start, end, freq="D")
    return days[days.weekday == wd]


def decision_time(dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return dates + pd.Timedelta(hours=DECISION_HOUR)


def fill_prices(daily: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.Series:
    """Close price of each decision day (forward-filled over missing days)."""
    p = daily.set_index("date")["price"].asfreq("D").ffill()
    return p.reindex(dates)
