# -*- coding: utf-8 -*-
"""The separate Long/Short view (src/ls.js) on frozen data (tests/fixtures/perp_trade.json, tests/fixtures/perp.json) and a
faked Binance futures API: switching views hides the buy / sell tabs without changing them; the plan shows the entry,
stop-loss, take-profit and win chance of the month's rule, at the trigger price while its signal is off and at the live
price once Run finds it on; leverage gives the liquidation price and warns when it comes before the stop; the tables stack
into cards on a phone; the older fixed-horizon study still works inside "Xem thêm"; going back to the buy side shows
exactly what it showed before."""
from __future__ import annotations

import asyncio
import json
import math
import pathlib
import re
import sys
import tempfile
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXED_NOW = "2026-11-02T09:30:00Z"
NOW_MS = 1793611800000  # 2026-11-02 09:30 UTC
HOUR, DAY = 3_600_000, 86_400_000
LT = json.loads((ROOT / "tests" / "fixtures" / "perp_trade.json").read_text(encoding="utf-8"))


def klines(step: int, n: int = 40) -> list[list]:
    """n candles of `step` ms, the last one still open at NOW; the last closed one jumps 3% (strong rise, high volatility)."""
    first = (NOW_MS // step) * step - (n - 1) * step
    out, c = [], 70000.0
    for i in range(n):
        o = first + i * step
        c = c * (1.03 if i == n - 2 else 1 + 0.0005 * math.sin(i))
        out.append([o, f"{c:.1f}", f"{c * 1.002:.1f}", f"{c * 0.998:.1f}", f"{c:.1f}", "100", o + step - 1, "1", 1, "0", "0", "0"])
    return out


FUNDING = [{"symbol": "BTCUSDT", "fundingTime": t, "fundingRate": "0.00010000"} for t in
           (1793548800005, 1793577600000, 1793606400003)]  # 01/11 16:00, 02/11 00:00, 02/11 08:00 UTC


def usd(x: float) -> str:
    return f"{round(x):,}".replace(",", ".") + " $"


@pytest.fixture(scope="module")
def page_path() -> pathlib.Path:
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415
    out = pathlib.Path(tempfile.mkdtemp()) / "page.html"
    build.build(str(out), kn_path=str(ROOT / "tests" / "fixtures" / "recommendation.json"), ls_path=str(ROOT / "tests" / "fixtures" / "perp.json"),
                lt_path=str(ROOT / "tests" / "fixtures" / "perp_trade.json"))
    return out


async def _run(page_path: pathlib.Path, vw: int) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415
    H = {"Access-Control-Allow-Origin": "*"}

    async def route(r):
        u = r.request.url
        if "fapi.binance.com/fapi/v1/klines" in u:
            q = parse_qs(urlparse(u).query)
            step = HOUR if q["interval"][0] == "1h" else DAY
            await r.fulfill(status=200, content_type="application/json", body=json.dumps(klines(step, int(q["limit"][0]))), headers=H)
        elif "fapi.binance.com/fapi/v1/fundingRate" in u:
            await r.fulfill(status=200, content_type="application/json", body=json.dumps(FUNDING), headers=H)
        elif u.startswith("file://"):
            await r.continue_()
        elif "fonts.g" in u:
            await r.abort()
        # every other request (the buy / sell data) is left pending, so that side stays exactly as first drawn

    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(viewport={"width": vw, "height": 900}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")
        pg = await ctx.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.clock.set_fixed_time(FIXED_NOW)
        await pg.route("**/*", route)
        await pg.route_web_socket(re.compile(".*"), lambda ws: None)  # no live price stream either
        await pg.goto(page_path.as_uri())
        res = {"errors": errs}
        buy_js = "document.getElementById('h-kpis').innerText + '|' + document.getElementById('kn-fresh').innerText"
        await pg.wait_for_timeout(800)
        buy_before = await pg.evaluate(buy_js)
        await pg.click("#mode-ls")
        await pg.wait_for_timeout(300)
        res["view"] = await pg.evaluate("""() => ({
            cls: document.body.className,
            pressed: ['mode-buy', 'mode-sell', 'mode-ls'].map((i) => document.getElementById(i).getAttribute('aria-pressed')),
            tabs: getComputedStyle(document.getElementById('tabs')).display,
            panels: [...document.querySelectorAll('#app > .tabp')].filter((p) => getComputedStyle(p).display !== 'none').length,
            ls: getComputedStyle(document.getElementById('ls-app')).display })""")
        res["first"] = await pg.inner_text("#lt-answer")
        res["status_first"] = await pg.inner_text("#ls-status")
        res["kpis"] = await pg.inner_text("#lt-kpis")
        res["curve"] = await pg.evaluate("(() => { const s = document.querySelector('#lt-curve svg'); return s ? [Number(s.getAttribute('width')), s.querySelectorAll('path').length] : null; })()")
        await pg.fill("#ls-lev", "10")
        await pg.wait_for_timeout(200)
        res["lev10"] = await pg.inner_text("#lt-answer")
        await pg.fill("#ls-amt", "200")
        await pg.fill("#ls-lev", "30")
        await pg.wait_for_timeout(200)
        res["lev30"] = await pg.inner_text("#lt-answer")
        await pg.fill("#ls-lev", "1")
        await pg.select_option("#lt-hold", "4")
        await pg.wait_for_timeout(200)
        res["hold4"] = await pg.inner_text("#lt-answer")
        res["hold_chart"] = await pg.evaluate("document.querySelectorAll('.lt-hc svg path').length")
        await pg.select_option("#lt-hold", "")
        await pg.click("#ls-go")
        await pg.wait_for_function("/nến giờ đóng/.test(document.getElementById('ls-status').textContent)", timeout=10000)
        await pg.wait_for_timeout(300)
        res["live"] = await pg.inner_text("#lt-answer")
        res["status_live"] = await pg.inner_text("#ls-status")
        res["table"] = await pg.evaluate("""() => { const t = document.getElementById('t-lt');
            return { rows: t.tBodies[0].rows.length, stack: t.classList.contains('stack'), label: t.tBodies[0].rows[0].cells[2].dataset.label,
                     here: t.querySelectorAll('tr.here').length, overflow: Math.max(0, t.scrollWidth - t.clientWidth) }; }""")
        await pg.click(".lt-side:nth-child(2) .btn")
        await pg.wait_for_timeout(200)
        res["short"] = await pg.inner_text("#lt-answer")
        res["past_rows"] = await pg.evaluate("document.getElementById('t-lt-past').tBodies[0].rows.length")
        res["past_notes"] = await pg.inner_text("#lt-past-notes")
        await pg.click("#t-lt tbody tr:nth-child(2) .lt-view")
        await pg.wait_for_timeout(300)
        res["picked"] = await pg.inner_text("#lt-answer")
        await pg.click("#lt-answer .lt-back")
        await pg.wait_for_timeout(200)
        res["unpicked"] = await pg.inner_text("#lt-answer")
        res["scroll_width"] = await pg.evaluate("document.documentElement.scrollWidth")
        # the older fixed-horizon study, inside "Xem thêm"
        await pg.click("#ls-old > summary")
        await pg.wait_for_timeout(200)
        res["old"] = await pg.inner_text("#ls-answer")
        res["marks"] = await pg.evaluate("[...document.querySelectorAll('#t-ls tbody tr')].map((tr) => tr.cells[1].textContent)")
        res["old_table"] = await pg.evaluate("""() => { const t = document.getElementById('t-ls');
            return { rows: t.tBodies[0].rows.length, stack: t.classList.contains('stack'), label: t.tBodies[0].rows[0].cells[2].dataset.label,
                     overflow: Math.max(0, t.scrollWidth - t.clientWidth) }; }""")
        res["scroll_width_old"] = await pg.evaluate("document.documentElement.scrollWidth")
        await pg.fill("#ls-lev", "200")
        await pg.wait_for_timeout(200)
        res["lev200"] = await pg.inner_text("#ls-answer")
        await pg.click("#ls-unit [data-u=d]")
        await pg.wait_for_timeout(200)
        res["day_options"] = await pg.evaluate("[...document.getElementById('ls-h').options].map((o) => o.textContent)")
        await pg.click("#mode-buy")
        await pg.wait_for_timeout(300)
        res["back"] = await pg.evaluate("""() => ({ cls: document.body.className, tabs: getComputedStyle(document.getElementById('tabs')).display,
            panels: [...document.querySelectorAll('#app > .tabp')].filter((p) => getComputedStyle(p).display !== 'none').map((p) => p.dataset.panel),
            ls: getComputedStyle(document.getElementById('ls-app')).display, stored: localStorage.getItem('btc-bot3-view') })""")
        res["buy_same"] = buy_before == await pg.evaluate(buy_js)
        await b.close()
    return res


@pytest.mark.parametrize("vw", [1280, 390])
def test_long_short_view_is_separate_and_works(page_path: pathlib.Path, vw: int) -> None:
    pytest.importorskip("playwright")
    r = asyncio.run(_run(page_path, vw))
    assert r["errors"] == []
    v = r["view"]
    assert v["cls"] == "ls-view" and v["pressed"] == ["false", "false", "true"] and v["tabs"] == "none" and v["panels"] == 0 and v["ls"] != "none"

    # before Run: Long meets c1, c2, c6 (signal off, walk-forward not positive), Short only c6 → no trade
    now, rule = LT["now"], LT["rules"][LT["sides"]["long"]["current"]["rule"]["id"]]
    E, s = now["ma"], rule["k"] * now["atr"]
    f = r["first"]
    assert "kiểm tra lúc 16:00 02/11/2026" in f.lower() and "Không nên vào lệnh" in f
    assert "Long đạt 3/6, Short đạt 1/6" in f and "Có công thức của tháng: t = 2,31" in f and "Chấm đi tới: 0 lệnh" in f
    assert "Long chưa tháng nào đạt 6/6 (cao nhất 4/6)" in f
    assert "công thức tháng 11/2026 của phía long" in f.lower() and "Long theo xu hướng" in f and "Tín hiệu chưa bật" in f and f"lên trên {usd(E)}" in f
    assert "Nếu vẫn vào lệnh Long theo công thức này" in f
    assert usd(E * (1 - s)) in f and usd(E * (1 + rule["r"] * s)) in f and "7 ngày" in f      # stop 2 ATR, target 2R, hold 168 h
    assert f"xác suất thắng nếu giữ tối đa 7 ngày\n{round(rule['p'] * 100)}%" in f.lower()
    assert "265 lệnh lịch sử" in f and "1.152 công thức" in f and "1x: giá phải đi ngược gần 100%" in f
    assert "Đang dùng số liệu lúc bot cập nhật 16:00 02/11/2026" in r["status_first"]
    assert "Chưa có lợi thế" in r["kpis"] and "167" in r["kpis"]
    assert r["curve"] is not None and r["curve"][0] > 200 and r["curve"][1] == 2

    # leverage: liquidation 9,6% away at 10x; at 30x it comes before the 5,3% stop, so Long loses c6
    assert "Tiền và đòn bẩy 10x" in r["lev10"] and "Giá thanh lý xấp xỉ" in r["lev10"] and "giá đi ngược 9,6%" in r["lev10"]
    assert "Cắt lỗ chạy trước thanh lý" in r["lev10"] and "17,5x" in r["lev10"] and "Long đạt 3/6" in r["lev10"]
    assert "Bị thanh lý trước khi chạm cắt lỗ" in r["lev30"] and "Ký quỹ 200 $ × 30x = vị thế 6.000 $" in r["lev30"]
    assert "Chạm cắt lỗ: −100,0% ký quỹ (−200,00 $)" in r["lev30"] and "Long đạt 2/6" in r["lev30"] and "đến trước cắt lỗ" in r["lev30"]

    # the hold the user picks: 4 hours → the same rule's numbers with a 4-hour hold, flagged as not walk-forward tested
    hv = rule["holds"]; i = hv["h"].index(4)
    assert f"xác suất thắng nếu giữ tối đa 4 giờ\n{round(hv['p'][i] * 100)}%" in r["hold4"].lower()
    assert "Bạn chọn giữ tối đa 4 giờ; công thức giữ 7 ngày" in r["hold4"] and f"{hv['n'][i]:,} lệnh".replace(",", ".") in r["hold4"]
    assert r["hold_chart"] == 3

    # after Run: the last closed hourly candle jumped 3% above its 20-day mean → Long's signal is on (4/6), entry at the live price
    live_price = float(klines(HOUR, 500)[-1][4])
    assert "Tín hiệu đang bật" in r["live"] and "Long đạt 4/6" in r["live"] and "Không nên vào lệnh" in r["live"] and usd(live_price) in r["live"]
    assert "16:00 02/11/2026" in r["status_live"]          # last closed hourly candle: 09:00 UTC
    assert "Nếu vẫn vào lệnh Short theo công thức này" in r["short"] and "Phía Short chưa có công thức đạt t ≥ 2" in r["short"]
    assert r["past_rows"] == 5 and "chưa tháng nào đạt đủ 6/6" in r["past_notes"]

    t = r["table"]
    assert t["rows"] == 12 and t["label"] == "Lệnh" and t["here"] == 1
    assert "công thức bạn đang xem" in r["picked"].lower() and "Không nên vào lệnh" in r["picked"]
    assert "công thức tháng 11/2026 của phía" in r["unpicked"].lower()
    assert r["scroll_width"] <= vw and r["scroll_width_old"] <= vw
    if vw < 700:
        assert t["stack"] and t["overflow"] <= 1

    # older study (fixed horizon, no stop): same states and verdict as before
    o = r["old"]
    assert "Funding cao" in o and "Vừa tăng mạnh" in o and "Dao động cao" in o and "Giá trên trung bình 20 nến" in o
    assert r["marks"].count("●") == 5                       # moc, trend up, funding high, strong rise, high volatility
    assert "Không nên vào lệnh" in o                         # the fixture has no cell with an edge
    assert "Đòn bẩy quá cao" in r["lev200"]
    assert r["day_options"] == ["1 ngày", "3 ngày"]
    ot = r["old_table"]
    assert ot["rows"] == 9 and ot["label"] == "Long có lãi"
    if vw < 700:
        assert ot["stack"] and ot["overflow"] <= 1

    b = r["back"]
    assert b["cls"] == "" and b["tabs"] != "none" and b["panels"] == ["home"] and b["ls"] == "none" and b["stored"] is None
    assert r["buy_same"]
