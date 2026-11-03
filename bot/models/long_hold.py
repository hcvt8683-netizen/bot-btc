"""Buy and hold: bought on any day since 2016 and held h days, how often was it a gain after costs (config/candidates.yaml,
section long_hold; registered before any number was computed). Not a direction forecast: every buying day counts.
The buying price is the entry module's result read back (waiting for a lower price never beat buying now), with the fill
chances of limit orders below today's price (data/results/entry.json)."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.models import price_forecast as pf

OUT = DATA / "results" / "hold.json"
DISCOUNTS = ("0.01", "0.02", "0.03", "0.05", "0.08", "0.10")


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["long_hold"]


def version(cfg: dict) -> str:
    code = (ROOT / "bot" / "models" / "long_hold.py").read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def gains(p: pd.Series, h: int, cost: float) -> pd.Series:
    """Return of buying at the close of T and selling at the close of T + h, after costs on both sides (NaN if unknown)."""
    return p.shift(-h) * (1 - cost) / (p * (1 + cost)) - 1


def stats(r: np.ndarray, h: int) -> dict:
    n = len(r)
    if not n:
        return {"n": 0}
    win = r > 0
    eff = max(1, round(n / h))
    return {"n": n, "n_eff": eff, "p": float(win.mean()), "ci": list(wilson(round(float(win.mean()) * eff), eff)),
            "median": float(np.median(r)), "p10": float(np.quantile(r, 0.10)), "p90": float(np.quantile(r, 0.90))}


def table(p: pd.Series, cfg: dict) -> list[dict]:
    start = pd.Timestamp(str(cfg["period"]["from"]))
    rows = []
    for h in cfg["horizons_days"]:
        g = gains(p, int(h), float(cfg["costs"]))
        g = g[(g.index >= start) & g.notna()]
        if g.empty:
            rows.append({"h": int(h), "n": 0})
            continue
        mid = g.index[len(g) // 2]
        halves = [stats(g[g.index < mid].to_numpy(), int(h)), stats(g[g.index >= mid].to_numpy(), int(h))]
        rows.append({"h": int(h), **stats(g.to_numpy(), int(h)), "halves": halves, "from": g.index[0].strftime("%Y-%m-%d"),
                     "to": g.index[-1].strftime("%Y-%m-%d"), "split": mid.strftime("%Y-%m-%d")})
    return rows


def hold_at_least(rows: list[dict]) -> int | None:
    """Shortest holding time with a gain at least 80% of the time in both halves and a Wilson lower bound of 50% or more."""
    for r in rows:
        if r.get("n") and r["ci"][0] is not None and r["ci"][0] >= 0.5 and all(x.get("n") and x["p"] >= 0.8 for x in r["halves"]):
            return r["h"]
    return None


def buy_price(path=None) -> dict | None:
    """What the entry module already says (read back, nothing computed): fill chances of limit orders, and the verdict of
    'buy now or wait'."""
    path = path or DATA / "results" / "entry.json"
    if not path.exists():
        return None
    e = json.loads(path.read_text(encoding="utf-8"))
    by_k = {r["k"]: r for r in e["rows"]}
    waits = e["wait"]["rows"]
    return {"anchor": e["anchor"], "price": e["price"],
            "fills": {str(k): {x: by_k[k]["probs"].get(x) for x in DISCOUNTS} for k in (7, 30) if k in by_k},
            "low30": {q: by_k[30][q] for q in ("q10", "q50", "q90")} if 30 in by_k else None,
            "wait": {"configs": len(waits), "better": sum(w["verdict"] == "cho" for w in waits), "worse": sum(w["verdict"] == "ngay" for w in waits)}}


def run(write: bool = True, end: pd.Timestamp | None = None) -> dict:
    cfg = spec()
    p = pf.daily_prices(end)
    rows = table(p, cfg)
    T = p.dropna().index[-1]
    out = {"version": version(cfg), "anchor": T.strftime("%Y-%m-%d"), "price": float(p.loc[T]), "costs": cfg["costs"],
           "rows": rows, "hold_at_least": hold_at_least(rows), "buy": buy_price()}
    if write:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out
