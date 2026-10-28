"""Data quality checks run on every fetch: duplicates, order, gaps, outliers (flagged, not removed), staleness.

Errors block saving and trigger the DCA fallback; warnings are reported only.
"""
from __future__ import annotations

import dataclasses
import datetime as dt

import numpy as np
import pandas as pd

from bot.i18n import fmt, t as tr

# allowed calendar gap between consecutive rows, and allowed age of the last row, per frequency
GAP_DAYS = {"D": 1, "B": 5, "M": 31, "8h": 1}
STALE_EXTRA = {"D": 0, "B": 4, "M": 75, "8h": 0}


@dataclasses.dataclass
class QualityReport:
    source: str
    ok: bool = True
    errors: list[str] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)
    last: str | None = None
    rows: int = 0

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def check(df: pd.DataFrame, source: str, values: list[str], freq: str = "D", stale_days: int = 3,
          now: dt.datetime | None = None, key: str | None = None, max_gap_warn: int = 3) -> QualityReport:
    """Run every check on a tidy frame (sorted by key) and return a report."""
    rep = QualityReport(source=source, rows=len(df))
    if df.empty:
        rep.ok, rep.errors = False, [tr("quality.empty")]
        return rep
    key = key or ("time" if "time" in df.columns else "date")
    t = pd.to_datetime(df[key])
    if t.duplicated().any():
        rep.errors.append(tr("quality.duplicates", n=int(t.duplicated().sum())))
    if not t.is_monotonic_increasing:
        rep.errors.append(tr("quality.not_sorted"))
    day = t.dt.normalize().drop_duplicates().reset_index(drop=True)
    gaps = day.diff().dt.days.fillna(1)
    big = gaps[gaps > GAP_DAYS.get(freq, 1)]
    if len(big):
        where = ", ".join(f"{fmt.date(day.iloc[i - 1])}→{fmt.date(day.iloc[i])}" for i in big.index[:3] if i > 0)
        msg = tr("quality.gaps", n=len(big), max=int(big.max()), where=where)
        (rep.errors if len(big) > max_gap_warn and freq == "D" else rep.warnings).append(msg)
    for c in values:
        v = pd.to_numeric(df[c], errors="coerce")
        if (v <= 0).any() and c not in ("funding_rate", "real_yield_10y"):
            rep.warnings.append(tr("quality.non_positive", col=c))
        lv = np.log(v.where(v > 0)) if c not in ("funding_rate", "real_yield_10y") else v
        ch = lv.diff()
        sd = ch.std()
        if sd and np.isfinite(sd):
            out = ch[(ch - ch.mean()).abs() > 5 * sd]
            if len(out):
                rep.warnings.append(tr("quality.outliers", col=c, n=len(out), last=fmt.date(t[out.index[-1]])))
    valid = df.dropna(subset=[values[0]]) if values else df
    last = pd.to_datetime(valid[key]).max()
    rep.last = None if pd.isna(last) else last.strftime("%Y-%m-%d")
    now = now or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    age = (pd.Timestamp(now).normalize() - last.normalize()).days if rep.last else 10**6
    if age > stale_days + STALE_EXTRA.get(freq, 0):
        rep.errors.append(tr("quality.stale", last=fmt.date(last), days=age))
    rep.ok = not rep.errors
    return rep
