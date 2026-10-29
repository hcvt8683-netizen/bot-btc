"""Bitstamp public OHLC (no key): daily BTC/USD candles from 2011-08-18. Second price source for the years before
Binance (2017) and for cross-checking Coin Metrics. A row dated d is the candle that opens at d 00:00 UTC."""
from __future__ import annotations

import pandas as pd

from bot.data import http

URL = "https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000&start={start}"
FIRST = 1313625600  # 2011-08-18


def parse(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    out = pd.DataFrame({"date": pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="s")})
    for c in ("open", "high", "low", "close", "volume"):
        out[c] = pd.to_numeric(df[c], errors="coerce")
    return out


def fetch() -> pd.DataFrame:
    """All daily candles; drops today's still-open candle."""
    rows, start = [], FIRST
    for _ in range(20):
        j = http.get_json(URL.format(start=start))
        batch = (j.get("data") or {}).get("ohlc") or []
        if not batch:
            break
        rows += batch
        nxt = int(batch[-1]["timestamp"]) + 86400
        if nxt <= start or len(batch) < 1000:
            break
        start = nxt
    df = parse(rows).drop_duplicates("date").sort_values("date")
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    return df[df["date"] < today].reset_index(drop=True)
