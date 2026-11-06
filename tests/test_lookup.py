# -*- coding: utf-8 -*-
"""Tra cứu tại ngày t (bot/models/lookup.py và src/lookup.js, mục lookup / analog của config/candidates.yaml).

- Dải giá bằng đúng price_forecast.bands ở các kỳ hạn đã kiểm định.
- LOOKUP_CORE (trình duyệt) cho cùng mọi con số với bản Python: tra cứu tại nhiều (t, h) và kiểm chứng quá khứ.
- Không nhìn trước: đổi giá sau ngày t không đổi gì ở ngày t (trừ phần "điều đã xảy ra"), ở cả hai bản; và một hàm cố ý
  nhìn trước thì bị bắt.
- Quy tắc kết luận và Holm của Tình huống tương tự.
"""
from __future__ import annotations

import copy
import json
import math
import pathlib
import subprocess
import tempfile

import numpy as np
import pandas as pd
import pytest

from bot.models import lookup as lk
from bot.models import price_forecast as pf

ROOT = pathlib.Path(__file__).resolve().parent.parent
START = "2010-07-18"


def synth(seed: int = 7, end: str = "2021-06-30") -> dict:
    """Giá giả: bước ngẫu nhiên có các giai đoạn dao động khác nhau, vài ngày thiếu giá; cao / thấp từ 18/08/2011."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(START, end, freq="D")
    n = len(idx)
    vol = 0.03 * (1 + 0.7 * np.sin(np.arange(n) / 230.0))
    p = 0.08 * np.exp(np.cumsum(rng.normal(0.0012, 1.0, n) * vol))
    p[[1500, 2900]] = np.nan
    hi = p * np.exp(np.abs(rng.normal(0, 0.02, n)))
    lo = p * np.exp(-np.abs(rng.normal(0, 0.02, n)))
    before = idx < pd.Timestamp("2011-08-18")
    hi[before], lo[before] = np.nan, np.nan
    hi[3100], lo[3100] = np.nan, np.nan
    r8 = np.vectorize(lk.r8)
    return {"start": idx[0], "close": r8(p), "high": r8(hi), "low": r8(lo)}


def prepared(D: dict) -> tuple[dict, dict, dict]:
    cfg = lk.spec()
    S = lk.series(D, cfg)
    return cfg, S, lk.features(D, S, cfg)


CASES = [("2016-01-01", 1), ("2016-03-15", 7), ("2017-06-30", 30), ("2018-12-15", 90), ("2019-07-01", 365), ("2020-03-12", 45),
         ("2020-12-31", 730), ("2021-06-29", 7), ("2021-06-30", 1461), ("2016-08-01", 1096), ("2016-08-01", 1200), ("2014-01-05", 30)]
CHECK_H = [1, 7, 30, 90, 365, 1461]


def page_json(D: dict, cfg: dict, F: dict) -> dict:
    res = lk.research(D, F, cfg)
    page = lk.page_data(D, cfg, lk._round(res))
    return json.loads(json.dumps(page))


def close_enough(a, b, path: str = "") -> list[str]:
    """Khác nhau ở đâu (số thực: tương đối 1e-9)."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.append(f"{path}.{k}: chỉ có ở một bên")
            else:
                out += close_enough(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return [f"{path}: độ dài {len(a)} ≠ {len(b)}"]
        for i, (x, y) in enumerate(zip(a, b)):
            out += close_enough(x, y, f"{path}[{i}]")
    elif isinstance(a, bool) or isinstance(b, bool):
        if bool(a) != bool(b) or type(a) is not type(b):
            out.append(f"{path}: {a} ≠ {b}")
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not (a == b or abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))):
            out.append(f"{path}: {a} ≠ {b}")
    elif a != b:
        out.append(f"{path}: {a!r} ≠ {b!r}")
    return out


def run_node(js: str) -> dict:
    r = subprocess.run(["node", "-e", js], cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def test_band_equals_price_forecast_bands_on_registered_horizons():
    D = synth()
    cfg, S, _ = prepared(D)
    p = pd.Series(D["close"], index=pd.date_range(START, periods=len(D["close"]), freq="D"))
    checked = 0
    for k in (1, 2, 3, 4, 5, 6, 7, 30):
        B = pf.bands(p, k, cfg["forecast"])
        for t in range(1200, len(p), 61):
            b, ref = lk.band_at(D, S, t, k, cfg), B.iloc[t]
            if ref.isna().any():
                assert b is None or not np.isfinite(D["close"][t])
                continue
            assert b is not None
            for q in ("q10", "q25", "q50", "q75", "q90"):
                assert b[q] == pytest.approx(ref[q], rel=1e-12)
            checked += 1
    assert checked > 250


def test_browser_core_gives_the_same_numbers_and_never_looks_ahead():
    D = synth()
    cfg, S, F = prepared(D)
    L = page_json(D, cfg, F)
    # bản đổi giá sau ngày t của từng trường hợp: phần tại t phải giữ nguyên
    rng = np.random.default_rng(3)
    shocked = []
    for d, h in CASES:
        t = lk.index_of(D, d)
        L2 = copy.deepcopy(L)
        for key in ("close", "high", "low"):
            L2[key] = [v if v is None or i <= t else v * float(rng.uniform(0.5, 2.0)) for i, v in enumerate(L2[key])]
        shocked.append(L2)
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "lk.json").write_text(json.dumps(L), encoding="utf-8")
    (tmp / "shock.json").write_text(json.dumps(shocked), encoding="utf-8")
    cases = [[lk.index_of(D, d), h] for d, h in CASES]
    js = f"""
const fs = require('fs'); const K = require('./src/lookup.js');
const L = JSON.parse(fs.readFileSync({json.dumps(str(tmp / 'lk.json'))}, 'utf8')), SH = JSON.parse(fs.readFileSync({json.dumps(str(tmp / 'shock.json'))}, 'utf8'));
const P = K.prepare(L), cases = {json.dumps(cases)};
const look = cases.map(([t, h]) => K.lookup(P, t, h));
const shock = cases.map(([t, h], i) => K.lookup(K.prepare(SH[i]), t, h));
const check = {json.dumps(CHECK_H)}.map((h) => K.check(P, h));
process.stdout.write(JSON.stringify({{ look, shock, check }}));
"""
    out = run_node(js)
    for (t, h), got, sh in zip(cases, out["look"], out["shock"]):
        want = json.loads(json.dumps(lk.lookup(D, S, F, t, h, cfg)))
        diff = close_enough(want, got)
        assert not diff, (t, h, diff[:5])
        a, b = dict(got), dict(sh)
        a.pop("outcome"), b.pop("outcome")
        assert a == b, (t, h, "trình duyệt: giá sau ngày t làm đổi kết quả tại t")
    for h, got in zip(CHECK_H, out["check"]):
        want = json.loads(json.dumps(lk.check(D, S, h, cfg)))
        diff = close_enough(want, got)
        assert not diff, (h, diff[:5])
    assert sum(1 for x in out["look"] if x["outcome"]) >= 6 and sum(1 for x in out["look"] if x["band"]) >= 8


def _at_t(D: dict, t: int, h: int) -> dict:
    cfg, S, F = prepared(D)
    x = lk.lookup(D, S, F, t, h, cfg)
    x.pop("outcome")
    return json.loads(json.dumps(x))


def _assert_no_leak(D: dict, cases: list) -> None:
    rng = np.random.default_rng(11)
    for d, h in cases:
        t = lk.index_of(D, d)
        D2 = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in D.items()}
        for key in ("close", "high", "low"):
            D2[key][t + 1:] = D2[key][t + 1:] * rng.uniform(0.5, 2.0, len(D2[key]) - t - 1)
        assert _at_t(D, t, h) == _at_t(D2, t, h), (d, h)


LEAK_CASES = [("2016-06-01", 7), ("2018-02-10", 30), ("2020-03-12", 365), ("2021-01-01", 90)]


def test_python_never_looks_ahead():
    _assert_no_leak(synth(), LEAK_CASES)


def test_the_leak_check_catches_a_leaky_band(monkeypatch):
    """Cài thử lỗi nhìn trước (dải giá dùng giá ngày t + 1): bài kiểm tra trên phải bắt được."""
    real = lk.band_at

    def leaky(D, S, t, h, cfg):
        b = real(D, S, t, h, cfg)
        if b and t + 1 < len(D["close"]):
            b = {**b, "q50": float(D["close"][t + 1])}
        return b

    monkeypatch.setattr(lk, "band_at", leaky)
    with pytest.raises(AssertionError):
        _assert_no_leak(synth(), LEAK_CASES)


def test_hold_counts_only_buys_whose_outcome_is_known_at_t():
    D = synth()
    cfg, S, F = prepared(D)
    t, h = lk.index_of(D, "2019-07-01"), 365
    x = lk.hold_at(D, t, h, cfg["costs"])
    p, c = D["close"], cfg["costs"]
    g = [p[i + h] * (1 - c) / (p[i] * (1 + c)) - 1 for i in range(t - h - 1460, t - h + 1)]
    g = [v for v in g if np.isfinite(v)]
    assert x["n"] == len(g) and x["p"] == pytest.approx(np.mean([v > 0 for v in g]))
    assert x["n_eff"] == lk.rnd(len(g) / h)
    assert lk.hold_at(D, lk.index_of(D, "2012-01-01"), 365, c) is None      # chưa đủ 365 ngày mua đã biết kết quả


def test_feature_groups_follow_the_registered_cuts():
    D = synth()
    cfg, S, F = prepared(D)
    R = F["_raw"]
    for t in range(1500, len(D["close"]), 37):
        r7, g = R["r7"][t], F["r7"][t]
        if np.isfinite(r7):
            assert g == (0 if r7 <= -0.10 else 1 if r7 <= -0.03 else 2 if r7 < 0.03 else 3 if r7 < 0.10 else 4)
        if np.isfinite(R["dd"][t]):
            assert F["dd"][t] == (0 if R["dd"][t] < 0.2 else 1 if R["dd"][t] < 0.5 else 2)
        if np.isfinite(R["ma"][t]) and np.isfinite(D["close"][t]):
            assert F["ma200"][t] == (0 if D["close"][t] > R["ma"][t] else 1)
    assert set(np.unique(F["vol"][F["vol"] >= 0])) == {0, 1, 2}


def _row(p_holm, diff, halves, n_eff=200, half_n=50):
    return {"p_holm": p_holm, "diff": diff, "cond": {"n_eff": n_eff},
            "halves": [{"diff": d, "cond": {"n_eff": half_n}} for d in halves]}


def test_verdict_needs_holm_and_the_same_sign_in_both_halves():
    assert lk.verdict(_row(0.01, 0.08, [0.05, 0.1])) == "hon"
    assert lk.verdict(_row(0.01, -0.08, [-0.05, -0.1])) == "kem"
    assert lk.verdict(_row(0.01, 0.08, [0.05, -0.01])) == "nhu_bat_ky"
    assert lk.verdict(_row(0.2, 0.08, [0.05, 0.1])) == "nhu_bat_ky"
    assert lk.verdict(_row(0.001, 0.2, [0.2, 0.2], n_eff=29)) == "it_du_lieu"
    assert lk.verdict(_row(0.001, 0.2, [0.2, 0.2], half_n=4)) == "it_du_lieu"
    rows = [{"p_value": v} for v in (0.01, 0.04, None, 0.03)]
    lk.holm(rows)
    assert [r["p_holm"] for r in rows] == [pytest.approx(0.03), pytest.approx(0.06), None, pytest.approx(0.06)]


def test_research_counts_every_registered_test():
    D = synth()
    cfg, S, F = prepared(D)
    res = lk.research(D, F, cfg)
    assert res["tests"] == 72 == len(res["rows"])
    assert sum(res["summary"].values()) == 72
    for r in res["rows"]:
        assert r["cond"]["n"] + r["rest"]["n"] > 0 and r["verdict"] in ("hon", "kem", "nhu_bat_ky", "it_du_lieu")
    assert lk.rnd(2.5) == 3 and lk.rnd(3.5) == 4                              # nửa lên như Math.round của trang
