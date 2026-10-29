# -*- coding: utf-8 -*-
"""Part H tests: the forward log only appends; a change of code, config or frozen state stops logging and a new freeze
starts a new log; rows never use data after their Sunday; the frozen model is not refitted; scoring uses matured rows only."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from bot.features import weekly_close as wc
from bot.models import forward as fw
from tests.test_scenarios import synth

T0 = pd.Timestamp("2020-06-28")
WEEK = pd.Timedelta(weeks=1)


def table_fn(s):
    return lambda asof: wc.build(s["cm"], s["ext"], s["fng"], s["fed"], end=asof)


@pytest.fixture(scope="module")
def data():
    return synth()


def run_log(root, fn, weeks, start=T0):
    out = []
    for k in range(weeks):
        d = start + k * WEEK
        out.append(fw.log_week(root, d, fn, now=d + pd.Timedelta(days=1)))
    return out


def test_log_is_append_only_idempotent_and_frozen(tmp_path, data):
    fn = table_fn(data)
    vid, created = fw.freeze(tmp_path, T0, fn, mode="test", now=T0 + pd.Timedelta(days=1))
    assert created and (tmp_path / vid / "forward_log.csv").exists()
    assert fw.freeze(tmp_path, T0, fn, mode="test", now=T0 + pd.Timedelta(days=1)) == (vid, False)  # same hash: no second version
    run_log(tmp_path, fn, 3)
    path = tmp_path / vid / "forward_log.csv"
    first = path.read_bytes()
    assert fw.log_week(tmp_path, T0 + WEEK, fn) is None and path.read_bytes() == first  # already logged
    run_log(tmp_path, fn, 3, T0 + 3 * WEEK)
    assert path.read_bytes().startswith(first)  # earlier rows untouched
    log = fw.read_log(tmp_path / vid)
    assert list(log.columns) == fw.COLUMNS and len(log) == 6 and set(log["model_version"]) == {vid} and set(log["late"]) == {"0"}
    m = json.loads((tmp_path / vid / "model.json").read_text(encoding="utf-8"))
    t = fn(T0 + 5 * WEEK)
    assert log["score"].iloc[-1] == fw._fmt(fw._predict(m["state"]["fit"], t.iloc[-1]))  # frozen weights, no refit


def test_change_stops_logging_and_a_new_version_starts_a_new_log(tmp_path, data, monkeypatch):
    fn = table_fn(data)
    v1, _ = fw.freeze(tmp_path, T0, fn, now=T0 + pd.Timedelta(days=1))
    run_log(tmp_path, fn, 2)
    before = (tmp_path / v1 / "forward_log.csv").read_bytes()
    real = fw.config_part
    monkeypatch.setattr(fw, "config_part", lambda: {**real(), "zones": {**real()["zones"], "hysteresis": 7}})
    with pytest.raises(fw.ModelChanged, match="config.zones"):
        fw.log_week(tmp_path, T0 + 2 * WEEK, fn)
    v2, created = fw.freeze(tmp_path, T0 + 2 * WEEK, fn, now=T0 + 2 * WEEK + pd.Timedelta(days=1))
    assert created and v2 != v1 and v2.startswith("v2-")
    assert fw.log_week(tmp_path, T0 + 2 * WEEK, fn, now=T0 + 2 * WEEK + pd.Timedelta(days=1))["model_version"] == v2
    assert (tmp_path / v1 / "forward_log.csv").read_bytes() == before and len(fw.read_log(tmp_path / v2)) == 1


def test_tampered_state_and_line_endings(tmp_path, data, monkeypatch):
    fn = table_fn(data)
    vid, _ = fw.freeze(tmp_path, T0, fn, now=T0 + pd.Timedelta(days=1))
    p = tmp_path / vid / "model.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    m["state"]["gate"] = "dat_phan_i"  # pretend Part I passed without a new version
    p.write_text(json.dumps(m), encoding="utf-8")
    assert fw.check(tmp_path / vid) == ["model.json"]
    lf = fw._sha(b"a\nb\n")
    assert fw._sha(b"a\r\nb\r\n".replace(b"\r\n", b"\n")) == lf


def test_rows_never_use_data_after_their_sunday_and_late_flag(tmp_path, data):
    a_root, b_root = tmp_path / "a", tmp_path / "b"
    cut = T0 + 3 * WEEK
    changed = {k: (v.assign(**{c: v[c].where(v["date"] <= cut, v[c] * 5) for c in v.columns if c != "date"}) if v is not None else v)
               for k, v in data.items()}
    fw.freeze(a_root, T0, table_fn(data), now=T0 + pd.Timedelta(days=1))
    fw.freeze(b_root, T0, table_fn(changed), now=T0 + pd.Timedelta(days=1))
    run_log(a_root, table_fn(data), 4)
    run_log(b_root, table_fn(changed), 4)
    a, b = fw.read_log(fw.current(a_root)), fw.read_log(fw.current(b_root))
    pd.testing.assert_frame_equal(a.drop(columns="model_version"), b.drop(columns="model_version"))
    late = fw.log_week(a_root, T0 + 4 * WEEK, table_fn(data), now=T0 + 4 * WEEK + pd.Timedelta(days=8))
    assert late["late"] == "1"


def test_score_counts_only_matured_rows(tmp_path, data):
    fn = table_fn(data)
    vid, _ = fw.freeze(tmp_path, T0, fn, now=T0 + pd.Timedelta(days=1))
    run_log(tmp_path, fn, 30)
    end = T0 + 40 * WEEK
    t = fn(end)
    res = fw.score(tmp_path / vid, t, [4, 26], n_boot=200, seed=1, gap=4)
    ex = t["exec_monday"]
    dates = [T0 + k * WEEK for k in range(30)]
    for h in (4, 26):
        want = sum(np.isfinite(ex.get(d, np.nan)) and np.isfinite(ex.get(d + h * WEEK, np.nan)) for d in dates)
        assert res["matured"][h] == want
    assert res["matured"][26] < 30 and res["rows"] == 30


def test_frozen_fit_is_used_and_logging_never_refits(tmp_path, data, monkeypatch):
    from bot.models import wf_logit as wf
    fit = wf.Fit(["mvrv", "p_200wma"], np.array([0.8, 0.3]), 0.1, np.array([0.5, 0.5]), np.array([0.3, 0.3]), [], 1.0)
    monkeypatch.setattr(fw.wf, "freeze_fit", lambda *a, **k: ("S1", fit, 0.6))
    fn = table_fn(data)
    vid, _ = fw.freeze(tmp_path, T0, fn, now=T0 + pd.Timedelta(days=1))

    def boom(*a, **k):
        raise AssertionError("refit during logging")
    for name in ("freeze_fit", "nested_oos", "fit_signed", "config_oos"):
        monkeypatch.setattr(fw.wf, name, boom)
    run_log(tmp_path, fn, 20)
    log = fw.read_log(tmp_path / vid)
    for k in (0, 7, 19):
        t = fn(T0 + k * WEEK)
        want = wf.predict(fit, t[["cheap_mvrv", "cheap_p_200wma"]].to_numpy(dtype=float)[-1:], ["mvrv", "p_200wma"])[0]
        assert abs(float(log["score"].iloc[k]) - want) < 1e-6
    assert (log["rank"] != "").sum() >= 5 and set(log["zone"][log["rank"] != ""]) <= {"phai", "cannhac", "khong"}
