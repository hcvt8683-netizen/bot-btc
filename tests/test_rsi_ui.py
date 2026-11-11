# -*- coding: utf-8 -*-
"""RSI 14 on the page (mục rsi_check) on frozen data (tests/fixtures/rsi.json): the browser RSI (window.LS_RSI14 in
src/ls.js) gives exactly what bot/models/rsi_check.rsi gives on many price series; after Run the Long/Short plan shows the
RSI of the downloaded closed hourly candles; the Trend, Long/Short and Price action views show the RSI tables / lines with
the honest note, and none of them changes its verdict because of RSI."""
from __future__ import annotations

import asyncio
import json
import math
import pathlib
import re
import sys
import tempfile
from urllib.parse import parse_qs, urlparse

import numpy as np
import pytest

from bot.models import rsi_check as rc

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
FIXED_NOW = "2026-11-02T09:30:00Z"
NOW_MS = 1793611800000
HOUR, DAY = 3_600_000, 86_400_000
RSI = json.loads((FIX / "rsi.json").read_text(encoding="utf-8"))


def klines(step: int, n: int) -> list[list]:
    first = (NOW_MS // step) * step - (n - 1) * step
    out, c = [], 70000.0
    for i in range(n):
        o = first + i * step
        c = c * (1 + 0.004 * math.sin(i / 5) + 0.001 * math.cos(i / 2))
        out.append([o, f"{c:.1f}", f"{c * 1.002:.1f}", f"{c * 0.998:.1f}", f"{c:.1f}", "100", o + step - 1, "1", 1, "0", "0", "0"])
    return out


def series() -> list[list[float]]:
    rng = np.random.default_rng(5)
    out = [list(100 * np.exp(np.cumsum(rng.normal(0, s, n)))) for s, n in ((0.01, 60), (0.03, 500), (0.002, 15), (0.05, 200))]
    out.append([1.0 + 0.01 * i for i in range(40)])          # chỉ tăng: RSI = 100
    out.append([5.0] * 30)                                     # đứng yên: giảm TB = 0 → 100 (như Python)
    return out


@pytest.fixture(scope="module")
def page_path() -> pathlib.Path:
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415
    out = pathlib.Path(tempfile.mkdtemp()) / "page.html"
    build.build(str(out), kn_path=str(FIX / "recommendation.json"), ls_path=str(FIX / "perp.json"), lt_path=str(FIX / "perp_trade.json"),
                tr_path=str(FIX / "trend.json"), sr_path=str(FIX / "sr.json"), hold_path=str(FIX / "hold.json"), rsi_path=str(FIX / "rsi.json"))
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
            await r.fulfill(status=200, content_type="application/json", body="[]", headers=H)
        elif u.startswith("file://"):
            await r.continue_()
        elif "fonts.g" in u:
            await r.abort()

    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(viewport={"width": vw, "height": 900}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")
        pg = await ctx.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.clock.set_fixed_time(FIXED_NOW)
        await pg.route("**/*", route)
        await pg.route_web_socket(re.compile(".*"), lambda ws: None)
        await pg.goto(page_path.as_uri())
        await pg.wait_for_timeout(600)
        res = {"errors": errs}
        res["js"] = await pg.evaluate("(ss) => ss.map((s) => window.LS_RSI14(s))", series())
        await pg.click("#mode-ls")
        await pg.wait_for_timeout(300)
        res["ls_first"] = await pg.inner_text("#lt-answer")
        res["ls_sec"] = await pg.inner_text("#ls-rsi-sec")
        res["ls_rows"] = await pg.evaluate("document.querySelectorAll('#t-ls-rsi tbody tr').length")
        res["ls_good"] = await pg.evaluate("document.querySelectorAll('#t-ls-rsi td.good').length")
        await pg.click("#ls-go")
        await pg.wait_for_function("/nến giờ đóng/.test(document.getElementById('ls-status').textContent)", timeout=10000)
        await pg.wait_for_timeout(300)
        res["ls_live"] = await pg.inner_text("#lt-answer")
        res["ls_scroll"] = await pg.evaluate("document.documentElement.scrollWidth")
        await pg.click("#mode-tr")
        await pg.wait_for_timeout(400)
        res["tr_sec"] = await pg.inner_text("#tr-rsi-sec")
        res["tr_rows"] = await pg.evaluate("document.querySelectorAll('#t-tr-rsi tbody tr').length")
        res["tr_overflow"] = await pg.evaluate("(() => { const t = document.getElementById('t-tr-rsi'); return Math.max(0, t.scrollWidth - t.clientWidth); })()")
        res["tr_scroll"] = await pg.evaluate("document.documentElement.scrollWidth")
        await pg.click("#mode-pa")
        await pg.wait_for_timeout(400)
        res["pact_now"] = await pg.inner_text("#pact-now")
        await b.close()
    return res


@pytest.mark.parametrize("vw", [1280, 390])
def test_rsi_on_three_views(page_path: pathlib.Path, vw: int) -> None:
    pytest.importorskip("playwright")
    r = asyncio.run(_run(page_path, vw))
    assert r["errors"] == []
    # hàm RSI trên trình duyệt = rsi_check.rsi trong Python
    for s, js in zip(series(), r["js"]):
        py = rc.rsi(np.asarray(s))
        assert len(js) == len(py)
        for a, b in zip(js, py):
            if np.isnan(b):
                assert a is None or (isinstance(a, float) and math.isnan(a))
            else:
                assert a == pytest.approx(b, rel=1e-9, abs=1e-9)
    # Long/Short trước khi bấm Chạy: RSI giờ của lần chạy Daily, ghi trung thực, kết luận không đổi
    t = RSI["today"]["hourly"]
    want = f"{t['rsi']:.1f}".replace(".", ",")
    assert f"RSI 14 giờ lúc này: {want} — trung tính (30–70)" in r["ls_first"] and "không nói gì về hướng" in r["ls_first"]
    assert "Không nên vào lệnh" in r["ls_first"]
    # sau khi bấm Chạy: RSI của các nến giờ đã đóng vừa tải
    closes = [float(k[4]) for k in klines(HOUR, 500) if k[6] < NOW_MS]
    x = rc.rsi(np.asarray(closes))[-1]
    assert f"RSI 14 giờ lúc này: {x:.1f}".replace(".", ",") in r["ls_live"]
    band = rc.band_of(x)
    if band is None:
        assert "không nói gì về hướng" in r["ls_live"]
    # thẻ RSI giờ: 12 kỳ hạn, đúng số ô có lợi thế của fixture, ghi chưa trừ phí và niềm tin "dải sâu" 0/56
    edges_h = [e for e in RSI["edges"] if "|hourly|" in e]
    assert r["ls_rows"] == len(RSI["horizons"]["hourly"]) and r["ls_good"] == len(edges_h)
    assert f"{len(edges_h)} ô đúng hướng hơn hẳn" in r["ls_sec"] and "chưa trừ phí" in r["ls_sec"]
    assert f"{RSI['claim_summary']['deeper_better']}/{RSI['claim_summary']['n']} cặp" in r["ls_sec"]
    # Xu hướng: bảng nến ngày, không ô nào có lợi thế → ghi rõ, dự báo không đổi
    edges_d = [e for e in RSI["edges"] if "|daily|" in e]
    assert r["tr_rows"] == len(RSI["horizons"]["daily"])
    if not edges_d:
        assert "không dải RSI nào đoán hướng hơn hẳn" in r["tr_sec"] and "không đổi theo RSI" in r["tr_sec"]
    assert "số liệu không ủng hộ" in r["tr_sec"]
    # Price action: dòng RSI ngày kèm ghi chú, đề xuất không đổi
    d = RSI["today"]["daily"]
    assert f"RSI 14 ngày" in r["pact_now"] and f"{d['rsi']:.1f}".replace(".", ",") in r["pact_now"]
    assert "đề xuất ở trên không đổi theo RSI" in r["pact_now"]
    assert r["ls_scroll"] <= vw and r["tr_scroll"] <= vw
    if vw < 700:
        assert r["tr_overflow"] <= 1
