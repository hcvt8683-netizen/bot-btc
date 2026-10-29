"""Extra Coin Metrics community fields kept as a separate source (the main `coinmetrics` snapshots keep their schema):
- AssetEODCompletionTime: when the end-of-day metrics of that row were complete (publication timestamp);
- volume_reported_spot_usd_1d: reported spot volume across exchanges (longer history than Binance, 2017+);
- SplyCur, IssTotNtv: supply and native issuance (for checks of the derived realized cap and Puell)."""
from __future__ import annotations

import urllib.parse

import pandas as pd

from bot.data import http

BASE = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
METRICS = {"AssetEODCompletionTime": "eod_completed_at", "volume_reported_spot_usd_1d": "volume_spot_usd", "SplyCur": "supply",
           "IssTotNtv": "iss_btc"}


def url(start: str = "2010-07-18") -> str:
    q = {"assets": "btc", "metrics": ",".join(METRICS), "start_time": start, "page_size": 10000,
         "ignore_forbidden_errors": "true", "ignore_unsupported_errors": "true"}
    return BASE + "?" + urllib.parse.urlencode(q)


def parse(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    out = pd.DataFrame({"date": pd.to_datetime(df["time"].str.slice(0, 10))})
    for k, v in METRICS.items():
        out[v] = pd.to_numeric(df[k], errors="coerce") if k in df else float("nan")
    out["eod_completed_at"] = pd.to_datetime(out["eod_completed_at"], unit="s")
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
