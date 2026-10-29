# -*- coding: utf-8 -*-
"""Part C: the permutation test gives a small p-value to a real signal and a large one to noise; max-statistic and
Holm adjusted p-values are never below the raw ones."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.models import part_c


def _fake(name: str, signal: bool, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n = 400
    x = np.zeros(n)
    for k in range(1, n):
        x[k] = 0.97 * x[k - 1] + rng.normal(0, 0.2)
    lr = rng.normal(0.003, 0.04, n)
    if signal:
        lr[1:] += 0.02 * x[:-1]
    price = 100 * np.exp(np.cumsum(lr))
    score = pd.Series(x if signal else rng.normal(size=n), index=pd.date_range("2015-01-04", periods=n, freq="7D"))
    rank = score.rank(pct=True)
    r26 = part_c.fwd(price, 26)
    return {"name": name, "_score": score, "_mult": part_c.multiplier(rank), "_price": price,
            "ic26": part_c.ic(score.to_numpy(), r26), "cost_basis": part_c.cost_basis(price, part_c.multiplier(rank))}


def test_permutation_separates_signal_from_noise_and_adjusts_upwards():
    res = [_fake("tin_hieu", True, 1), _fake("nhieu_1", False, 2), _fake("nhieu_2", False, 3)]
    out = part_c.permutation(res, 300, 52, 7)
    ic = out["ic26"]
    assert ic["tin_hieu"]["p_raw"] < 0.05 < ic["nhieu_1"]["p_raw"]
    for v in ic.values():
        assert v["p_maxstat"] >= v["p_raw"] - 1e-12 and v["p_holm"] >= v["p_raw"] - 1e-12
