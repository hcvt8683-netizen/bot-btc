# -*- coding: utf-8 -*-
"""Data layer tests with small inline fixtures (no network)."""
from __future__ import annotations

import datetime as dt
import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from bot.data import http, pit_store, quality, update
from bot.data.fetchers import alternative, binance, binance_vision, coinmetrics, defillama, events, fred
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


def _zip(name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, text)
    return buf.getvalue()


def _archive(monkeypatch, files: dict[str, bytes]) -> list[str]:
    """Fake data.binance.vision: listed URLs answer, every other file is not published yet (HTTP 404)."""
    asked: list[str] = []

    def get(url: str, **kw) -> bytes:
        asked.append(url)
        if url in files:
            return files[url]
        raise http.FetchError(url, "HTTP 404", 404)
    monkeypatch.setattr(http, "get", get)
    return asked


def test_archive_funding_same_rows_as_api(monkeypatch):
    # rows copied from BTCUSDT-fundingRate-2026-10.zip (unsorted here); September is not "published"
    oct_ = binance_vision.FUNDING.format(month="2026-10")
    csv = "calc_time,funding_interval_hours,last_funding_rate\n1793462400000,8,0.00010000\n1790812800001,8,0.00007981\n"
    asked = _archive(monkeypatch, {oct_: _zip("f.csv", csv)})
    f = binance_vision.fetch_funding(today=dt.date(2026, 11, 2))
    assert asked == [binance_vision.FUNDING.format(month="2026-09"), oct_]
    api = binance.parse_funding([{"fundingTime": 1790812800001, "fundingRate": "0.00007981"}, {"fundingTime": 1793462400000, "fundingRate": "0.0001"}])
    pd.testing.assert_frame_equal(f, api)  # same keys to the millisecond, same values, sorted


def test_archive_oi_is_last_row_of_previous_day(monkeypatch):
    head = "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio\n"
    files = {binance_vision.METRICS.format(day="2026-10-26"): _zip("m.csv", head +  # unsorted, as in the archive
                 "2026-10-26 23:55:00,BTCUSDT,95514.126,7652201416.500469,3.0\n2026-10-26 00:00:00,BTCUSDT,93704.608,7.5e9,3.0\n"),
             binance_vision.METRICS.format(day="2026-10-27"): _zip("m.csv", head + "2026-10-27 12:00:00,BTCUSDT,1,1,1\n")}  # day incomplete
    _archive(monkeypatch, files)
    oi = binance_vision.fetch_oi(days=3, today=dt.date(2026, 10, 29))  # 28/10 not published yet
    api = binance.parse_oi([{"timestamp": 1793059200000, "sumOpenInterest": "95514.126", "sumOpenInterestValue": "7652201416.500469"}])
    pd.testing.assert_frame_equal(oi, api)  # API row of 27/10 = archive 26/10 23:55


def test_archive_quarterly_contract_rolls_on_expiry(monkeypatch):
    q = binance_vision.current_quarter_expiry
    assert q(dt.date(2026, 9, 24)) == dt.date(2026, 9, 25) and q(dt.date(2026, 9, 25)) == dt.date(2026, 12, 25)
    assert q(dt.date(2026, 12, 26)) == dt.date(2027, 3, 26) and q(dt.date(2027, 1, 1)) == dt.date(2027, 3, 26)
    row = "1790208000000,84000,84500,83900,{c},1,1790294399999,1,1,1,1,0\n"
    header = ",".join(binance_vision.KLINE_COLS) + "\n"
    _archive(monkeypatch, {
        binance_vision.CM_KLINES.format(symbol="BTCUSD_260925", day="2026-09-24"): _zip("k.csv", row.format(c=84373.4)),  # no header
        binance_vision.CM_KLINES.format(symbol="BTCUSD_261225", day="2026-09-25"): _zip("k.csv", header + row.format(c=85026.2) * 2)})
    b = binance_vision.fetch_basis(days=3, today=dt.date(2026, 9, 26))  # 23/09 missing from the archive
    assert list(b["date"].dt.strftime("%d/%m")) == ["24/09", "25/09"] and list(b["fut_close"]) == [84373.4, 85026.2]  # = dapi CURRENT_QUARTER


def _oi(last: str) -> pd.DataFrame:
    d = pd.date_range(end=last, periods=20, freq="D")
    return pd.DataFrame({"date": d, "oi_btc": 9e4, "oi_usd": np.linspace(7e9, 8e9, 20)})


def test_update_uses_archive_when_api_is_blocked(monkeypatch):
    now = dt.datetime(2026, 11, 2, 1)

    def blocked() -> pd.DataFrame:
        raise http.FetchError("https://fapi.binance.com/futures/data/openInterestHist", "HTTP 451", 451)

    def run(fetch, fallback=None) -> dict:
        monkeypatch.setattr(update, "SOURCES", [update.Source("binance_oi", fetch, ["oi_usd"], forward_only=True, fallback=fallback)])
        return update.run(now=now, save=False)["sources"]["binance_oi"]

    e = run(blocked, lambda: _oi("2026-10-28"))  # 5 days old: within 3 + archive_lag_days (2)
    assert e["ok"] and e["via"] == "data.binance.vision" and "451" in e["primary_error"] and e["last"] == "2026-10-28"
    e = run(blocked, lambda: _oi("2026-10-27"))
    assert not e["ok"] and any("cũ" in x for x in e["errors"])
    assert not run(lambda: _oi("2026-10-28"))["ok"]  # same age straight from the API is stale: the delay applies to the archive only
    e = run(lambda: _oi("2026-11-01"), lambda: pytest.fail("fallback used although the API answered"))
    assert e["ok"] and "via" not in e
    e = run(blocked)
    assert not e["ok"] and "451" in e["errors"][0]


def test_fetch_errors_never_carry_the_api_key():
    key = "abcd1234abcd1234abcd1234abcd1234"
    e = http.FetchError(f"https://api.stlouisfed.org/fred/series/observations?series_id=DTWEXBGS&api_key={key}&file_type=json", "HTTP 400", 400)
    assert key not in str(e) and key not in e.url and "api_key=***&file_type=json" in str(e)  # status.json is published


def test_fred_weekly_release_is_not_stale():
    src = {s.name: s for s in update.SOURCES}
    assert src["fred_DTWEXBGS"].stale_days == 7 and src["fred_DFII10"].stale_days is None
    d = pd.bdate_range("2026-06-01", "2026-10-23")
    usd = pd.DataFrame({"date": d, "usd_broad": np.linspace(120, 121, len(d))})
    monday = dt.datetime(2026, 11, 2, 1)  # before that Monday's H.10 release the newest row is Friday 23/10, 10 days old
    assert quality.check(usd, "fred_DTWEXBGS", ["usd_broad"], freq="B", stale_days=7, now=monday).ok
    assert not quality.check(usd, "fred_DTWEXBGS", ["usd_broad"], freq="B", stale_days=7, now=monday + dt.timedelta(days=2)).ok
