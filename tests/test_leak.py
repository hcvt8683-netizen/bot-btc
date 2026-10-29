# -*- coding: utf-8 -*-
"""Leak tests (written first, must pass before any backtest): changing, shuffling or removing data after week t must
not change anything computed for weeks ≤ t."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.features import weekly_close as wc

T = pd.Timestamp("2019-06-30")  # a Sunday


def synth(n_days: int = 4200, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    d = pd.date_range("2012-01-01", periods=n_days, freq="D")
    p = 10 * np.exp(np.cumsum(rng.normal(0.0015, 0.04, n_days)))
    mvrv = 1.6 + 0.6 * np.sin(np.arange(n_days) / 300) + rng.normal(0, 0.02, n_days)
    cm = pd.DataFrame({"date": d, "price": p, "mcap": p * 1.5e7, "mvrv": mvrv, "hashrate": np.exp(np.arange(n_days) / 700) * (1 + 0.1 * np.sin(np.arange(n_days) / 30)),
                       "iss_usd": p * 3600 * np.where(np.arange(n_days) < 1700, 1, 0.5)})
    ext = pd.DataFrame({"date": d, "volume_spot_usd": 1e8 * (1 + rng.uniform(0, 1, n_days)), "supply": 1e7, "iss_btc": 3600.0})
    fng = pd.DataFrame({"date": d[d >= "2018-02-01"], "fng": rng.integers(5, 95, (d >= "2018-02-01").sum()).astype(float)})
    fed = pd.DataFrame({"date": d, "fed_upper": np.repeat(np.r_[0.25, 0.5, 1.0, 2.5, 1.75, 0.25], -(-n_days // 6))[:n_days]})
    return {"cm": cm, "ext": ext, "fng": fng, "fed": fed}


def after(df: pd.DataFrame, how: str, rng: np.random.Generator) -> pd.DataFrame:
    """Return a copy where every row after T is shuffled, scaled or removed."""
    out = df.copy()
    m = out["date"] > T
    cols = [c for c in out.columns if c != "date"]
    if how == "drop":
        return out[~m]
    if how == "shuffle":
        out.loc[m, cols] = out.loc[m, cols].sample(frac=1.0, random_state=int(rng.integers(1e9))).to_numpy()
    if how == "scale":
        out.loc[m, cols] = out.loc[m, cols] * 3.7
    return out


@pytest.mark.parametrize("how", ["drop", "shuffle", "scale"])
def test_weekly_table_ignores_the_future(how):
    rng = np.random.default_rng(1)
    s = synth()
    base = wc.build(**s)
    changed = wc.build(**{k: after(v, how, rng) for k, v in s.items()})
    a, b = base.loc[:T], changed.loc[:T]
    assert len(a) == len(b) > 300
    pd.testing.assert_frame_equal(a, b, check_exact=True)


def test_end_parameter_cuts_inputs():
    s = synth()
    full = wc.build(**s)
    cut = wc.build(**s, end=T)
    assert cut.index.max() == T
    pd.testing.assert_frame_equal(full.loc[:T], cut, check_exact=True)


def test_rows_are_sunday_closes_and_percentiles_need_history():
    t = wc.build(**synth())
    assert (t.index.weekday == 6).all()
    assert t["pct_mvrv"].iloc[:103].isna().all() and t["pct_mvrv"].iloc[103:].notna().all()
    assert set(t["fed_regime"].dropna()) <= {"tang", "giu", "giam"}
    assert t["raw_fng"].loc[:"2018-01-31"].isna().all()
