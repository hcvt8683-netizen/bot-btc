"""Price action panel of the Long/Short view (config/candidates.yaml, section pa_sheet; registered before any number of
the panel was computed).

No direction signal: the criteria of section price_action had no edge (0/48). The panel shows (1) price action now, by
the registered definitions: criteria on the last closed Bitstamp candle, swing lows / highs known at that candle within
365 days, ATR and the zone half-width for the next candle, structure; (2) for an entry, stop-loss and take-profit, how
often in the past (every day from 2016) the price touched the target before the stop at the same distances in ATR,
against the share needed to break even. `check` is the reference of what src/pa.js computes in the browser.
"""
from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np
import pandas as pd

from bot.config import CONFIG, DATA, load_yaml
from bot.models import price_action as pa

STEP, LEVELS = 0.25, 32               # grid 0.25..8 ATR
SINCE = pd.Timestamp("2016-01-01")
HOLDS = (7, 30)
CHART_DAYS = 120   # nến ngày cho đồ thị của bảng (pa_hold.chart), chỉ hiển thị
OUT = DATA / "results" / "pa.json"


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["pa_sheet"]


def grid() -> np.ndarray:
    return STEP * np.arange(1, LEVELS + 1)


def first_touch(d: pd.DataFrame, H: int, since: pd.Timestamp = SINCE, atr_days: int = 14) -> tuple[np.ndarray, np.ndarray, int]:
    """For every day T from `since` with ATR(T) and the H candles after it all closed and complete: index (0..H−1) of the
    first candle whose high reaches close(T) + u·ATR(T), and whose low reaches close(T) − d·ATR(T), for every grid level
    (H when never). Returns (up (n, 32), down (n, 32), n)."""
    C, Hi, Lo = (d[k].to_numpy() for k in ("close", "high", "low"))
    a = pa.atr(d, atr_days).to_numpy()
    m = len(d)
    ts = [t for t in np.flatnonzero((d.index >= since) & np.isfinite(C) & np.isfinite(a)) if t + H < m]
    ts = np.array([t for t in ts if np.isfinite(Hi[t + 1:t + H + 1]).all() and np.isfinite(Lo[t + 1:t + H + 1]).all()], dtype=int)
    if not len(ts):
        z = np.zeros((0, LEVELS), int)
        return z, z, 0
    win = ts[:, None] + np.arange(1, H + 1)[None, :]
    up_x = np.maximum.accumulate((Hi[win] - C[ts, None]) / a[ts, None], axis=1)      # running best move up, in ATR
    dn_x = np.maximum.accumulate((C[ts, None] - Lo[win]) / a[ts, None], axis=1)      # running best move down, in ATR
    g = grid()

    def first(x: np.ndarray) -> np.ndarray:
        hit = x[:, :, None] >= g[None, None, :]                                     # (n, H, 32)
        return np.where(hit.any(axis=1), hit.argmax(axis=1), H)

    return first(up_x), first(dn_x), len(ts)


def touch(d: pd.DataFrame, H: int, since: pd.Timestamp = SINCE) -> dict:
    """Counts over the grid (row = level up u, column = level down d): up strictly first, down strictly first, both on
    the same candle; N days."""
    tu, td, n = first_touch(d, H, since)
    U, D = tu[:, :, None], td[:, None, :]
    return {"H": H, "N": int(n), "up": (U < D).sum(axis=0).tolist(), "down": (D < U).sum(axis=0).tolist(),
            "same": ((U == D) & (U < H)).sum(axis=0).tolist()}


def state(d: pd.DataFrame, cfg: dict) -> dict:
    """Price action at the last closed candle L, and what is fixed for the next one (registered definitions only)."""
    p = cfg["params"]
    n, look = int(p["swing_n"]), int(p["level_lookback_days"])
    L = int(np.flatnonzero(np.isfinite(d["close"].to_numpy()))[-1])
    f = pa.flags(d, cfg)
    hi, lo = pa.swings(d, n)
    up, down = pa.structure(d, hi, lo, n)
    a = float(pa.atr(d, int(p["atr_days"])).iloc[L])
    lag = pa.known_after(n)
    keep = lambda mask, col: [{"date": d.index[j].strftime("%Y-%m-%d"), "price": float(d[col].iloc[j])}  # noqa: E731
                              for j in np.flatnonzero(mask) if L - look <= j <= L - lag]
    return {"anchor": d.index[L].strftime("%Y-%m-%d"), "close": float(d["close"].iloc[L]), "atr": a, "w": float(p["zone_atr"]) * a,
            "lows": keep(lo, "low"), "highs": keep(hi, "high"), "structure": "up" if up[L] else "down" if down[L] else "none",
            "active": [c for c in f.columns if bool(f[c].iloc[L])]}


def base_rates(d: pd.DataFrame, since: pd.Timestamp = SINCE) -> dict:
    """Share of days from `since` with a higher (lower) close k days later: any day, for each holding time."""
    C = d["close"]
    out = {}
    for k in HOLDS:
        r = (C.shift(-k) / C).to_numpy()
        ok = (d.index >= since) & np.isfinite(r)
        out[str(k)] = {"up": float((r[ok] > 1).mean()), "down": float((r[ok] < 1).mean()), "n": int(ok.sum())}
    return out


def research(path=None) -> dict | None:
    """What the panel shows of the price action test (data/results/price_action.json)."""
    path = path or DATA / "results" / "price_action.json"
    if not path.exists():
        return None
    o = json.loads(path.read_text(encoding="utf-8"))
    keys = ("crit", "k", "dir", "n", "episodes", "hit", "base", "diff", "ci", "p_holm", "verdict")
    return {"from": o["research"]["from"], "to": o["research"]["to"], "n_pairs": o["n_pairs"], "counts": o["counts"],
            "rows": [{k: r[k] for k in keys} for r in o["rows"]]}


def recent(d: pd.DataFrame, n: int = CHART_DAYS) -> list[list]:
    """The last n closed daily candles [date, open, high, low, close] for the panel's chart (display only)."""
    x = d.dropna().iloc[-n:]
    return [[i.strftime("%Y-%m-%d"), *(round(float(v), 2) for v in r)] for i, r in zip(x.index, x[["open", "high", "low", "close"]].to_numpy())]


def run(write: bool = True, d: pd.DataFrame | None = None) -> dict:
    d = pa.daily() if d is None else d
    out = {"made": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "since": SINCE.strftime("%Y-%m-%d"),
           "step": STEP, "levels": LEVELS, "state": state(d, pa.spec()), "base": base_rates(d),
           "touch": {str(H): touch(d, H) for H in HOLDS}, "research": research(), "candles": recent(d)}
    if write:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


def _idx(x: float) -> tuple[int, bool]:
    """0-based grid level nearest to x ATR (half up), clamped; True when x was outside the grid."""
    i = math.floor(x / STEP + 0.5)
    return min(LEVELS, max(1, i)) - 1, not (1 <= i <= LEVELS)


def wilson(p: float, n: float, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    c, m = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / (1 + z * z / n), (c + m) / (1 + z * z / n)


def suggest(o: dict, side: str, E: float) -> dict:
    """Nearest support (highest swing low below E) and resistance (lowest swing high above E), and the suggested stop
    and target of section pa_sheet.stops."""
    st = o["state"]
    lows = [x["price"] for x in st["lows"] if x["price"] < E]
    highs = [x["price"] for x in st["highs"] if x["price"] > E]
    S, R, w, a = (max(lows) if lows else None), (min(highs) if highs else None), st["w"], st["atr"]
    if side == "long":
        SL = S - w if S is not None else E - a
        TP = R - w if R is not None and R - w > E else E + 2 * (E - SL)
    else:
        SL = R + w if R is not None else E + a
        TP = S + w if S is not None and S + w < E else E - 2 * (SL - E)
    return {"S": S, "R": R, "SL": SL, "TP": TP}


def check(o: dict, side: str, E: float, SL: float | None = None, TP: float | None = None, H: int = 30) -> dict:
    """The registered verdict for one entry: touch shares at the same ATR distances, the share needed to break even,
    Wilson over independent windows, expected R."""
    sg = suggest(o, side, E)
    SL = sg["SL"] if SL is None else SL
    TP = sg["TP"] if TP is None else TP
    long = side == "long"
    if not ((SL < E < TP) if long else (TP < E < SL)):
        return {"valid": False, **sg, "SL": SL, "TP": TP}
    a, t = o["state"]["atr"], o["touch"][str(H)]
    risk, reward = abs(E - SL), abs(TP - E)
    (iu, cu), (idn, cd) = _idx((reward if long else risk) / a), _idx((risk if long else reward) / a)
    up, down, same, N = t["up"][iu][idn], t["down"][iu][idn], t["same"][iu][idn], t["N"]
    pt, ps = ((up, down + same) if long else (down, up + same))
    Pt, Ps = pt / N, ps / N
    p = Pt / (Pt + Ps) if Pt + Ps else float("nan")
    n_eff = N * (Pt + Ps) / H
    lo, hi = wilson(p, n_eff)
    q = risk / (risk + reward)
    verdict = "loi" if lo > q else "bat_loi" if hi < q else "ngang"
    return {"valid": True, **sg, "SL": SL, "TP": TP, "risk": risk / E, "reward": reward / E, "risk_atr": risk / a, "reward_atr": reward / a,
            "rr": reward / risk, "q": q, "Pt": Pt, "Ps": Ps, "Pn": max(0.0, 1 - Pt - Ps), "p": p, "ci": [lo, hi], "n_eff": n_eff,
            "exp_r": p * reward / risk - (1 - p), "verdict": verdict, "clamped": bool(cu or cd)}
