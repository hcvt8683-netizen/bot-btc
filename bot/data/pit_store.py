"""Point-in-time store.

Raw snapshots are immutable files `data/raw/<source>/<YYYY-MM-DD>.parquet`: what a source returned on that day.
The first snapshot holds the full history; later ones keep only the recent rows (default 90 days), which is
where publications and revisions happen, so the folder stays small. History = union of snapshots, latest
vintage per key, with `first_seen` = date of the first snapshot that contained the row.

`available_at` follows the publication-lag rule from config: end of the row's period + lag_days.
"""
from __future__ import annotations

import datetime as dt
import pathlib

import pandas as pd

from bot.config import DATA, cfg

RAW = DATA / "raw"
RECENT_DAYS = 90


def _dir(source: str, root: pathlib.Path | None = None) -> pathlib.Path:
    return (root or RAW) / source


def snapshots(source: str, root: pathlib.Path | None = None) -> list[pathlib.Path]:
    d = _dir(source, root)
    return sorted(d.glob("*.parquet")) if d.exists() else []


def key_of(df: pd.DataFrame) -> str:
    return "time" if "time" in df.columns else "date"


def save_snapshot(source: str, df: pd.DataFrame, day: dt.date | None = None, root: pathlib.Path | None = None,
                  recent_days: int | None = RECENT_DAYS) -> pathlib.Path | None:
    """Write today's snapshot once. Returns the path, or None when a snapshot for that day already exists."""
    day = day or dt.datetime.now(dt.timezone.utc).date()
    path = _dir(source, root) / f"{day.isoformat()}.parquet"
    if path.exists():
        return None
    out = df
    if recent_days is not None and snapshots(source, root):
        k = key_of(df)
        out = df[df[k] >= pd.Timestamp(day) - pd.Timedelta(days=recent_days)]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    out.to_parquet(tmp, index=False, compression="zstd")
    tmp.replace(path)
    return path


def load_history(source: str, root: pathlib.Path | None = None, as_of_snapshot: dt.date | None = None) -> pd.DataFrame:
    """Union of snapshots (optionally only those up to a snapshot date): latest vintage per key + first_seen."""
    parts = []
    for p in snapshots(source, root):
        day = dt.date.fromisoformat(p.stem)
        if as_of_snapshot and day > as_of_snapshot:
            continue
        df = pd.read_parquet(p)
        df["_snap"] = pd.Timestamp(day)
        parts.append(df)
    if not parts:
        return pd.DataFrame()
    allv = pd.concat(parts, ignore_index=True)
    k = key_of(allv)
    first = allv.groupby(k)["_snap"].min().rename("first_seen")
    last = allv.sort_values([k, "_snap"]).groupby(k).tail(1).drop(columns="_snap")
    return last.merge(first, left_on=k, right_index=True).sort_values(k).reset_index(drop=True)


def period_end(dates: pd.Series, freq: str) -> pd.Series:
    """End of the period a row describes: daily rows end at next 00:00 UTC; monthly rows at the next month start;
    event rows (freq 'event') are known at their own timestamp."""
    if freq == "M":
        return dates + pd.offsets.MonthBegin(1)
    if freq == "event":
        return dates
    return dates.dt.normalize() + pd.Timedelta(days=1)


def with_available_at(df: pd.DataFrame, source: str, freq: str = "D") -> pd.DataFrame:
    """Add available_at = period end + lag_days of the source (config `sources`)."""
    lag = (cfg().get("sources", {}).get(source) or {}).get("lag_days", 1)
    out = df.copy()
    out["available_at"] = period_end(out[key_of(out)], freq) + pd.Timedelta(days=lag)
    return out


def asof(df: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    """Rows already published at time t."""
    return df[df["available_at"] <= t]
