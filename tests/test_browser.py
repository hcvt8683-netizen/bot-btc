# -*- coding: utf-8 -*-
"""Thử cả trang trong trình duyệt không màn hình với dữ liệu giả lập đi qua đường tải dữ liệu thật của trang (Coin Metrics,
Alternative.me, Binance), không cần mạng: trang tải xong không lỗi, Tổng quan / Giá & ngày mua / Bên bán / Chốt lời dần
hiện đủ, thẻ Phân tích cũ đã gỡ (bước A2) và báo cáo tải về không còn phần chưa kiểm định, không trượt ngang, ở 1280 sáng,
390 sáng và 1280 tối. Chạy khoảng 22 giây cả ba cỡ (03/11/2026) nên đánh dấu `slow`: không chạy trong `make test` / Daily, CI chạy
riêng bằng `python -m pytest -m slow`. Chạy tay: `python tests/test_browser.py` (ảnh chụp lưu ở tests/out/)."""
from __future__ import annotations

import asyncio
import datetime
import json
import math
import os
import pathlib
import random
import re
import sys
import tempfile

import pytest

pytestmark = pytest.mark.slow
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "out"


def fake_data():
    """Giá, MVRV, phát hành, Fear & Greed và nến Binance giả lập từ 2010 tới hôm qua (cùng hạt giống: luôn như nhau)."""
    random.seed(5)
    start, end = datetime.date(2010, 7, 18), datetime.date.today() - datetime.timedelta(days=1)
    cm, fng, kl = [], [], []
    p, rp, i, d, prev = 0.08, 0.08, 0, start, 0.08
    while d <= end:
        cyc = math.sin(i / 1461 * 2 * math.pi)
        p *= math.exp(0.0016 + 0.004 * cyc + (random.random() - 0.5) * 0.07 - 0.0008 * math.log(p / rp)); rp += (p - rp) / 500
        issue = 7200 if i < 800 else 3600 if i < 2300 else 1800 if i < 3700 else 900 if i < 5100 else 450
        cm.append({"asset": "btc", "time": d.isoformat() + "T00:00:00.000000000Z", "PriceUSD": str(p), "CapMrktCurUSD": str(p * (3e6 + i * 4000)),
                   "CapMVRVCur": str(p / rp), "IssTotUSD": str(issue * p)})
        ts = int(datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc).timestamp())
        if d >= datetime.date(2018, 2, 1):
            fng.append({"value": str(max(1, min(99, round(50 + 30 * cyc + (random.random() - 0.5) * 40)))), "timestamp": str(ts)})
        if d >= datetime.date(2017, 8, 17):
            mv = abs(math.log(p / prev)); kl.append([ts * 1000, "0", "0", "0", str(p), "0", 0, str(1e9 * (1 + i / 3000) * (0.5 + random.random()) * (1 + mv * 40))])
        prev = p; d += datetime.timedelta(days=1); i += 1
    fng.reverse()
    return cm, fng, kl, p


@pytest.fixture(scope="module")
def page_path() -> pathlib.Path:
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415
    out = pathlib.Path(tempfile.mkdtemp()) / "page.html"
    build.build(str(out))
    return out


async def _run(page: pathlib.Path, vw: int, scheme: str) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415
    cm, fng, kl, last = fake_data()
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(viewport={"width": vw, "height": 900}, color_scheme=scheme, accept_downloads=True)
        pg = await ctx.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        async def route(r):
            u, H = r.request.url, {"Access-Control-Allow-Origin": "*"}
            if "coinmetrics" in u:
                await r.fulfill(status=200, content_type="application/json", body=json.dumps({"data": cm}), headers=H)
            elif "alternative.me" in u:
                await r.fulfill(status=200, content_type="application/json", body=json.dumps({"data": fng}), headers=H)
            elif "klines" in u:
                m = re.search(r"startTime=(\d+)", u); s = int(m.group(1)) if m else kl[-1][0] - 86400000   # nến 24 giờ ở đầu trang không có startTime
                await r.fulfill(status=200, content_type="application/json", body=json.dumps([k for k in kl if k[0] >= s][:1000]), headers=H)
            elif "ticker/price" in u:
                await r.fulfill(status=200, content_type="application/json", body=json.dumps({"price": str(last)}), headers=H)
            elif u.startswith("file://"):
                await r.continue_()
            else:
                await r.abort()

        await pg.route("**/*", route)
        await pg.add_init_script("window.BOT_NO_WS = true;")      # không mở luồng giá trực tiếp, số liệu cố định
        t0 = datetime.datetime.now()
        await pg.goto(page.as_uri())
        await pg.wait_for_selector("#old-body:not([hidden])", state="attached", timeout=150000)   # phần tính cũ (ẩn) chạy xong = dữ liệu đã tải
        await pg.wait_for_timeout(800)
        res = {"errors": errs, "seconds": (datetime.datetime.now() - t0).total_seconds()}
        res["tabs"] = await pg.evaluate("[...document.querySelectorAll('#tabs [data-tab]')].map((b) => b.dataset.tab)")
        res["home_cards"] = await pg.locator("#h-kpis .kpi").count()
        res["home"] = await pg.inner_text("#h-kpis")
        await pg.click("[data-tab=entry]"); await pg.wait_for_timeout(300)
        res["entry"] = await pg.inner_text("#en-answer")
        await pg.goto(page.as_uri() + "#old"); await pg.wait_for_timeout(600)
        res["old_hash"] = await pg.evaluate("[...document.querySelectorAll('.tabp')].filter((p) => !p.hidden).map((p) => p.dataset.panel)")
        res["scroll"] = [await pg.evaluate("document.documentElement.scrollWidth")]
        await pg.click("#mode-sell"); await pg.wait_for_timeout(600)
        res["sell_home"] = await pg.inner_text("#h-kpis")
        await pg.click("[data-tab=plan]"); await pg.wait_for_timeout(300)
        res["sell_plan"] = await pg.evaluate("({ sp: !document.getElementById('sp-sec').hidden, plan: document.getElementById('plan-sec').hidden })")
        res["scroll"].append(await pg.evaluate("document.documentElement.scrollWidth"))
        await pg.click("[data-tab=ai]"); await pg.wait_for_timeout(300)
        async with pg.expect_download() as dl:
            await pg.click("#dl-md")
        d = await dl.value
        res["report"] = pathlib.Path(await d.path()).read_text(encoding="utf-8")
        if os.environ.get("BOT_SHOTS"):
            OUT.mkdir(exist_ok=True)
            await pg.screenshot(path=str(OUT / f"browser_{scheme}_{vw}.png"), full_page=True)
        await pg.click("#mode-buy"); await pg.wait_for_timeout(300)
        res["back_buy"] = await pg.evaluate("document.getElementById('mode-buy').getAttribute('aria-pressed')")
        await b.close()
    return res


@pytest.mark.parametrize("vw,scheme", [(1280, "light"), (390, "light"), (1280, "dark")])
def test_whole_page_with_fake_data(page_path: pathlib.Path, vw: int, scheme: str) -> None:
    pytest.importorskip("playwright")
    r = asyncio.run(_run(page_path, vw, scheme))
    assert r["errors"] == [], r["errors"]
    assert "old" not in r["tabs"] and {"home", "entry", "plan", "fc", "check", "ai"} <= set(r["tabs"])
    assert r["home_cards"] >= 4 and "Khuyến nghị tuần này" in r["home"]
    assert r["entry"].strip()
    assert r["old_hash"] == ["home"]                              # địa chỉ #old cũ đưa về Tổng quan
    assert "Bên bán tuần này" in r["sell_home"] and r["sell_plan"] == {"sp": True, "plan": True}
    assert all(w <= vw for w in r["scroll"]), r["scroll"]
    md = r["report"]
    assert "đã gỡ ngày 03/11/2026" in md and "## Bên bán" not in md and "## Giá đề xuất mua và bán" not in md
    assert r["back_buy"] == "true"


if __name__ == "__main__":
    os.environ.setdefault("BOT_SHOTS", "1")
    sys.exit(pytest.main([__file__, "-m", "slow", "-q", "-p", "no:cacheprovider"]))
