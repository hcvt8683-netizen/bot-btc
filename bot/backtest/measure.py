"""Uniform measurement (rebuild, part B). Every table uses the same rules:

- episodes: consecutive weeks in the same zone; weeks at most `gap` weeks apart are merged (default 4);
- confidence intervals: stationary block bootstrap (Politis & Romano) on the weekly observations, mean block length =
  horizon in weeks, 2,000 resamples, on the DIFFERENCE between the zone and the baseline of the same weeks; plus a
  Wilson interval over episodes (one observation per episode: its first week) for comparison;
- an interval of the difference that contains 0 → "no edge yet" (no action label);
- probabilities: Brier score against the training base rate; if not better (bootstrap), show only the rank.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.backtest.metrics import wilson

NO_EDGE = "chua_co_loi_the"
FEW_EPISODES = "it_dot"
MIN_EPISODES = 3  # fewer independent episodes than this → no conclusion, whatever the bootstrap says (see docs/REBUILD_LOG.md)


def stationary_indices(n: int, mean_block: float, runs: int, rng: np.random.Generator) -> np.ndarray:
    """(runs, n) indices: blocks start at random places, each step continues the block with probability 1 − 1/L (circular)."""
    p = 1.0 / max(1.0, mean_block)
    idx = np.empty((runs, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, runs)
    new = rng.random((runs, n)) < p
    jump = rng.integers(0, n, (runs, n))
    for t in range(1, n):
        idx[:, t] = np.where(new[:, t], jump[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def episodes(mask: np.ndarray, gap: int = 4) -> list[tuple[int, int]]:
    """(first, last) week index of each episode; flagged weeks at most `gap` weeks apart belong to one episode."""
    out: list[list[int]] = []
    for j in np.where(np.asarray(mask, dtype=bool))[0]:
        if out and j - out[-1][1] <= gap:
            out[-1][1] = j
        else:
            out.append([j, j])
    return [(a, b) for a, b in out]


def forward(price: np.ndarray, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Return over h weeks and the worst drawdown inside the holding period (weekly prices), NaN where unknown."""
    n = len(price)
    ret, dd = np.full(n, np.nan), np.full(n, np.nan)
    for t in range(n - h):
        path = price[t:t + h + 1]
        if np.isfinite(path).all():
            ret[t] = path[-1] / path[0] - 1
            dd[t] = (path / path[0]).min() - 1
    return ret, dd


def zone_table(zones: pd.Series, price: np.ndarray, horizons: list[int], order: list[str], n_boot: int = 2000, seed: int = 0,
               gap: int = 4) -> dict:
    """Win rate (price higher after h weeks) per zone vs the baseline of the same weeks, for every horizon.

    zones: label per week (index = week dates), price: entry/exit price per week (aligned), only weeks whose label is
    known are used for each horizon. Returns {"baseline": {...}, zone: {...}} with weeks, episodes, win, diff, CI."""
    rng = np.random.default_rng(seed)
    lab = zones.to_numpy(dtype=object)
    out: dict = {"horizons": horizons, "zones": {}}
    base_rows = {}
    for h in horizons:
        r, dd = forward(price, h)
        ok = np.isfinite(r) & pd.notna(lab)
        y = (r > 0).astype(float)
        base = {"weeks": int(ok.sum()), "win": float(y[ok].mean()) if ok.any() else None,
                "median": float(np.median(r[ok])) if ok.any() else None, "q1": float(np.quantile(r[ok], 0.25)) if ok.any() else None,
                "q3": float(np.quantile(r[ok], 0.75)) if ok.any() else None, "mdd_median": float(np.median(dd[ok])) if ok.any() else None}
        base_rows[h] = base
        pos = np.where(ok)[0]
        idx = stationary_indices(len(pos), h, n_boot, rng) if len(pos) else None
        for z in order:
            m = ok & (lab == z)
            row = out["zones"].setdefault(z, {})
            if not m.any():
                row[h] = {"weeks": 0, "episodes": 0}
                continue
            eps = episodes(m, gap)
            first = [a for a, _ in eps]
            k_ep = int(sum(y[a] for a in first))
            lo_e, hi_e = wilson(k_ep, len(first))
            win = float(y[m].mean())
            # bootstrap of (zone win − baseline win) on the same resampled weeks
            mz = (lab[pos] == z)
            yy = y[pos]
            diffs = []
            for b in range(n_boot):
                s = idx[b]
                zz = mz[s]
                if zz.any():
                    diffs.append(yy[s][zz].mean() - yy[s].mean())
            diffs = np.array(diffs)
            lo, hi = (float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))) if len(diffs) > 50 else (None, None)
            row[h] = {"weeks": int(m.sum()), "episodes": len(eps), "win": win, "diff": win - base["win"], "ci": [lo, hi],
                      "boot_used": int(len(diffs)), "wilson_episodes": [lo_e, hi_e], "episode_win": k_ep / len(first),
                      "median": float(np.median(r[m])), "q1": float(np.quantile(r[m], 0.25)), "q3": float(np.quantile(r[m], 0.75)),
                      "mdd_median": float(np.median(dd[m])),
                      "verdict": verdict(lo, hi, len(eps))}
    out["baseline"] = base_rows
    out["monotone"] = monotone(out, order)
    return out


def verdict(lo: float | None, hi: float | None, n_episodes: int) -> str:
    """'it_dot' under MIN_EPISODES episodes; otherwise 'chua_co_loi_the' when the interval of the difference contains 0."""
    if n_episodes < MIN_EPISODES:
        return FEW_EPISODES
    if lo is None or lo <= 0 <= hi:
        return NO_EDGE
    return "hon_moc" if lo > 0 else "kem_moc"


def monotone(tab: dict, order: list[str]) -> dict:
    """Zones must be ordered (e.g. Phải mua ≥ Cân nhắc mua ≥ baseline ≥ Không nên mua) at every horizon."""
    res = {}
    for h in tab["horizons"]:
        seq = []
        for z in order:
            if z == "__baseline__":
                seq.append(tab["baseline"][h]["win"])
            else:
                c = tab["zones"].get(z, {}).get(h, {})
                seq.append(c.get("win"))
        vals = [v for v in seq if v is not None]
        res[h] = all(a >= b for a, b in zip(vals, vals[1:]))
    return res


def calibration(p: np.ndarray, p0: np.ndarray, y: np.ndarray, h: int, n_boot: int = 2000, seed: int = 0) -> dict:
    """Brier score of model probabilities p vs the training base rate p0, with a stationary-bootstrap interval of
    (Brier_base − Brier_model) and a reliability table by deciles of p. show_probability only if the interval is > 0."""
    ok = np.isfinite(p) & np.isfinite(p0) & np.isfinite(y)
    p, p0, y = p[ok], p0[ok], y[ok]
    e, e0 = (p - y) ** 2, (p0 - y) ** 2
    rng = np.random.default_rng(seed)
    idx = stationary_indices(len(y), h, n_boot, rng)
    gain = (e0[idx] - e[idx]).mean(axis=1)
    lo, hi = float(np.quantile(gain, 0.025)), float(np.quantile(gain, 0.975))
    bins = []
    edges = np.quantile(p, np.linspace(0, 1, 11))
    k = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, 9)
    for b in range(10):
        m = k == b
        if m.any():
            bins.append({"decile": b + 1, "pred": float(p[m].mean()), "actual": float(y[m].mean()), "weeks": int(m.sum())})
    brier, brier0 = float(e.mean()), float(e0.mean())
    return {"weeks": int(len(y)), "brier": brier, "brier_base": brier0, "skill": 1 - brier / brier0 if brier0 else None,
            "gain_ci": [lo, hi], "show_probability": lo > 0, "reliability": bins}


def cost_basis_with_cash(equity_ratio: float) -> float:
    """Cost-basis advantage counting leftover cash at the final price: total contributed / (BTC + cash / P_T), against
    DCA. With equal contributions this equals equity ratio − 1."""
    return equity_ratio - 1.0
