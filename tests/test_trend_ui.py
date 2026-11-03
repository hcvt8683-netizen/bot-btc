# -*- coding: utf-8 -*-
"""The Trend view (src/trend.js) and the sell-side "Chốt lời dần" tool (src/ui.js) on frozen data (tests/fixtures/trend.json,
tests/fixtures/recommendation.json): switching to Trend hides every other part and back; cards per horizon group, fan
chart, the model heat table, the cross-check with the other tabs and the walk-forward table; no sideways scroll on a phone.
On the sell side the Giải ngân tab becomes Chốt lời dần with the recommended plan and a dated schedule; on the buy side the
plan summary no longer shows its "this is also the best" sentence before an amount is entered (L1). When the plans are a tie
(plan.stable) no schedule is chosen until the user clicks one, and the USD box takes "$1000"-style amounts."""
from __future__ import annotations

import asyncio
import json
import pathlib
import re
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
TR = json.loads((FIX / "trend.json").read_text(encoding="utf-8"))
KN = json.loads((FIX / "recommendation.json").read_bytes().decode("utf-8"))
SP, PLAN = KN["sell_plan"], KN["plan"]


def usd(x: float) -> str:
    return f"{round(x):,}".replace(",", ".") + " $"


@pytest.fixture(scope="module")
def page_path() -> pathlib.Path:
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415
    out = pathlib.Path(tempfile.mkdtemp()) / "page.html"
    build.build(str(out), kn_path=str(FIX / "recommendation.json"), ls_path=str(FIX / "perp.json"), lt_path=str(FIX / "perp_trade.json"),
                tr_path=str(FIX / "trend.json"))
    return out


async def _run(page_path: pathlib.Path, vw: int) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415

    async def route(r):
        if r.request.url.startswith("file://"):
            await r.continue_()
        elif "fonts.g" in r.request.url:
            await r.abort()
        # everything else stays pending: the page shows the frozen numbers

    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(viewport={"width": vw, "height": 900}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")
        pg = await ctx.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script("window.BOT_NO_WS = true;")
        await pg.route("**/*", route)
        await pg.route_web_socket(re.compile(".*"), lambda ws: None)
        await pg.goto(page_path.as_uri())
        await pg.wait_for_timeout(800)
        res: dict = {"errors": errs}
        # buy side, Giải ngân before an amount (L1)
        await pg.click("[data-tab=plan]")
        await pg.wait_for_timeout(200)
        res["plan_sum"] = await pg.inner_text("#plan-sum")
        # a tie: no schedule until a plan is picked; USD amounts with a currency sign; too small to split
        await pg.fill("#plan-amount", "1000")                                # type, then click USD at once (the first click used to be lost)
        await pg.click("#plan-unit button:nth-child(2)")
        res["usd_ph"] = await pg.get_attribute("#plan-amount", "placeholder")
        res["usd_on"] = [await pg.get_attribute("#plan-unit button:nth-child(2)", "aria-pressed"), await pg.input_value("#plan-amount")]
        await pg.fill("#plan-amount", "$1000")
        await pg.wait_for_timeout(100)
        res["usd_before_pick"] = [await pg.inner_text("#plan-sum"), await pg.evaluate("document.getElementById('t-plan-sched').tBodies[0].rows.length"),
                                  await pg.evaluate("document.getElementById('dl-plan').disabled")]
        await pg.click("#plan-opts button:nth-child(5)")
        await pg.wait_for_timeout(100)
        res["usd_pick"] = [await pg.inner_text("#plan-sum"), await pg.evaluate("document.getElementById('t-plan-sched').tBodies[0].rows.length"),
                           await pg.inner_text("#t-plan-sched tbody tr:first-child"), await pg.evaluate("document.getElementById('dl-plan').disabled")]
        await pg.fill("#plan-amount", "0,1 USD")
        await pg.wait_for_timeout(100)
        res["usd_small"] = await pg.inner_text("#plan-sum")
        # Trend view
        await pg.click("#mode-tr")
        await pg.wait_for_timeout(400)
        res["view"] = await pg.evaluate("""() => ({ cls: document.body.className,
            pressed: ['mode-buy', 'mode-sell', 'mode-ls', 'mode-tr'].map((i) => document.getElementById(i).getAttribute('aria-pressed')),
            tabs: getComputedStyle(document.getElementById('tabs')).display, ls: getComputedStyle(document.getElementById('ls-app')).display,
            tr: getComputedStyle(document.getElementById('tr-app')).display,
            panels: [...document.querySelectorAll('#app > .tabp')].filter((p) => getComputedStyle(p).display !== 'none').length })""")
        res["head"] = await pg.inner_text("#tr-sec")
        res["sure"] = await pg.inner_text("#tr-sure")
        res["cd"] = await pg.evaluate("""() => { const t = document.getElementById('t-tr-cd');
            return { rows: t.tBodies[0].rows.length, stack: t.classList.contains('stack'), today: document.getElementById('tr-cd-today').innerText }; }""")
        res["bt_notes"] = await pg.inner_text("#tr-bt-notes")
        res["model_cols"] = await pg.evaluate("document.getElementById('t-tr-models').tHead.rows[0].cells.length")
        res["price"] = await pg.inner_text("#tr-price")
        res["cards"] = {}
        for g in ("week", "month", "day"):
            await pg.click(f"#tr-groups [data-g={g}]")
            await pg.wait_for_timeout(150)
            res["cards"][g] = await pg.evaluate("[...document.querySelectorAll('#tr-cards .tr-card')].map((c) => c.innerText)")
        res["fan"] = await pg.evaluate("(() => { const s = document.querySelector('#tr-fan svg'); return s ? [Number(s.getAttribute('width')), s.querySelectorAll('polygon').length, s.querySelectorAll('circle').length] : null; })()")
        res["tables"] = await pg.evaluate("""() => Object.fromEntries(['t-tr-models', 't-tr-cross', 't-tr-bt'].map((id) => { const t = document.getElementById(id);
            return [id, { rows: t.tBodies[0].rows.length, stack: t.classList.contains('stack'), overflow: Math.max(0, t.scrollWidth - t.clientWidth),
                          text: t.innerText }]; }))""")
        res["hits"] = await pg.evaluate("document.querySelectorAll('#tr-hits rect').length")
        res["scroll_width"] = await pg.evaluate("document.documentElement.scrollWidth")
        await pg.click("#mode-ls")
        await pg.wait_for_timeout(200)
        res["to_ls"] = await pg.evaluate("document.body.className")
        await pg.click("#mode-tr")
        await pg.wait_for_timeout(200)
        res["to_tr"] = await pg.evaluate("document.body.className")
        # sell side: Chốt lời dần
        await pg.click("#mode-sell")
        await pg.wait_for_timeout(300)
        res["after_sell"] = await pg.evaluate("({ cls: document.body.className, stored: localStorage.getItem('btc-bot3-view') })")
        await pg.click("[data-tab=plan]")
        await pg.wait_for_timeout(200)
        res["sell_tab"] = await pg.inner_text("#tabs [data-tab=plan]")
        res["sell_vis"] = await pg.evaluate("[!document.getElementById('sp-sec').hidden, !document.getElementById('plan-sec').hidden]")
        res["sp_empty"] = await pg.inner_text("#sp-sum")
        await pg.fill("#sp-amount", "0,5")
        await pg.wait_for_timeout(200)
        res["sp_sum"] = await pg.inner_text("#sp-sum")
        res["sp_rows"] = await pg.evaluate("document.getElementById('t-sp-sched').tBodies[0].rows.length")
        res["sp_table"] = await pg.evaluate("document.getElementById('t-sp').tBodies[0].rows.length")
        res["sell_scroll"] = await pg.evaluate("document.documentElement.scrollWidth")
        await pg.click("#mode-buy")
        await pg.wait_for_timeout(200)
        res["buy_tab"] = await pg.inner_text("#tabs [data-tab=plan]")
        res["buy_vis"] = await pg.evaluate("[!document.getElementById('sp-sec').hidden, !document.getElementById('plan-sec').hidden]")
        await b.close()
    return res


@pytest.mark.parametrize("vw", [1280, 390])
def test_trend_view_and_sell_plan(page_path: pathlib.Path, vw: int) -> None:
    pytest.importorskip("playwright")
    r = asyncio.run(_run(page_path, vw))
    assert r["errors"] == []
    assert "Đây cũng là cách" not in r["plan_sum"]                       # L1: no orphan sentence before an amount
    assert PLAN["recommended"] is None and "gần như ngang nhau" in r["plan_sum"] and "Đề xuất" not in r["plan_sum"]
    assert r["usd_ph"] == "Ví dụ 5.000" and r["usd_on"] == ["true", "1.000,00"]
    before, picked = r["usd_before_pick"], r["usd_pick"]
    assert "Bấm một cách" in before[0] and before[1] == 1 and before[2] is True     # no schedule chosen for the user
    assert "Bạn chọn: Chia đều 52 tuần" in picked[0] and "19,23 $" in picked[0] and picked[1] == 52 and "19,23 $" in picked[2] and picked[3] is False
    assert "Số tiền quá nhỏ để chia 52 lần" in r["usd_small"] and "0,52 $" in r["usd_small"]
    v = r["view"]
    assert v["cls"] == "tr-view" and v["pressed"] == ["false", "false", "false", "true"] and v["tabs"] == "none" and v["ls"] == "none" and v["panels"] == 0 and v["tr"] != "none"
    assert r["price"] == usd(TR["close"])
    assert "Chưa mô hình nào đoán hướng giá tốt hơn tỷ lệ gốc" in r["head"] and "80 phép so sánh" in r["head"]
    r7 = next(x for x in TR["now"] if x["k"] == 7)
    c90 = TR["eval"]["7"]["models"][TR["eval"]["7"]["mag_model"]]["cover90"]
    assert "Giá sau 7 ngày nằm trong" in r["sure"] and usd(TR["close"] * (1 + r7["q5"])) in r["sure"] and usd(TR["close"] * (1 + r7["q95"])) in r["sure"]
    assert f"đúng {round(c90 * 100)}% số lần" in r["sure"] and "không cách nào đoán hướng tốt hơn tỷ lệ gốc" in r["sure"]
    assert r["cd"]["rows"] == 12 and "Nến ngày" in r["cd"]["today"] and r["model_cols"] == 8          # horizon + 6 models + learned model
    assert "16/16 kỳ hạn" in r["bt_notes"] and "Bitstamp" in r["bt_notes"]
    assert "9/10 lần" in r["cards"]["day"][0] if "cards" in r else True
    c = r["cards"]
    assert len(c["day"]) == 7 and len(c["week"]) == 4 and len(c["month"]) == 6 and "9/10 lần" in c["day"][0] and "8/10 lần" in c["day"][0]
    r30 = next(x for x in TR["now"] if x["k"] == 30)
    assert "1 tháng" in c["month"][0] and f"{round(r30['p'] * 100)}%" in c["month"][0] and "theo tỷ lệ gốc 4 năm" in c["month"][0]
    assert {"day": "1 ngày", "week": "1 tuần"}["day"] in c["day"][0] and "1 tuần" in c["week"][0]
    assert r["fan"] is not None and r["fan"][0] > 200 and r["fan"][1] == 2 and r["fan"][2] == 8      # 9/10 and 8/10 bands; now + 7 days
    t = r["tables"]
    assert t["t-tr-models"]["rows"] == 16 and t["t-tr-bt"]["rows"] == 16 and t["t-tr-cross"]["rows"] >= 6
    assert "Khớp" in t["t-tr-cross"]["text"] and "Chưa có lợi thế" in t["t-tr-bt"]["text"]
    assert r["hits"] == 32
    assert r["scroll_width"] <= vw and r["sell_scroll"] <= vw
    if vw < 700:
        assert all(x["stack"] and x["overflow"] <= 1 for x in t.values()) and r["cd"]["stack"]
    assert r["to_ls"] == "ls-view" and r["to_tr"] == "tr-view"
    assert r["after_sell"]["cls"] == "" and r["after_sell"]["stored"] is None
    # Chốt lời dần on the sell side, Giải ngân on the buy side
    assert r["sell_tab"] == "Chốt lời dần" and r["sell_vis"] == [True, False]
    assert "Nhập số BTC" in r["sp_empty"]
    n = SP["recommended"]
    assert f"Đề xuất: Chia đều {n} tuần" in r["sp_sum"] and r["sp_rows"] == n and r["sp_table"] == len(SP["options"])
    assert r["buy_tab"] == "Giải ngân" and r["buy_vis"] == [False, True]
