# -*- coding: utf-8 -*-
"""The Price action view (src/pa.js) on frozen data (tests/fixtures/sr.json) and a faked Binance futures API: only its
button is lit, the other views are hidden, the levels of the picked frame are the highest high / lowest low of the last
W closed candles (as sr_levels.levels), changing unit and number redraws the cards and the table, the table stacks into
cards on a phone, the entry-check panel lives here (not in Long/Short), a failed download falls back to the stored
levels, and going back to the buy side shows exactly what it showed before."""
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
FIX = ROOT / "tests" / "fixtures"
FIXED_NOW = "2026-11-02T09:30:00Z"
NOW_MS = 1793611800000  # 2026-11-02 09:30 UTC
HOUR, DAY = 3_600_000, 86_400_000
SR = json.loads((FIX / "sr.json").read_text(encoding="utf-8"))


def klines(step: int, n: int) -> list[list]:
    """n candles of `step` ms, the last one still open at NOW; a slow wave so highs and lows differ by window."""
    first = (NOW_MS // step) * step - (n - 1) * step
    out = []
    for i in range(n):
        o = first + i * step
        c = 70000 * (1 + 0.04 * math.sin(i / 17) + 0.0004 * i)
        out.append([o, f"{c:.1f}", f"{c * 1.004:.1f}", f"{c * 0.995:.1f}", f"{c:.1f}", "100", o + step - 1, "1", 1, "0", "0", "0"])
    return out


def usd(x: float) -> str:
    return f"{math.floor(x + 0.5):,}".replace(",", ".") + " $"   # half up, like Intl.NumberFormat on the page


SERIES = 3000   # nến giả liên tục; API giả trả 1500 nến mới nhất, hoặc 1500 nến trước endTime (trang thứ hai)


def page(step: int, limit: int, end: int | None) -> list[list]:
    k = klines(step, SERIES)
    if end is not None:
        k = [r for r in k if r[0] <= end]
    return k[-limit:]


def levels(step: int, n: int, W: int) -> tuple[float, float]:
    k = klines(step, SERIES)
    closed = [r for r in k if r[6] < NOW_MS][-W:]
    return max(float(r[2]) for r in closed), min(float(r[3]) for r in closed)


@pytest.fixture(scope="module")
def page_path() -> pathlib.Path:
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415
    out = pathlib.Path(tempfile.mkdtemp()) / "page.html"
    build.build(str(out), kn_path=str(FIX / "recommendation.json"), ls_path=str(FIX / "perp.json"), lt_path=str(FIX / "perp_trade.json"),
                tr_path=str(FIX / "trend.json") if (FIX / "trend.json").exists() else None, sr_path=str(FIX / "sr.json"),
                rsi_path=str(FIX / "rsi.json"))
    return out


async def _run(page_path: pathlib.Path, vw: int, fail: bool) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415
    H = {"Access-Control-Allow-Origin": "*"}

    async def route(r):
        u = r.request.url
        if "fapi.binance.com/fapi/v1/klines" in u:
            if fail:
                await r.fulfill(status=451, body="blocked", headers=H)
                return
            q = parse_qs(urlparse(u).query)
            step = HOUR if q["interval"][0] == "1h" else DAY
            end = int(q["endTime"][0]) if "endTime" in q else None
            await r.fulfill(status=200, content_type="application/json", body=json.dumps(page(step, int(q["limit"][0]), end)), headers=H)
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
        await pg.route_web_socket(re.compile(".*"), lambda ws: None)
        await pg.goto(page_path.as_uri())
        await pg.wait_for_timeout(800)
        buy_js = "document.getElementById('h-kpis').innerText + '|' + document.getElementById('kn-fresh').innerText"
        buy_before = await pg.evaluate(buy_js)
        await pg.click("#mode-pa")
        await pg.wait_for_function("document.getElementById('sr-status').textContent.length > 0 && !/đang tải/.test(document.getElementById('sr-status').textContent)", timeout=10000)
        await pg.wait_for_timeout(300)
        res = {"errors": errs}
        res["view"] = await pg.evaluate("""() => ({ cls: document.body.className,
            pressed: ['mode-buy', 'mode-sell', 'mode-ls', 'mode-tr', 'mode-pa'].map((i) => document.getElementById(i).getAttribute('aria-pressed')),
            hidden: ['tabs', 'ls-app', 'tr-app'].map((i) => getComputedStyle(document.getElementById(i)).display),
            pa: getComputedStyle(document.getElementById('pa-app')).display,
            pactHere: !!document.querySelector('#pa-app #pact-sec'), pactInLs: !!document.querySelector('#ls-app #pact-sec') })""")
        res["status"] = await pg.inner_text("#sr-status")
        res["day1"] = await pg.inner_text("#sr-cards")
        res["chart1"] = await pg.evaluate("""() => ({ candles: document.querySelectorAll('#sr-chart rect.cu, #sr-chart rect.cd').length,
            labels: [...document.querySelectorAll('#sr-chart .pt text')].map((t) => t.textContent.split(' ')[0]) })""")
        res["honest"] = await pg.inner_text("#sr-honest")
        res["rows_day"] = await pg.evaluate("document.querySelectorAll('#t-sr tbody tr').length")
        await pg.click("#sr-unit [data-u=thang]")
        await pg.click("#sr-ns button:nth-child(6)")
        await pg.wait_for_timeout(200)
        res["month6"] = await pg.inner_text("#sr-cards")
        res["chart6"] = await pg.evaluate("document.querySelectorAll('#sr-chart rect.cu, #sr-chart rect.cd').length")
        res["chart6_title"] = await pg.inner_text("#sr-chart-title")
        res["chart6_span"] = await pg.evaluate("""() => { const s = document.querySelector('#sr-chart rect.span'), t = document.querySelector('#sr-chart .span-t');
            const c = [...document.querySelectorAll('#sr-chart rect.cu, #sr-chart rect.cd')].map((r) => +r.getAttribute('x'));
            return { x: s ? +s.getAttribute('x') : null, label: t ? t.textContent : null, inside: s ? c.filter((x) => x >= +s.getAttribute('x')).length : 0 }; }""")
        res["same"] = await pg.evaluate("[...document.querySelectorAll('#t-sr tbody tr')].map((tr) => [tr.cells[1], tr.cells[4]].map((c) => (c.querySelector('.same') || {}).textContent || ''))")
        res["levels_all"] = {}
        for unit in ("gio", "ngay", "tuan", "thang"):
            await pg.click(f"#sr-unit [data-u={unit}]")
            await pg.wait_for_timeout(100)
            res["levels_all"][unit] = await pg.evaluate(
                "[...document.querySelectorAll('#t-sr tbody tr')].map((tr) => [tr.cells[1], tr.cells[4]].map((c) => c.childNodes[0].textContent))")
        await pg.click("#sr-unit [data-u=thang]")
        await pg.wait_for_timeout(100)
        res["table"] = await pg.evaluate("""() => { const t = document.getElementById('t-sr');
            return { rows: t.tBodies[0].rows.length, here: t.querySelectorAll('tr.here').length, stack: t.classList.contains('stack'),
                     label: t.tBodies[0].rows[0].cells[1].dataset.label, overflow: Math.max(0, t.scrollWidth - t.clientWidth) }; }""")
        await pg.click("#t-sr tbody tr:nth-child(2)")
        await pg.wait_for_timeout(200)
        res["picked"] = await pg.evaluate("document.querySelector('#sr-ns button[aria-pressed=true]').textContent")
        res["ladder"] = await pg.evaluate("document.querySelectorAll('#sr-chart .pt').length")
        res["scroll_width"] = await pg.evaluate("document.documentElement.scrollWidth")
        await pg.click("#mode-buy")
        await pg.wait_for_timeout(300)
        res["back"] = await pg.evaluate("""() => ({ cls: document.body.className, pa: getComputedStyle(document.getElementById('pa-app')).display,
            pressed: ['mode-buy', 'mode-pa'].map((i) => document.getElementById(i).getAttribute('aria-pressed')), stored: localStorage.getItem('btc-bot3-view') })""")
        res["buy_same"] = buy_before == await pg.evaluate(buy_js)
        await b.close()
    return res


@pytest.mark.parametrize("vw", [1280, 390])
def test_price_action_view(page_path: pathlib.Path, vw: int) -> None:
    pytest.importorskip("playwright")
    r = asyncio.run(_run(page_path, vw, fail=False))
    assert r["errors"] == []
    v = r["view"]
    assert v["cls"] == "pa-view" and v["pressed"] == ["false", "false", "false", "false", "true"]
    assert v["hidden"] == ["none", "none", "none"] and v["pa"] != "none" and v["pactHere"] and not v["pactInLs"]
    assert "nến giờ đóng lúc 16:00 02/11/2026" in r["status"]
    R, S = levels(HOUR, SERIES, 24)                           # 1 ngày = 24 nến giờ đã đóng
    assert "Kháng cự 1 ngày" in r["day1"] and usd(R) in r["day1"] and "Hỗ trợ 1 ngày" in r["day1"] and usd(S) in r["day1"]
    assert "Bật xuống" in r["day1"] and "Mức giả cùng khoảng cách" in r["day1"]
    s = SR["summary"]
    assert f"{SR['tests']} khung × phía" in r["honest"] and f"{s['nhu_bat_ky']} như mức bất kỳ" in r["honest"]
    assert r["rows_day"] == 7
    # mục sr_view (11/11/2026): mỗi nến vẽ = trọn khung; khung 1 ngày: nến 24 giờ, tối đa 30 nến; 2 trang nến được ghép
    assert r["chart1"]["candles"] == 30 and {"Kháng", "Hỗ", "Lúc"} <= set(r["chart1"]["labels"])
    n6 = (SERIES - 1) // 180                                  # nến 6 tháng (180 nến ngày) đủ từ 2.999 nến ngày đã đóng
    assert r["chart6"] == n6 and f"{n6} nến gần nhất, mỗi nến = 6 tháng (gộp 180 nến ngày)" in r["chart6_title"]
    assert r["chart6_span"]["label"] == "6 tháng" and r["chart6_span"]["inside"] == 1          # nền xám = nến cuối = khung
    R6, S6 = levels(DAY, SERIES, 180)                         # 6 tháng = 180 nến ngày đã đóng
    assert "Kháng cự 6 tháng" in r["month6"] and usd(R6) in r["month6"] and usd(S6) in r["month6"]
    want = []                                                 # "= khung …" khi mức bằng đúng mức của khung trước
    first = {}
    for n in range(1, 13):
        lv = levels(DAY, SERIES, 30 * n)
        cells = []
        for i, x in enumerate(lv):
            if n == 1 or x != levels(DAY, SERIES, 30 * (n - 1))[i]:
                first[i] = n
            cells.append("" if first[i] == n else f"= khung {first[i]} tháng")
        want.append(cells)
    assert r["same"] == want and any(c for row in want for c in row)
    # mỗi khung của cả 4 đơn vị phải ra đúng mức của cửa sổ W nến riêng (như sr_levels.levels trong Python)
    FRAMES = {"gio": (HOUR, SERIES, 1, 24), "ngay": (HOUR, SERIES, 24, 7), "tuan": (DAY, SERIES, 7, 8), "thang": (DAY, SERIES, 30, 12)}
    for unit, (step, cnt, per, mx) in FRAMES.items():
        want_lv = [[usd(v) for v in levels(step, cnt, per * n)] for n in range(1, mx + 1)]
        assert r["levels_all"][unit] == want_lv, unit
    # cửa sổ khác nhau phải cho mức khác nhau ở dữ liệu này (bắt lỗi mọi khung dùng chung một cửa sổ)
    assert len({tuple(row) for row in r["levels_all"]["gio"]}) > 1
    assert len({tuple(row) for row in r["levels_all"]["thang"]}) > 1
    t = r["table"]
    assert t["rows"] == 12 and t["here"] == 1 and t["label"] == "Kháng cự"
    assert r["picked"] == "2" and r["ladder"] >= 3
    assert r["scroll_width"] <= vw
    if vw < 700:
        assert t["stack"] and t["overflow"] <= 1
    b = r["back"]
    assert b["cls"] == "" and b["pa"] == "none" and b["pressed"] == ["true", "false"] and b["stored"] is None
    assert r["buy_same"]


def test_price_action_view_falls_back_when_binance_fails(page_path: pathlib.Path) -> None:
    pytest.importorskip("playwright")
    r = asyncio.run(_run(page_path, 1280, fail=True))
    assert r["errors"] == []
    assert "Không tải được nến trực tiếp từ Binance" in r["status"]
    lv = SR["now"]["1h"]["levels"]["ngay|1"]
    assert usd(lv["R"]) in r["day1"] and usd(lv["S"]) in r["day1"]
