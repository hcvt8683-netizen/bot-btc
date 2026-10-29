# -*- coding: utf-8 -*-
"""Leak tests for the walk-forward model (must pass before any backtest): scores at week t must not change when
anything after t changes; training labels must end h weeks before each refit; the sign constraint must hold."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.models import wf_logit as wf

H = 26


def table(n: int = 520, seed: int = 0) -> pd.DataFrame:
    """Persistent features (slow AR processes) so that they predict the 26-week return: a cheap → higher, b the opposite."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2013-01-06", periods=n, freq="7D")  # Sundays

    def slow() -> np.ndarray:
        x = np.zeros(n)
        for k in range(1, n):
            x[k] = 0.95 * x[k - 1] + rng.normal(0, 0.3)
        return pd.Series(x).rank(pct=True).to_numpy()

    a, b, c = slow(), slow(), rng.uniform(size=n)
    lr = rng.normal(0.003, 0.05, n)
    lr[1:] += 0.03 * (a[:-1] - 0.5) - 0.02 * (b[:-1] - 0.5)
    price = 100 * np.exp(np.cumsum(lr))
    return pd.DataFrame({"cheap_a": a, "cheap_b": b, "cheap_c": c, "exec_monday": price}, index=idx)


def future_changed(t: pd.DataFrame, T: pd.Timestamp) -> pd.DataFrame:
    """Everything after T replaced: features shuffled, prices move against the recent labels, so many labels of the last
    h weeks before T flip (a rally if they were mostly 0, a crash if mostly 1)."""
    out = t.copy()
    after = out.index > T
    rng = np.random.default_rng(5)
    for c in ("cheap_a", "cheap_b", "cheap_c"):
        out.loc[after, c] = rng.permutation(out.loc[after, c].to_numpy())
    # the execution price of row T is the Monday AFTER Sunday T, i.e. already future at signal time: change it too
    fut = out.index >= T
    k = int(np.where(~fut)[0][-1])
    pT = out["exec_monday"].iloc[k]
    drift = 0.06 if np.nanmean(wf.labels(t, H)[k - H + 1:k + 1]) < 0.5 else -0.06
    out.loc[fut, "exec_monday"] = pT * np.exp(np.cumsum(rng.normal(drift, 0.03, fut.sum())))
    return out


SETS = {"A": ["a"], "AB": ["a", "b"], "C": ["c"]}


def test_scores_ignore_the_future():
    t = table()
    T = t.index[400]
    changed = future_changed(t, T)
    assert (np.nan_to_num(wf.labels(t, H)[375:401], nan=-1) != np.nan_to_num(wf.labels(changed, H)[375:401], nan=-1)).sum() >= 10
    base = wf.nested_oos(t, SETS, [1.0, 3.0], h=H)
    other = wf.nested_oos(changed, SETS, [1.0, 3.0], h=H)
    a, b = base.loc[:T], other.loc[:T]
    assert a["p"].loc[T - pd.Timedelta(weeks=H):].notna().sum() >= 20  # real scores right before T
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    fixed_a = wf.config_oos(t, ["a", "b"], 1.0, h=H)
    fixed_b = wf.config_oos(changed, ["a", "b"], 1.0, h=H)
    pd.testing.assert_frame_equal(fixed_a.loc[:T], fixed_b.loc[:T], check_exact=True)


def test_labels_end_h_weeks_before_refit():
    t = table()
    y = wf.labels(t, H)
    assert np.isnan(y[-H:]).all() and np.isfinite(y[:-H]).all()
    X = t[["cheap_a"]].to_numpy()
    rows = wf.train_rows(X, y, 300 - 1 - H)
    assert rows.max() + H <= 300 - 1  # every label used at a refit on week 300 is known before it


def test_sign_constraint_drops_reversed_feature():
    t = table(2000, seed=1)
    y = wf.labels(t, 4)
    ok = np.isfinite(y)
    X = t[["cheap_a", "cheap_b"]].to_numpy()[ok]
    f = wf.fit_signed(X, y[ok], ["a", "b"], 1.0)
    assert f is not None and f.features == ["a"] and f.dropped == ["b"] and (f.coef >= 0).all()


def test_rank_uses_only_previous_scores():
    p = pd.Series(np.arange(100, dtype=float))
    r = wf.oos_rank(p, min_weeks=52)
    assert r.iloc[:52].isna().all() and r.iloc[60] == 1.0  # rising scores: each is above all previous ones
    r2 = wf.oos_rank(pd.concat([p.iloc[:70], pd.Series([-1.0] * 30)], ignore_index=True), min_weeks=52)
    assert (r.iloc[:70] == r2.iloc[:70]).all() or (r.iloc[:70].isna() == r2.iloc[:70].isna()).all()


def test_no_leak_at_any_refit_offset():
    """Refits happen every 13 weeks; checking 14 consecutive cut-off weeks puts a refit right before every one of them,
    so even a leak of a single week is caught."""
    t = table()
    for k in range(388, 402):
        T = t.index[k]
        changed = future_changed(t, T)
        a = wf.config_oos(t, ["a", "b"], 1.0, h=H).loc[:T]
        b = wf.config_oos(changed, ["a", "b"], 1.0, h=H).loc[:T]
        pd.testing.assert_frame_equal(a, b, check_exact=True)
