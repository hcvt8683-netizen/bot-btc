"""Support / resistance by the frame the user picks, and whether a touch bounces or breaks (config/candidates.yaml,
section sr_levels; registered before any number was computed).

For a frame of W candles (1–24 hours and 1–7 days on hourly candles of the BTCUSDT perpetual, 1–8 weeks and 1–12 months
on Bitstamp daily candles), resistance R(t) is the highest high of the W candles up to t and support S(t) the lowest low.
A touch at the next candle u comes from beyond the zone w = 0.25 ATR; within H candles it bounces (price goes 1 ATR back)
or breaks (a close 0.5 ATR beyond the level; a candle doing both counts as a break). Touches whose outcome windows
overlap form one episode. The same is measured at a placebo level at the same relative distance taken from an older,
non-overlapping window, so the page can say whether a real level holds better than any level. Holm over 102 tests.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from scipy.stats import norm

from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.models import perp_signal as ps
from bot.models import price_action as pa

ATR_N = 14
SIDES = ("R", "S")      # resistance, support
H_LIMITS = {"1h": (6, 168), "1d": (3, 60)}
FROM = {"1h": pd.Timestamp("2020-07-01"), "1d": pd.Timestamp("2016-01-01")}
REACH_EDGES = (0.0, 0.5, 1.0, 2.0, 4.0, np.inf)
BOUNCE, BREAK, OPEN = 1, 0, -1          # outcome codes; NaN = not known yet


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["sr_levels"]


def version(cfg: dict) -> str:
    code = b"".join((ROOT / "bot" / "models" / f).read_bytes().replace(b"\r\n", b"\n") for f in ("sr_levels.py", "perp_signal.py", "price_action.py"))
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def frames(cfg: dict) -> list[dict]:
    """Every frame in registered order: unit, n, candle type, window W and outcome horizon H (in candles)."""
    out = []
    for unit, f in cfg["frames"].items():
        lo, hi = H_LIMITS[f["candles"]]
        for n in f["n"]:
            W = int(n) * int(f["per_unit"])
            out.append({"unit": unit, "n": int(n), "candles": f["candles"], "W": W, "H": int(min(hi, max(lo, W)))})
    return out


def candles(kind: str, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """High, low, close on a gap-free grid: hourly perpetual candles (index = close time) or Bitstamp daily candles."""
    d = ps.hourly({"start": "2020-01-01"}, end) if kind == "1h" else pa.daily(end)
    return d[["high", "low", "close"]].astype(float)


# ----- levels, only data up to t -----
def levels(d: pd.DataFrame, W: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """R(t), S(t) of the W candles t−W+1..t and ATR(t)."""
    return (d["high"].rolling(W, min_periods=W).max(), d["low"].rolling(W, min_periods=W).min(), pa.atr(d, ATR_N))


def placebo(d: pd.DataFrame, L: pd.Series, delta: int) -> pd.Series:
    """The level of an older window (delta candles back) moved to today's price: same relative distance, not a real level."""
    c = d["close"]
    return c * L.shift(delta) / c.shift(delta)


# ----- touches and what came after -----
def touches(d: pd.DataFrame, L: np.ndarray, A: np.ndarray, side: str, cfg: dict) -> np.ndarray:
    """Positions u of the touches: the zone of the level set at t = u − 1 is reached at u, coming from beyond it."""
    hi, lo, c = (d[k].to_numpy(dtype=float) for k in ("high", "low", "close"))
    w = cfg["zone_atr"] * A
    Lp, wp, cp = L[:-1], w[:-1], c[:-1]
    with np.errstate(invalid="ignore"):
        hit = (hi[1:] >= Lp - wp) & (cp < Lp - wp) if side == "R" else (lo[1:] <= Lp + wp) & (cp > Lp + wp)
    return np.flatnonzero(hit & np.isfinite(Lp) & np.isfinite(wp)) + 1


def outcomes(d: pd.DataFrame, u: np.ndarray, L: np.ndarray, A: np.ndarray, side: str, H: int, cfg: dict) -> np.ndarray:
    """BOUNCE / BREAK / OPEN (nothing within H candles) for each touch at u, NaN while not known yet."""
    lo, hi, c = (d[k].to_numpy(dtype=float) for k in ("low", "high", "close"))
    N = len(c)
    if not len(u):
        return np.zeros(0)
    t = u - 1
    lvl, a = L[t], A[t]
    off = np.arange(H + 1)
    pos = u[:, None] + off[None, :]
    inside = pos < N
    pc = np.where(inside, pos, 0)
    g = 1.0 if side == "R" else -1.0
    with np.errstate(invalid="ignore"):
        brk = inside & (g * (c[pc] - lvl[:, None]) >= cfg["break_atr"] * a[:, None])
        far = (lo if side == "R" else hi)[pc]
        bnc = inside & (off[None, :] >= 1) & (g * (lvl[:, None] - far) >= cfg["bounce_atr"] * a[:, None])
    first = lambda m: np.where(m.any(axis=1), m.argmax(axis=1), H + 1)  # noqa: E731
    fb, fk = first(brk), first(bnc)
    out = np.where(fb <= fk, np.where(fb <= H, BREAK, np.nan), BOUNCE).astype(float)
    complete = (u + H) < N
    out = np.where(np.isnan(out), np.where(complete, OPEN, np.nan), out)
    return out


def episode_starts(u: np.ndarray, H: int) -> np.ndarray:
    """Index (into u) of the first touch of each episode: a later touch within H candles of that first one joins it."""
    keep, last = [], -10 ** 12
    for i, x in enumerate(u.tolist()):
        if x > last + H:
            keep.append(i)
            last = x
    return np.asarray(keep, dtype=int)


def events(d: pd.DataFrame, L: pd.Series, A: pd.Series, side: str, H: int, cfg: dict, start: pd.Timestamp) -> pd.DataFrame:
    """One row per episode (first touch) with a known outcome, touch time from `start` on."""
    Lv, Av = L.to_numpy(dtype=float), A.to_numpy(dtype=float)
    u = touches(d, Lv, Av, side, cfg)
    u = u[d.index[u] >= start] if len(u) else u
    e = episode_starts(u, H)
    u = u[e]
    o = outcomes(d, u, Lv, Av, side, H, cfg)
    ok = ~np.isnan(o)
    return pd.DataFrame({"t": d.index[u[ok]], "out": o[ok].astype(int)})


# ----- statistics -----
def rate(ev: pd.DataFrame) -> dict:
    b, k, o = int((ev["out"] == BOUNCE).sum()), int((ev["out"] == BREAK).sum()), int((ev["out"] == OPEN).sum())
    n = b + k
    return {"episodes": len(ev), "bounce": b, "break": k, "open": o, "n": n, "p": b / n if n else None, "ci": list(wilson(b, n))}


def two_prop(a: dict, b: dict) -> float | None:
    """Two-sided p of the pooled two-proportion z test (bounce share among decided episodes)."""
    if not a["n"] or not b["n"]:
        return None
    p = (a["bounce"] + b["bounce"]) / (a["n"] + b["n"])
    se = np.sqrt(p * (1 - p) * (1 / a["n"] + 1 / b["n"]))
    if se == 0:
        return 1.0
    return float(2 * norm.sf(abs(a["p"] - b["p"]) / se))


def compare(real: pd.DataFrame, fake: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    mid = start + (end - start) / 2
    r, f = rate(real), rate(fake)
    halves = []
    for m in (lambda x: x["t"] < mid, lambda x: x["t"] >= mid):
        rh, fh = rate(real[m(real)]), rate(fake[m(fake)])
        halves.append({"real": rh, "fake": fh, "diff": (rh["p"] - fh["p"]) if rh["n"] and fh["n"] else None})
    return {"real": r, "fake": f, "diff": (r["p"] - f["p"]) if r["n"] and f["n"] else None, "p": two_prop(r, f),
            "halves": halves, "split": mid.strftime("%Y-%m-%d")}


def verdict(c: dict) -> str:
    h = c["halves"]
    if c["real"]["n"] < 30 or any(x["real"]["n"] < 5 for x in h):
        return "it_du_lieu"
    if c.get("p_holm") is not None and c["p_holm"] < 0.05 and all(x["diff"] is not None for x in h):
        if c["diff"] > 0 and all(x["diff"] > 0 for x in h):
            return "manh_hon"
        if c["diff"] < 0 and all(x["diff"] < 0 for x in h):
            return "yeu_hon"
    return "nhu_bat_ky"


def reach(d: pd.DataFrame, L: pd.Series, A: pd.Series, side: str, H: int, cfg: dict, start: pd.Timestamp) -> list[dict]:
    """Chance that the zone is reached within the next H candles, by today's distance to the level in ATR (5 groups)."""
    c = d["close"]
    w = cfg["zone_atr"] * A
    if side == "R":
        dist = (L - c) / A
        fwd = d["high"][::-1].rolling(H, min_periods=H).max()[::-1].shift(-1)
        hit = fwd >= L - w
    else:
        dist = (c - L) / A
        fwd = d["low"][::-1].rolling(H, min_periods=H).min()[::-1].shift(-1)
        hit = fwd <= L + w
    m = (d.index >= start) & dist.notna().to_numpy() & fwd.notna().to_numpy()
    dd, hh = dist[m].to_numpy(), hit[m].to_numpy()
    out = []
    for a, b in zip(REACH_EDGES[:-1], REACH_EDGES[1:]):
        g = (dd >= a) & (dd < b)
        n, k = int(g.sum()), int(hh[g].sum())
        eff = max(1, round(n / H)) if n else 0
        out.append({"from": a, "to": None if not np.isfinite(b) else b, "n": n, "p": k / n if n else None,
                    "ci": list(wilson(round(k / n * eff), eff)) if n else [None, None]})
    return out


def holm(rows: list[dict]) -> None:
    """Holm step-down on rows[i]['p'] (None skipped), written to rows[i]['p_holm']."""
    idx = [i for i, r in enumerate(rows) if r["p"] is not None]
    run, M = 0.0, len(idx)
    for k, i in enumerate(sorted(idx, key=lambda j: rows[j]["p"])):
        run = max(run, min(1.0, (M - k) * rows[i]["p"]))
        rows[i]["p_holm"] = run
    for i, r in enumerate(rows):
        r.setdefault("p_holm", None)


# ----- everything -----
def now_levels(d: pd.DataFrame, fr: dict, cfg: dict) -> dict:
    R, S, A = levels(d, fr["W"])
    T = d["close"].dropna().index[-1]
    val = lambda s: None if pd.isna(s.loc[T]) else float(s.loc[T])  # noqa: E731
    return {"R": val(R), "S": val(S), "atr": val(A)}


def run(write: bool = True, end: pd.Timestamp | None = None) -> dict:
    cfg = spec()
    data = {k: candles(k, end) for k in ("1h", "1d")}
    rows = []
    for fr in frames(cfg):
        d = data[fr["candles"]]
        R, S, A = levels(d, fr["W"])
        delta = 2 * fr["W"] + fr["H"]
        start, last = FROM[fr["candles"]], d.index[-1]
        for side, L in (("R", R), ("S", S)):
            real = events(d, L, A, side, fr["H"], cfg, start)
            fake = events(d, placebo(d, L, delta), A, side, fr["H"], cfg, start)
            c = compare(real, fake, start, last)
            rows.append({**fr, "side": side, **c, "reach": reach(d, L, A, side, fr["H"], cfg, start)})
    holm(rows)
    for r in rows:
        r["verdict"] = verdict(r)
    now = {}
    for k, d in data.items():
        T = d["close"].dropna().index[-1]
        now[k] = {"anchor": T.strftime("%Y-%m-%d %H:%M"), "close": float(d["close"].loc[T]),
                  "levels": {f"{fr['unit']}|{fr['n']}": now_levels(d, fr, cfg) for fr in frames(cfg) if fr["candles"] == k}}
    out = {"version": version(cfg), "params": {k: cfg[k] for k in ("zone_atr", "bounce_atr", "break_atr")}, "atr_n": ATR_N,
           "tests": len(rows), "from": {k: v.strftime("%Y-%m-%d") for k, v in FROM.items()},
           "to": {k: d.index[-1].strftime("%Y-%m-%d %H:%M") for k, d in data.items()}, "frames": rows, "now": now,
           "summary": {v: sum(r["verdict"] == v for r in rows) for v in ("manh_hon", "yeu_hon", "nhu_bat_ky", "it_du_lieu")}}
    if write:
        (DATA / "results").mkdir(exist_ok=True)
        (DATA / "results" / "sr.json").write_text(json.dumps(ps._round(out, 5), ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    return out
