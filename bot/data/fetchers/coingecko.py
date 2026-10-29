"""CoinGecko public API: daily BTC price. The free tier only serves the last 365 days, so it is used to cross-check
the other price sources over the most recent year, never as a model input."""
from __future__ import annotations

import pandas as pd

from bot.data import http

URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365&interval=daily"


def parse(j: dict) -> pd.DataFrame:
    df = pd.DataFrame(j["prices"], columns=["t", "price"])
    # CoinGecko stamps the daily point at 00:00 UTC with the price at that instant = close of the previous day
    out = pd.DataFrame({"date": pd.to_datetime(df["t"], unit="ms").dt.normalize() - pd.Timedelta(days=1), "price": df["price"]})
    return out.drop_duplicates("date", keep="first").sort_values("date").reset_index(drop=True)


def fetch() -> pd.DataFrame:
    df = parse(http.get_json(URL))
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    return df[df["date"] < today - pd.Timedelta(days=0)].reset_index(drop=True)
