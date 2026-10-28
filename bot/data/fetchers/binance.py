"""Binance public market data (read-only, no API key): spot klines, funding rate, open interest, quarterly basis.

`api.binance.com` and `fapi/dapi.binance.com` often answer HTTP 451/403 from US data centers (GitHub runners);
spot klines fall back to `data-api.binance.vision`. Futures data has no mirror: the caller marks it unavailable.
"""
from __future__ import annotations

import pandas as pd

from bot.data import http

SPOT = ["https://api.binance.com/api/v3/klines", "https://data-api.binance.vision/api/v3/klines"]
FUNDING = "https://fapi.binance.com/fapi/v1/fundingRate"
OI_HIST = "https://fapi.binance.com/futures/data/openInterestHist"
DAPI_CONT = "https://dapi.binance.com/dapi/v1/continuousKlines"
DAY_MS = 86_400_000


def _klines_df(rows: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(rows).iloc[:, :8]
    df.columns = ["t", "open", "high", "low", "close", "volume", "t_close", "quote_volume"]
    out = pd.DataFrame({"date": pd.to_datetime(df["t"].astype("int64"), unit="ms")})
    for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
        out[c] = pd.to_numeric(df[c], errors="coerce")
    return out


def fetch_spot(start: str = "2017-08-17", end_ms: int | None = None) -> pd.DataFrame:
    """Daily BTCUSDT spot candles. Drops the still-open candle of today."""
    last_err: Exception | None = None
    for base in SPOT:
        try:
            s, rows = int(pd.Timestamp(start).value // 1_000_000), []
            for _ in range(20):
                j = http.get_json(f"{base}?symbol=BTCUSDT&interval=1d&startTime={s}&limit=1000")
                if not j:
                    break
                rows += j
                s = j[-1][0] + DAY_MS
                if len(j) < 1000:
                    break
            df = _klines_df(rows)
            now = pd.Timestamp.utcnow().tz_localize(None).normalize() if end_ms is None else pd.Timestamp(end_ms, unit="ms").normalize()
            return df[df["date"] < now].drop_duplicates("date").reset_index(drop=True)
        except http.FetchError as e:
            last_err = e
    raise last_err or http.FetchError(SPOT[0], "no data")


def parse_funding(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    return pd.DataFrame({"time": pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms"),
                         "funding_rate": pd.to_numeric(df["fundingRate"], errors="coerce")})


def fetch_funding(start: str = "2019-09-01") -> pd.DataFrame:
    """Every 8-hour funding rate of the BTCUSDT perpetual since launch (Sep 2019)."""
    s, rows = int(pd.Timestamp(start).value // 1_000_000), []
    for _ in range(60):
        j = http.get_json(f"{FUNDING}?symbol=BTCUSDT&startTime={s}&limit=1000")
        if not j:
            break
        rows += j
        s = int(j[-1]["fundingTime"]) + 1
        if len(j) < 1000:
            break
    return parse_funding(rows).drop_duplicates("time").sort_values("time").reset_index(drop=True)


def parse_oi(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    return pd.DataFrame({"date": pd.to_datetime(df["timestamp"].astype("int64"), unit="ms"),
                         "oi_btc": pd.to_numeric(df["sumOpenInterest"], errors="coerce"),
                         "oi_usd": pd.to_numeric(df["sumOpenInterestValue"], errors="coerce")})


def fetch_oi() -> pd.DataFrame:
    """Daily open interest; Binance keeps only ~30 days, so this must be recorded forward every day."""
    return parse_oi(http.get_json(f"{OI_HIST}?symbol=BTCUSDT&period=1d&limit=500"))


def fetch_basis(start: str = "2020-08-01") -> pd.DataFrame:
    """Daily close of the current-quarter coin-margined future (BTCUSD); basis is computed later against spot."""
    s, end, rows = pd.Timestamp(start), pd.Timestamp.utcnow().tz_localize(None), []
    while s < end:
        e = min(s + pd.Timedelta(days=199), end)
        j = http.get_json(f"{DAPI_CONT}?pair=BTCUSD&contractType=CURRENT_QUARTER&interval=1d"
                          f"&startTime={s.value // 1_000_000}&endTime={e.value // 1_000_000}&limit=1500")
        rows += j
        s = e + pd.Timedelta(days=1)
    df = _klines_df(rows)[["date", "close"]].rename(columns={"close": "fut_close"})
    today = end.normalize()
    return df[df["date"] < today].drop_duplicates("date").sort_values("date").reset_index(drop=True)
