"""Bridge to the current JavaScript bot: convert stored data to its input format, run its walk-forward scoring
with node (tools/export_current_bot.js) and load the weekly scores back.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile

import pandas as pd

from bot.config import DATA, ROOT
from bot.data import pit_store

CACHE = DATA / "derived" / "current_bot_scores.json"


def browser_input() -> dict:
    """Coin Metrics, Binance klines and Fear & Greed in the exact shapes the web page downloads."""
    cm = pit_store.load_history("coinmetrics")
    kl = pit_store.load_history("binance_spot")
    fng = pit_store.load_history("fng")
    nz = lambda v: None if pd.isna(v) else repr(float(v))  # noqa: E731
    cm_rows = [{"time": f"{d:%Y-%m-%d}T00:00:00.000000000Z", "PriceUSD": nz(p), "CapMrktCurUSD": nz(m), "CapMVRVCur": nz(v), "IssTotUSD": nz(i)}
               for d, p, m, v, i in zip(cm["date"], cm["price"], cm["mcap"], cm["mvrv"], cm["iss_usd"])]
    kl_rows = [[int(d.value // 1_000_000), "0", "0", "0", repr(float(c)), "0", 0, repr(float(q))] for d, c, q in zip(kl["date"], kl["close"], kl["quote_volume"])]
    fng_rows = [{"value": str(int(v)), "timestamp": str(int(d.value // 1_000_000_000))} for d, v in zip(fng["date"], fng["fng"])]
    return {"cm": cm_rows, "kl": kl_rows, "fng": fng_rows}


def export(every: int = 4, auto_from: str = "2021-01-03", force: bool = False) -> dict:
    """Run the JS export once and cache it in data/derived (rebuilt when forced or missing)."""
    if CACHE.exists() and not force:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        inp = pathlib.Path(tmp) / "in.json"
        inp.write_text(json.dumps(browser_input()), encoding="utf-8")
        out = pathlib.Path(tmp) / "out.json"
        subprocess.run(["node", "tools/export_current_bot.js", str(inp), str(out), str(every), auto_from], cwd=ROOT, check=True)
        res = json.loads(out.read_text(encoding="utf-8"))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(res), encoding="utf-8")
    return res


def series(res: dict, key: str) -> pd.DataFrame:
    """Weekly scores of a fixed option ('pa1'…'pa5', 'all') or the re-selected 'auto' bot.

    Columns: date (Sunday of the score), buy, sell, ids. Scores of a set at a past Sunday do not depend on later data
    (walk-forward), so the auto bot uses, from each re-selection date on, the series of the set chosen that day."""
    def frame(s: dict) -> pd.DataFrame:
        df = pd.DataFrame(s["buy"], columns=["date", "buy", "sell"])
        df["date"] = pd.to_datetime(df["date"])
        df["ids"] = ",".join(s["ids"])
        return df

    if key != "auto":
        return frame(res["fixed"][key])
    sets = {",".join(sorted(s["ids"])): frame(s) for s in res["sets"]}
    picks = res["auto"]
    # before the first re-selection the ranking window (from 01/01/2021) is empty and the UI falls back to all indicators
    first = frame(res["fixed"]["all"])
    parts = [first[first["date"] < pd.Timestamp(picks[0]["date"])].assign(option="all")]
    for k, a in enumerate(picks):
        lo = pd.Timestamp(a["date"])
        hi = pd.Timestamp(picks[k + 1]["date"]) if k + 1 < len(picks) else pd.Timestamp.max
        s = sets[",".join(sorted(a["ids"]))]
        parts.append(s[(s["date"] >= lo) & (s["date"] < hi)].assign(option=a["option"]))
    return pd.concat(parts, ignore_index=True)
