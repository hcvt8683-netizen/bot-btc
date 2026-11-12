# -*- coding: utf-8 -*-
"""Trend forecast (bot/models/trend.py): states and predictions use only data up to T (a planted look-ahead is caught),
the conditional probability is the registered shrinkage of same-state windows, the combined model averages the four,
Holm, labels, and the append-only log."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import trend as tr

CFG = tr.spec()


def fake(days: int = 2400, seed: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    p = 1000 * np.exp(np.cumsum(rng.normal(0.0008, 0.03, days)))
    mv = 1.5 + 0.5 * np.sin(np.arange(days) / 90) + rng.normal(0, 0.05, days)
    return pd.DataFrame({"p": p, "mvrv": mv}, index=pd.date_range("2015-01-01", periods=days, freq="D"))


def preds(d: pd.DataFrame, k: int) -> dict:
    return tr.predict(d, tr.base_states(d, CFG), k, CFG)


def test_predictions_use_only_data_up_to_t():
    d = fake()
    T = d.index[2000]
    for k in (3, 30):
        a = preds(d, k)
        for crash in (0.3, 3.0):
            e = d.copy()
            e.loc[e.index > T, "p"] *= crash
            e.loc[e.index > T, "mvrv"] *= crash
            b = preds(e, k)
            for m in tr.ALL:
                pd.testing.assert_frame_equal(a["models"][m].loc[:T], b["models"][m].loc[:T])
            for m, st in a["states"].items():
                pd.testing.assert_series_equal(st.loc[:T], b["states"][m].loc[:T], check_names=False)
        assert a["models"]["ket_hop"].loc[T].notna().all()


def test_a_planted_look_ahead_is_caught(monkeypatch):
    """Known windows taken one day too late (their outcome is the price of T + 1) must make the check above fail."""
    real = tr.predict

    def leaky(d, bs, k, cfg):
        orig = pd.Series.shift
        monkeypatch.setattr(pd.Series, "shift", lambda self, n=1, *a, **kw: orig(self, n - 1 if n == k and k > 1 else n, *a, **kw))
        try:
            return real(d, bs, k, cfg)
        finally:
            monkeypatch.setattr(pd.Series, "shift", orig)
    monkeypatch.setattr(tr, "predict", leaky)
    with pytest.raises(AssertionError):
        test_predictions_use_only_data_up_to_t()


def test_a_planted_look_ahead_in_a_state_is_caught(monkeypatch):
    """A rank that also sees the next day must make the check fail."""
    real = tr._past_rank
    monkeypatch.setattr(tr, "_past_rank", lambda x, w, m: real(np.r_[x[1:], np.nan], w, m))
    with pytest.raises(AssertionError):
        test_predictions_use_only_data_up_to_t()


def test_conditional_probability_is_the_registered_shrinkage():
    d = fake()
    k = 7
    pr = preds(d, k)
    T = d.index[1900]
    W = int(CFG["window_days"]) - k
    z = pr["r"] / (pr["sig"] * np.sqrt(k))
    up = (z > 0).astype(float).where(z.notna())
    st = pr["states"]["ma200"]
    win = slice(T - pd.Timedelta(days=W - 1 + k), T - pd.Timedelta(days=k))     # windows i with i + k <= T, 4 years back
    zi, ui, si = z.loc[win], up.loc[win], st.loc[win]
    base = ui.mean()
    same = (si == st.loc[T]) & zi.notna()
    expect = (ui[same].sum() + tr.SHRINK * base) / (same.sum() + tr.SHRINK)
    assert pr["models"]["goc"].loc[T, "p"] == pytest.approx(base)
    assert pr["models"]["ma200"].loc[T, "p"] == pytest.approx(expect)
    assert pr["models"]["ma200"].loc[T, 0.5] == pytest.approx(zi[same].quantile(0.5))
    comb = np.mean([pr["models"][m].loc[T, "p"] for m in tr.COND])
    assert pr["models"]["ket_hop"].loc[T, "p"] == pytest.approx(comb)


def test_holm_and_labels():
    adj = tr.holm({"a": 0.01, "b": 0.02, "c": 0.5})
    assert adj["a"] == pytest.approx(0.03) and adj["b"] == pytest.approx(0.04) and adj["c"] == pytest.approx(0.5)
    assert tr.label(0.55, CFG) == "tang" and tr.label(0.45, CFG) == "giam" and tr.label(0.5, CFG) == "khong_ro" and tr.label(None, CFG) == "khong_ro"


def test_evaluate_and_verdict_shape():
    d = fake()
    ev = {k: tr.evaluate(preds(d, k), k, {**CFG, "eval_from": "2018-01-01"}) for k in (1, 7)}
    tr.verdicts(ev)
    for e in ev.values():
        assert e["n"] > 500 and set(e["models"]) == set(tr.ALL)
        assert e["dir_model"] in tr.ALL and e["mag_model"] in tr.ALL
        for m in tr.TESTED:
            x = e["models"][m]
            assert 0 < x["dir_p"] <= 1 and x["dir_holm"] >= x["dir_p"] and x["dir_ci"][0] <= x["dir_ci"][1]


def test_log_is_append_only(tmp_path):
    p = tmp_path / "log.csv"
    row = {"k": 7, "target": "2026-11-08", "models": {m: {"p": 0.52} for m in tr.ALL}, "dir_model": "goc", "mag_model": "goc", "q10": -0.05, "q50": 0.002, "q90": 0.06}
    res = {"version": "v1", "anchor": "2026-11-01", "close": 78000.0, "now": [row, {**row, "k": 1, "target": "2026-11-02"}]}
    now = pd.Timestamp("2026-11-02 10:00")
    rows = tr.log_today(res, now, p)
    assert [r["k"] for r in rows] == [7]                 # the 1-day target (02/11) is not ahead any more
    assert tr.log_today(res, now, p) == []
    assert len(tr.log_today({**res, "version": "v2"}, now, p)) == 1
    assert [r["version"] for r in tr.read_log(p)] == ["v1", "v2"]


def test_sell_plan_receives_the_monday_closes_minus_costs():
    """Chốt lời dần (bot/models/sell_plan.py): selling 1 BTC in 4 weekly parts receives the mean of those closes after costs."""
    from bot.models import sell_plan as sp
    price = np.array([100.0, 110.0, 90.0, 120.0, 130.0, 80.0, 70.0])
    roi, mdd = sp.outcomes(price, np.array([0]), 4, 6, 0.001, 0.0005)
    got = sum(p / 4 * (1 - 0.0005) * (1 - 0.001) for p in price[:4])
    assert roi[0] == pytest.approx(got / 100 - 1) and mdd[0] <= 0
    once, _ = sp.outcomes(price, np.array([0]), 1, 6, 0.001, 0.0005)
    assert once[0] == pytest.approx((1 - 0.0005) * (1 - 0.001) - 1)


def test_a_chosen_model_without_a_number_today_gives_way_to_the_base_rate():
    # 11/11/2026: MVRV of the last day not published yet → dinh_gia and ket_hop empty, the 1-day band showed one price
    qs = [0.1, 0.5, 0.9, 0.05, 0.95]
    full = {"p": 0.53, **{f"q{round(q * 100)}": 0.01 for q in qs}}
    empty = {"p": None, **{f"q{round(q * 100)}": None for q in qs}}
    models = {"goc": full, "ket_hop": empty, "dong_luong": full}
    assert tr.pick(models, "ket_hop", "ket_hop", qs) == ("goc", "goc", "ket_hop", "ket_hop")
    assert tr.pick(models, "dong_luong", "dong_luong", qs) == ("dong_luong", "dong_luong", None, None)
    assert tr.pick(models, "goc", "goc", qs) == ("goc", "goc", None, None)
    assert tr.pick({**models, "ket_hop": {**full, "q5": None}}, "goc", "ket_hop", qs) == ("goc", "goc", None, "ket_hop")
