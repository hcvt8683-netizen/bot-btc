"""Trend forecast: up or down, and by how much, over 1–7 days, 1–4 weeks and 1–6 months (config/candidates.yaml, section
trend; registered before any number was computed).

Target: the k-day log return of the Coin Metrics daily close, standardised like the price bands (divided by the 30-day
daily volatility × √k). The base rate (goc) reads P(up) and the 10/50/90% quantiles from every window already known in
the 4 years before the anchor day. Four conditional models (momentum, above / below the 200-day mean, MVRV valuation,
short-term reversal) use only the known windows that were in the same state as today, shrunk toward the base rate; a
fifth averages them. Each is scored walk-forward every day since 2016 against the base rate (Brier for the direction,
pinball loss for the size), with a stationary block bootstrap, Holm over 5 models × 16 horizons and both halves. The page
only says "up" or "down" from a model that beat the base rate that way; otherwise it shows the base rate.
"""
from __future__ import annotations

import bisect
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.models import price_forecast as pf

LOG = DATA / "trend" / "trend_log.csv"
COND = ("dong_luong", "ma200", "dinh_gia", "dao_chieu")
TESTED = COND + ("ket_hop",)
ALL = ("goc",) + TESTED
SHRINK, MIN_SAME, MIN_OBS, VOL_DAYS, MA_DAYS, RANK_MIN = 20, 100, 365, 30, 200, 365
N_BOOT, SEED = 4000, 0
BAND90 = (0.05, 0.95)          # trend_plus.band90: the "9 out of 10" band, same way as the 10–90% band
ML_REFIT, ML_MIN = 30, 730     # trend_plus.ml: refit every 30 days on at least 730 known days
LOG_COLS = ["issued", "k", "target", "price", *[f"p_{m}" for m in ALL], "dir_model", "mag_model", "q10", "q50", "q90", "version", "logged_at"]


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["trend"]


def version(cfg: dict) -> str:
    code = b"".join((ROOT / "bot" / "models" / f).read_bytes().replace(b"\r\n", b"\n") for f in ("trend.py", "price_forecast.py", "candles.py"))
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


# ----- data and states (each known at its own day) -----
def load(end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Daily close and MVRV on the gap-free calendar of the price."""
    from bot.data import pit_store as ps
    p = pf.daily_prices(end)
    cm = ps.load_history("coinmetrics")
    mv = cm.assign(date=pd.to_datetime(cm["date"])).drop_duplicates("date", keep="last").set_index("date")["mvrv"].astype(float)
    return pd.DataFrame({"p": p, "mvrv": mv.reindex(p.index)}, index=p.index)


def _past_rank(x: np.ndarray, window: int | None, min_hist: int) -> np.ndarray:
    """Share of the earlier values (the `window` days before, or all before when None; the day itself excluded) that are
    below x[t]; NaN with fewer than `min_hist` earlier values."""
    out = np.full(len(x), np.nan)
    if window is None:
        seen: list[float] = []
        for t, v in enumerate(x):
            if np.isfinite(v):
                if len(seen) >= min_hist:
                    out[t] = bisect.bisect_left(seen, v) / len(seen)
                bisect.insort(seen, v)
        return out
    for t in range(len(x)):
        if not np.isfinite(x[t]):
            continue
        w = x[max(0, t - window):t]
        w = w[np.isfinite(w)]
        if len(w) >= min_hist:
            out[t] = float((w < x[t]).mean())
    return out


def base_states(d: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """States that do not depend on the horizon: ma200 (0 below or equal, 1 above), dinh_gia and dao_chieu (0 low, 1
    middle, 2 high). NaN while unknown."""
    p = d["p"]
    ma = p.rolling(MA_DAYS, min_periods=MA_DAYS).mean()
    ma200 = np.where(ma.notna() & p.notna(), (p > ma).astype(float), np.nan)
    r_mv = _past_rank(d["mvrv"].to_numpy(dtype=float), None, RANK_MIN)
    dinh_gia = np.where(np.isfinite(r_mv), np.where(r_mv < 1 / 3, 0.0, np.where(r_mv < 2 / 3, 1.0, 2.0)), np.nan)
    sig = np.log(p).diff().rolling(VOL_DAYS, min_periods=VOL_DAYS).std()
    x7 = (np.log(p / p.shift(7)) / (sig * np.sqrt(7))).to_numpy(dtype=float)
    r7 = _past_rank(x7, int(cfg["window_days"]), RANK_MIN)
    dao_chieu = np.where(np.isfinite(r7), np.where(r7 < 0.2, 0.0, np.where(r7 >= 0.8, 2.0, 1.0)), np.nan)
    return pd.DataFrame({"ma200": ma200, "dinh_gia": dinh_gia, "dao_chieu": dao_chieu, "rank_mv": r_mv, "rank7": r7}, index=d.index)


def momentum_state(p: pd.Series, k: int) -> pd.Series:
    """Sign of the return of the last L days (L = k from 7 days up, 7 below): 1 positive, 0 zero or negative."""
    L = k if k >= 7 else 7
    past = p / p.shift(L) - 1
    return pd.Series(np.where(past.notna(), (past > 0).astype(float), np.nan), index=p.index)


# ----- predictions for every anchor day T, from windows known at T only -----
def predict(d: pd.DataFrame, bs: pd.DataFrame, k: int, cfg: dict) -> dict:
    """Per model: P(up) and the 10/50/90% quantiles of z at every T; plus sigma, the outcome r and up (NaN until known)."""
    p = d["p"]
    sig = np.log(p).diff().rolling(VOL_DAYS, min_periods=VOL_DAYS).std()
    r = np.log(p.shift(-k) / p)
    z = r / (sig * np.sqrt(k))
    up = pd.Series(np.where(z.notna(), (z > 0).astype(float), np.nan), index=p.index)
    W = int(cfg["window_days"]) - k
    zk, upk = z.shift(k), up.shift(k)              # at T: the window that started k days earlier, whose end is T
    known = zk.notna()
    qs = [float(q) for q in cfg["quantiles"]] + list(BAND90)
    goc_p = upk.rolling(W, min_periods=MIN_OBS).mean()
    goc_q = {q: zk.rolling(W, min_periods=MIN_OBS).quantile(q) for q in qs}
    out = {"goc": pd.DataFrame({"p": goc_p, **{q: goc_q[q] for q in qs}})}
    states = {"dong_luong": momentum_state(p, k), "ma200": bs["ma200"], "dinh_gia": bs["dinh_gia"], "dao_chieu": bs["dao_chieu"]}
    for m, st in states.items():
        stk = st.shift(k)                          # the state each known window had on its own day
        pm = pd.Series(np.nan, index=p.index)
        qm = {q: pd.Series(np.nan, index=p.index) for q in qs}
        for v in sorted(x for x in st.dropna().unique()):
            same = (stk == v) & known
            n = same.astype(float).rolling(W, min_periods=1).sum()
            ups = (same & (upk == 1)).astype(float).rolling(W, min_periods=1).sum()
            now = (st == v) & goc_p.notna()
            pm = pm.where(~now, (ups + SHRINK * goc_p) / (n + SHRINK))
            for q in qs:
                zq = zk.where(same).rolling(W, min_periods=MIN_SAME).quantile(q)
                qm[q] = qm[q].where(~now, zq.fillna(goc_q[q]))
        out[m] = pd.DataFrame({"p": pm, **qm})
    comb = pd.concat([out[m]["p"] for m in COND], axis=1)
    out["ket_hop"] = pd.DataFrame({"p": comb.mean(axis=1, skipna=False),
                                   **{q: pd.concat([out[m][q] for m in COND], axis=1).mean(axis=1, skipna=False) for q in qs}})
    return {"models": out, "sig": sig, "r": r, "up": up, "states": states}


# ----- learned model (trend_plus.ml): logistic regression refitted every 30 days on days already known -----
def ml_features(d: pd.DataFrame, bs: pd.DataFrame, flags: pd.DataFrame, k: int) -> pd.DataFrame:
    """16 features at T, all known at T: momentum (as dong_luong), distance to the 200-day mean, MVRV rank, 7-day
    stretch rank, 30-day volatility and the 11 candle-pattern flags (bot/models/candles.py)."""
    p = d["p"]
    sig = np.log(p).diff().rolling(VOL_DAYS, min_periods=VOL_DAYS).std()
    L = k if k >= 7 else 7
    X = pd.DataFrame({"mom": np.log(p / p.shift(L)) / (sig * np.sqrt(L)), "ma": p / p.rolling(MA_DAYS, min_periods=MA_DAYS).mean() - 1,
                      "rank_mv": bs["rank_mv"], "rank7": bs["rank7"], "sig": sig}, index=d.index)
    return X.join(flags.reindex(d.index))


def ml_predict(X: pd.DataFrame, up: pd.Series, k: int) -> pd.Series:
    """P(up) at every T from a model fitted at the last refit day j ≤ T on the days i with i + k ≤ j."""
    import warnings
    from sklearn.linear_model import LogisticRegression
    Xv, y = X.to_numpy(dtype=float), up.to_numpy(dtype=float)
    okX, n = np.isfinite(Xv).all(axis=1), len(y)
    out = np.full(n, np.nan)
    lab = np.flatnonzero(okX & np.isfinite(y))
    if len(lab) <= ML_MIN:
        return pd.Series(out, index=X.index)
    j = lab[ML_MIN] + k
    while j < n:
        tr = lab[lab <= j - k]
        if len(tr) >= ML_MIN and len(np.unique(y[tr])) == 2:
            mu, sd = Xv[tr].mean(axis=0), Xv[tr].std(axis=0)
            sd = np.where(sd > 0, sd, 1.0)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                lr = LogisticRegression(C=1.0, max_iter=1000).fit((Xv[tr] - mu) / sd, y[tr])
            rows = np.arange(j, min(n, j + ML_REFIT))
            rows = rows[okX[rows]]
            if len(rows):
                out[rows] = lr.predict_proba((Xv[rows] - mu) / sd)[:, 1]
        j += ML_REFIT
    return pd.Series(out, index=X.index)


def evaluate_ml(pr: dict, pml: pd.Series, k: int, cfg: dict) -> dict:
    """The learned model against the base rate, scored like evaluate (Brier, stationary bootstrap, both halves)."""
    goc, r, up, idx = pr["models"]["goc"]["p"], pr["r"], pr["up"], pr["r"].index
    ok = (idx >= pd.Timestamp(str(cfg["eval_from"]))) & r.notna().to_numpy() & goc.notna().to_numpy() & pml.notna().to_numpy()
    n = int(ok.sum())
    if n < 2 * k + 10:
        return {"n": n}
    y, pg, pm = up.to_numpy()[ok], goc.to_numpy()[ok], pml.to_numpy()[ok]
    bg, bm = (pg - y) ** 2, (pm - y) ** 2
    gain, half = bg - bm, n // 2
    g = gain[measure.stationary_indices(n, k, N_BOOT, np.random.default_rng(SEED))].mean(axis=1)
    return {"n": n, "from": idx[ok][0].strftime("%Y-%m-%d"), "brier": float(bm.mean()), "brier_goc": float(bg.mean()), "hit": float(((pm > 0.5) == (y == 1)).mean()),
            "hit_goc": float(((pg > 0.5) == (y == 1)).mean()), "dir_gain": float(gain.mean()), "dir_ci": [float(np.quantile(g, 0.025)), float(np.quantile(g, 0.975))],
            "dir_p": float(max((g <= 0).mean(), 1 / N_BOOT)), "dir_halves": bool(gain[:half].mean() > 0 and gain[half:].mean() > 0)}


# ----- scoring -----
def pinball(qr: np.ndarray, r: np.ndarray, qs: list[float]) -> np.ndarray:
    d = r[:, None] - qr
    q = np.array(qs)[None, :]
    return np.maximum(q * d, (q - 1) * d).mean(axis=1)


def holm(pvals: dict) -> dict:
    """Holm step-down adjusted p-values for {key: p}."""
    keys = sorted(pvals, key=lambda x: pvals[x])
    m, run, out = len(keys), 0.0, {}
    for i, key in enumerate(keys):
        run = max(run, min(1.0, (m - i) * pvals[key]))
        out[key] = run
    return out


def evaluate(pr: dict, k: int, cfg: dict) -> dict:
    """Walk-forward score of every model at horizon k against the base rate, over the days where all of them are known."""
    qs = [float(q) for q in cfg["quantiles"]]
    mods, sig, r, up = pr["models"], pr["sig"], pr["r"], pr["up"]
    idx = r.index
    ok = (idx >= pd.Timestamp(str(cfg["eval_from"]))) & r.notna().to_numpy() & sig.notna().to_numpy()
    for m in ALL:
        ok &= mods[m][["p", *qs]].notna().all(axis=1).to_numpy()
    n = int(ok.sum())
    if n < 2 * k + 10:
        return {"n": n}
    y, rr, sc = up.to_numpy()[ok], r.to_numpy()[ok], (sig * np.sqrt(k)).to_numpy()[ok]
    half = n // 2
    res = {"n": n, "from": idx[ok][0].strftime("%Y-%m-%d"), "to": idx[ok][-1].strftime("%Y-%m-%d"), "split": idx[ok][half].strftime("%Y-%m-%d"),
           "windows": n // k, "base_up": float(y.mean()), "models": {}}
    br, pb = {}, {}
    for m in ALL:
        pm = mods[m]["p"].to_numpy()[ok]
        qr = np.column_stack([mods[m][q].to_numpy()[ok] for q in qs]) * sc[:, None]
        br[m], pb[m] = (pm - y) ** 2, pinball(qr, rr, qs)
        q90 = np.column_stack([mods[m][q].to_numpy()[ok] for q in BAND90]) * sc[:, None]
        c90 = float(((rr >= q90[:, 0]) & (rr <= q90[:, 1])).mean())
        res["models"][m] = {"brier": float(br[m].mean()), "pinball": float(pb[m].mean()), "hit": float(((pm > 0.5) == (y == 1)).mean()),
                            "cover80": float(((rr >= qr[:, 0]) & (rr <= qr[:, -1])).mean()),
                            "cover90": c90, "cover90_ci": list(wilson(round(c90 * max(1, n // k)), max(1, n // k))),
                            "brier_halves": [float(br[m][:half].mean()), float(br[m][half:].mean())],
                            "pinball_halves": [float(pb[m][:half].mean()), float(pb[m][half:].mean())]}
    boot = measure.stationary_indices(n, k, N_BOOT, np.random.default_rng(SEED))
    for m in TESTED:
        x = res["models"][m]
        for kind, loss in (("dir", br), ("mag", pb)):
            gain = loss["goc"] - loss[m]
            g = gain[boot].mean(axis=1)
            x[f"{kind}_gain"] = float(gain.mean())
            x[f"{kind}_ci"] = [float(np.quantile(g, 0.025)), float(np.quantile(g, 0.975))]
            x[f"{kind}_p"] = float(max((g <= 0).mean(), 1 / N_BOOT))
            x[f"{kind}_halves"] = bool(gain[:half].mean() > 0 and gain[half:].mean() > 0)
    del boot
    return res


def verdicts(ev: dict) -> None:
    """Holm over 5 models × all horizons, separately for direction and size; pick per horizon (in place)."""
    for kind in ("dir", "mag"):
        pv = {(k, m): e["models"][m][f"{kind}_p"] for k, e in ev.items() if e.get("models") for m in TESTED}
        adj = holm(pv)
        for (k, m), a in adj.items():
            x = ev[k]["models"][m]
            x[f"{kind}_holm"] = a
            x[f"{kind}_edge"] = bool(a < 0.05 and x[f"{kind}_halves"] and x[f"{kind}_gain"] > 0)
        for k, e in ev.items():
            if not e.get("models"):
                e[f"{kind}_model"] = "goc"
                continue
            win = [m for m in TESTED if e["models"][m][f"{kind}_edge"]]
            e[f"{kind}_model"] = max(win, key=lambda m: e["models"][m][f"{kind}_gain"]) if win else "goc"


def label(p: float | None, cfg: dict) -> str:
    if p is None or not np.isfinite(p):
        return "khong_ro"
    return "tang" if p >= 0.55 else "giam" if p <= 0.45 else "khong_ro"


STATE_NAMES = {"dong_luong": {0: "giam", 1: "tang"}, "ma200": {0: "duoi", 1: "tren"}, "dinh_gia": {0: "re", 1: "giua", 2: "dat"},
               "dao_chieu": {0: "giam_manh", 1: "binh_thuong", 2: "tang_manh"}}


# ----- everything -----
def bitstamp_frame(end: pd.Timestamp | None = None) -> pd.DataFrame:
    """trend_plus.bitstamp: the same frame with the Bitstamp daily close in place of Coin Metrics (MVRV unchanged)."""
    from bot.models import candles as cd
    b = cd.load(end)
    cm = load(end)
    return pd.DataFrame({"p": b["close"], "mvrv": cm["mvrv"].reindex(b.index)}, index=b.index)


def check_bitstamp(cfg: dict, end: pd.Timestamp | None = None) -> dict:
    """Rerun the registered trend scoring on Bitstamp prices; per horizon the verdict and the band coverage."""
    d = bitstamp_frame(end)
    bs = base_states(d, cfg)
    ev = {k: evaluate(predict(d, bs, k, cfg), k, cfg) for k in [int(x) for x in cfg["horizons_days"]]}
    verdicts(ev)
    out = {}
    for k, e in ev.items():
        if not e.get("models"):
            continue
        best = max(TESTED, key=lambda m: e["models"][m]["dir_gain"])
        out[str(k)] = {"n": e["n"], "dir_model": e["dir_model"], "mag_model": e["mag_model"], "goc_hit": e["models"]["goc"]["hit"],
                       "cover80": e["models"][e["mag_model"]]["cover80"], "cover90": e["models"][e["mag_model"]]["cover90"],
                       "best": best, "best_gain": e["models"][best]["dir_gain"], "best_holm": e["models"][best]["dir_holm"]}
    return out


def pick(models: dict, dm: str, mm: str, qs: list[float]) -> tuple[str, str, str | None, str | None]:
    """The models the page uses at T. A chosen model with no number at T (an input such as MVRV is published a day
    late) gives way to goc that day; the one it replaced is returned as missing so the page can say so."""
    dmiss = dm if dm != "goc" and models[dm]["p"] is None else None
    mmiss = mm if mm != "goc" and any(models[mm][f"q{round(q * 100)}"] is None for q in qs) else None
    return ("goc" if dmiss else dm), ("goc" if mmiss else mm), dmiss, mmiss


def run(write: bool = True, end: pd.Timestamp | None = None) -> dict:
    """Everything the page shows (window TR); `end` cuts the data (frozen fixtures for the page tests)."""
    from bot.models import candles as cd
    cfg = spec()
    d = load(end)
    bs = base_states(d, cfg)
    qs = [float(q) for q in cfg["quantiles"]] + list(BAND90)
    T = d["p"].dropna().index[-1]
    cdf = cd.load(end)
    flags = cd.ml_flags(cd.detect(cdf)).where(cdf["close"].notna())    # a missing Bitstamp candle → no flags that day
    ev, now_rows, preds, ml, pml = {}, [], {}, {}, {}
    for k in [int(x) for x in cfg["horizons_days"]]:
        pr = predict(d, bs, k, cfg)
        preds[k] = pr
        ev[k] = evaluate(pr, k, cfg)
        pml[k] = ml_predict(ml_features(d, bs, flags, k), pr["up"], k)
        ml[k] = evaluate_ml(pr, pml[k], k, cfg)
    verdicts(ev)
    adj = holm({k: x["dir_p"] for k, x in ml.items() if "dir_p" in x})       # Holm of its own over the 16 horizons
    for k, x in ml.items():
        if k in adj:
            x["dir_holm"] = adj[k]
            x["dir_edge"] = bool(adj[k] < 0.05 and x["dir_halves"] and x["dir_gain"] > 0)
            e = ev[k]
            cur = e["models"][e["dir_model"]]["dir_gain"] if e.get("models") and e["dir_model"] != "goc" else 0.0
            if x["dir_edge"] and x["dir_gain"] > cur:
                e["dir_model"] = "hoc_may"
    for k, pr in preds.items():
        sk = float(pr["sig"].loc[T] * np.sqrt(k))
        row = {"k": k, "target": (T + pd.Timedelta(days=k)).strftime("%Y-%m-%d"), "models": {}}
        for m in ALL:
            x = pr["models"][m].loc[T]
            row["models"][m] = {"p": None if pd.isna(x["p"]) else float(x["p"]),
                                **{f"q{round(q * 100)}": None if pd.isna(x[q]) else float(np.exp(x[q] * sk) - 1) for q in qs}}
        pm = pml[k].loc[T] if T in pml[k].index else np.nan
        row["models"]["hoc_may"] = {**row["models"]["goc"], "p": None if pd.isna(pm) else float(pm)}
        e = ev[k]
        dm, mm = e.get("dir_model", "goc"), e.get("mag_model", "goc")
        dm, mm, dmiss, mmiss = pick(row["models"], dm, mm, qs)
        pdir = row["models"][dm]["p"]
        ups = sum(1 for m in TESTED if (row["models"][m]["p"] or 0.5) > 0.5)
        downs = sum(1 for m in TESTED if row["models"][m]["p"] is not None and row["models"][m]["p"] < 0.5)
        row.update(dir_model=dm, mag_model=mm, label=label(pdir, cfg), p=pdir, **{f"q{round(q * 100)}": row["models"][mm][f"q{round(q * 100)}"] for q in qs},
                   agree_up=ups, agree_down=downs, dir_missing=dmiss, mag_missing=mmiss)
        now_rows.append(row)
    states_now = {m: STATE_NAMES[m].get(int(v)) if pd.notna(v := (momentum_state(d["p"], 7).loc[T] if m == "dong_luong" else bs[m].loc[T])) else None
                  for m in COND}
    cs = cd.run(write=False, end=end)
    out = {"version": version(cfg), "anchor": T.strftime("%Y-%m-%d"), "close": float(d["p"].loc[T]), "sigma": float(preds[1]["sig"].loc[T]),
           "states": states_now, "now": now_rows,
           "eval": {str(k): e for k, e in ev.items()}, "tests": len(TESTED) * len(ev), "cross": cross_check(d["p"], T),
           "ml": {str(k): x for k, x in ml.items()}, "bitstamp": check_bitstamp(cfg, end),
           "candles": {k: cs[k] for k in ("anchor", "today", "patterns", "tests", "from", "edges")}}
    out["log"] = score_log(d["p"])
    if write:
        (DATA / "results").mkdir(exist_ok=True)
        (DATA / "results" / "trend.json").write_text(json.dumps(_round(out), ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    return out


def cross_check(p: pd.Series, T: pd.Timestamp) -> dict:
    """What the other tabs say at the same time: price bands (1–7, 30 days), calibrated probability of profit (4, 13, 26
    weeks) and the Long/Short checklist, read from their own result files."""
    out: dict = {}
    try:
        f = pf.forecast(p.loc[:T], pf.spec())
        out["forecast"] = {"anchor": f["anchor"], "rows": [{"k": r["k"], "q10": r["q10"] / f["price"] - 1, "q50": r["q50"] / f["price"] - 1,
                                                             "q90": r["q90"] / f["price"] - 1} for r in f["rows"]]}
    except Exception:  # noqa: BLE001
        out["forecast"] = None
    path = DATA / "results" / "calib.json"
    if path.exists():
        c = json.loads(path.read_text(encoding="utf-8"))
        out["calib"] = [{"weeks": int(h), "p": c[h]["now"]["p"], "method": c[h]["now"]["method"], "date": c[h]["now"]["date"]}
                        for h in ("4", "13", "26") if h in c and c[h].get("now")]
    path = DATA / "results" / "perp_trade.json"
    if path.exists():
        lt = json.loads(path.read_text(encoding="utf-8"))
        sides = {}
        for sd in ("long", "short"):
            s = lt.get("sides", {}).get(sd)
            if not s:
                continue
            cur = s["current"].get("rule") or s["current"].get("best") or {}
            on = lt.get("now", {}).get("signals", {}).get(f"{cur.get('sig')}|{sd}")
            sides[sd] = sum(bool(v) for v in s["check"].values()) + (1 if on else 0) + 1   # c6 holds at 1x
        out["long_short"] = {"anchor": lt.get("data", {}).get("to"), "score": sides, "edge": bool(lt.get("wf", {}).get("edge"))}
    return out


def _round(x, nd: int = 5):
    if isinstance(x, float):
        return None if not np.isfinite(x) else round(x, nd)
    if isinstance(x, dict):
        return {str(k): _round(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, nd) for v in x]
    if isinstance(x, (np.floating, np.integer)):
        return _round(float(x), nd)
    return x


# ----- forward log -----
def read_log(path: Path = LOG) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def log_today(res: dict, now: pd.Timestamp, path: Path = LOG) -> list[dict]:
    """Append once per anchor day and version, every horizon whose target day is still ahead. Never back-fills."""
    path = Path(path)
    v, T = res["version"], res["anchor"]
    if any(r["issued"] == T and r["version"] == v for r in read_log(path)):
        return []
    rows = []
    for row in res["now"]:
        if pd.Timestamp(row["target"]) <= now.normalize():
            continue
        f = lambda x: "" if x is None else f"{x:.5f}"  # noqa: E731
        rows.append({"issued": T, "k": row["k"], "target": row["target"], "price": f"{res['close']:.2f}",
                     **{f"p_{m}": f(row["models"][m]["p"]) for m in ALL}, "dir_model": row["dir_model"], "mag_model": row["mag_model"],
                     "q10": f(row["q10"]), "q50": f(row["q50"]), "q90": f(row["q90"]), "version": v, "logged_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")})
    if not rows:
        return []
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_COLS)
        if new:
            w.writeheader()
        w.writerows(rows)
    return rows


def score_log(p: pd.Series, path: Path = LOG) -> dict:
    """Logged forecasts whose target day has a close: direction right or wrong per model, inside the 80% band."""
    done = []
    for r in read_log(path):
        t1 = pd.Timestamp(r["target"])
        if t1 not in p.index or pd.isna(p.loc[t1]):
            continue
        ret = float(p.loc[t1]) / float(r["price"]) - 1
        done.append({"k": int(r["k"]), "up": ret > 0, "ret": ret, **{m: r[f"p_{m}"] for m in ALL}, "q10": r["q10"], "q90": r["q90"]})
    out = {"rows": len(read_log(path)), "matured": len(done), "hit": {}}
    if done:
        for m in ALL:
            x = [d for d in done if d[m] != ""]
            out["hit"][m] = float(np.mean([(float(d[m]) > 0.5) == d["up"] for d in x])) if x else None
        b = [d for d in done if d["q10"] != ""]
        out["cover80"] = float(np.mean([float(d["q10"]) <= d["ret"] <= float(d["q90"]) for d in b])) if b else None
    return out


def utc_now() -> pd.Timestamp:
    return pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
