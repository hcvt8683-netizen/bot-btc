# -*- coding: utf-8 -*-
"""Part D tests: hysteresis, multiplier from the confidence bound, walk-forward without look-ahead, Part I gate."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from bot.models import zones as zn

TH = {"phai": 80, "cannhac": 60}


def test_hysteresis_enters_at_threshold_and_leaves_5_points_below():
    r = pd.Series([50, 61, 58, 56, 54, 81, 77, 76, 74, 79, 81, 59, 54])
    z = zn.hysteresis_zones(r, TH, 5)
    assert list(z) == ["khong", "cannhac", "cannhac", "cannhac", "khong", "phai", "phai", "phai", "cannhac", "cannhac", "phai", "cannhac", "khong"]
    noisy = pd.Series(80 + np.tile([1, -1], 30))  # rank wobbling around 80
    assert zn.flips(zn.hysteresis_zones(noisy, TH, 5)) == 0 and zn.flips(zn.plain_zones(noisy, TH)) == 59


def test_multiplier_uses_the_bound_not_the_center():
    e = {"episodes": 5, "ci": [0.10, 0.40], "diff": 0.25}
    assert zn.zone_multiplier("phai", e, 2.0, (0.5, 1.5), 3) == pytest.approx(1.2)
    assert zn.zone_multiplier("phai", {**e, "ci": [-0.01, 0.6]}, 2.0, (0.5, 1.5), 3) == 1.0  # interval touches 0
    assert zn.zone_multiplier("phai", {**e, "episodes": 2}, 2.0, (0.5, 1.5), 3) == 1.0  # too few episodes
    assert zn.zone_multiplier("khong", {"episodes": 4, "ci": [-0.5, -0.4]}, 2.0, (0.5, 1.5), 3) == 0.5  # capped
    assert zn.zone_multiplier("phai", {"episodes": 9, "ci": [0.4, 0.9]}, 2.0, (0.5, 1.5), 3) == 1.5


def _informative(n=420, seed=3):
    """Zones that really are better than the baseline (built from the future on purpose, only to get multipliers ≠ 1)."""
    rng = np.random.default_rng(seed)
    price = 100 * np.exp(np.cumsum(rng.normal(0.002, 0.05, n)))
    fwd = np.r_[price[26:] / price[:-26] - 1, np.zeros(26)]
    good = np.where(fwd > 0, 85.0, 30.0)
    rank = pd.Series(np.where(rng.random(n) < 0.65, good, rng.uniform(0, 100, n)))  # right ~65% of the time: unsaturated multipliers
    return price, zn.hysteresis_zones(rank, TH, 5)


def test_walk_multipliers_ignore_the_future():
    price, z = _informative()
    m1, _ = zn.walk_multipliers(z, price, 26, 13, 2.0, (0.5, 1.5), 3, 150, 1)
    assert ((m1 > 1) & (m1 < 1.5)).sum() > 30  # multipliers strictly inside the bounds, so small changes would show
    rng = np.random.default_rng(9)
    for T in range(300, 314):  # every offset from a refit, so even a one-week leak shows
        p2 = price.copy()
        p2[T:] = p2[T - 1] * np.exp(np.cumsum(rng.normal(-0.08, 0.02, len(price) - T)))  # from the Monday after week T on
        m2, _ = zn.walk_multipliers(z, p2, 26, 13, 2.0, (0.5, 1.5), 3, 150, 1)
        assert (m1[:T + 1] == m2[:T + 1]).all(), T


def test_gate_keeps_dca_until_part_i_passes(tmp_path):
    f = tmp_path / "acc.json"
    assert zn.gate(1.3, f) == (1.0, "chua_kiem_dinh")
    f.write_text(json.dumps({"passed": False}), encoding="utf-8")
    assert zn.gate(1.3, f) == (1.0, "chua_dat_phan_i")
    f.write_text(json.dumps({"passed": True}), encoding="utf-8")
    assert zn.gate(1.3, f) == (1.3, "dat_phan_i")


def test_every_refit_sees_only_weeks_before_it(monkeypatch):
    """White-box check: at a refit on week T the edge estimate receives exactly weeks 0..T−1 (prices and zones)."""
    from bot.backtest import measure
    seen = []
    real = measure.zone_table

    def spy(z, price, *a, **k):
        seen.append((len(z), len(price)))
        return real(z, price, *a, **k)

    monkeypatch.setattr(measure, "zone_table", spy)
    price, z = _informative()
    _, hist = zn.walk_multipliers(z, price, 26, 13, 2.0, (0.5, 1.5), 3, 50, 1)
    assert seen and len(seen) == len(hist)
    assert all(nz == npx == h["refit"] for (nz, npx), h in zip(seen, hist))
