"""Binance public data archive `data.binance.vision` (zip files of CSV, no key): fallback for the futures sources
when fapi/dapi.binance.com answer HTTP 451/403 (GitHub runners in the US).

Same columns and values as the API (checked on 02/11/2026 against the API snapshots of 28–29/10/2026):
- funding rate: monthly file, one row per funding time (identical to the millisecond); a month appears a few days
  after it ends, so the newest rows can be about a month old;
- open interest: the API row of day d (`openInterestHist`, 1d) is the last 5-minute row of the daily `metrics` file
  of day d−1 (23:55); a daily file appears about one day after the day ends;
- quarterly future: daily candles of the coin-margined contract BTCUSD_YYMMDD that expires after day d
  (CURRENT_QUARTER rolls to the next contract on the expiry day).
A file not published yet (HTTP 404) is skipped; the quality checks then report the gap or the staleness (the archive
also misses a file now and then, e.g. the quarterly candle of 28/10/2026).
"""
from __future__ import annotations

import datetime as dt
import io
import zipfile

import pandas as pd

from bot.data import http

BASE = "https://data.binance.vision/data/futures"
FUNDING = BASE + "/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{month}.zip"
METRICS = BASE + "/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-{day}.zip"
CM_KLINES = BASE + "/cm/daily/klines/{symbol}/1d/{symbol}-1d-{day}.zip"
DAYS = 14  # daily files read per run: refills two weeks of missed runs (some files answer slowly, ~20 s)
KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count",
              "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def read_zip_csv(blob: bytes, names: list[str] | None = None) -> pd.DataFrame:
    """First CSV of a zip. With `names`, the file may or may not have a header row (older kline files have none)."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        raw = z.read(z.namelist()[0])
    if names is None:
        return pd.read_csv(io.BytesIO(raw))
    df = pd.read_csv(io.BytesIO(raw), header=None, names=names)
    return df[df[names[0]].astype(str) != names[0]].reset_index(drop=True)


def _get(url: str, names: list[str] | None = None) -> pd.DataFrame | None:
    """One archive file; None when it is not published yet (HTTP 404). Other errors (e.g. 451) are raised."""
    try:
        return read_zip_csv(http.get(url), names)
    except http.FetchError as e:
        if e.status == 404:
            return None
        raise


def _today(today: dt.date | None) -> dt.date:
    return today or dt.datetime.now(dt.timezone.utc).date()


def parse_funding(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"time": pd.to_datetime(df["calc_time"].astype("int64"), unit="ms"),
                         "funding_rate": pd.to_numeric(df["last_funding_rate"], errors="coerce")})


def fetch_funding(months: int = 2, today: dt.date | None = None) -> pd.DataFrame:
    """Funding rates of the last `months` complete months (the current month is published only after it ends)."""
    this = pd.Period(_today(today), "M")
    parts = [f for k in range(months, 0, -1) if (f := _get(FUNDING.format(month=str(this - k)))) is not None]
    if not parts:
        return pd.DataFrame(columns=["time", "funding_rate"])
    out = parse_funding(pd.concat(parts, ignore_index=True))
    return out.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def oi_row(metrics: pd.DataFrame, day: dt.date) -> dict | None:
    """API-style row dated day+1 from the metrics file of `day`: its last 5-minute row (None if the day is incomplete)."""
    m = metrics.assign(t=pd.to_datetime(metrics["create_time"])).sort_values("t")
    last = m.iloc[-1]
    if last["t"] < pd.Timestamp(day) + pd.Timedelta(hours=23):
        return None
    return {"date": pd.Timestamp(day + dt.timedelta(days=1)), "oi_btc": float(last["sum_open_interest"]),
            "oi_usd": float(last["sum_open_interest_value"])}


def fetch_oi(days: int = DAYS, today: dt.date | None = None) -> pd.DataFrame:
    """Daily open interest like `openInterestHist` (1d) from the daily metrics files of the last `days` days."""
    t, rows = _today(today), []
    for k in range(days, 0, -1):
        d = t - dt.timedelta(days=k)
        m = _get(METRICS.format(day=d.isoformat()))
        if m is not None and len(m) and (r := oi_row(m, d)):
            rows.append(r)
    return pd.DataFrame(rows, columns=["date", "oi_btc", "oi_usd"]).astype({"date": "datetime64[ms]"})


def _last_friday(year: int, month: int) -> dt.date:
    end = dt.date(year + month // 12, month % 12 + 1, 1) - dt.timedelta(days=1)
    return end - dt.timedelta(days=(end.weekday() - 4) % 7)


def current_quarter_expiry(day: dt.date) -> dt.date:
    """Expiry (last Friday of Mar/Jun/Sep/Dec) of the current-quarter contract on `day`: the first one after it."""
    y, q = day.year, (day.month - 1) // 3
    while (e := _last_friday(y, 3 * q + 3)) <= day:
        y, q = (y + 1, 0) if q == 3 else (y, q + 1)
    return e


def fetch_basis(days: int = DAYS, today: dt.date | None = None) -> pd.DataFrame:
    """Daily close of the current-quarter BTCUSD future, like dapi `continuousKlines` CURRENT_QUARTER."""
    t, rows = _today(today), []
    for k in range(days, 0, -1):
        d = t - dt.timedelta(days=k)
        symbol = "BTCUSD_" + current_quarter_expiry(d).strftime("%y%m%d")
        c = _get(CM_KLINES.format(symbol=symbol, day=d.isoformat()), KLINE_COLS)
        if c is not None and len(c):
            rows.append({"date": pd.Timestamp(d), "fut_close": float(c["close"].iloc[0])})
    return pd.DataFrame(rows, columns=["date", "fut_close"]).astype({"date": "datetime64[ms]"})
