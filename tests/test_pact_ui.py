# -*- coding: utf-8 -*-
"""The entry-check panel of the Price action view (src/pact.js) on panel data built from synthetic candles: it renders
without errors, its entry check gives exactly what bot/models/pa_sheet.check gives for many entries, a wrong stop is
refused, "take the Long/Short plan" fills the inputs from the plan above, and nothing scrolls sideways on a phone."""
from __future__ import annotations

import asyncio
import json
import pathlib
import re
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

from bot.models import pa_sheet as ps

ROOT = pathlib.Path(__file__).resolve().parent.parent


def synth() -> pd.DataFrame:
    rng = np.random.default_rng(21)
    n = 2600
    c = 400 * np.exp(np.cumsum(rng.normal(0.0006, 0.03, n)))
    o = np.r_[c[0], c[:-1]] * np.exp(rng.normal(0, 0.004, n))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.012, n)))
    lo = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.012, n)))
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c}, index=pd.date_range("2014-01-01", periods=n, freq="D"))


@pytest.fixture(scope="module")
def built() -> tuple[pathlib.Path, dict]:
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415
    tmp = pathlib.Path(tempfile.mkdtemp())
    o = ps.run(write=False, d=synth())
    (tmp / "pa.json").write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
    build.PACT_PATH = str(tmp / "pa.json")
    try:
        out = build.build(str(tmp / "page.html"), kn_path=str(ROOT / "tests" / "fixtures" / "recommendation.json"),
                          ls_path=str(ROOT / "tests" / "fixtures" / "perp.json"), lt_path=str(ROOT / "tests" / "fixtures" / "perp_trade.json"))
    finally:
        build.PACT_PATH = None
    return pathlib.Path(out), json.loads(json.dumps(o))


def cases(o: dict) -> list[tuple]:
    rng = np.random.default_rng(3)
    c, a, out = o["state"]["close"], o["state"]["atr"], []
    for i in range(40):
        side, H = ("long", "short")[i % 2], (7, 30)[(i // 2) % 2]
        E = c * (1 + rng.uniform(-0.15, 0.15))
        g = 1 if side == "long" else -1
        SL = None if i % 3 == 0 else E - g * a * rng.uniform(0.2, 9)
        TP = None if i % 4 == 0 else E + g * a * rng.uniform(0.2, 9)
        out.append((side, E, SL, TP, H))
    out += [("long", c, None, None, 30), ("short", c, None, None, 7), ("long", c, c + a, c + 2 * a, 7)]   # the last one is invalid
    return out


async def _run(page: pathlib.Path, o: dict, vw: int) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(viewport={"width": vw, "height": 900}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")
        pg = await ctx.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file://") else r.abort())
        await pg.route_web_socket(re.compile(".*"), lambda ws: None)
        await pg.goto(page.as_uri())
        await pg.wait_for_timeout(500)
        await pg.click("#mode-ls")                 # the Long/Short plan sets window.LT_PLAN for the "from plan" button
        await pg.wait_for_timeout(400)
        await pg.click("#mode-pa")
        await pg.wait_for_timeout(400)
        res = {"errors": errs, "text": await pg.inner_text("#pact-sec"), "answer": await pg.inner_text("#pact-answer"),
               "scroll": await pg.evaluate("document.documentElement.scrollWidth")}
        res["js"] = await pg.evaluate("(cs) => cs.map(([s, E, SL, TP, H]) => window.BOT_PACT.check(s, E, SL, TP, H))", [list(x) for x in cases(o)])
        await pg.fill("#pact-stop", str(round(o["state"]["close"] * 1.05)))
        await pg.wait_for_timeout(100)
        res["invalid"] = await pg.inner_text("#pact-answer")
        await pg.click("#pact-plan")
        await pg.wait_for_timeout(200)
        res["plan"] = await pg.evaluate("""() => ({ plan: window.LT_PLAN, entry: document.getElementById('pact-entry').value,
            side: document.querySelector('#pact-side button[aria-pressed=true]').dataset.s, answer: document.getElementById('pact-answer').innerText })""")
        await b.close()
        return res


@pytest.mark.parametrize("vw", [1280, 390])
def test_price_action_panel(built, vw):
    page, o = built
    res = asyncio.run(_run(page, o, vw))
    assert res["errors"] == []
    assert "Price action" in res["text"] and "0/48" in res["text"] and "không phải tín hiệu vào lệnh" in res["text"]
    assert ("Ngang mức hòa vốn" in res["answer"]) or ("Bất lợi" in res["answer"]) or ("Có lợi" in res["answer"])
    for (side, E, SL, TP, H), js in zip(cases(o), res["js"]):
        py = ps.check(o, side, E, SL, TP, H)
        assert js["valid"] == py["valid"]
        assert js["SL"] == pytest.approx(py["SL"]) and js["TP"] == pytest.approx(py["TP"])
        if py["valid"]:
            for k in ("p", "q", "Pt", "Ps", "Pn", "n_eff", "exp_r", "rr"):
                assert js[k] == pytest.approx(py[k], rel=1e-9, abs=1e-12), k
            assert js["verdict"] == py["verdict"] and js["clamped"] == py["clamped"]
    assert "Lệnh Long cần giá cắt lỗ thấp hơn" in res["invalid"]
    p = res["plan"]
    assert p["plan"] and p["side"] == p["plan"]["side"]
    assert abs(float(p["entry"].replace(".", "").replace(",", ".")) - p["plan"]["E"]) < 0.06
    assert "Vị trí" in p["answer"] and "Trong lịch sử" in p["answer"]
    assert res["scroll"] <= vw
