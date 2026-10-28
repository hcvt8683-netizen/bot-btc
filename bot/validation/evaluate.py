"""One call that applies the whole protocol to a multiplier series and logs the trial in the registry."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.backtest import benchmark, metrics
from bot.config import cfg
from bot.validation import bootstrap, dsr, placebo, registry, splits


def evaluate(name: str, dates: pd.DatetimeIndex, price: np.ndarray, mult: np.ndarray, *, final: bool = False,
             features: list[str] | str = "", params: dict | None = None, stage: str = "dev", heavy: bool = True,
             log: bool = True) -> dict:
    """Splits, cycles, rolling windows; with heavy=True also bootstrap and placebo on the validation split (and the
    holdout in a final run) and the Deflated Sharpe Ratio of weekly active returns over validation."""
    v = cfg()["validation"]
    res = benchmark.evaluate(dates, price, mult, final)
    a, b = splits.split("validation")
    val = (dates >= a) & (dates <= b)
    act = metrics.active_returns(price[val], mult[val])
    res["sr_active"] = metrics.sharpe(act)
    if heavy:
        seed, blk = int(v.get("seed", 0)), v["bootstrap_block_weeks"]
        # one simulation started at the beginning of the period; a whole-history run would be dominated by early, cheap coins
        periods = [("validation", val)]
        if final:
            h0 = splits.holdout_start()
            periods.append(("holdout", dates >= h0))
        for key, sel in periods:
            sfx = "" if key == "validation" else "_holdout"
            res["bootstrap" + sfx] = bootstrap.bootstrap(price[sel], mult[sel], n=v["bootstrap_n"], block=blk, seed=seed)
            res["placebo" + sfx] = placebo.placebo(price[sel], mult[sel], n=v["placebo_n"], block=blk, seed=seed)
        sr = registry.sharpes()
        n = registry.n_trials() + 1
        res["dsr"] = dsr.deflated_sharpe(act, n, float(np.var(sr + [res["sr_active"] or 0.0])) if sr else 0.0)
    if log:
        vs = res["splits"].get("Kiểm định", {})
        registry.log(name, "final" if final else stage, features, params or {},
                     {"er_val": vs.get("equity_ratio"), "roll_med_val": vs.get("roll_er_median"), "roll_p10_val": vs.get("roll_er_p10"),
                      "sr_active": res["sr_active"], "cycles_above_1": sum(1 for c in res["cycles"].values() if c["equity_ratio"] > 1),
                      "placebo_pct": (res.get("placebo") or {}).get("percentile")})
    return res
