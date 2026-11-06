# -*- coding: utf-8 -*-
"""Chế độ Tra cứu (src/lookup.js) trên giá giả cố định: chỉ nút của nó sáng, các phần khác ẩn; mở ra là ngày cuối với kỳ hạn 1 tháng;
giá, dải giá, mua giữ, điều đã xảy ra trùng với bot/models/lookup.py; ngày ngoài khoảng thì báo; điện thoại không trượt ngang và
bảng thành thẻ; bấm lại Bên mua thì trang như cũ."""
from __future__ import annotations

import asyncio
import json
import math
import pathlib
import re
import sys
import tempfile

import pytest

from tests.test_lookup import page_json, prepared, synth
from bot.models import lookup as lk

ROOT = pathlib.Path(__file__).resolve().parent.parent


def usd(x: float) -> str:
    return f"{math.floor(x + 0.5):,}".replace(",", ".") + " $" if x >= 10 else f"{x:.2f}".replace(".", ",") + " $"


@pytest.fixture(scope="module")
def built() -> tuple[pathlib.Path, dict]:
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415
    D = synth()
    cfg, S, F = prepared(D)
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "lookup.json").write_text(json.dumps(page_json(D, cfg, F)), encoding="utf-8")
    build.LK_PATH = str(tmp / "lookup.json")
    try:
        out = build.build(str(tmp / "page.html"), kn_path=str(ROOT / "tests" / "fixtures" / "recommendation.json"),
                          ls_path=str(ROOT / "tests" / "fixtures" / "perp.json"), lt_path=str(ROOT / "tests" / "fixtures" / "perp_trade.json"),
                          sr_path=str(ROOT / "tests" / "fixtures" / "sr.json"))
    finally:
        build.LK_PATH = None
    return pathlib.Path(out), {"D": D, "S": S, "F": F, "cfg": cfg}


async def _run(page: pathlib.Path, vw: int) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415

    async def route(r):
        if r.request.url.startswith("file://"):
            await r.continue_()
        elif "fonts.g" in r.request.url:
            await r.abort()
        # mọi yêu cầu khác (bên mua / bán) để treo, nên bên đó giữ nguyên như lúc đầu

    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(viewport={"width": vw, "height": 900}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")
        pg = await ctx.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script("window.BOT_NO_WS = true")
        await pg.route("**/*", route)
        await pg.route_web_socket(re.compile(".*"), lambda ws: None)
        await pg.goto(page.as_uri())
        await pg.wait_for_timeout(600)
        buy_js = "document.getElementById('h-kpis').innerText"
        buy_before = await pg.evaluate(buy_js)
        await pg.click("#mode-lk")
        await pg.wait_for_function("document.getElementById('lk-price').textContent !== '—'", timeout=15000)
        res = {"errors": errs}
        res["view"] = await pg.evaluate("""() => ({ cls: document.body.className,
            pressed: ['mode-buy', 'mode-sell', 'mode-ls', 'mode-tr', 'mode-pa', 'mode-lk'].map((i) => document.getElementById(i).getAttribute('aria-pressed')),
            hidden: ['tabs', 'ls-app', 'tr-app', 'pa-app'].map((i) => getComputedStyle(document.getElementById(i)).display),
            lk: getComputedStyle(document.getElementById('lk-app')).display, t: document.getElementById('lk-t').value,
            min: document.getElementById('lk-t').min, msgHidden: document.getElementById('lk-msg').hidden })""")
        res["price"] = await pg.inner_text("#lk-price")
        res["band"] = await pg.inner_text("#lk-band")
        res["hold"] = await pg.inner_text("#lk-hold")
        res["honest"] = await pg.inner_text("#lk-honest")
        res["chart"] = await pg.evaluate("({ cone: document.querySelectorAll('#lk-chart polygon').length, line: document.querySelectorAll('#lk-chart path.ln').length })")
        # một ngày đã biết kết quả, kỳ hạn 1 năm
        await pg.fill("#lk-t", "2019-07-01")
        await pg.fill("#lk-hn", "1")
        await pg.select_option("#lk-hu", "365")
        await pg.click("#lk-go")
        await pg.wait_for_timeout(400)
        res["past_band"] = await pg.inner_text("#lk-band")
        res["past_hold"] = await pg.inner_text("#lk-hold")
        res["past_chart"] = await pg.evaluate("document.querySelectorAll('#lk-chart path.ln.after').length")
        res["tables"] = await pg.evaluate("""() => ['t-lk-lv', 't-lk-an', 't-lk-ck'].map((id) => { const t = document.getElementById(id);
            return { rows: t.tBodies[0] ? t.tBodies[0].rows.length : 0, stack: t.classList.contains('stack'), overflow: Math.max(0, t.scrollWidth - t.clientWidth) }; })""")
        res["ck_title"] = await pg.inner_text("#lk-ck-title")
        res["scroll_width"] = await pg.evaluate("document.documentElement.scrollWidth")
        # kỳ hạn nhanh và ngày ngoài khoảng
        await pg.click("#lk-quick button[data-n='7']")
        await pg.wait_for_timeout(300)
        res["quick"] = await pg.inner_text("#lk-band-title")
        await pg.fill("#lk-t", "2014-05-01")
        await pg.click("#lk-go")
        await pg.wait_for_timeout(200)
        res["msg"] = await pg.evaluate("({ hidden: document.getElementById('lk-msg').hidden, text: document.getElementById('lk-msg').textContent })")
        await pg.click("#mode-buy")
        await pg.wait_for_timeout(300)
        res["back"] = await pg.evaluate("""() => ({ cls: document.body.className, lk: getComputedStyle(document.getElementById('lk-app')).display,
            pressed: ['mode-buy', 'mode-lk'].map((i) => document.getElementById(i).getAttribute('aria-pressed')) })""")
        res["buy_same"] = buy_before == await pg.evaluate(buy_js)
        await pg.click("#mode-lk")
        await pg.wait_for_timeout(200)
        await pg.click("#mode-pa")
        await pg.wait_for_timeout(200)
        res["to_pa"] = await pg.evaluate("""() => ({ cls: document.body.className, lk: getComputedStyle(document.getElementById('lk-app')).display,
            pressed: ['mode-pa', 'mode-lk'].map((i) => document.getElementById(i).getAttribute('aria-pressed')) })""")
        await b.close()
    return res


@pytest.mark.parametrize("vw", [1280, 390])
def test_lookup_view(built, vw: int) -> None:
    pytest.importorskip("playwright")
    page, M = built
    r = asyncio.run(_run(page, vw))
    assert r["errors"] == []
    v = r["view"]
    assert v["cls"] == "lk-view" and v["pressed"] == ["false"] * 5 + ["true"]
    assert v["hidden"] == ["none"] * 4 and v["lk"] != "none" and v["min"] == "2016-01-01" and v["msgHidden"]
    D, S, F, cfg = M["D"], M["S"], M["F"], M["cfg"]
    last = len(D["close"]) - 1
    assert v["t"] == lk.day(D, last).strftime("%Y-%m-%d")
    x = lk.lookup(D, S, F, last, 30, cfg)                       # mở ra: ngày cuối, kỳ hạn 1 tháng
    assert r["price"] == usd(x["state"]["close"])
    assert usd(x["band"]["q10"]) in r["band"] and usd(x["band"]["q90"]) in r["band"] and "chưa tới" in r["band"]
    assert f"{round(x['hold']['p'] * 100)}%" in r["hold"] and "mua đều" in r["hold"]
    assert "0 tình huống sau đó lên nhiều hơn" in r["honest"] or "tình huống sau đó lên nhiều hơn" in r["honest"]
    assert r["chart"] == {"cone": 2, "line": 1}
    t = lk.index_of(D, "2019-07-01")
    y = lk.lookup(D, S, F, t, 365, cfg)
    o = y["outcome"]
    assert o is not None and usd(o["close"]) in r["past_band"]
    assert ("Nằm trong dải 8/10 lần: có" in r["past_band"]) == o["in80"]
    assert ("(lãi)" in r["past_hold"]) == (o["gain"] > 0) and r["past_chart"] == 1
    assert r["ck_title"].endswith("1 năm")
    assert all(tb["rows"] >= 1 for tb in r["tables"])
    assert "7 ngày" in r["quick"]
    assert not r["msg"]["hidden"] and "01/01/2016" in r["msg"]["text"]
    assert r["scroll_width"] <= vw
    if vw < 700:
        assert all(tb["stack"] and tb["overflow"] <= 1 for tb in r["tables"])
    b = r["back"]
    assert b["cls"] == "" and b["lk"] == "none" and b["pressed"] == ["true", "false"] and r["buy_same"]
    p = r["to_pa"]
    assert p["cls"] == "pa-view" and p["lk"] == "none" and p["pressed"] == ["true", "false"]
