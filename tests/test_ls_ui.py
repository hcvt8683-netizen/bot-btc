# -*- coding: utf-8 -*-
"""The separate Long/Short view (src/ls.js) on frozen data (tests/fixtures/perp.json) and a faked Binance futures API:
switching views hides the buy / sell tabs without changing them, the table stacks into cards on a phone, Run reads the
live state, leverage gives liquidation numbers, and going back to the buy side shows exactly what it showed before."""
from __future__ import annotations

import asyncio
import json
import math
import pathlib
import re
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXED_NOW = "2026-11-02T09:30:00Z"
NOW_MS = 1793611800000  # 2026-11-02 09:30 UTC
HOUR, DAY = 3_600_000, 86_400_000


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


@pytest.fixture(scope="module")
def page_path() -> pathlib.Path:
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415
    out = pathlib.Path(tempfile.mkdtemp()) / "page.html"
    build.build(str(out), kn_path=str(ROOT / "tests" / "fixtures" / "recommendation.json"), ls_path=str(ROOT / "tests" / "fixtures" / "perp.json"))
    return out


async def _run(page_path: pathlib.Path, vw: int) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415
    H = {"Access-Control-Allow-Origin": "*"}

    async def route(r):
        u = r.request.url
        if "fapi.binance.com/fapi/v1/klines" in u:
            step = HOUR if "interval=1h" in u else DAY
            await r.fulfill(status=200, content_type="application/json", body=json.dumps(klines(step)), headers=H)
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
        res["first"] = await pg.inner_text("#ls-answer")
        res["status_first"] = await pg.inner_text("#ls-status")
        await pg.fill("#ls-lev", "10")
        await pg.wait_for_timeout(200)
        res["lev10"] = await pg.inner_text("#ls-answer")
        await pg.click("#ls-go")
        await pg.wait_for_function("/nến đóng/.test(document.getElementById('ls-status').textContent)", timeout=10000)
        await pg.wait_for_timeout(300)
        res["live"] = await pg.inner_text("#ls-answer")
        res["status_live"] = await pg.inner_text("#ls-status")
        res["marks"] = await pg.evaluate("[...document.querySelectorAll('#t-ls tbody tr')].map((tr) => tr.cells[1].textContent)")
        res["table"] = await pg.evaluate("""() => { const t = document.getElementById('t-ls');
            return { rows: t.tBodies[0].rows.length, stack: t.classList.contains('stack'), label: t.tBodies[0].rows[0].cells[2].dataset.label,
                     overflow: Math.max(0, t.scrollWidth - t.clientWidth) }; }""")
        res["scroll_width"] = await pg.evaluate("document.documentElement.scrollWidth")
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
    assert "Không nên vào lệnh" in r["first"] and "Đang hiện trạng thái lúc bot cập nhật" in r["status_first"]
    assert "1x: giá phải đi ngược gần 100%" in r["first"]
    assert "Với đòn bẩy 10x" in r["lev10"] and "Giá thanh lý xấp xỉ" in r["lev10"] and re.search(r"giá đi ngược 9,6%", r["lev10"])
    assert "Funding cao" in r["live"] and "Vừa tăng mạnh" in r["live"] and "Dao động cao" in r["live"] and "Giá trên trung bình 20 nến" in r["live"]
    assert "16:00 02/11/2026" in r["status_live"]          # last closed hourly candle: 09:00 UTC
    assert r["marks"].count("●") == 5                       # moc, trend up, funding high, strong rise, high volatility
    assert "Không nên vào lệnh" in r["live"]                # the fixture has no cell with an edge
    assert "Đòn bẩy quá cao" in r["lev200"]
    assert r["day_options"] == ["1 ngày", "3 ngày"]
    t = r["table"]
    assert t["rows"] == 9 and t["label"] == "Long có lãi"
    assert r["scroll_width"] <= vw
    if vw < 700:
        assert t["stack"] and t["overflow"] <= 1
    b = r["back"]
    assert b["cls"] == "" and b["tabs"] != "none" and b["panels"] == ["home"] and b["ls"] == "none" and b["stored"] is None
    assert r["buy_same"]
