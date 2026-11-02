# -*- coding: utf-8 -*-
"""Hồi cứu cắt ngang: tại 24 thời điểm trong quá khứ (ngày 1 hằng tháng, 11/2024 → 10/2026), mỗi phần của trang nói gì
(tính lại bằng đúng hàm của nó, chỉ dữ liệu có đến thời điểm đó), rồi so với điều đã xảy ra. Ghi docs/HOI_CUU.md.

Chạy: python tools/hoi_cuu.py   (không cần mạng; không ghi gì vào data/)
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot.backtest.metrics import wilson  # noqa: E402

DATES = list(pd.date_range("2024-11-01", "2026-10-01", freq="MS"))
OUT = ROOT / "docs" / "HOI_CUU.md"


def pct(x, d=0):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:.{d}f}%".replace(".", ",")


def spct(x, d=1):
    return "—" if x is None or not np.isfinite(x) else ("+" if x > 0 else "−" if x < 0 else "") + f"{abs(x) * 100:.{d}f}%".replace(".", ",")


def money(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:,.0f} $".replace(",", ".")


def share(flags: list[bool]) -> str:
    n, k = len(flags), int(sum(flags))
    if not n:
        return "chưa có kết quả"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {pct(k / n)} (Wilson 95%: {pct(lo)}–{pct(hi)})"


def f3(x: float) -> str:
    return "—" if not np.isfinite(x) else f"{x:.3f}".replace(".", ",")


def brier(p: list[float], y: list[bool]) -> float:
    return float(np.mean([(a - b) ** 2 for a, b in zip(p, y)])) if p else float("nan")


# ----- 1. Dự báo dải giá (thẻ Dự báo, bên mua và bên bán) -----
def bands() -> tuple[list[str], dict]:
    from bot.models import price_forecast as pf
    cfg, p = pf.spec(), pf.daily_prices()
    L, summ = ["## 1. Dải giá 7 ngày và 30 ngày (thẻ Dự báo)", "",
               "| Ngày gốc | Giá | Dải 7 ngày (8/10 lần) | Giá thật sau 7 ngày | Trúng | Dải 30 ngày | Giá thật sau 30 ngày | Trúng |", "|---|---|---|---|---|---|---|---|"], {}
    hits = {7: [], 30: []}
    b = {k: pf.bands(p, k, cfg) for k in (7, 30)}
    for T in DATES:
        cells = [T.strftime("%d/%m/%Y"), money(p.loc[T])]
        for k in (7, 30):
            q, t1 = b[k].loc[T], T + pd.Timedelta(days=k)
            a = p.get(t1, np.nan) if t1 in p.index else np.nan
            ok = bool(q["q10"] <= a <= q["q90"]) if np.isfinite(a) else None
            if ok is not None:
                hits[k].append(ok)
            cells += [f"{money(q['q10'])} – {money(q['q90'])}", money(a), "—" if ok is None else ("có" if ok else "**không**")]
        L.append("| " + " | ".join(cells) + " |")
    for k in (7, 30):
        summ[f"band{k}"] = hits[k]
    L += ["", f"Trúng khoảng 8/10 lần: 7 ngày {share(hits[7])}; 30 ngày {share(hits[30])}. Mục tiêu khoảng 80%.", ""]
    return L, summ


# ----- 2. Giá chờ mua −3% và giá chờ bán +3% trong 7 ngày (thẻ Giá & ngày mua / bán) -----
def touches() -> tuple[list[str], dict]:
    from bot.models import entry_timing as et, exit_timing as xt
    L, summ = ["## 2. Khả năng chạm giá chờ mua −3% và giá chờ bán +3% trong 7 ngày (thẻ Giá & ngày mua / bán)", "",
               "| Ngày gốc | Bot nói chạm −3% | Thật | Bot nói chạm +3% | Thật |", "|---|---|---|---|---|"], {}
    de, cfe = et.candles(), et.spec()
    dx, cfx = xt.candles(), xt.spec()
    qe, qx = et.z_quantiles(de, 7, cfe), xt.z_quantiles(dx, 7, cfx)
    se, sx = et.sigma(de["close"], cfe), xt.sigma(dx["close"], cfx)
    lo7, hi7 = et.next_min(de["low"], 7), xt.next_max(dx["high"], 7)
    pe, ye, px, yx = [], [], [], []
    for T in DATES:
        row = [T.strftime("%d/%m/%Y")]
        for q, s, d, nxt, sign, P, Y in ((qe, se, de, lo7, -1, pe, ye), (qx, sx, dx, hi7, 1, px, yx)):
            if T not in d.index or T not in q.index:
                row += ["—", "—"]
                continue
            sk = float(s.loc[T]) * np.sqrt(7)
            thr = np.log(1 + sign * 0.03) / sk
            z = q.loc[T].to_numpy()
            prob = float(et.touch_prob(np.array([thr]), z[None, :])[0]) if sign < 0 else float(xt.touch_up(np.array([thr]), z[None, :])[0])
            n = nxt.loc[T]
            hit = None if not np.isfinite(n) else bool(n <= d["close"].loc[T] * 0.97) if sign < 0 else bool(n >= d["close"].loc[T] * 1.03)
            if hit is not None:
                P.append(prob)
                Y.append(hit)
            row += [pct(prob), "—" if hit is None else ("chạm" if hit else "không chạm")]
        L.append("| " + " | ".join(row) + " |")
    L += ["", f"Giá chờ mua −3%: bot nói trung bình {pct(np.mean(pe))}, thực tế chạm {share(ye)}; sai số Brier {f3(brier(pe, ye))}.",
          f"Giá chờ bán +3%: bot nói trung bình {pct(np.mean(px))}, thực tế chạm {share(yx)}; sai số Brier {f3(brier(px, yx))}.", ""]
    summ.update(entry=(pe, ye), exit=(px, yx))
    return L, summ


# ----- 3. Xác suất có lãi 4 và 13 tuần (thẻ Dự báo, phần Xác suất có lãi) -----
def calib() -> tuple[list[str], dict]:
    from bot.features import weekly_close as wc
    from bot.models import calib_prob as cp
    t = wc.load(None)
    L, summ = ["## 3. Xác suất có lãi sau 4 và 13 tuần (thẻ Dự báo, Xác suất có lãi)", "",
               "| Tuần (Chủ nhật trước ngày gốc) | Bot nói có lãi 4 tuần | Thật | Bot nói có lãi 13 tuần | Thật |", "|---|---|---|---|---|"], {}
    pr = {h: cp.predictions(t, h) for h in (4, 13)}
    res = {h: ([], []) for h in (4, 13)}
    for T in DATES:
        w = t.index[t.index < T][-1]
        row = [w.strftime("%d/%m/%Y")]
        for h in (4, 13):
            x = pr[h].loc[w]
            p, y = float(x["base"]), x["y"]
            if np.isfinite(y):
                res[h][0].append(p)
                res[h][1].append(bool(y))
            row += [pct(p), "—" if not np.isfinite(y) else ("có lãi" if y else "lỗ")]
        L.append("| " + " | ".join(row) + " |")
    for h in (4, 13):
        p, y = res[h]
        L.append(f"- {h} tuần: bot nói trung bình {pct(np.mean(p))}, thực tế có lãi {share(y)}; Brier {f3(brier(p, y))} (nói 50% mọi lần thì Brier 0,250).")
    L.append("")
    summ.update(calib4=res[4], calib13=res[13])
    return L, summ


# ----- 4. Long/Short: công thức của tháng, số tiêu chí đạt lúc đó, lệnh thật trong tháng -----
def long_short() -> tuple[list[str], dict]:
    from bot.models import perp_trade as pt
    cfg = pt.spec()
    b = pt.build(cfg)
    book, sigs = b["book"], b["sigs"]
    rs = pt.rules(cfg)
    trades = pt.standalone(book, sigs, rs)
    months = pt.months_of(book, cfg)
    out_rows, summ = [], {}
    for sd in pt.SIDES:
        rs_sd = [r for r in rs if r.side == sd]
        sel = pt.selection(book, trades, rs_sd, cfg)
        wf, _ = pt.walk_forward(book, sigs, {m: v["rule"] for m, v in sel.items()})
        for i, m in enumerate(months):
            if m not in DATES:
                continue
            past = wf[wf["exit_t"] <= m]
            pm = months[:i] or [m]
            if len(past):
                half = pm[len(pm) // 2]
                side = {**pt.trade_stats(past), "boot": pt.boot_months(past, pm, n=2000), "halves": [pt.trade_stats(past[past["t"] < half]), pt.trade_stats(past[past["t"] >= half])]}
            else:
                side = {"n": 0, "boot": [None, None], "halves": [{"n": 0}, {"n": 0}]}
            c = pt.checklist_static(side, {"rule": sel[m]["rule"]})
            end = months[i + 1] if i + 1 < len(months) else pd.Timestamp.max
            tm = wf[(wf["t"] >= m) & (wf["t"] < end)]
            score = sum(c.values()) + 1 + (1 if len(tm) else 0)
            rid = sel[m]["rule"].id.replace("|", " · ") if sel[m]["rule"] else "đứng ngoài"   # "|" would break the Markdown table
            out_rows.append((m, sd, rid, score, len(tm), int((tm["net"] > 0).sum()), float(tm["R"].sum())))
    L = ["## 4. Long/Short: bot đề xuất gì mỗi tháng và lệnh thật ra sao", "",
         "| Tháng | Phía | Công thức của tháng | Tiêu chí đạt lúc đó | Đề xuất vào lệnh? | Lệnh trong tháng | Thắng | Tổng R |", "|---|---|---|---|---|---|---|---|"]
    for m, sd, rule, score, n, w, R in sorted(out_rows):
        L.append(f"| {m:%m/%Y} | {sd} | {rule} | {score}/6 | {'có' if score == 6 else 'không'} | {n} | {w} | {spct(R / 100, 1).replace('%', 'R') if n else '—'} |")
    calls = [x for x in out_rows if x[3] == 6]
    lw = [x for x in out_rows if x[1] == "long"]
    wins, n_tr = sum(x[5] for x in lw), sum(x[4] for x in lw)
    L += ["", f"Tháng đạt đủ 6/6 (bot sẽ nói Nên long / Nên short): {len(calls)}. Nếu đã vào lệnh theo công thức long của mọi tháng (bất chấp tiêu chí): "
          f"{n_tr} lệnh, thắng {share([True] * wins + [False] * (n_tr - wins)) if n_tr else '—'}, tổng {spct(sum(x[6] for x in lw) / 100, 1).replace('%', 'R')}. "
          "Tức là tiêu chí đã chặn đúng những tháng lẽ ra thua.", ""]
    summ["ls_calls"] = len(calls)
    summ["ls_long"] = (n_tr, wins, sum(x[6] for x in lw))
    return L, summ


# ----- 5. Xu hướng: hướng và khoảng giá 7, 30, 90 ngày -----
def trend() -> tuple[list[str], dict]:
    from bot.models import trend as tr
    cfg = tr.spec()
    d = tr.load()
    bs = tr.base_states(d, cfg)
    L = ["## 5. Xu hướng: hướng và khoảng giá sau 7, 30, 90 ngày (thẻ Xu hướng)", "",
         "| Ngày gốc | 7 ngày: bot nói | thật | 30 ngày: bot nói | thật | 90 ngày: bot nói | thật |", "|---|---|---|---|---|---|---|"]
    lab = {"tang": "nghiêng tăng", "giam": "nghiêng giảm", "khong_ro": "không rõ"}
    pr = {k: tr.predict(d, bs, k, cfg) for k in (7, 30, 90)}
    res = {k: {"called": [], "cover": [], "p": [], "y": []} for k in pr}
    for T in DATES:
        row = [T.strftime("%d/%m/%Y")]
        for k, x in pr.items():
            m = x["models"]["goc"].loc[T]
            p, r = float(m["p"]), x["r"].loc[T]
            sk = float(x["sig"].loc[T] * np.sqrt(k))
            label = tr.label(p, cfg)
            if np.isfinite(r):
                res[k]["p"].append(p)
                res[k]["y"].append(bool(r > 0))
                res[k]["cover"].append(bool(m[0.1] * sk <= r <= m[0.9] * sk))
                if label != "khong_ro":
                    res[k]["called"].append((label == "tang") == (r > 0))
            row += [f"{lab[label]} ({pct(p)})", "—" if not np.isfinite(r) else spct(np.exp(r) - 1)]
        L.append("| " + " | ".join(row) + " |")
    L.append("")
    for k, v in res.items():
        L.append(f"- {k} ngày: khi bot nghiêng một phía, đúng {share(v['called'])}; Brier {f3(brier(v['p'], v['y']))} (nói 50% mọi lần thì 0,250); "
                 f"giá thật nằm trong khoảng 8/10 lần {share(v['cover'])}.")
    L.append("")
    return L, {"trend": res}


def main() -> None:
    parts = [bands(), touches(), calib(), long_short(), trend()]
    s = {k: v for _, x in parts for k, v in x.items()}
    head = ["# Hồi cứu cắt ngang các phần của trang (02/11/2026)", "",
            f"Tại {len(DATES)} thời điểm ({DATES[0]:%d/%m/%Y} → {DATES[-1]:%d/%m/%Y}, ngày 1 hằng tháng), tính lại điều mỗi phần của trang đã nói **chỉ bằng dữ liệu có đến lúc đó** "
            "(cùng hàm mà trang dùng), rồi so với điều đã xảy ra. Các thời điểm cách nhau 1 tháng nên kỳ hạn đến 30 ngày không chồng nhau; 90 ngày và 13 tuần thì chồng nhau, "
            "khoảng tin cậy thực tế rộng hơn số ghi. 24 thời điểm là ít: đây là kiểm tra sức khỏe, không phải kiểm định (kiểm định dài hạn nằm trong từng thẻ).", "",
            "Tạo bằng `python tools/hoi_cuu.py`.", "",
            "## Tóm tắt", "", "| Phần | Kiểm tra | Kết quả | Đánh giá |", "|---|---|---|---|",
            f"| Dự báo dải giá | Trúng khoảng 8/10 lần, 7 và 30 ngày | 7 ngày: {share(s['band7'])}; 30 ngày: {share(s['band30'])} | đúng tỷ lệ khi khoảng tin cậy chứa 80% |",
            f"| Giá chờ mua / bán | Khả năng chạm ±3% trong 7 ngày | mua: nói {pct(np.mean(s['entry'][0]))}, chạm {share(s['entry'][1])}; bán: nói {pct(np.mean(s['exit'][0]))}, chạm {share(s['exit'][1])} | đúng khi tỷ lệ chạm gần mức bot nói |",
            f"| Xác suất có lãi | 4 và 13 tuần | 4 tuần: nói {pct(np.mean(s['calib4'][0]))}, có lãi {share(s['calib4'][1])}; 13 tuần: nói {pct(np.mean(s['calib13'][0]))}, có lãi {share(s['calib13'][1])} | tỷ lệ gốc, không đoán thời điểm |",
            f"| Long/Short | Tháng đạt 6/6 | {s['ls_calls']} tháng; long theo công thức mọi tháng: {s['ls_long'][0]} lệnh, tổng {spct(s['ls_long'][2] / 100, 1).replace('%', 'R')} | không đề xuất là đúng khi tổng R âm |",
            f"| Xu hướng | Đúng hướng khi nghiêng 1 phía, 30 ngày | {share(s['trend'][30]['called'])} | tỷ lệ gốc, không phải tín hiệu |", ""]
    body = [line for L, _ in parts for line in L]
    OUT.write_text("\n".join(head + body) + "\nCông cụ tham khảo, không phải lời khuyên đầu tư.\n", encoding="utf-8", newline="\n")
    print("\n".join(head))


if __name__ == "__main__":
    main()
