"""Part C runner: nested walk-forward, simple baselines, every fixed configuration, permutation tests with multiple-testing
correction, leave-one-cycle-out, monotonicity and zone merging. All settings come from config/candidates.yaml
(pre-registered, committed before the first run). Data stop at eval_end (31/12/2023); the holdout stays closed."""
from __future__ import annotations

import csv
import datetime as dt
import json

import numpy as np
import pandas as pd
from scipy import stats

from bot.backtest import measure, metrics
from bot.backtest.engine import simulate
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.features import weekly_close as wc
from bot.models import wf_logit as wf
from bot.report.measure_b import sim_config

ZONE_NAMES = {"phai": "Phải mua", "cannhac": "Cân nhắc mua", "mua": "Mua thêm (gộp)", "khong": "Không nên mua"}


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")


def table(eval_end: pd.Timestamp) -> pd.DataFrame:
    """Weekly table cut at eval_end: an execution price after eval_end is unknown (NaN), so no label reaches the holdout."""
    return wc.load(eval_end)


def zones_of(rank: pd.Series) -> pd.Series:
    r = rank.to_numpy(dtype=float)
    z = np.where(np.isnan(r), None, np.where(r >= 0.8, "phai", np.where(r >= 0.6, "cannhac", "khong")))
    return pd.Series(z, index=rank.index, dtype=object)


def multiplier(rank: pd.Series) -> np.ndarray:
    """Comparison mapping fixed in the pre-registration: m = 0.5 + rank (neutral 1.0 when there is no rank)."""
    r = rank.to_numpy(dtype=float)
    return np.where(np.isnan(r), 1.0, 0.5 + r)


def fwd(price: np.ndarray, h: int) -> np.ndarray:
    out = np.full(len(price), np.nan)
    out[:-h] = price[h:] / price[:-h] - 1
    return out


def ic(score: np.ndarray, ret: np.ndarray) -> float:
    ok = np.isfinite(score) & np.isfinite(ret)
    return float(stats.spearmanr(score[ok], ret[ok]).statistic) if ok.sum() > 20 else np.nan


def cost_basis(price: np.ndarray, mult: np.ndarray) -> float:
    c = sim_config()
    return float(metrics.equity_ratio(simulate(price, mult, c), simulate(price, None, c))[0]) - 1


def evaluate_strategy(name: str, score: pd.Series, rank: pd.Series, t: pd.DataFrame, horizons: list[int], seed: int, n_boot: int) -> dict:
    price = t["exec_monday"].reindex(score.index).to_numpy(dtype=float)
    ok_price = np.isfinite(price)
    s, rk, price = score[ok_price], rank[ok_price], price[ok_price]
    m = multiplier(rk)
    r26 = fwd(price, 26)
    cb = cost_basis(price, m)
    rng = np.random.default_rng(seed)
    lr = np.diff(np.log(price))
    idx = measure.stationary_indices(len(lr), 26, n_boot, rng)
    P = np.concatenate([np.full((n_boot, 1), price[0]), price[0] * np.exp(np.cumsum(lr[idx], axis=1))], axis=1)
    M = np.concatenate([np.full((n_boot, 1), m[0]), m[1:][idx]], axis=1)
    c = sim_config()
    boots = metrics.equity_ratio(simulate(P, M, c), simulate(P, None, c)) - 1
    z = zones_of(rk)
    tab = measure.zone_table(z, price, horizons, ["phai", "cannhac", "khong"], n_boot=n_boot, seed=seed)
    mono = measure.monotone(tab, ["phai", "cannhac", "__baseline__", "khong"])
    merged = None
    if not all(mono.values()):
        zm = z.map(lambda v: None if v is None else ("mua" if v in ("phai", "cannhac") else "khong"))
        merged = measure.zone_table(zm, price, horizons, ["mua", "khong"], n_boot=n_boot, seed=seed)
        merged["monotone"] = measure.monotone(merged, ["mua", "__baseline__", "khong"])
    return {"name": name, "from": s.index.min().strftime("%Y-%m-%d"), "to": s.index.max().strftime("%Y-%m-%d"), "weeks": int(len(s)),
            "ic26": ic(s.to_numpy(dtype=float), r26), "cost_basis": cb, "cost_ci": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
            "zones": tab, "monotone": mono, "merged": merged, "_score": s, "_mult": m, "_price": price}


def permutation(results: list[dict], n: int, min_shift: int, seed: int) -> dict:
    """Circular shifts of each signal against its returns (offset ≥ min_shift weeks), the same draws for every strategy.
    Raw p-values for IC and cost basis, max-statistic adjusted p-values over all strategies, and Holm."""
    rng = np.random.default_rng(seed)
    u = rng.random(n)
    c = sim_config()
    out = {}
    shifted = {"ic26": np.full((len(results), n), np.nan), "cost_basis": np.full((len(results), n), np.nan)}
    for j, r in enumerate(results):
        s, m, price = r["_score"].to_numpy(dtype=float), r["_mult"], r["_price"]
        L = len(s)
        if L < 2 * min_shift + 10:
            continue
        ks = (min_shift + (u * (L - 2 * min_shift)).astype(int))
        r26 = fwd(price, 26)
        shifted["ic26"][j] = [ic(np.roll(s, k), r26) for k in ks]
        M = np.stack([np.roll(m, k) for k in ks])
        P = np.broadcast_to(price, M.shape)
        shifted["cost_basis"][j] = metrics.equity_ratio(simulate(P, M, c), simulate(P, None, c)) - 1
    for stat in ("ic26", "cost_basis"):
        obs = np.array([r[stat] for r in results])
        sh = shifted[stat]
        raw = np.array([(1 + np.sum(sh[j] >= obs[j])) / (1 + n) if np.isfinite(sh[j]).any() else np.nan for j in range(len(results))])
        mx = np.nanmax(sh, axis=0)
        adj = np.array([(1 + np.sum(mx >= obs[j])) / (1 + n) for j in range(len(results))])
        order = np.argsort(np.where(np.isnan(raw), 1, raw))
        holm = np.full(len(raw), np.nan)
        running = 0.0
        valid = int(np.isfinite(raw).sum())
        for rank_k, j in enumerate(order):
            if np.isnan(raw[j]):
                continue
            running = max(running, min(1.0, (valid - rank_k) * raw[j]))
            holm[j] = running
        out[stat] = {r["name"]: {"obs": float(obs[j]), "p_raw": float(raw[j]), "p_maxstat": float(adj[j]), "p_holm": float(holm[j])}
                     for j, r in enumerate(results)}
    return out


def loco(t: pd.DataFrame, sets: dict, cycles: list[str], h: int, lam: float = 1.0) -> dict:
    """Leave one halving cycle out of training (with a purge of h weeks around it) and score that cycle. Not a forward
    test: models may learn from later cycles; it shows whether a set works in every cycle."""
    y = wf.labels(t, h)
    price = t["exec_monday"].to_numpy(dtype=float)
    r26 = fwd(price, 26)
    res = {}
    for name, feats in sets.items():
        X = t[["cheap_" + f for f in feats]].to_numpy(dtype=float)
        res[name] = {}
        for cyc in cycles:
            a, b = (pd.Timestamp(x) for x in cyc.split("/"))
            inside = (t.index >= a) & (t.index <= b)
            k = np.arange(len(t))
            near = (t.index >= a - pd.Timedelta(weeks=h)) & (t.index <= b)
            tr = k[(~near) & np.isfinite(X).all(axis=1) & np.isfinite(y)]
            te = k[inside & np.isfinite(X).all(axis=1)]
            if len(tr) < 104 or len(te) < 26:
                res[name][cyc] = None
                continue
            f = wf.fit_signed(X[tr], y[tr], feats, lam)
            if f is None:
                res[name][cyc] = {"weeks": int(len(te)), "kept": [], "dropped": feats}
                continue
            p_tr, p_te = wf.predict(f, X[tr], feats), wf.predict(f, X[te], feats)
            ref = np.sort(p_tr)
            rank = (np.searchsorted(ref, p_te, "left") + np.searchsorted(ref, p_te, "right")) / (2 * len(ref))
            ok = np.isfinite(price[te])
            res[name][cyc] = {"weeks": int(len(te)), "kept": f.features, "dropped": f.dropped, "ic26": ic(p_te, r26[te]),
                              "cost_basis": cost_basis(price[te][ok], (0.5 + rank)[ok]) if ok.sum() > 26 else None}
    return res


def run(write: bool = True) -> dict:
    sp = spec()
    md, ts = sp["model"], sp["tests"]
    eval_end = pd.Timestamp(str(md["eval_end"]))
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    seed, n_boot, horizons = rb["seed"], rb["bootstrap_n"], rb["horizons_weeks"]
    t = table(eval_end)
    sets = {k: v["features"] for k, v in sp["sets"].items()}
    h = md["target_weeks"]
    nested = wf.nested_oos(t, sets, md["lambdas"], h=h, refit=md["refit_weeks"], min_train=md["min_train_weeks"], inner_valid=md["inner_valid_weeks"])
    fixed = {f"{k}/λ{lam:g}": wf.config_oos(t, f, lam, h=h, refit=md["refit_weeks"], min_train=md["min_train_weeks"])
             for k, f in sets.items() for lam in md["lambdas"]}
    strategies = {"Lồng nhau (vòng trong chọn bộ và λ)": nested["p"]}
    strategies.update({k: v["p"] for k, v in fixed.items()})
    rules = {"Quy tắc MVRV": t["cheap_mvrv"], "Quy tắc Giá/MA 200 tuần": t["cheap_p_200wma"]}
    results = []
    for name, p in {**strategies, **rules}.items():
        p = p.dropna()
        if len(p) < 60:
            continue
        rank = wf.oos_rank(p, md["rank_min_weeks"]).dropna()
        sc = p.reindex(rank.index)
        if len(rank) < 52:
            continue
        results.append(evaluate_strategy(name, sc, rank, t, horizons, seed, n_boot))
    # common window of the nested model and the two rules, for a like-for-like comparison
    main = next(r for r in results if r["name"].startswith("Lồng nhau"))
    start = main["from"]
    common = []
    for r in results:
        if r["name"].startswith("Lồng nhau") or r["name"].startswith("Quy tắc"):
            s = r["_score"].loc[start:]
            common.append({"name": r["name"], "from": s.index.min().strftime("%Y-%m-%d"), "weeks": int(len(s)),
                           "ic26": ic(s.to_numpy(dtype=float), fwd(t["exec_monday"].reindex(s.index).to_numpy(dtype=float), 26)),
                           "cost_basis": cost_basis(t["exec_monday"].reindex(s.index).to_numpy(dtype=float), r["_mult"][-len(s):])})
    perm = permutation(results, ts["permutation_n"], ts["permutation_min_shift_weeks"], seed)
    lc = loco(t, sets, ts["loco_cycles"], h)
    picks = nested.dropna(subset=["config"])
    sel = picks.groupby(["config", "lam"]).size().sort_values(ascending=False).reset_index(name="weeks").to_dict("records")
    drops = {}
    for k, v in fixed.items():
        d = v["dropped"].dropna()
        drops[k] = {"refits_with_drop": int((d != "").sum()), "dropped": sorted({x for s in d for x in s.split("+") if x})}
    cal = None
    nn = nested.dropna(subset=["p"])
    if len(nn):
        y = wf.labels(t, h)
        yy = pd.Series(y, index=t.index).reindex(nn.index).to_numpy()
        cal = measure.calibration(nn["p"].to_numpy(), nn["p0"].to_numpy(), yy, h, n_boot, seed)
    out = {"run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "eval_end": eval_end.strftime("%Y-%m-%d"),
           "n_strategies": len(results), "results": [{k: v for k, v in r.items() if not k.startswith("_")} for r in results],
           "common": common, "permutation": perm, "loco": lc, "selected": sel, "sign_drops": drops, "calibration": cal,
           "no_model_weeks": int(nested["config"].isna().sum()), "nested_weeks": int(len(nested))}
    if write:
        (DATA / "results" / "part_c.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        log_configs(out)
    return out


def log_configs(out: dict) -> None:
    """experiments/rebuild_configs.csv: every configuration tried, with its out-of-sample results (appendix)."""
    path = ROOT / "experiments" / "rebuild_configs.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run_at", "part", "strategy", "from", "to", "weeks", "ic26", "cost_basis", "cost_ci_lo", "cost_ci_hi",
                        "p_ic_raw", "p_ic_maxstat", "p_cost_raw", "p_cost_maxstat"])
        for r in out["results"]:
            pi, pc = out["permutation"]["ic26"][r["name"]], out["permutation"]["cost_basis"][r["name"]]
            w.writerow([out["run_at"], "C", r["name"], r["from"], r["to"], r["weeks"], round(r["ic26"], 4), round(r["cost_basis"], 4),
                        round(r["cost_ci"][0], 4), round(r["cost_ci"][1], 4), pi["p_raw"], pi["p_maxstat"], pc["p_raw"], pc["p_maxstat"]])
