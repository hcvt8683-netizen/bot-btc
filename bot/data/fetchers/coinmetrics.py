"""Coin Metrics community API (free, CC BY-NC 4.0): price, market cap, MVRV, hash rate, issuance.

`CapRealUSD` is not in the free tier, so realized cap is derived as market cap / MVRV.
"""
from __future__ import annotations

import urllib.parse

import pandas as pd

from bot.data import http

BASE = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
METRICS = {"PriceUSD": "price", "CapMrktCurUSD": "mcap", "CapMVRVCur": "mvrv", "HashRate": "hashrate", "IssTotUSD": "iss_usd"}


def url(start: str = "2010-07-18") -> str:
    q = {"assets": "btc", "metrics": ",".join(METRICS), "start_time": start, "page_size": 10000,
         "ignore_forbidden_errors": "true", "ignore_unsupported_errors": "true"}
    return BASE + "?" + urllib.parse.urlencode(q)


def parse(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    out = pd.DataFrame({"date": pd.to_datetime(df["time"].str.slice(0, 10))})
    for k, v in METRICS.items():
        out[v] = pd.to_numeric(df[k], errors="coerce") if k in df else float("nan")
    out = out[out["price"] > 0]
    out["realized_cap"] = out["mcap"] / out["mvrv"]
    return out.sort_values("date").reset_index(drop=True)


def fetch(start: str = "2010-07-18") -> pd.DataFrame:
    rows, u = [], url(start)
    for _ in range(10):
        j = http.get_json(u, timeout=120)
        rows += j.get("data") or []
        u = j.get("next_page_url")
        if not u:
            break
    if not rows:
        raise http.FetchError(url(start), "no data")
    return parse(rows)
