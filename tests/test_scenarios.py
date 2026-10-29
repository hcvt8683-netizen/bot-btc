# -*- coding: utf-8 -*-
"""Part F tests: a scenario that follows the real path reproduces the real table; scenarios never read data after the
analysis date; the Fear & Greed response model recovers a known relation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.features import weekly_close as wc
from bot.models import scenarios as sc

ASOF = pd.Timestamp("2020-06-28")  # a Sunday


def synth(n=4000, seed=2):
    rng = np.random.default_rng(seed)
    d = pd.date_range("2012-01-01", periods=n, freq="D")
    p = 50 * np.exp(np.cumsum(rng.normal(0.001, 0.035, n)))
    supply, rc = 1.8e7, 3e10  # held constant, as the scenario assumes
    cm = pd.DataFrame({"date": d, "price": p, "mcap": p * supply, "mvrv": p * supply / rc, "hashrate": 5.0, "iss_usd": 900 * p})
    ext = pd.DataFrame({"date": d, "volume_spot_usd": 1e9, "supply": supply, "iss_btc": 900.0})
    m = d >= "2018-02-01"
    fng = pd.DataFrame({"date": d[m], "fng": np.clip(50 + 400 * np.log(p[m] / pd.Series(p).rolling(30, min_periods=1).mean().to_numpy()[m]), 1, 99)})
    fed = pd.DataFrame({"date": d, "fed_upper": 1.0})
    return {"cm": cm, "ext": ext, "fng": fng, "fed": fed}


def test_scenario_on_the_real_path_equals_the_real_table():
    s = synth()
    real = wc.build(s["cm"], s["ext"], s["fng"], s["fed"])
    k = 4
    days = pd.date_range(ASOF + pd.Timedelta(days=1), periods=7 * k, freq="D")
    path = s["cm"].set_index("date")["price"].reindex(days).to_numpy()
    fpath = s["fng"].set_index("date")["fng"].reindex(days).to_numpy()
    row = sc.scenario_row(s, ASOF, 0.0, k, price_path=path, fng_path=fpath)
    target = real.loc[ASOF + pd.Timedelta(weeks=k)]
    cols = [c for c in real.columns if c.startswith(("raw_", "pct_", "cheap_")) and "vol_rel" not in c]
    pd.testing.assert_series_equal(row[cols].astype(float), target[cols].astype(float), check_names=False, rtol=1e-9)


def test_scenarios_never_read_after_the_analysis_date():
    s = synth()
    a = sc.scenario_row(s, ASOF, -0.2, 2, fng_end=30.0)
    changed = {k: (v.assign(**{c: v[c].where(v["date"] <= ASOF, v[c] * 5) for c in v.columns if c != "date"}) if v is not None else v) for k, v in s.items()}
    b = sc.scenario_row(changed, ASOF, -0.2, 2, fng_end=30.0)
    pd.testing.assert_series_equal(a, b)


def test_fng_response_recovers_positive_price_sensitivity():
    s = synth()
    t = wc.build(s["cm"], s["ext"], s["fng"], s["fed"])
    m = sc.fng_response(t, 4)
    assert m["b"] > 0 and m["n"] > 100 and m["q"][0] < 0 < m["q"][1]
    lo, mid, hi = sc.fng_predict(m, 50, -0.2)
    assert lo <= mid <= hi and mid < 50  # a 20% fall lowers F&G
