"""DefiLlama stablecoins API: total circulating USD-pegged stablecoin supply (daily, from 2017-11)."""
from __future__ import annotations

import pandas as pd

from bot.data import http

URL = "https://stablecoins.llama.fi/stablecoincharts/all"


def parse(rows: list[dict]) -> pd.DataFrame:
    out = pd.DataFrame({"date": pd.to_datetime([int(r["date"]) for r in rows], unit="s").normalize(),
                        "stable_usd": [float((r.get("totalCirculatingUSD") or {}).get("peggedUSD") or "nan") for r in rows]})
    return out.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def fetch() -> pd.DataFrame:
    return parse(http.get_json(URL))
