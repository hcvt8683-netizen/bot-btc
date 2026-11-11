# -*- coding: utf-8 -*-
"""RSI joined with price action (bot/models/pa_rsi.py): a joined signal at T is the price action signal AND the RSI
condition at T; nothing at T changes when later candles are added (no look-ahead, with a planted leak that must be
caught); the RSI conditions follow the registered thresholds."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.models import pa_rsi as pr
from bot.models import price_action as pa
from bot.models import rsi_check as rc


def synth(n: int = 1400) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    c = 400 * np.exp(np.cumsum(rng.normal(0.0005, 0.03, n)))
    o = np.r_[c[0], c[:-1]] * np.exp(rng.normal(0, 0.004, n))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.012, n)))
    lo = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.012, n)))
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c}, index=pd.date_range("2014-01-01", periods=n, freq="D"))


def test_joined_is_signal_and_rsi() -> None:
    d, pcfg = synth(), pa.spec()
    J, jd, F, fd, A, ad = pr.build(d, pcfg)
    assert J.shape[1] == 12 * 3 and len(jd) == 36
    R = rc.rsi_series(d["close"]).to_numpy()
    for name, s in fd.items():
        for v in pr.VARIANTS:
            assert np.array_equal(J[f"{name}|{v}"].to_numpy(), F[name].to_numpy() & pr.rsi_ok(R, v, s))
    assert J.to_numpy().any()


def test_rsi_conditions() -> None:
    R = np.array([10, 29.9, 30, 49.9, 50, 50.1, 70, 70.1, np.nan])
    assert pr.rsi_ok(R, "qua_ban_mua", 1).tolist() == [True, True, False, False, False, False, False, False, False]
    assert pr.rsi_ok(R, "qua_ban_mua", -1).tolist() == [False] * 7 + [True, False]
    assert pr.rsi_ok(R, "nghieng_dao_chieu", 1).tolist() == [True, True, True, True, False, False, False, False, False]
    assert pr.rsi_ok(R, "nghieng_xu_huong", 1).tolist() == [False] * 5 + [True, True, True, False]


def test_no_lookahead() -> None:
    d, pcfg = synth(), pa.spec()
    full = pr.build(d, pcfg)[0]
    for cut in (700, 1000, 1399):
        part = pr.build(d.iloc[: cut + 1], pcfg)[0]
        assert part.iloc[-1].equals(full.iloc[cut]), cut
    # cài thử lỗi nhìn trước: RSI của ngày mai thay cho hôm nay phải làm tín hiệu khác đi
    R = rc.rsi_series(d["close"]).to_numpy()
    leak = np.r_[R[1:], np.nan]
    f = pa.flags(d, pcfg)
    s = pa.direction(pcfg)["cau_truc_tang"]
    assert not np.array_equal(f["cau_truc_tang"].to_numpy() & pr.rsi_ok(R, "nghieng_xu_huong", s),
                              f["cau_truc_tang"].to_numpy() & pr.rsi_ok(leak, "nghieng_xu_huong", s))
