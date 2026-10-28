# -*- coding: utf-8 -*-
"""Snapshot tests of the rendered web page on a frozen synthetic data set (no network).

What is frozen, so any change shows up as a diff to approve:
- tests/snapshots/theme.css: the <style> block of src/page.html (colors, fonts, spacing, tables).
- tests/snapshots/ui_<scheme>_<width>.txt: all visible text of the page, buy and sell views.
- tests/snapshots/ui_styles_<scheme>.json: computed styles of the main components.
- tests/snapshots/ui/<platform>/*.png: screenshots, compared only on the platform that made them
  (fonts differ between Windows, Mac and Linux).

Update after reviewing a change:  UPDATE_SNAPSHOTS=1 python -m pytest tests/test_ui_snapshot.py
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SNAP = ROOT / "tests" / "snapshots"
OUT = ROOT / "tests" / "out"
UPDATE = os.environ.get("UPDATE_SNAPSHOTS") == "1"
FIXED_NOW = "2026-10-28T03:00:00Z"
FIXED_END = "2026-10-27T00:00:00Z"
VIEWS = [(1280, "light"), (390, "light"), (1280, "dark")]
STYLE_PROBES = {
    "body": "body", "h1": ".top h1", "price": ".top .price", "panel": ".panel", "h2": "h2", "lead": ".lead",
    "btn_main": ".btn.main", "btn": ".btn", "seg_on": ".seg button[aria-pressed=true]", "th": "#t-pa th",
    "td": "#t-pa td", "tag": ".tag", "cons": ".cons", "gauge_big": ".gauge .big b", "tile": ".tile",
    "tile_p": ".tile .p", "row_here": "tr.here td", "warn": ".warn", "foot": ".foot", "scroll": ".scroll",
}
STYLE_PROPS = ["color", "background-color", "font-family", "font-size", "font-weight", "line-height",
               "border-radius", "padding", "border-top-color", "border-top-width"]


def check(name: str, text: str) -> None:
    """Compare text with the stored snapshot (or store it when updating)."""
    f = SNAP / name
    if UPDATE or not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8", newline="\n")
        return
    old = f.read_text(encoding="utf-8")
    if old != text:
        (SNAP / (name + ".new")).write_text(text, encoding="utf-8", newline="\n")
        a, b = old.splitlines(), text.splitlines()
        k = next((i for i in range(max(len(a), len(b))) if (a[i] if i < len(a) else None) != (b[i] if i < len(b) else None)), 0)
        pytest.fail(f"{name} changed at line {k + 1}:\n- {a[k] if k < len(a) else ''}\n+ {b[k] if k < len(b) else ''}\n(new version saved as {name}.new)")


def test_theme_css_unchanged() -> None:
    page = (ROOT / "src" / "page.html").read_text(encoding="utf-8")
    css = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    check("theme.css", css.strip() + "\n")


@pytest.fixture(scope="module")
def built_page() -> pathlib.Path:
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415
    out = pathlib.Path(tempfile.mkdtemp()) / "page.html"
    build.build(str(out))
    return out


@pytest.fixture(scope="module")
def synth() -> dict:
    js = f"const {{make}}=require('./tests/gen_data.js');process.stdout.write(JSON.stringify(make(Date.parse('{FIXED_END}'))))"
    raw = subprocess.run(["node", "-e", js], cwd=ROOT, capture_output=True, check=True).stdout
    return json.loads(raw)


async def _render(page_path: pathlib.Path, data: dict, vw: int, scheme: str) -> dict:
    from playwright.async_api import async_playwright  # noqa: PLC0415
    cm, kl, fng, p = data["cm"], data["kl"], data["fng"], data["p"]
    H = {"Access-Control-Allow-Origin": "*"}

    async def route(r):
        u = r.request.url
        if "coinmetrics" in u:
            await r.fulfill(status=200, content_type="application/json", body=json.dumps({"data": cm}), headers=H)
        elif "alternative.me" in u:
            await r.fulfill(status=200, content_type="application/json", body=json.dumps({"data": fng}), headers=H)
        elif "klines" in u:
            s = int(re.search(r"startTime=(\d+)", u).group(1))
            await r.fulfill(status=200, content_type="application/json", body=json.dumps([k for k in kl if k[0] >= s][:1000]), headers=H)
        elif "ticker/price" in u:
            await r.fulfill(status=200, content_type="application/json", body=json.dumps({"price": str(p)}), headers=H)
        elif u.startswith("file://"):
            await r.continue_()
        else:
            await r.abort()

    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(viewport={"width": vw, "height": 900}, color_scheme=scheme, locale="vi-VN",
                                  timezone_id="Asia/Ho_Chi_Minh", device_scale_factor=1)
        pg = await ctx.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.clock.set_fixed_time(FIXED_NOW)
        await pg.route("**/*", route)
        await pg.goto(page_path.as_uri())
        await pg.wait_for_function("/^Xong/.test(document.getElementById('progress').textContent)", timeout=240000)
        await pg.wait_for_timeout(500)
        res = {"errors": errs}
        res["buy_text"] = await pg.evaluate("document.querySelector('.top').innerText + '\\n' + document.getElementById('app').innerText")
        res["styles"] = await pg.evaluate("""([probes, props]) => {
            const out = { vars: {} }, cs = getComputedStyle(document.documentElement);
            for (const v of ['--bg','--panel','--ink','--muted','--line','--soft','--jade','--brass','--cinnabar','--blue','--font']) out.vars[v] = cs.getPropertyValue(v).trim();
            for (const [k, sel] of Object.entries(probes)) { const e = document.querySelector(sel); if (!e) { out[k] = null; continue; }
              const s = getComputedStyle(e); out[k] = Object.fromEntries(props.map((p) => [p, s.getPropertyValue(p)])); }
            return out; }""", [STYLE_PROBES, STYLE_PROPS])
        OUT.mkdir(exist_ok=True)
        res["shot_buy"] = OUT / f"snap_{scheme}_{vw}_buy.png"
        await pg.screenshot(path=str(res["shot_buy"]), full_page=True)
        await pg.click("#mode-sell")
        await pg.wait_for_timeout(600)
        res["sell_text"] = await pg.evaluate("document.getElementById('sell-view').innerText")
        res["shot_sell"] = OUT / f"snap_{scheme}_{vw}_sell.png"
        await pg.screenshot(path=str(res["shot_sell"]), full_page=True)
        res["scroll_width"] = await pg.evaluate("document.documentElement.scrollWidth")
        await b.close()
    return res


def _same_image(a: pathlib.Path, b: pathlib.Path) -> float:
    """Share of pixels that differ noticeably between two screenshots (1.0 when sizes differ)."""
    from PIL import Image, ImageChops  # noqa: PLC0415
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return 1.0
    diff = ImageChops.difference(ia, ib).convert("L").point(lambda v: 255 if v > 24 else 0)
    return diff.histogram()[255] / (ia.size[0] * ia.size[1])


@pytest.mark.parametrize("vw,scheme", VIEWS)
def test_ui_snapshot(built_page: pathlib.Path, synth: dict, vw: int, scheme: str) -> None:
    pytest.importorskip("playwright")
    res = asyncio.run(_render(built_page, synth, vw, scheme))
    assert res["errors"] == []
    assert res["scroll_width"] <= vw, "page scrolls horizontally"
    check(f"ui_{scheme}_{vw}.txt", "=== BÊN MUA ===\n" + res["buy_text"].strip() + "\n\n=== BÊN BÁN ===\n" + res["sell_text"].strip() + "\n")
    if vw == 1280:
        check(f"ui_styles_{scheme}.json", json.dumps(res["styles"], ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    plat = SNAP / "ui" / sys.platform
    for key in ("shot_buy", "shot_sell"):
        shot = res[key]
        base = plat / shot.name
        if UPDATE or not base.exists():
            plat.mkdir(parents=True, exist_ok=True)
            base.write_bytes(shot.read_bytes())
            continue
        share = _same_image(shot, base)
        assert share <= 0.002, f"{shot.name}: {share:.2%} of pixels changed (see tests/out/)"
