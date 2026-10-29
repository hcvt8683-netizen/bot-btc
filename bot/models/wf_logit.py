"""Nested walk-forward L2 logistic regression with sign constraints (rebuild, part C; settings in config/candidates.yaml).

Timing: week t is a Sunday close; the label of week i is "Monday close of week i+h above Monday close of week i", known
after that Monday, so a refit at Sunday T may use sample i only if i + h ≤ T − 1 (purge = horizon). The outer loop
refits every `refit` weeks on an expanding window and only scores the next block; the inner loop chooses the feature
set and lambda on the last `inner_valid` labelled weeks of the training data (themselves purged from the inner fit).
Buy-side sign constraint: every weight on "cheapness" must be ≥ 0; a feature that comes out negative is dropped (and
recorded) and the model is refitted.
"""
from __future__ import annotations

import dataclasses
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


@dataclasses.dataclass
class Fit:
    features: list[str]
    coef: np.ndarray
    intercept: float
    mu: np.ndarray
    sd: np.ndarray
    dropped: list[str]
    lam: float


def labels(table: pd.DataFrame, h: int) -> np.ndarray:
    """1 / 0 / NaN: execution price h weeks later above the execution price now (NaN when not known)."""
    p = table["exec_monday"].to_numpy(dtype=float)
    y = np.full(len(p), np.nan)
    ok = np.isfinite(p[:-h]) & np.isfinite(p[h:])
    y[:-h][ok] = (p[h:][ok] > p[:-h][ok]).astype(float)
    return y


def fit_signed(X: np.ndarray, y: np.ndarray, names: list[str], lam: float) -> Fit | None:
    """L2 logistic on standardised features; drop the most negative weight until all weights are ≥ 0."""
    keep, dropped = list(range(len(names))), []
    if len(np.unique(y)) < 2:
        return None
    while keep:
        Z = X[:, keep]
        mu, sd = Z.mean(axis=0), Z.std(axis=0)
        sd = np.where(sd > 0, sd, 1.0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = LogisticRegression(C=1.0 / lam, max_iter=1000).fit((Z - mu) / sd, y)
        w = m.coef_[0]
        if (w >= 0).all():
            return Fit([names[k] for k in keep], w, float(m.intercept_[0]), mu, sd, dropped, lam)
        worst = int(np.argmin(w))
        dropped.append(names[keep[worst]])
        keep.pop(worst)
    return None


def predict(f: Fit, X: np.ndarray, names: list[str]) -> np.ndarray:
    idx = [names.index(n) for n in f.features]
    z = (X[:, idx] - f.mu) / f.sd
    return 1 / (1 + np.exp(-(z @ f.coef + f.intercept)))


def _xy(table: pd.DataFrame, feats: list[str]) -> np.ndarray:
    return table[["cheap_" + f for f in feats]].to_numpy(dtype=float)


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def train_rows(X: np.ndarray, y: np.ndarray, last_label_week: int) -> np.ndarray:
    """Indices with all features, a known label and label week ≤ last_label_week (i.e. i ≤ last_label_week)."""
    i = np.arange(min(len(y), last_label_week + 1))
    return i[np.isfinite(X[i]).all(axis=1) & np.isfinite(y[i])]


def config_oos(table: pd.DataFrame, feats: list[str], lam: float, h: int = 26, refit: int = 13, min_train: int = 104,
               end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Out-of-sample probabilities of ONE fixed configuration (used for the multiple-testing correction)."""
    return _walk(table, [(tuple(feats), lam)], h, refit, min_train, None, end)


def nested_oos(table: pd.DataFrame, sets: dict[str, list[str]], lambdas: list[float], h: int = 26, refit: int = 13,
               min_train: int = 104, inner_valid: int = 52, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Out-of-sample probabilities where the inner loop picks set and lambda at every outer refit."""
    configs = [(tuple(f), lam, name) for name, f in sets.items() for lam in lambdas]
    return _walk(table, configs, h, refit, min_train, inner_valid, end)


def _fit_at(X_all, cols, y, configs, T, h, min_train, inner_valid):
    """Model used from Sunday T on: inner choice of configuration (if `inner_valid`), then the fit on every label known
    by T (i + h ≤ T − 1). Returns (configuration or None, Fit or None, base rate)."""
    last_lab = T - 1 - h
    chosen, best_ll = None, None
    if inner_valid:
        v_end, v_start = last_lab, last_lab - inner_valid + 1
        for c in configs:
            names = list(c[0])
            Xc = X_all[:, [cols[f] for f in names]]
            tr = train_rows(Xc, y, v_start - 1 - h)
            va = np.arange(max(0, v_start), v_end + 1)
            va = va[np.isfinite(Xc[va]).all(axis=1) & np.isfinite(y[va])]
            if len(tr) < min_train or len(va) < inner_valid // 2:
                continue
            f = fit_signed(Xc[tr], y[tr], names, c[1])
            if f is None:
                continue
            ll = log_loss(predict(f, Xc[va], names), y[va])
            ll0 = log_loss(np.full(len(va), y[tr].mean()), y[va])
            if ll < ll0 and (best_ll is None or ll < best_ll - 1e-12):
                chosen, best_ll = c, ll
    else:
        chosen = configs[0]
    if chosen is None:
        return None, None, np.nan
    names = list(chosen[0])
    Xc = X_all[:, [cols[f] for f in names]]
    tr = train_rows(Xc, y, last_lab)
    f = fit_signed(Xc[tr], y[tr], names, chosen[1]) if len(tr) >= min_train else None
    return chosen, f, (float(y[tr].mean()) if len(tr) else np.nan)


def freeze_fit(table: pd.DataFrame, sets: dict[str, list[str]], lambdas: list[float], h: int = 26, min_train: int = 104,
               inner_valid: int = 52) -> tuple[str | None, Fit | None, float]:
    """The nested model as it would be refitted at the LAST Sunday of `table` (Part H freeze): (set name, Fit, base rate)."""
    configs = [(tuple(f), lam, name) for name, f in sets.items() for lam in lambdas]
    allf = sorted({f for c in configs for f in c[0]})
    chosen, f, p0 = _fit_at(_xy(table, allf), {f: k for k, f in enumerate(allf)}, labels(table, h), configs, len(table) - 1, h,
                            min_train, inner_valid)
    return (chosen[2] if chosen else None), f, p0


def _walk(table, configs, h, refit, min_train, inner_valid, end) -> pd.DataFrame:
    t = table if end is None else table[table.index <= end]
    y = labels(t, h)
    n = len(t)
    allf = sorted({f for c in configs for f in c[0]})
    X_all = _xy(t, allf)
    cols = {f: k for k, f in enumerate(allf)}
    rows = []
    first = None
    for c in configs:  # first week where the outer loop can start for at least one configuration
        Xc = X_all[:, [cols[f] for f in c[0]]]
        ok = np.isfinite(Xc).all(axis=1) & np.isfinite(y)
        need = min_train + (inner_valid + h if inner_valid else 0)
        idx = np.where(ok)[0]
        if len(idx) >= need:
            cand = idx[need - 1] + h + 1
            first = cand if first is None else min(first, cand)
    if first is None:
        return pd.DataFrame(columns=["p", "p0", "config", "lam", "kept", "dropped"])
    for T in range(first, n, refit):
        chosen, f, p0 = _fit_at(X_all, cols, y, configs, T, h, min_train, inner_valid)
        test = np.arange(T, min(T + refit, n))
        if chosen is None:
            for i in test:
                rows.append((t.index[i], np.nan, np.nan, None, None, None, None))
            continue
        names = list(chosen[0])
        Xc = X_all[:, [cols[f_] for f_ in names]]
        for i in test:
            ok = np.isfinite(Xc[i]).all()
            p = float(predict(f, Xc[i:i + 1], names)[0]) if (f is not None and ok) else np.nan
            rows.append((t.index[i], p, p0, chosen[2] if len(chosen) > 2 else "+".join(names), chosen[1],
                         "+".join(f.features) if f else None, "+".join(f.dropped) if f and f.dropped else ""))
    out = pd.DataFrame(rows, columns=["date", "p", "p0", "config", "lam", "kept", "dropped"]).set_index("date")
    return out


def oos_rank(p: pd.Series, min_weeks: int = 52) -> pd.Series:
    """Rank (0–1) of each out-of-sample score among the out-of-sample scores BEFORE it (needs `min_weeks` of them)."""
    v = p.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    hist: list[float] = []
    for k, x in enumerate(v):
        if np.isfinite(x) and len(hist) >= min_weeks:
            a = np.array(hist)
            out[k] = (np.sum(a < x) + 0.5 * np.sum(a == x)) / len(a)
        if np.isfinite(x):
            hist.append(x)
    return pd.Series(out, index=p.index)
