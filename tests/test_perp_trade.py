# -*- coding: utf-8 -*-
"""Long/Short with entry, stop-loss and take-profit (bot/models/perp_trade.py): features and signals use only data up to
t (and a planted look-ahead is caught), every outcome matches a plain candle-by-candle loop of the registered rules
(stop wins a tie, a limit order fills at its price and only checks the stop in its fill candle, funding inside the
holding window), one position at a time, the monthly pick only sees trades closed before the month (a planted
look-ahead is caught), the verdict rule, and the append-only log."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.models import perp_signal as ps
from bot.models import perp_trade as pt

CFG = pt.spec()


@pytest.fixture(autouse=True)
def short_windows(monkeypatch):
    """Percentiles over 30 days (at least 10), trend over 3 days, ATR over 5 days: enough for 120 days of fake candles."""
    monkeypatch.setattr(pt, "LOOKBACK", 30 * 24)
    monkeypatch.setattr(pt, "MIN_HIST", 10 * 24)
    monkeypatch.setattr(pt, "TREND", 72)
    monkeypatch.setattr(pt, "ATR_DAYS", 5)


def walk_candles(days=120, seed=3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = days * 24
    close = 100 * np.exp(np.cumsum(rng.normal(0.0001, 0.006, n)))
    prev = np.r_[close[0], close[:-1]]
    hi = np.maximum(prev, close) * np.exp(np.abs(rng.normal(0, 0.003, n)))
    lo = np.minimum(prev, close) * np.exp(-np.abs(rng.normal(0, 0.003, n)))
    return pd.DataFrame({"high": hi, "low": lo, "close": close}, index=pd.date_range("2024-01-01 01:00", periods=n, freq="h"))


def fund(index: pd.DatetimeIndex, seed=7) -> tuple[pd.Series, pd.Series]:
    rng = np.random.default_rng(seed)
    mark = pd.Series((index.hour % 8 == 0).astype(float), index=index)
    return pd.Series(np.where(mark > 0, rng.normal(1e-4, 3e-4, len(index)), 0.0), index=index), mark


def make(h: pd.DataFrame, rate: pd.Series, mark: pd.Series) -> dict:
    f24 = ps.funding_24h(rate, mark, rate.index[-1])
    F = pt.features(h, f24)
    book = pt.Book(h, rate, rate.index[-1], CFG)
    book.prepare(F["atr"].to_numpy(dtype=float))
    return {"F": F, "book": book, "sigs": pt.signals(F)}


def test_features_and_signals_use_only_data_up_to_t():
    h = walk_candles()
    rate, mark = fund(h.index)
    T = h.index[1800]
    a = make(h, rate, mark)
    i = h.index.get_loc(T)
    for crash in (0.4, 2.5):                 # every later candle falls, or jumps (a max and a min must both stay put)
        e, r2 = h.copy(), rate.copy()
        e.loc[e.index > T] *= crash
        r2.loc[r2.index > T] *= -30
        b = make(e, r2, mark)
        pd.testing.assert_frame_equal(a["F"].loc[:T], b["F"].loc[:T])
        for k in a["sigs"]:
            assert (a["sigs"][k][:i + 1] == b["sigs"][k][:i + 1]).all(), k
    assert a["F"].loc[T].notna().all()
    assert sum(a["sigs"][k][:i + 1].sum() for k in a["sigs"] if k[0] != "moc") > 50


def test_a_planted_look_ahead_is_caught(monkeypatch):
    """Percentiles from a window centred on t (it sees the future) must make the check above fail."""
    monkeypatch.setattr(ps, "_past_q", lambda x, q, w, minp: x.rolling(w, min_periods=minp, center=True).quantile(q))
    with pytest.raises(AssertionError):
        test_features_and_signals_use_only_data_up_to_t()


def brute(h: pd.DataFrame, rate: np.ndarray, atr: np.ndarray, t: int, rule: pt.Rule) -> tuple[int, int, float]:
    """The registered rules, one candle at a time: (kind, exit position, net) with kind −1 when not known yet."""
    c, hi, lo = (h[k].to_numpy() for k in ("close", "high", "low"))
    N, long_, nb = len(c), rule.side == "long", int(CFG["limit_bars"])
    sgn = 1 if long_ else -1
    cost = 2 * (CFG["costs"]["fee"] + CFG["costs"]["slippage"])
    if rule.entry == "ngay":
        e, f = c[t], 0
    else:
        e, f = c[t] * (1 - sgn * CFG["limit_atr"] * atr[t]), None
        for j in range(1, nb + 1):
            if t + j >= N:
                return -1, 0, np.nan
            if (lo[t + j] <= e) if long_ else (hi[t + j] >= e):
                f = j
                break
        if f is None:
            return 3, t + nb, np.nan
    s = rule.k * atr[t]
    sl, tp = e * (1 - sgn * s), e * (1 + sgn * rule.r * s)
    kind, px, j = 2, None, f + rule.h
    for jj in range(max(f, 1), f + rule.h + 1):
        if t + jj >= N:
            return -1, 0, np.nan
        if (lo[t + jj] <= sl) if long_ else (hi[t + jj] >= sl):
            kind, px, j = 0, sl, jj
            break
        if jj >= f + 1 and ((hi[t + jj] >= tp) if long_ else (lo[t + jj] <= tp)):
            kind, px, j = 1, tp, jj
            break
    if t + j >= N:
        return -1, 0, np.nan
    px = c[t + j] if px is None else px
    paid = rate[t + max(f - 1, 0) + 1:t + j + 1].sum()
    return kind, t + j, sgn * (px / e - 1) - cost - sgn * paid


@pytest.mark.parametrize("rule", [pt.Rule("moc", "long", "ngay", 1.0, 2.0, 24), pt.Rule("moc", "short", "ngay", 0.5, 3.0, 72),
                                  pt.Rule("moc", "long", "cho", 1.5, 1.0, 24), pt.Rule("moc", "short", "cho", 2.0, 1.5, 168)])
def test_outcomes_match_a_plain_loop(rule):
    h = walk_candles(days=40, seed=11)
    rate, mark = fund(h.index)
    m = make(h, rate, mark)
    atr = m["F"]["atr"].to_numpy()
    oc = m["book"].oc(rule.combo)
    seen = set()
    for t in range(130, len(h)):
        k, ex, net = brute(h, rate.to_numpy(), atr, t, rule)
        assert oc["kind"][t] == k, (t, k)
        seen.add(k)
        if k >= 0:
            assert oc["exit"][t] == ex, t
        if k in (0, 1, 2):
            assert oc["net"][t] == pytest.approx(net, abs=1e-12), t
            assert oc["R"][t] == pytest.approx(net / (rule.k * atr[t]), abs=1e-9)
    assert -1 in seen and len(seen & {0, 1, 2}) >= 2
    if rule.entry == "cho":
        assert 3 in seen


def test_a_candle_touching_both_counts_as_the_stop():
    idx = pd.date_range("2024-01-01 01:00", periods=40, freq="h")
    h = pd.DataFrame({"high": 100.5, "low": 99.5, "close": 100.0}, index=idx)
    h.iloc[25, [0, 1]] = [130.0, 70.0]                      # one huge candle
    rate = pd.Series(0.0, index=idx)
    book = pt.Book(h, rate, idx[-1], CFG)
    book.prepare(np.full(len(h), 0.02))
    oc = book.oc(("long", "ngay", 1.0, 1.0, 24))
    assert oc["kind"][20] == 0 and oc["exit"][20] == 25
    assert oc["net"][20] == pytest.approx(-0.02 - 2 * (CFG["costs"]["fee"] + CFG["costs"]["slippage"]))


def test_one_position_at_a_time():
    h = walk_candles()
    rate, mark = fund(h.index)
    m = make(h, rate, mark)
    for rule in [pt.Rule("moc", "long", "ngay", 0.5, 1.0, 24), pt.Rule("xu_huong", "short", "cho", 1.0, 2.0, 72)]:
        oc = m["book"].oc(rule.combo)
        pos, _, _ = pt.walk(m["sigs"][(rule.sig, rule.side)], oc)
        assert len(pos) > 5
        ex = oc["exit"][pos]
        assert (np.asarray(pos[1:]) >= ex[:-1]).all()
        assert all(m["sigs"][(rule.sig, rule.side)][p] for p in pos)


def _picks(h: pd.DataFrame, rate: pd.Series, mark: pd.Series, cfg: dict) -> dict:
    m = make(h, rate, mark)
    rs = pt.rules(cfg)
    trades = pt.standalone(m["book"], m["sigs"], rs)
    out = {}
    for month in pd.date_range("2024-03-01", "2024-04-01", freq="MS"):
        at = int(h.index.searchsorted(month, side="right")) - 1
        r, t, n, best = pt.pick(trades, rs, at, cfg)
        out[month] = (best.id if best else None, t, n)
    return out


def test_the_monthly_pick_only_sees_trades_closed_before_the_month(monkeypatch):
    cfg = {**CFG, "select": {**CFG["select"], "min_trades": 5}, "stop_atr": [0.5, 1], "target_r": [1, 2], "max_hold_hours": [24]}
    monkeypatch.setattr(pt, "SIGNALS", pt.SIGNALS)
    h = walk_candles()
    rate, mark = fund(h.index)
    S = pd.Timestamp("2024-04-01")
    e = h.copy()
    e.loc[e.index > S] *= np.linspace(1.5, 0.5, int((e.index > S).sum()))[:, None]
    a, b = _picks(h, rate, mark, cfg), _picks(e, rate, mark, cfg)
    assert a == b and all(v[0] for v in a.values())
    real = pt.pick
    monkeypatch.setattr(pt, "pick", lambda trades, rs, at, c: real(trades, rs, len(h), c))   # sees every trade: look-ahead
    assert _picks(h, rate, mark, cfg) != _picks(e, rate, mark, cfg)


def test_registered_verdict():
    good = {"n": 150}
    halves = [{"n": 70, "meanR": 0.1}, {"n": 80, "meanR": 0.05}]
    assert pt.verdict(good, [0.01, 0.3], halves, CFG)
    assert not pt.verdict(good, [-0.01, 0.3], halves, CFG)
    assert not pt.verdict({"n": 99}, [0.01, 0.3], halves, CFG)
    assert not pt.verdict(good, [0.01, 0.3], [halves[0], {"n": 80, "meanR": -0.01}], CFG)


def test_rule_family_is_the_registered_one():
    rs = pt.rules(CFG)
    assert len(rs) == 1152 and len({r.id for r in rs}) == 1152 and len(pt.rules(CFG, ("moc",))) == 192
    assert rs[0].id == "moc|long|ngay|0.5|1|24" and pt.parse(rs[-1].id) == rs[-1]


def test_log_is_append_only(tmp_path):
    p = tmp_path / "log.csv"
    cur = {"month": "2026-11", "rule": {"id": "xu_huong|long|ngay|2|2|168"}, "t": 2.3, "n_train": 265}
    res = {"version": "v1", "current": cur,
           "sides": {"long": {"current": cur}, "short": {"current": {**cur, "rule": None, "t": 1.4, "n_train": 300}}}}
    now = pd.Timestamp("2026-11-02 10:00")
    assert len(pt.log_month(res, now, p)) == 3
    assert pt.log_month(res, now, p) == []
    assert len(pt.log_month({**res, "version": "v2"}, now, p)) == 3
    assert pt.log_month(res, pd.Timestamp("2026-12-01 01:00"), p) == []      # the picks of November are not written in December
    rows = pt.read_log(p)
    assert [r["version"] for r in rows] == ["v1"] * 3 + ["v2"] * 3
    assert [r["scope"] for r in rows[:3]] == ["tat_ca", "long", "short"] and rows[0]["rule"] == "xu_huong|long|ngay|2|2|168" and rows[2]["rule"] == ""


def test_checklist_static_criteria():
    side = {"n": 120, "boot": [0.01, 0.3], "halves": [{"n": 60, "meanR": 0.1}, {"n": 60, "meanR": 0.02}]}
    assert pt.checklist_static(side, {"rule": {"id": "x"}}) == {"c1": True, "c2": True, "c3": True, "c4": True}
    bad = {"n": 99, "boot": [-0.01, 0.3], "halves": [{"n": 60, "meanR": 0.1}, {"n": 39, "meanR": -0.02}]}
    assert pt.checklist_static(bad, {"rule": None}) == {"c1": False, "c2": False, "c3": False, "c4": False}


def test_hold_view_matches_the_rule_at_its_own_hold():
    """The page's hold picker: at the rule's own hold the numbers are the rule's; shares add up at every hold."""
    h = walk_candles()
    rate, mark = fund(h.index)
    m = make(h, rate, mark)
    rule = pt.Rule("xu_huong", "long", "cho", 1.0, 1.5, 72)
    v = pt.hold_view(m["book"], m["sigs"], rule, [1, 6, 24, 72, 168])
    oc = m["book"].oc(rule.combo)
    pos, _, _ = pt.walk(m["sigs"][("xu_huong", "long")], oc)
    st = pt.trade_stats(pt.trade_table(pos, oc, m["book"], rule))
    i = v["h"].index(72)
    assert v["n"][i] == st["n"] > 5 and v["p"][i] == pytest.approx(st["p"]) and v["meanR"][i] == pytest.approx(st["meanR"])
    for j in range(len(v["h"])):
        if v["n"][j]:
            assert v["p"][j] == pytest.approx(v["p_tp"][j] + v["p_tw"][j])
            assert v["lo"][j] <= v["p"][j] <= v["hi"][j]
    assert v["p_tp"][0] < v["p_tp"][-1]                   # 1 hour is rarely enough to reach the target
    assert (1, 6) not in [c[:1] for c in m["book"]._oc]   # one-off holds are not cached


def test_checklist_history_only_uses_trades_closed_before_each_month():
    """The past table: a month's score comes from trades closed before it, so later trades never change it."""
    months = list(pd.date_range("2024-01-01", periods=4, freq="MS"))
    t = pd.to_datetime(["2024-01-05", "2024-02-03", "2024-03-10", "2024-04-02"])
    wf = pd.DataFrame({"t": t, "exit_t": t + pd.Timedelta(days=2), "net": [0.01, -0.01, 0.02, 0.03], "R": [1.0, -1.0, 2.0, 3.0], "kind": [1, 0, 1, 1],
                       "hours": [48] * 4, "rule": ["x"] * 4, "exit_pos": [1, 2, 3, 4]})
    sel = {m: {"rule": pt.Rule("moc", "long", "ngay", 1, 1, 24)} for m in months}
    h = pt.checklist_history(wf, sel, months, CFG)
    assert h["full"] == 0 and h["max"] == 4                    # April: c1, c4 (Jan +1R | Feb −1R, Mar +2R), c5, c6; never 100 trades
    assert sum(x["n"] for x in h["by_score"]) == 4
    late = wf.copy()
    late.loc[3, ["net", "R"]] = [-0.5, -50.0]                   # the last trade (April) is changed
    h2 = pt.checklist_history(late, sel, months, CFG)
    assert [x["score"] for x in h2["by_score"]] == [x["score"] for x in h["by_score"]]
