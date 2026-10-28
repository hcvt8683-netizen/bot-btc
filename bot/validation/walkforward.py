"""Expanding-window walk-forward folds with purge and embargo (section 5).

A model is refit every `refit` weeks at the start of a test block. Training samples are purged when their label
window (i … i + horizon) reaches into the test block, and an embargo of `embargo` weeks keeps a gap before it.
With embargo = horizon both rules give the same cut-off, which is the default.
"""
from __future__ import annotations

import dataclasses

import numpy as np


@dataclasses.dataclass(frozen=True)
class Fold:
    train: np.ndarray   # indices of usable training samples (labels fully known before the test block)
    test: np.ndarray    # indices of the weeks scored by this fit


def folds(n: int, first_test: int, refit: int = 13, horizon: int = 26, embargo: int = 26,
          min_train: int = 52, last_test: int | None = None) -> list[Fold]:
    """Folds over sample indices 0..n-1; test blocks start at `first_test` and cover `refit` weeks each."""
    out = []
    end = n - 1 if last_test is None else last_test
    t0 = first_test
    while t0 <= end:
        cut = t0 - max(horizon, embargo)  # last allowed training index is cut - 1 ... label ends at cut - 1 + horizon < t0
        train = np.arange(0, max(0, cut))
        test = np.arange(t0, min(t0 + refit, end + 1))
        if len(train) >= min_train:
            out.append(Fold(train, test))
        t0 += refit
    return out


def check_no_overlap(f: Fold, horizon: int) -> bool:
    """True when no training label window touches the test block."""
    return len(f.train) == 0 or f.train.max() + horizon < f.test.min()
