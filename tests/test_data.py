# -*- coding: utf-8 -*-
"""Data layer tests with small inline fixtures (no network)."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from bot.data import pit_store, quality
from bot.data.fetchers import alternative, binance, coinmetrics, defillama, events, fred
from bot.i18n import fmt


def test_coinmetrics_parse_derives_realized_cap():
    rows = [{"time": "2026-10-25T00:00:00.000000000Z", "PriceUSD": "80000", "CapMrktCurUSD": "1600", "CapMVRVCur": "1.6", "HashRate": "1e9", "IssTotUSD": "4e7"},
            {"time": "2026-10-26T00:00:00.000000000Z", "PriceUSD": "81000", "CapMrktCurUSD": None, "CapMVRVCur": None, "HashRate": "1e9", "IssTotUSD": "4e7"}]
    df = coinmetrics.parse(rows)
    assert list(df["date"].dt.strftime("%Y-%m-%d")) == ["2026-10-25", "2026-10-26"]
    assert df["realized_cap"].iloc[0] == pytest.approx(1000) and np.isnan(df["realized_cap"].iloc[1])


def test_other_parsers():
    f = alternative.parse([{"value": "30", "timestamp": "1793145600"}, {"value": "25", "timestamp": "1793059200"}])
    assert list(f["fng"]) == [25, 30] and f["date"].is_monotonic_increasing
    fr = binance.parse_funding([{"fundingTime": 1568102400000, "fundingRate": "0.00010000"}])
    assert fr["funding_rate"].iloc[0] == pytest.approx(1e-4)
    oi = binance.parse_oi([{"timestamp": 1793059200000, "sumOpenInterest": "95514.1", "sumOpenInterestValue": "7652201416.5"}])
    assert oi["oi_usd"].iloc[0] == pytest.approx(7652201416.5)
    st = defillama.parse([{"date": "1511913600", "totalCirculatingUSD": {"peggedUSD": 110105}}])
    assert st["stable_usd"].iloc[0] == 110105
    fd = fred.parse_csv("observation_date,DFII10\n2026-10-23,1.85\n2026-10-26,\n", "DFII10")
    assert len(fd) == 1 and fd["real_yield_10y"].iloc[0] == 1.85


def test_event_parsers_and_rules():
    cal = ('<h4><a id="1">2026 FOMC Meetings</a></h4><div class="fomc-meeting__month x"><strong>Jan/Feb</strong></div>'
           '<div class="fomc-meeting__date y">31-1</div><div class="fomc-meeting__month x"><strong>March</strong></div>'
           '<div class="fomc-meeting__date y">17-18*</div><div class="fomc-meeting__month x"><strong>May</strong></div>'
           '<div class="fomc-meeting__date y">22 (notation vote)</div>')
    assert events.parse_fomc_calendar(cal) == [dt.date(2026, 2, 1), dt.date(2026, 3, 18)]
    hist = ('<h5 class="a">July 31-August 1  Meeting - 2012</h5><h5 class="a">August 1 Conference Call - 2011</h5>'
            '<h5 class="a">March 2 (unscheduled) Meeting - 2020</h5><h5 class="a">April/May 30-1 Meeting - 2013</h5>')
    assert events.parse_fomc_historical(hist) == [dt.date(2012, 8, 1), dt.date(2013, 5, 1)]
    assert events.parse_cpi_archive('<a href="/news.release/archives/cpi_10142026.htm">') == [dt.date(2026, 10, 14)]
    assert events.options_expiry(dt.date(2026, 10, 1), dt.date(2026, 12, 31)) == ["2026-10-30T08:00Z", "2026-11-27T08:00Z", "2026-12-25T08:00Z"]
    assert events.et_to_utc(dt.date(2026, 7, 29), 14, 0) == "2026-07-29T18:00Z"   # daylight saving
    assert events.et_to_utc(dt.date(2026, 12, 9), 14, 0) == "2026-12-09T19:00Z"


def _daily(n: int, end: str = "2026-10-27", start_val: float = 100.0) -> pd.DataFrame:
    d = pd.date_range(end=end, periods=n, freq="D")
    return pd.DataFrame({"date": d, "price": start_val * np.exp(np.linspace(0, 0.1, n))})


def test_snapshots_are_immutable_and_merge(tmp_path):
    full = _daily(200)
    p1 = pit_store.save_snapshot("cm", full, dt.date(2026, 10, 27), root=tmp_path)
    assert p1 is not None and pit_store.save_snapshot("cm", full.iloc[:10], dt.date(2026, 10, 27), root=tmp_path) is None
    later = _daily(201, end="2026-10-28")
    later.loc[later.index[-2], "price"] = 999.0  # a revision of 27/10
    pit_store.save_snapshot("cm", later, dt.date(2026, 10, 28), root=tmp_path)
    assert len(pd.read_parquet(tmp_path / "cm" / "2026-10-28.parquet")) <= pit_store.RECENT_DAYS + 1  # only recent rows
    h = pit_store.load_history("cm", root=tmp_path)
    assert len(h) == 201 and h["price"].iloc[-2] == 999.0
    assert h["first_seen"].iloc[-1] == pd.Timestamp("2026-10-28") and h["first_seen"].iloc[0] == pd.Timestamp("2026-10-27")
    old = pit_store.load_history("cm", root=tmp_path, as_of_snapshot=dt.date(2026, 10, 27))
    assert len(old) == 200 and old["price"].iloc[-1] != 999.0


def test_available_at_uses_publication_lag():
    df = pit_store.with_available_at(_daily(3), "coinmetrics")
    assert df["available_at"].iloc[-1] == pd.Timestamp("2026-10-29")  # day 27 ends 28th 00:00, +1 day lag
    m = pit_store.with_available_at(pd.DataFrame({"date": pd.to_datetime(["2026-09-01"]), "m2": [1.0]}), "fred_monthly", freq="M")
    assert m["available_at"].iloc[0] == pd.Timestamp("2026-10-01") + pd.Timedelta(days=45)
    assert list(pit_store.asof(df, pd.Timestamp("2026-10-28T01:00"))["date"].dt.day) == [25, 26]  # 27th not yet published


def test_quality_flags_problems():
    now = dt.datetime(2026, 10, 28, 1)
    good = _daily(400)
    assert quality.check(good, "x", ["price"], now=now).ok
    dup = pd.concat([good, good.iloc[[-1]]], ignore_index=True)
    assert any("trùng" in e for e in quality.check(dup, "x", ["price"], now=now).errors)
    rev = good.iloc[::-1].reset_index(drop=True)
    assert not quality.check(rev, "x", ["price"], now=now).ok
    gap = good.drop(index=range(100, 105)).reset_index(drop=True)
    assert any("khoảng trống" in w for w in quality.check(gap, "x", ["price"], now=now).warnings)
    spike = good.copy()
    spike.loc[200, "price"] *= 3
    r = quality.check(spike, "x", ["price"], now=now)
    assert r.ok and any("5σ" in w for w in r.warnings) and len(spike) == len(good)  # flagged, not removed
    stale = quality.check(_daily(400, end="2026-10-20"), "x", ["price"], now=now)
    assert not stale.ok and any("cũ" in e for e in stale.errors)


def test_vi_formats():
    assert fmt.usd(80754.4) == "80.754 $" and fmt.dec(0.49) == "0,49" and fmt.dec(1.37) == "1,37"
    assert fmt.pct(0.79) == "79%" and fmt.pct(-0.05) == "-5%" and fmt.pct(0.19, sign=True) == "+19%"
    assert fmt.date(dt.date(2026, 10, 28)) == "28/10/2026"
    assert fmt.datetime_vn("2026-10-28T18:00Z") == "01:00 29/10/2026"
    assert fmt.btc(0.0248) == "0,0248 BTC" and fmt.btc(0.00012345) == "0,000123 BTC"
    assert fmt.usd(None) == "—" and fmt.num(1234567.891, 2) == "1.234.567,89"


def test_new_source_parsers():
    from bot.data.fetchers import bitstamp, coingecko, coinmetrics_ext
    b = bitstamp.parse([{"timestamp": "1313625600", "open": "10.90", "high": "10.90", "low": "10.90", "close": "10.90", "volume": "0.49"}])
    assert b["date"].iloc[0] == pd.Timestamp("2011-08-18") and b["close"].iloc[0] == 10.9
    g = coingecko.parse({"prices": [[1793232000000, 81274.4], [1793238810000, 80095.3]]})  # 29/10 00:00 = close of 28/10; later point dropped
    assert list(g["date"]) == [pd.Timestamp("2026-10-28")] and g["price"].iloc[0] == 81274.4
    e = coinmetrics_ext.parse([{"time": "2026-10-27T00:00:00.000000000Z", "AssetEODCompletionTime": "1793155778", "volume_reported_spot_usd_1d": "6.0e9",
                                "SplyCur": "2.0e7", "IssTotNtv": "450"}])
    assert e["eod_completed_at"].iloc[0] == pd.Timestamp("2026-10-28 02:49:38") and e["volume_spot_usd"].iloc[0] == 6e9


def test_fed_regime_from_six_month_change():
    from bot.features import weekly_close as wc
    days = pd.date_range("2024-01-01", "2026-10-25", freq="D")
    rate = np.where(days < "2025-01-01", 5.5, np.where(days < "2026-01-01", 4.5, 4.5))
    fed = pd.DataFrame({"date": days, "fed_upper": rate})
    sundays = pd.DatetimeIndex(["2024-12-29", "2025-03-02", "2025-08-03", "2026-10-25"])
    assert list(wc.fed_regime(fed, sundays)) == ["giu", "giam", "giu", "giu"]
