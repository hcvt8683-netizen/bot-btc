"""Macro event calendar from official pages: FOMC (federalreserve.gov), CPI (bls.gov), PCE (bea.gov).

Used once to build config/events.yaml (then maintained by hand). Times are stored in UTC.
Monthly crypto options expiry is a rule (last Friday, 08:00 UTC) and is computed, not stored.
"""
from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo

from bot.data import http

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
MONTHS = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                          "September", "October", "November", "December"])}
FED_CAL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FED_HIST = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
BLS_CPI = "https://www.bls.gov/bls/news-release/cpi.htm"
BEA_SCHEDULE = "https://www.bea.gov/news/schedule"


def et_to_utc(day: dt.date, hh: int, mm: int) -> str:
    """Eastern-time clock on a given day → ISO UTC string (handles daylight saving)."""
    t = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=ET).astimezone(UTC)
    return t.strftime("%Y-%m-%dT%H:%MZ")


ABBR = {m[:3]: i for m, i in MONTHS.items()}


def _last_day(month_txt: str, days_txt: str, year: int) -> dt.date:
    """'Apr/May' + '30-1' → May 1; 'January' + '27-28*' → Jan 28."""
    months = [ABBR[m[:3]] for m in re.findall(r"[A-Z][a-z]+", month_txt) if m[:3] in ABBR]
    days = [int(x) for x in re.findall(r"\d+", days_txt)]
    return dt.date(year, months[-1], days[-1])


def parse_fomc_calendar(html: str) -> list[dt.date]:
    """Current calendar page: one panel per year with month/date cells; skips unscheduled meetings and notation votes."""
    out: list[dt.date] = []
    for m in re.finditer(r'<h4><a id="\d+">(\d{4}) FOMC Meetings</a></h4>(.*?)(?=<h4><a id="\d+">\d{4} FOMC Meetings|$)', html, re.S):
        year, body = int(m.group(1)), m.group(2)
        for row in re.finditer(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<', body, re.S):
            month_txt, days_txt = row.group(1).strip(), row.group(2).strip()
            if "unscheduled" in days_txt.lower() or "notation" in days_txt.lower() or not re.search(r"\d", days_txt):
                continue
            out.append(_last_day(month_txt, days_txt, year))
    return sorted(set(out))


def parse_fomc_historical(html: str) -> list[dt.date]:
    """Historical year page: scheduled meetings only, e.g. 'July 31-August 1 Meeting - 2012', 'April/May 30-1 Meeting - 2013'.
    Skips conference calls, notation votes, unscheduled and cancelled meetings."""
    out = []
    for h in re.findall(r"<h5[^>]*>([^<]+)</h5>", html):
        m = re.match(r"\s*(.+?)\s+Meeting\s*-\s*(\d{4})\s*$", h)
        if not m or "(" in h:
            continue
        out.append(_last_day(m.group(1), m.group(1), int(m.group(2))))
    return sorted(set(out))


def parse_cpi_archive(html: str) -> list[dt.date]:
    """BLS CPI archive links are named cpi_MMDDYYYY.htm (release date)."""
    out = []
    for mm, dd, yyyy in re.findall(r"cpi_(\d{2})(\d{2})(\d{4})\.htm", html):
        out.append(dt.date(int(yyyy), int(mm), int(dd)))
    return sorted(set(out))


def parse_bea_pce(html: str) -> list[dt.date]:
    """BEA release schedule: 'Personal Income and Outlays, <Month> <Year>' rows with a release date without year."""
    out = []
    for m in re.finditer(r'release-date">([A-Za-z]+) (\d{1,2})</div>.*?release-title[^>]*>\s*Personal Income and Outlays, ([A-Za-z]+) (\d{4})', html, re.S):
        rel_m, rel_d, ref_m, ref_y = MONTHS[m.group(1)], int(m.group(2)), MONTHS[m.group(3)], int(m.group(4))
        year = ref_y + (1 if rel_m < ref_m else 0)
        out.append(dt.date(year, rel_m, rel_d))
    return sorted(set(out))


def options_expiry(start: dt.date, end: dt.date) -> list[str]:
    """Last Friday of each month, 08:00 UTC (Deribit monthly expiry)."""
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        d = dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
        d -= dt.timedelta(days=(d.weekday() - 4) % 7)
        if start <= d <= end:
            out.append(f"{d.isoformat()}T08:00Z")
        y, m = y + (m == 12), m % 12 + 1
    return out


def fetch_all(first_year: int = 2011) -> dict[str, list[str]]:
    """Download and parse every calendar; returns UTC ISO times per event type."""
    fomc = set(parse_fomc_calendar(http.get(FED_CAL, ua=http.UA_PAGE).decode("utf-8", "replace")))
    for y in range(first_year, min(fomc).year if fomc else dt.date.today().year):
        fomc |= set(parse_fomc_historical(http.get(FED_HIST.format(year=y), ua=http.UA_PAGE).decode("utf-8", "replace")))
    cpi = [d for d in parse_cpi_archive(http.get(BLS_CPI, ua=http.UA_PAGE).decode("utf-8", "replace")) if d.year >= first_year]
    pce = parse_bea_pce(http.get(BEA_SCHEDULE, ua=http.UA_PAGE).decode("utf-8", "replace"))
    return {"fomc": [et_to_utc(d, 14, 0) for d in sorted(fomc)], "cpi": [et_to_utc(d, 8, 30) for d in cpi],
            "pce": [et_to_utc(d, 8, 30) for d in pce]}
