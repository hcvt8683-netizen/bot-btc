"""FRED macro series. The public graph CSV needs no key; with FRED_API_KEY set, the official API is used instead."""
from __future__ import annotations

import io
import os

import pandas as pd

from bot.data import http

SERIES = {"DTWEXBGS": "usd_broad", "DFII10": "real_yield_10y", "NASDAQCOM": "nasdaq", "M2SL": "m2"}
MONTHLY = {"M2SL"}


def parse_csv(text: str, series: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text))
    df.columns = ["date", "value"]
    return pd.DataFrame({"date": pd.to_datetime(df["date"]), SERIES[series]: pd.to_numeric(df["value"], errors="coerce")}).dropna()


def fetch_one(series: str) -> pd.DataFrame:
    key = os.environ.get("FRED_API_KEY")
    if key:
        j = http.get_json(f"https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={key}&file_type=json")
        df = pd.DataFrame(j["observations"])
        return pd.DataFrame({"date": pd.to_datetime(df["date"]), SERIES[series]: pd.to_numeric(df["value"], errors="coerce")}).dropna()
    return parse_csv(http.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}").decode("utf-8"), series)


def fetch() -> dict[str, pd.DataFrame]:
    return {s: fetch_one(s) for s in SERIES}
