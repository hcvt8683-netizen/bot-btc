"""Daily data job: fetch every source, check quality, save immutable snapshots, write data/status.json.

One failed source never stops the others; its features become unavailable and the report falls back to DCA
if a required source is missing or stale.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import traceback
from typing import Callable

import pandas as pd

from bot.config import DATA, cfg
from bot.data import pit_store, quality
from bot.data.fetchers import alternative, binance, bitstamp, coingecko, coinmetrics, coinmetrics_ext, defillama, fred


@dataclasses.dataclass
class Source:
    name: str
    fetch: Callable[[], pd.DataFrame]
    values: list[str]
    freq: str = "D"
    stale_days: int | None = None
    forward_only: bool = False  # history cannot be downloaded later: every snapshot keeps all returned rows


def _fred(series: str) -> Callable[[], pd.DataFrame]:
    return lambda: fred.fetch_one(series)


SOURCES: list[Source] = [
    Source("coinmetrics", coinmetrics.fetch, ["price", "mcap", "mvrv", "hashrate", "iss_usd"]),
    Source("coinmetrics_ext", coinmetrics_ext.fetch, ["volume_spot_usd", "supply"]),
    Source("bitstamp", bitstamp.fetch, ["close"]),
    Source("coingecko", coingecko.fetch, ["price"]),
    Source("fng", alternative.fetch, ["fng"]),
    Source("binance_spot", binance.fetch_spot, ["close", "quote_volume"]),
    Source("binance_funding", binance.fetch_funding, ["funding_rate"], freq="8h"),
    Source("binance_oi", binance.fetch_oi, ["oi_usd"], forward_only=True),
    Source("binance_basis", binance.fetch_basis, ["fut_close"]),
    Source("stablecoins", defillama.fetch, ["stable_usd"]),
    *[Source(f"fred_{s}", _fred(s), [col], freq="M" if s in fred.MONTHLY else "B") for s, col in fred.SERIES.items()],
]


def run(names: list[str] | None = None, now: dt.datetime | None = None, save: bool = True) -> dict:
    """Fetch, check and store; returns and writes the status of every source."""
    now = now or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    stale = int((cfg().get("risk") or {}).get("stale_data_days", 3))
    status = {"fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "sources": {}}
    for s in SOURCES:
        if names and s.name not in names:
            continue
        entry: dict = {"ok": False}
        try:
            df = s.fetch()
            rep = quality.check(df, s.name, s.values, freq=s.freq, stale_days=s.stale_days or stale, now=now)
            entry.update(rep.to_dict())
            if rep.ok and save:
                p = pit_store.save_snapshot(s.name, df, now.date(), recent_days=None if s.forward_only else pit_store.RECENT_DAYS)
                entry["snapshot"] = p.name if p else "đã có bản hôm nay"
        except Exception as e:  # noqa: BLE001 - one source must never stop the run
            entry.update({"ok": False, "errors": [f"{type(e).__name__}: {str(e)[:200]}"], "trace": traceback.format_exc(limit=2)[-400:]})
        status["sources"][s.name] = entry
        print(f"{s.name:18s} {'OK ' if entry.get('ok') else 'LỖI'} {entry.get('last') or ''} {'; '.join(entry.get('errors') or [])[:160]}")
    if save:
        path = DATA / "status.json"
        old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"sources": {}}
        old["sources"].update(status["sources"])
        old["fetched_at"] = status["fetched_at"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    return status
