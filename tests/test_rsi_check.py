# -*- coding: utf-8 -*-
"""RSI 14 (bot/models/rsi_check.py): the Wilder formula on a hand-checked series, no look-ahead (the value at t is the
same whether the series stops at t or continues), band edges exactly at the registered thresholds, independent spacing
and the base-rate comparison on synthetic data, and the deeper-vs-shallow claim test."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import rsi_check as rc


def wave(n: int = 900, seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    return pd.Series(c, index=pd.date_range("2015-01-01", periods=n, freq="D"))


def rsi_slow(v: np.ndarray, n: int = 14) -> np.ndarray:
    """A plain textbook implementation, written independently of rc.rsi."""
    out = np.full(len(v), np.nan)
    ch = np.diff(v)
    au = np.mean([max(x, 0) for x in ch[:n]])
    ad = np.mean([max(-x, 0) for x in ch[:n]])
    for i in range(n, len(v)):
        if i > n:
            au = (au * (n - 1) + max(ch[i - 1], 0)) / n
            ad = (ad * (n - 1) + max(-ch[i - 1], 0)) / n
        out[i] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def test_rsi_matches_textbook_and_bounds() -> None:
    v = wave().to_numpy()
    got = rc.rsi(v)
    want = rsi_slow(v)
    assert np.allclose(got[14:], want[14:], atol=1e-12)
    assert np.all(np.isnan(got[:14]))
    assert np.nanmin(got) >= 0 and np.nanmax(got) <= 100
    up = np.linspace(1, 2, 40)                 # only gains: average loss 0 -> RSI = 100 (registered rule)
    assert np.all(rc.rsi(up)[14:] == 100.0)


def test_rsi_no_lookahead() -> None:
    c = wave()
    full = rc.rsi_series(c)
    for cut in (200, 500, 899):
        part = rc.rsi_series(c.iloc[: cut + 1])
        assert part.iloc[-1] == pytest.approx(full.iloc[cut], abs=1e-12)
    # cài thử lỗi nhìn trước: một phiên bản dùng cả nến sau t phải bị bài này bắt
    leaked = rc.rsi(c.to_numpy()[::-1])[::-1]
    assert not np.allclose(leaked[14:-14], full.to_numpy()[14:-14], atol=1e-6)


def test_band_edges() -> None:
    assert [rc.band_of(x) for x in (0, 19.999, 20, 29.999, 30, 50, 70, 70.001, 80, 80.001, 100)] == [
        "qua_ban_sau", "qua_ban_sau", "qua_ban", "qua_ban", None, None, None, "qua_mua", "qua_mua", "qua_mua_sau", "qua_mua_sau"]
    assert rc.band_of(float("nan")) is None


def test_evaluate_counts_independent_and_compares_to_base() -> None:
    c = wave(1200, seed=3)
    res: dict = {}
    pv: dict = {}
    rc.HORIZONS["synthetic"] = [5]
    rc.FROM["synthetic"] = pd.Timestamp("2015-06-01")
    try:
        rc.evaluate(c, "synthetic", res, pv)
    finally:
        del rc.HORIZONS["synthetic"], rc.FROM["synthetic"]
    R = rc.rsi_series(c)
    r5 = c.shift(-5) / c - 1
    known = r5.notna() & (c.index >= "2015-06-01")
    x = res["qua_ban"]["per_k"]["synthetic|5"]
    assert x["base"] == pytest.approx(float((r5[known] > 0).mean()))
    pos = np.flatnonzero((R.to_numpy() >= 20) & (R.to_numpy() < 30) & known.to_numpy())
    kept = rc.cd._spaced(pos, 5)
    assert x["n"] == len(kept) and np.all(np.diff(kept) >= 5)
    assert x["hits"] == int((r5.to_numpy()[kept] > 0).sum())


def test_claim_rows_cover_all_pairs() -> None:
    res = {b: {"dir": d, "per_k": {f"{kind}|{k}": {"n": 40, "hits": 20 + i, "rate": (20 + i) / 40, "base": 0.5, "p": 0.5}
                                   for kind in rc.HORIZONS for k in rc.HORIZONS[kind]}}
           for i, (b, d) in enumerate(rc.BANDS.items())}
    rows = rc.claim_tests(res)
    assert len(rows) == 2 * sum(len(v) for v in rc.HORIZONS.values()) == 56
    assert all(r["p"] is not None and r["p_holm"] is not None for r in rows)
    assert all(not r["deeper_better"] for r in rows)      # chênh 1–3/40 không thể chắc chắn
