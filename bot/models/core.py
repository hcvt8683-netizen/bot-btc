"""Layer A: core multiplier from Group A (cycle and valuation) features, section 4.2.

Models in order of simplicity (stop at the simplest that passes validation):
1. equal-weight composite of sign-adjusted percentiles ("cheapness"), no fitting;
2. ridge regression on forward log returns with sign constraints (coefficients ≥ 0 on cheapness), walk-forward,
   features whose unconstrained sign flips across folds are dropped;
3. monotonic gradient boosting only if 1 and 2 fail (not needed so far).
score_A ∈ [0, 1] is mapped to m_A with a monotone step table.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

from bot.validation import walkforward

STEP_TABLE: list[tuple[float, float]] = [(0.80, 2.0), (0.60, 1.25), (0.40, 0.75), (0.0, 0.25)]


def step_map(score: np.ndarray, table: list[tuple[float, float]] = STEP_TABLE) -> np.ndarray:
    """score_A → m_A; NaN (feature not yet available) → 1.0 (plain DCA)."""
    s = np.asarray(score, dtype=float)
    out = np.ones(len(s))
    for k, x in enumerate(s):
        if np.isfinite(x):
            out[k] = next(m for thr, m in table if x >= thr)
    return out


def composite(feat: pd.DataFrame, names: list[str]) -> pd.Series:
    """Mean cheapness of the chosen features; NaN unless all are available."""
    cols = feat[["cheap_" + n for n in names]]
    return cols.mean(axis=1).where(cols.notna().all(axis=1))


def _ridge(X: np.ndarray, y: np.ndarray, lam: float, nonneg: bool) -> tuple[np.ndarray, float]:
    """Ridge on centred data; intercept = mean(y) − mean(X)·w. Non-negative coefficients when nonneg."""
    mx, my = X.mean(axis=0), y.mean()
    Xc, yc = X - mx, y - my
    k = X.shape[1]
    A = np.vstack([Xc, np.sqrt(lam) * np.eye(k)])
    b = np.concatenate([yc, np.zeros(k)])
    lb = np.zeros(k) if nonneg else np.full(k, -np.inf)
    w = lsq_linear(A, b, bounds=(lb, np.full(k, np.inf))).x
    return w, float(my - mx @ w)


def _ridge_scores(feat: pd.DataFrame, names: list[str], horizons: tuple[int, ...], refit: int, lam: float, first_test: int,
                  nonneg: bool, signs: dict | None = None) -> np.ndarray:
    X_all = feat[["cheap_" + n for n in names]].to_numpy(dtype=float)
    idx = np.where(np.isfinite(X_all).all(axis=1))[0]
    scores = np.full((len(horizons), len(feat)), np.nan)
    for hi, h in enumerate(horizons):
        y_all = feat[f"fwd_{h}"].to_numpy(dtype=float)
        for f in walkforward.folds(len(idx), first_test=first_test, refit=refit, horizon=h, embargo=h, min_train=52):
            tr, te = idx[f.train], idx[f.test]
            tr = tr[np.isfinite(y_all[tr])]
            if len(tr) < 52:
                continue
            w, b = _ridge(X_all[tr], y_all[tr], lam, nonneg=nonneg)
            if signs is not None:
                for k, nme in enumerate(names):
                    signs[nme].append(float(np.sign(w[k])))
            if np.all(np.abs(w) < 1e-12):
                continue  # no information: leave NaN, which maps to plain DCA
            fitted = np.sort(X_all[tr] @ w + b)
            pred = X_all[te] @ w + b
            scores[hi, te] = (np.searchsorted(fitted, pred, "left") + np.searchsorted(fitted, pred, "right")) / (2 * len(fitted))
    return scores


def ridge_signed(feat: pd.DataFrame, names: list[str], horizons: tuple[int, ...] = (26, 52), refit: int = 13,
                 lam: float = 1.0, first_test: int = 104) -> tuple[pd.Series, dict]:
    """Walk-forward sign-constrained ridge. Pass 1 (unconstrained) finds features whose sign flips across folds or is
    mostly against the prior; they are dropped. Pass 2 fits the rest with coefficients ≥ 0. score_A = mean over horizons
    of the rank of the prediction among the training fit's own fitted values (point in time)."""
    signs: dict = {n: [] for n in names}
    _ridge_scores(feat, names, horizons, refit, lam, first_test, nonneg=False, signs=signs)
    dropped = {n for n, s in signs.items() if s and (min(s) < 0 < max(s) or np.mean(s) < 0)}
    keep = [n for n in names if n not in dropped]
    info = {"signs": {n: float(np.mean(s)) if s else None for n, s in signs.items()}, "dropped": dropped, "kept": keep}
    if not keep:
        return pd.Series(np.nan, index=feat.index), info
    sc = _ridge_scores(feat, keep, horizons, refit, lam, first_test, nonneg=True)
    with np.errstate(all="ignore"):
        out = np.where(np.isfinite(sc).any(axis=0), np.nanmean(np.where(np.isfinite(sc), sc, np.nan), axis=0), np.nan)
    return pd.Series(out, index=feat.index), info


def gbm_monotone(feat: pd.DataFrame, names: list[str], horizons: tuple[int, ...] = (26, 52), refit: int = 13,
                 first_test: int = 104, seed: int = 0) -> pd.Series:
    """Model 3: small gradient boosting with monotone increasing constraints on cheapness (sklearn), same walk-forward
    folds and rank-to-score step as the ridge. Fixed settings, no tuning."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    X_all = feat[["cheap_" + n for n in names]].to_numpy(dtype=float)
    idx = np.where(np.isfinite(X_all).all(axis=1))[0]
    scores = np.full((len(horizons), len(feat)), np.nan)
    for hi, h in enumerate(horizons):
        y_all = feat[f"fwd_{h}"].to_numpy(dtype=float)
        for f in walkforward.folds(len(idx), first_test=first_test, refit=refit, horizon=h, embargo=h, min_train=52):
            tr, te = idx[f.train], idx[f.test]
            tr = tr[np.isfinite(y_all[tr])]
            if len(tr) < 52:
                continue
            g = HistGradientBoostingRegressor(max_depth=2, max_iter=100, learning_rate=0.05, monotonic_cst=[1] * len(names),
                                              random_state=seed).fit(X_all[tr], y_all[tr])
            fitted = np.sort(g.predict(X_all[tr]))
            pred = g.predict(X_all[te])
            if fitted[-1] - fitted[0] < 1e-12:
                continue
            scores[hi, te] = (np.searchsorted(fitted, pred, "left") + np.searchsorted(fitted, pred, "right")) / (2 * len(fitted))
    with np.errstate(all="ignore"):
        out = np.where(np.isfinite(scores).any(axis=0), np.nanmean(np.where(np.isfinite(scores), scores, np.nan), axis=0), np.nan)
    return pd.Series(out, index=feat.index)
