"""Alternative.me Fear & Greed index (daily, from 2018-02)."""
from __future__ import annotations

import pandas as pd

from bot.data import http

URL = "https://api.alternative.me/fng/?limit=0&format=json"


def parse(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    out = pd.DataFrame({"date": pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="s").dt.normalize(),
                        "fng": pd.to_numeric(df["value"], errors="coerce")})
    return out.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def fetch() -> pd.DataFrame:
    return parse(http.get_json(URL)["data"])
