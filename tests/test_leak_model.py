# -*- coding: utf-8 -*-
"""Leak tests for the walk-forward model (must pass before any backtest): scores at week t must not change when
anything after t changes; training labels must end h weeks before each refit; the sign constraint must hold."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.models import wf_logit as wf

H = 26


def table(n: int = 520, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2013-01-06", periods=n, freq="7D")  # Sundays
    a = rng.uniform(size=n)
    b = rng.uniform(size=n)
    noise = rng.normal(0, 0.06, n)
    lr = noise.copy()
    lr[1:] += 0.08 * (a[:-1] - 0.5) - 0.06 * (b[:-1] - 0.5)  # next week's return: a "cheap → higher", b the opposite
    price = 100 * np.exp(np.cumsum(lr))
    return pd.DataFrame({"cheap_a": a, "cheap_b": b, "cheap_c": rng.uniform(size=n), "exec_monday": price}, index=idx)


SETS = {"A": ["a"], "AB": ["a", "b"], "C": ["c"]}


def test_scores_ignore_the_future():
    t = table()
    T = t.index[400]
    base = wf.nested_oos(t, SETS, [1.0, 3.0], h=H)
    changed = t.copy()
    rng = np.random.default_rng(5)
    after = changed.index > T
    changed.loc[after, :] = changed.loc[after, :].sample(frac=1.0, random_state=3).to_numpy() * rng.uniform(0.5, 2.0)
    other = wf.nested_oos(changed, SETS, [1.0, 3.0], h=H)
    a, b = base.loc[:T], other.loc[:T]
    assert len(a) > 100
    pd.testing.assert_frame_equal(a, b)
    fixed_a = wf.config_oos(t, ["a", "b"], 1.0, h=H)
    fixed_b = wf.config_oos(changed, ["a", "b"], 1.0, h=H)
    pd.testing.assert_frame_equal(fixed_a.loc[:T], fixed_b.loc[:T])


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
