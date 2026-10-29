"""Part D: buy zones with hysteresis and the multiplier rule (settings in config/candidates.yaml, sections zones and
multiplier).

- "Tỷ lệ nên mua" is the RANK (0–100) of this week's score among earlier out-of-sample scores, not a probability.
- Hysteresis: a zone is entered when the rank crosses its threshold and left only when the rank falls more than
  `band` points below it (weekly closes only), so the label does not flip back and forth around a threshold.
- Multiplier in [0.5, 1.5]: the deviation from 1.0 is proportional to the confidence BOUND of the zone's edge (lower
  bound for buy zones, upper bound for "Không nên mua"), estimated walk-forward from weeks whose outcome is already
  known; a bound that touches 0, or fewer than `min_episodes` episodes, gives 1.0.
- Gate: anything other than 1.0 is used only when every Part I acceptance criterion passes.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.config import DATA

ORDER = ["phai", "cannhac", "khong"]


def plain_zones(rank: pd.Series, th: dict) -> pd.Series:
    r = rank.to_numpy(dtype=float)
    z = np.where(np.isnan(r), None, np.where(r >= th["phai"], "phai", np.where(r >= th["cannhac"], "cannhac", "khong")))
    return pd.Series(z, index=rank.index, dtype=object)


def step(cur: str | None, r: float, th: dict, band: float) -> str | None:
    """One week of hysteresis: up-moves happen at the threshold, down-moves only below threshold − band."""
    if np.isnan(r):
        return None
    if cur is None or cur == "khong":
        return "phai" if r >= th["phai"] else "cannhac" if r >= th["cannhac"] else "khong"
    if cur == "cannhac":
        return "phai" if r >= th["phai"] else "khong" if r < th["cannhac"] - band else "cannhac"
    if r < th["phai"] - band:  # phai
        return "cannhac" if r >= th["cannhac"] - band else "khong"
    return "phai"


def hysteresis_zones(rank: pd.Series, th: dict, band: float) -> pd.Series:
    """rank in 0–100. Up-moves happen at the threshold, down-moves only below threshold − band."""
    out, cur = [], None
    for r in rank.to_numpy(dtype=float):
        cur = step(cur, r, th, band)
        out.append(cur)
    return pd.Series(out, index=rank.index, dtype=object)


def flips(z: pd.Series) -> int:
    v = [x for x in z if x is not None]
    return int(sum(a != b for a, b in zip(v, v[1:])))


def zone_multiplier(zone: str | None, edge: dict | None, scale: float, bounds: tuple[float, float], min_eps: int) -> float:
    """1 + scale × (lower bound) for buy zones, 1 + scale × (upper bound) for Không nên mua; 1.0 when the interval
    contains 0, the zone has too few episodes, or there is no estimate."""
    if zone is None or not edge or edge.get("episodes", 0) < min_eps or edge.get("ci") is None or edge["ci"][0] is None:
        return 1.0
    lo, hi = edge["ci"]
    if zone in ("phai", "cannhac"):
        m = 1 + scale * lo if lo > 0 else 1.0
    else:
        m = 1 + scale * hi if hi < 0 else 1.0
    return float(np.clip(m, bounds[0], bounds[1]))


def edges(z: pd.Series, known_price: np.ndarray, h: int, n_boot: int, seed: int, gap: int = 4) -> dict:
    """Edge of every zone (weeks, episodes, difference vs baseline, 95% interval) from the weeks whose outcome is known."""
    tab = measure.zone_table(z, known_price, [h], ORDER, n_boot=n_boot, seed=seed, gap=gap)
    e = {zn: tab["zones"].get(zn, {}).get(h) for zn in ORDER}
    return {zn: (None if not v or not v.get("weeks") else {"weeks": v["weeks"], "episodes": v["episodes"], "diff": v["diff"], "ci": v["ci"]})
            for zn, v in e.items()}


def walk_multipliers(z: pd.Series, price: np.ndarray, h: int, refit: int, scale: float, bounds: tuple[float, float],
                     min_eps: int, n_boot: int, seed: int, gap: int = 4) -> tuple[np.ndarray, list[dict]]:
    """Multiplier per week. Every `refit` weeks the zone edges are re-estimated with the uniform zone table on the weeks
    whose h-week outcome is already known (price data up to the week before the refit only)."""
    n = len(z)
    m = np.ones(n)
    history = []
    zones = z.to_numpy(dtype=object)
    first = next((k for k, v in enumerate(zones) if v is not None), None)
    if first is None:
        return m, history
    for T in range(first + h + 52, n, refit):
        # execution prices up to the Monday after Sunday T−1: labels end before week T
        rec = {"refit": T, "edges": edges(pd.Series(zones[:T], dtype=object), price[:T].copy(), h, n_boot, seed, gap)}
        history.append(rec)
        for i in range(T, min(T + refit, n)):
            m[i] = zone_multiplier(zones[i], rec["edges"].get(zones[i]) if zones[i] else None, scale, bounds, min_eps)
    return m, history


def gate(m: float, acceptance_path=None) -> tuple[float, str]:
    """Part I gate: return (multiplier to use, reason). Without a passed acceptance file the answer is 1.0."""
    p = acceptance_path or (DATA / "results" / "acceptance.json")
    try:
        acc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 1.0, "chua_kiem_dinh"
    if not acc.get("passed"):
        return 1.0, "chua_dat_phan_i"
    return m, "dat_phan_i"
