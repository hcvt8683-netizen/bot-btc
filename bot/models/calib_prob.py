"""Calibrated probability of profit for 1, 3, 6 and 12 months (settings in config/candidates.yaml, section calib).

"Profit" = Monday close h weeks later above the Monday close of the buying week (the execution rule of the rebuild).
Three pre-registered ways to give that probability for week T, each using only labels known at T (week i counts only
if i + h <= T - 1): the base rate of the 208 weeks before, 5 bins of the out-of-sample rank of the Giá/MA 200 tuần
cheapness shrunk toward the base rate, and an L2 logistic refitted every 13 weeks. A method other than the base rate is
used to pick buying weeks only if its Brier improvement over the base rate has a block-bootstrap 95% interval above 0.
The predicted return (quantiles 10/50/90% of the h-week return) follows the same rule with the pinball loss, base vs
bins. The sell side is the other face of the same measurement: P(price lower after h weeks) = 1 - P(profit).
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from bot.backtest import measure
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.models import wf_logit as wf

FEATS = ["cheap_mvrv", "cheap_p_200wma", "cheap_dev_ma20w"]
WINDOW, SHRINK, REFIT, MIN_TRAIN, BINS, MIN_OBS = 208, 20, 13, 104, 5, 52
QS = (0.1, 0.5, 0.9)
QK = [f"q{int(round(q * 100))}" for q in QS]


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["calib"]


def labels(t: pd.DataFrame, h: int) -> np.ndarray:
    p = t["exec_monday"].to_numpy(dtype=float)
    y = np.full(len(p), np.nan)
    ok = np.isfinite(p[:-h]) & np.isfinite(p[h:])
    y[:-h][ok] = (p[h:][ok] > p[:-h][ok]).astype(float)
    return y


def log_returns(t: pd.DataFrame, h: int) -> np.ndarray:
    p = t["exec_monday"].to_numpy(dtype=float)
    r = np.full(len(p), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        r[:-h] = np.log(p[h:] / p[:-h])
    r[~np.isfinite(r)] = np.nan
    return r


def bins_of(t: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Out-of-sample rank of the Giá/MA 200 tuần cheapness and its bin 0–4 (NaN while the rank is unknown)."""
    rank = wf.oos_rank(t["cheap_p_200wma"]).to_numpy(dtype=float)
    return rank, np.where(np.isfinite(rank), np.minimum(BINS - 1, np.floor(np.nan_to_num(rank) * BINS)), np.nan)


def predictions(t: pd.DataFrame, h: int) -> pd.DataFrame:
    """Probability for every week T from the three methods, each built from labels known at T only."""
    n, y = len(t), labels(t, h)
    rank, b = bins_of(t)
    X = t[FEATS].to_numpy(dtype=float)
    base, bins, logit = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    model, fitted_at = None, -10 ** 9
    for j in range(n):
        last = j - 1 - h  # newest week whose label is known at T = j
        if last < 0:
            continue
        lo = max(0, last - WINDOW + 1)
        w = y[lo:last + 1]
        w = w[np.isfinite(w)]
        if len(w) >= MIN_OBS:
            base[j] = w.mean()
        if np.isfinite(base[j]) and np.isfinite(b[j]):
            m = np.isfinite(y[:last + 1]) & (b[:last + 1] == b[j])
            bins[j] = (y[:last + 1][m].sum() + SHRINK * base[j]) / (m.sum() + SHRINK)
        if j - fitted_at >= REFIT:
            tr = np.arange(last + 1)
            tr = tr[np.isfinite(y[tr]) & np.isfinite(X[tr]).all(axis=1)]
            model = None
            if len(tr) >= MIN_TRAIN and len(np.unique(y[tr])) == 2:
                mu, sd = X[tr].mean(axis=0), X[tr].std(axis=0)
                sd = np.where(sd > 0, sd, 1.0)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model = (LogisticRegression(C=1.0, max_iter=1000).fit((X[tr] - mu) / sd, y[tr]), mu, sd)
            fitted_at = j
        if model is not None and np.isfinite(X[j]).all():
            lr, mu, sd = model
            logit[j] = float(lr.predict_proba(((X[j] - mu) / sd).reshape(1, -1))[0, 1])
    return pd.DataFrame({"base": base, "bins": bins, "logit": logit, "y": y, "rank200": rank}, index=t.index)


def ret_predictions(t: pd.DataFrame, h: int) -> pd.DataFrame:
    """Quantiles 10/50/90% of the h-week log return for every week T (base and bins), from returns known at T only."""
    n, r = len(t), log_returns(t, h)
    _, b = bins_of(t)
    out = {f"{m}_{k}": np.full(n, np.nan) for m in ("base", "bins") for k in QK}
    for j in range(n):
        last = j - 1 - h
        if last < 0:
            continue
        w = r[max(0, last - WINDOW + 1):last + 1]
        w = w[np.isfinite(w)]
        if len(w) < MIN_OBS:
            continue
        qb = np.quantile(w, QS)
        same = r[:last + 1][np.isfinite(r[:last + 1]) & (b[:last + 1] == b[j])] if np.isfinite(b[j]) else np.array([])
        qn = np.quantile(same, QS) if len(same) >= MIN_OBS else qb
        for k, x, z in zip(QK, qb, qn):
            out[f"base_{k}"][j], out[f"bins_{k}"][j] = x, z
    df = pd.DataFrame(out, index=t.index)
    df["r"] = r
    return df


def pinball(qp: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Mean pinball loss over the quantiles QS for every week (qp: weeks × quantiles)."""
    d = r[:, None] - qp
    q = np.array(QS)
    return np.maximum(q * d, (q - 1) * d).mean(axis=1)


def evaluate_returns(rp: pd.DataFrame, mask: np.ndarray, h: int, n_boot: int, seed: int) -> dict:
    e = rp[mask & rp["r"].notna().to_numpy()]
    r = e["r"].to_numpy()
    loss = {m: pinball(e[[f"{m}_{k}" for k in QK]].to_numpy(), r) for m in ("base", "bins")}
    idx = measure.stationary_indices(len(r), h, n_boot, np.random.default_rng(seed))
    gain = (loss["base"][idx] - loss["bins"][idx]).mean(axis=1)
    lo, hi = float(np.quantile(gain, 0.025)), float(np.quantile(gain, 0.975))
    methods = {m: {"loss": float(loss[m].mean()), "cover80": float(((r >= e[f"{m}_q10"]) & (r <= e[f"{m}_q90"])).mean()),
                   "below10": float((r < e[f"{m}_q10"]).mean()), "above90": float((r > e[f"{m}_q90"]).mean())} for m in loss}
    return {"weeks": int(len(r)), "methods": methods, "gain_ci": [lo, hi], "pick": lo > 0}


def _flag(flag: np.ndarray, valid: np.ndarray, index: pd.Index, price: np.ndarray, h: int, n_boot: int, seed: int, gap: int) -> dict:
    """Flagged weeks vs all scored weeks: how often the price was higher after h weeks, by independent episode."""
    z = pd.Series(np.where(valid, np.where(flag, "cao", "khac"), None), index=index, dtype=object)
    tab = measure.zone_table(z, price, [h], ["cao", "khac"], n_boot=n_boot, seed=seed, gap=gap)
    c = tab["zones"]["cao"].get(h, {})
    return {"weeks": c.get("weeks", 0), "episodes": c.get("episodes", 0), "win": c.get("win"), "base": tab["baseline"][h]["win"],
            "diff": c.get("diff"), "ci": c.get("ci"), "wilson": c.get("wilson_episodes"), "verdict": c.get("verdict")}


def evaluate(t: pd.DataFrame, h: int, eval_from: pd.Timestamp, n_boot: int, seed: int, gap: int) -> dict:
    pr = predictions(t, h)
    m = (pr.index >= eval_from) & pr[["base", "bins", "logit", "y"]].notna().all(axis=1).to_numpy()
    e = pr[m]
    out = {"h": h, "weeks": int(m.sum()), "from": e.index[0].strftime("%Y-%m-%d") if m.any() else None,
           "to": e.index[-1].strftime("%Y-%m-%d") if m.any() else None, "methods": {}}
    for name in ("base", "bins", "logit"):
        cal = measure.calibration(e[name].to_numpy(), e["base"].to_numpy(), e["y"].to_numpy(), h, n_boot, seed)
        out["methods"][name] = {k: cal[k] for k in ("weeks", "brier", "brier_base", "gain_ci", "reliability")}
    best = min(("bins", "logit"), key=lambda k: out["methods"][k]["brier"])
    ok = out["methods"][best]["gain_ci"][0] > 0
    out["best"], out["pick"] = best, bool(ok)
    price = t["exec_monday"].reindex(pr.index).to_numpy(dtype=float)
    after = pr.index >= eval_from
    args = (pr.index, price, h, n_boot, seed, gap)
    # buy side: the weeks with the highest probability (top 20% among earlier predictions) vs all weeks
    r = wf.oos_rank(pr[best]).to_numpy(dtype=float)
    out["top20"] = _flag(r >= 0.8, np.isfinite(r) & after, *args)
    # added after the first run (descriptive only, logged in docs/REBUILD_LOG.md): weeks where a method said >= 80%
    out["said80"] = {name: _flag(pr[name].to_numpy() >= 0.8, np.isfinite(pr[name].to_numpy()) & after, *args) for name in ("bins", "logit")}
    # sell side (pre-registered with the extension): weeks where a method said <= 20%, and the 20% lowest-probability weeks
    out["said20"] = {name: _flag(pr[name].to_numpy() <= 0.2, np.isfinite(pr[name].to_numpy()) & after, *args) for name in ("bins", "logit")}
    out["bottom20"] = _flag(r <= 0.2, np.isfinite(r) & after, *args)
    show = best if ok else "base"
    lastp = pr[show].dropna()
    out["now"] = {"date": lastp.index[-1].strftime("%Y-%m-%d"), "method": show, "p": float(lastp.iloc[-1]), "base": float(pr["base"].dropna().iloc[-1]),
                  "bins_p": float(pr["bins"].dropna().iloc[-1]), "logit_p": float(pr["logit"].dropna().iloc[-1]),
                  "close": float(t["close"].iloc[-1]), "close_date": t.index[-1].strftime("%Y-%m-%d")}
    # predicted return if held h weeks: quantiles of the return, base vs bins (pinball loss), same scored weeks
    rp = ret_predictions(t, h)
    ret = evaluate_returns(rp, m, h, n_boot, seed)
    rshow = "bins" if ret["pick"] else "base"
    q = rp[[f"{rshow}_{k}" for k in QK]].dropna().iloc[-1]
    lastq = rp.dropna(subset=[f"base_{k}" for k in QK]).iloc[-1]
    ret["now"] = {"date": q.name.strftime("%Y-%m-%d"), "method": rshow, "q": [float(np.expm1(x)) for x in q.to_numpy()],
                  "base": [float(np.expm1(lastq[f"base_{k}"])) for k in QK], "bins": [float(np.expm1(lastq[f"bins_{k}"])) for k in QK]}
    out["ret"] = ret
    return out


def run(write: bool = True) -> dict:
    from bot.features import weekly_close as wc
    cfg, rb = spec(), load_yaml(CONFIG / "bot.yaml")["rebuild"]
    t = wc.load(None)
    res = {str(h): evaluate(t, h, pd.Timestamp(str(cfg["eval_from"])), rb["bootstrap_n"], rb["seed"], rb["episode_gap_weeks"]) for h in cfg["horizons_weeks"]}
    if write:
        (DATA / "results" / "calib.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return res


LOG = DATA / "calib" / "calib_log.csv"
LOG_COLS = ["date", "h_weeks", "method", "p", "base", "logit_p", "bins_p", "logged_at"]
RET_LOG = DATA / "calib" / "ret_log.csv"
RET_COLS = ["date", "h_weeks", "method", "q10", "q50", "q90", "logged_at"]


def _append(path, cols: list[str], rows: list[list]) -> int:
    import csv
    seen = set()
    if path.exists():
        with open(path, encoding="utf-8-sig", newline="") as f:
            seen = {(r["date"], r["h_weeks"]) for r in csv.DictReader(f)}
    rows = [x for x in rows if (x[0], str(x[1])) not in seen]
    if rows:
        new = not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(cols)
            w.writerows(rows)
    return len(rows)


def log_week(res: dict, now: str) -> int:
    """Append this week's probabilities and return quantiles once per (Sunday, horizon): the forward check."""
    n = _append(LOG, LOG_COLS, [[o["now"]["date"], h, o["now"]["method"], f"{o['now']['p']:.4f}", f"{o['now']['base']:.4f}", f"{o['now']['logit_p']:.4f}",
                                 f"{o['now']['bins_p']:.4f}", now] for h, o in res.items()])
    n += _append(RET_LOG, RET_COLS, [[o["ret"]["now"]["date"], h, o["ret"]["now"]["method"], *(f"{x:.4f}" for x in o["ret"]["now"]["q"]), now]
                                     for h, o in res.items() if "ret" in o])
    return n
