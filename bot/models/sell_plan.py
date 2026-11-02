"""Plan for selling a quantity of BTC in stages, the sell side of the deployment plan (config/candidates.yaml, section
sell_plan; registered before any number was computed).

For every past start week, 1 BTC is sold in N equal weekly parts at the Monday close (receiving price × (1 − slippage),
minus the fee, as the bot), cash already received earns nothing, and the total received is read 52 weeks after the first
sale (every plan has sold everything by then). Return = total received / (1 BTC × the Monday close of the first sale
week) − 1. Each plan gets the distribution of that return over all start weeks, the deepest fall of cash + unsold BTC,
and how often it received more than selling everything at once. The recommended plan follows the rule of the buy side:
among the best median and the plans not significantly worse (block-bootstrap interval of the median paired difference
contains 0), the one with the highest 10th percentile. No signal tilts the plans.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, cfg, load_yaml
from bot.models.deploy_plan import start_weeks


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["sell_plan"]


def outcomes(price: np.ndarray, starts: np.ndarray, n_weeks: int, horizon: int, fee: float, slip: float) -> tuple[np.ndarray, np.ndarray]:
    """Return after `horizon` weeks and the deepest fall of cash + unsold BTC, selling 1 BTC in `n_weeks` equal parts."""
    sells = np.zeros(horizon + 1)
    sells[:n_weeks] = 1.0 / n_weeks
    left = 1.0 - np.cumsum(sells)
    roi, mdd = np.empty(len(starts)), np.empty(len(starts))
    for k, i in enumerate(starts):
        p = price[i:i + horizon + 1]
        cash = np.cumsum(sells * p * (1 - slip) * (1 - fee))
        v = cash + left * p
        roi[k] = v[-1] / p[0] - 1
        mdd[k] = float(np.min(v / np.maximum.accumulate(v) - 1))
    return roi, mdd


def compute(t: pd.DataFrame, sc: dict, fee: float, slip: float, n_boot: int, seed: int, data_from: pd.Timestamp) -> dict:
    H = int(sc["horizon_weeks"])
    price = t["exec_monday"].to_numpy(dtype=float)
    starts = start_weeks(t, H, data_from)
    if len(starts) < 2 * H:
        return {"starts": int(len(starts)), "options": []}
    res = {int(n): outcomes(price, starts, int(n), H, fee, slip) for n in sc["options_weeks"]}
    first = int(sc["options_weeks"][0])
    once = res[first][0]
    best = max(res, key=lambda n: np.median(res[n][0]))
    idx = measure.stationary_indices(len(starts), H, n_boot, np.random.default_rng(seed))
    eps = max(1, len(starts) // H)
    opts = []
    for n, (roi, mdd) in res.items():
        d = res[best][0] - roi
        boot = np.median(d[idx], axis=1)
        ci = [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]
        beat = None if n == first else float(np.mean(roi > once))
        opts.append({"weeks": n, "median": float(np.median(roi)), "p10": float(np.quantile(roi, 0.10)), "p90": float(np.quantile(roi, 0.90)),
                     "worst": float(roi.min()), "below_start": float(np.mean(roi < 0)), "mdd_median": float(np.median(mdd)), "mdd_worst": float(mdd.min()),
                     "beat_once": beat, "beat_once_ci": list(wilson(round(beat * eps), eps)) if beat is not None else None,
                     "diff_vs_best": float(np.median(d)), "diff_ci": ci, "not_worse": bool(n == best or ci[0] <= 0 <= ci[1])})
    rec = max((o for o in opts if o["not_worse"]), key=lambda o: o["p10"])
    return {"from": t.index[starts[0]].strftime("%Y-%m-%d"), "to": t.index[starts[-1]].strftime("%Y-%m-%d"), "starts": int(len(starts)), "episodes": eps,
            "horizon": H, "options": opts, "best": int(best), "recommended": int(rec["weeks"])}


def for_report(t: pd.DataFrame | None = None) -> dict:
    """Block for data/recommendation.json (KN.sell_plan)."""
    from bot.features import weekly_close as wc
    sc = spec()
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    c = cfg()["costs"]
    t = wc.load(None) if t is None else t
    out = compute(t, sc, c["fee"], c["slippage"], rb["bootstrap_n"], rb["seed"], pd.Timestamp(str(sc["data_from"])))
    out["full"] = {k: v for k, v in compute(t, sc, c["fee"], c["slippage"], rb["bootstrap_n"], rb["seed"], pd.Timestamp(str(sc["data_from_full"]))).items()
                   if k in ("from", "to", "starts", "episodes", "best", "recommended")}
    out["cost"] = float(c["fee"] + c["slippage"])
    out["last_week"] = t.index[np.isfinite(t["exec_monday"].to_numpy(dtype=float))][-1].strftime("%Y-%m-%d")
    acc = DATA / "results" / "acceptance.json"
    out["signals_passed"] = json.loads(acc.read_text(encoding="utf-8")).get("passed") if acc.exists() else None
    return out
