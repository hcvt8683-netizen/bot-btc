# -*- coding: utf-8 -*-
"""Thử giao diện trong trình duyệt không màn hình, với dữ liệu giả lập (không cần mạng).
Cần: pip install playwright && python -m playwright install chromium
Chạy: python build.py && python tests/test_browser.py   (ảnh chụp lưu ở tests/out/)
"""
import os, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "bot-xac-suat.html").as_uri()
OUT = str(ROOT / "tests" / "out"); os.makedirs(OUT, exist_ok=True)
import json, asyncio, math, random, datetime, re
random.seed(5)
start = datetime.date(2010,7,18); end = datetime.date.today() - datetime.timedelta(days=1)
cm, fng, kl = [], [], []; p = 0.08; rp = 0.08; i = 0; d = start; prev = p
while d <= end:
    cyc = math.sin(i/1461*2*math.pi)
    p *= math.exp(0.0016 + 0.004*cyc + (random.random()-0.5)*0.07 - 0.0008*math.log(p/rp)); rp += (p-rp)/500
    issue = 7200 if i<800 else 3600 if i<2300 else 1800 if i<3700 else 900 if i<5100 else 450
    cm.append({"asset":"btc","time":d.isoformat()+"T00:00:00.000000000Z","PriceUSD":str(p),"CapMrktCurUSD":str(p*(3e6+i*4000)),"CapMVRVCur":str(p/rp),"IssTotUSD":str(issue*p)})
    ts = int(datetime.datetime(d.year,d.month,d.day,tzinfo=datetime.timezone.utc).timestamp())
    if d >= datetime.date(2018,2,1): fng.append({"value":str(max(1,min(99,round(50+30*cyc+(random.random()-0.5)*40)))),"timestamp":str(ts)})
    if d >= datetime.date(2017,8,17):
        mv = abs(math.log(p/prev)); kl.append([ts*1000,"0","0","0",str(p),"0",0,str(1e9*(1+i/3000)*(0.5+random.random())*(1+mv*40))])
    prev = p; d += datetime.timedelta(days=1); i += 1
fng.reverse()


from playwright.async_api import async_playwright
import csv, io
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        for vw, scheme in [(1280, 'light'), (390, 'light'), (1280, 'dark')]:
            ctx = await b.new_context(viewport={'width': vw, 'height': 900}, color_scheme=scheme, accept_downloads=True)
            pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            async def route(r):
                u = r.request.url; H = {"Access-Control-Allow-Origin": "*"}
                if 'coinmetrics' in u: await r.fulfill(status=200, content_type='application/json', body=json.dumps({"data": cm}), headers=H)
                elif 'alternative.me' in u: await r.fulfill(status=200, content_type='application/json', body=json.dumps({"data": fng}), headers=H)
                elif 'klines' in u:
                    s_ = int(re.search(r'startTime=(\d+)', u).group(1)); await r.fulfill(status=200, content_type='application/json', body=json.dumps([k for k in kl if k[0] >= s_][:1000]), headers=H)
                elif 'ticker/price' in u: await r.fulfill(status=200, content_type='application/json', body=json.dumps({"price": str(p)}), headers=H)
                elif u.startswith('file://'): await r.continue_()
                else: await r.abort()
            await pg.route('**/*', route)
            t0 = datetime.datetime.now()
            await pg.goto(PAGE)
            await pg.wait_for_selector('#app:not([hidden])', timeout=150000)
            await pg.wait_for_function("document.querySelectorAll('#t-pa tbody tr').length > 0", timeout=120000); await pg.wait_for_timeout(800)
            tag = f'{scheme}_{vw}'
            print(tag, 'ready', round((datetime.datetime.now() - t0).total_seconds(), 1), 's |', await pg.text_content('#progress'))
            print('  set buttons:', ' | '.join([t.strip() for t in await pg.locator('#sets button').all_text_contents()]))
            print('  options rows:', await pg.locator('#t-pa tbody tr').count(), '| ind charts:', await pg.locator('#ind-charts canvas').count())
            await pg.screenshot(path=OUT + f'/o_{tag}.png', full_page=True)
            await pg.click('#mode-sell'); await pg.wait_for_timeout(600)
            print('  sell visible:', await pg.is_visible('#sell-view'), '| buy hidden:', not await pg.is_visible('#buy-view'))
            print('  hero:', (await pg.text_content('#s-hero'))[:220])
            await pg.screenshot(path=OUT + f'/s_{tag}.png', full_page=True)
            if tag == 'light_1280':
                await pg.fill('#s-cost', '62000'); await pg.fill('#s-qty', '0.5'); await pg.wait_for_timeout(200)
                print('  P/L line:', (await pg.text_content('#s-hero .pl'))[-160:])
                print('  tp rows:', await pg.locator('#t-tp tbody tr').count(), '| levels rows:', await pg.locator('#t-tplv tbody tr').count(), '| sim rows:', await pg.locator('#t-sim tbody tr').count())
                print('  weak note:', (await pg.text_content('#s-tp-weak'))[:160] if await pg.locator('#s-tp-weak').count() else '-')
                async with pg.expect_download() as dl: await pg.click('#dl-tp')
                d = await dl.value; raw = open(await d.path(), 'rb').read().decode('utf-8-sig'); rows = list(csv.reader(io.StringIO(raw)))
                print('  ', d.suggested_filename, 'rows', len(rows), 'cols', len(rows[0]))
                async with pg.expect_download() as dl2: await pg.click('#dl-md')
                d2 = await dl2.value; md = open(await d2.path(), encoding='utf-8').read(); print('   report has sell section:', '## Bên bán' in md)
                await pg.locator('#s-chart').scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
                box = await pg.locator('#s-chart').bounding_box(); await pg.mouse.click(box['x'] + box['width'] * 0.6, box['y'] + 80); await pg.wait_for_timeout(2500)
                print('  after sell-chart click date:', await pg.input_value('#date'), '| hero:', (await pg.text_content('#s-hero'))[:80])
                await pg.reload(); await pg.wait_for_selector('#app:not([hidden])', timeout=150000); await pg.wait_for_timeout(1500)
                print('  mode remembered after reload:', await pg.is_visible('#sell-view'), '| cost kept:', await pg.input_value('#s-cost'))
                await pg.click('#mode-buy'); await pg.wait_for_timeout(300); print('  back to buy:', await pg.is_visible('#buy-view'))
            print(tag, 'errors:', errs, 'scrollWidth', await pg.evaluate('document.documentElement.scrollWidth'))
        await b.close()
asyncio.run(main())
