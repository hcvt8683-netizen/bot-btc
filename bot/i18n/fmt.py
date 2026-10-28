"""vi-VN number, money and date formats (single source; the web page mirrors these in JavaScript).

| Type | Example |
|---|---|
| USD price | 80.754 $ |
| Decimal | 0,49 |
| Percent | 79%, -5%, +19% |
| Date | 28/10/2026 |
| Date and time (Vietnam time) | 01:00 29/10/2026 |
| BTC amount | 0,0248 BTC |
"""
from __future__ import annotations

import datetime as dt
import math
from zoneinfo import ZoneInfo

VN = ZoneInfo("Asia/Ho_Chi_Minh")
DASH = "—"


def _ok(x: float | None) -> bool:
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def num(x: float | None, d: int = 0) -> str:
    """Thousands with '.', decimals with ','."""
    if not _ok(x):
        return DASH
    s = f"{abs(x):,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return ("-" if x < 0 and float(f"{abs(x):.{d}f}") != 0 else "") + s


def usd(x: float | None, d: int = 0) -> str:
    return DASH if not _ok(x) else f"{num(x, d)} $"


def dec(x: float | None, d: int = 2) -> str:
    return num(x, d)


def pct(x: float | None, d: int = 0, sign: bool = False) -> str:
    """x is a fraction (0.79 → 79%). sign=True adds '+' to positive values."""
    if not _ok(x):
        return DASH
    s = num(x * 100, d) + "%"
    return ("+" + s) if sign and round(x * 100, d) > 0 else s


def btc(x: float | None) -> str:
    """4–8 decimals, enough for 3 significant digits."""
    if not _ok(x):
        return DASH
    d = 4 if x == 0 or abs(x) >= 0.01 else min(8, max(4, 2 - math.floor(math.log10(abs(x)))))
    return f"{num(x, d)} BTC"


def date(d: dt.date | dt.datetime | str | None) -> str:
    if d is None:
        return DASH
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10])
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def datetime_vn(t: dt.datetime | str | None) -> str:
    """UTC (aware or naive-UTC) → 'HH:mm dd/mm/yyyy' in Vietnam time."""
    if t is None:
        return DASH
    if isinstance(t, str):
        t = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    v = t.astimezone(VN)
    return f"{v:%H:%M} {date(v)}"
