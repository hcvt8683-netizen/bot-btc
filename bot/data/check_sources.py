"""Reachability check of every data endpoint (used on the GitHub runner, logged into docs/DEPLOY.md)."""
from __future__ import annotations

import time

from bot.data import http

ENDPOINTS = {
    "Coin Metrics": "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD&page_size=1",
    "Alternative.me": "https://api.alternative.me/fng/?limit=1",
    "Binance api (spot)": "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1",
    "Binance data-api.binance.vision (spot)": "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1",
    "Binance fapi (funding, OI)": "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1",
    "Binance dapi (quarterly futures)": "https://dapi.binance.com/dapi/v1/continuousKlines?pair=BTCUSD&contractType=CURRENT_QUARTER&interval=1d&limit=1",
    "CoinGecko": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
    "DefiLlama": "https://stablecoins.llama.fi/stablecoincharts/all",
    "FRED (CSV)": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10",
}


def run() -> list[tuple[str, str, float]]:
    rows = []
    for name, url in ENDPOINTS.items():
        t0 = time.time()
        try:
            http.get(url, timeout=30, retries=1)
            res = "200 OK"
        except http.FetchError as e:
            res = f"HTTP {e.status}" if e.status else str(e)[:60]
        rows.append((name, res, round(time.time() - t0, 1)))
    print("| Nguồn | Kết quả | Giây |\n|---|---|---|")
    for r in rows:
        print(f"| {r[0]} | {r[1]} | {r[2]} |")
    return rows
