# -*- coding: utf-8 -*-
"""Hồi cứu mở rộng: tại nhiều thời điểm trong quá khứ, tính lại điều bot đã nói (đúng hàm của trang, chỉ dữ liệu
có đến lúc đó), rồi so với điều đã xảy ra. Thời điểm cách nhau đúng bằng kỳ hạn nên các lần không chồng nhau.

Kiểm tra sức khỏe, không phải kiểm định: mỗi phần đã có kiểm định đăng ký trước riêng. Phần 1 so cả cách tính dải giá đang
dùng với cách cũ chỉ dùng độ dao động 30 ngày (đổi ngày 03/11/2026, docs/FORECAST_REGIME.md).

Chạy: python tools/hoi_cuu_mo_rong.py   (hoặc make hoi-cuu; không cần mạng; chỉ ghi docs/HOI_CUU_MO_RONG.md)
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "HOI_CUU_MO_RONG.md"
sys.path.insert(0, str(ROOT))
from bot.backtest.metrics import wilson  # noqa: E402

L: list[str] = []


def pct(x, d=0):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:.{d}f}%".replace(".", ",")


def share(flags) -> str:
    flags = [bool(f) for f in flags]
    n, k = len(flags), int(sum(flags))
    if not n:
        return "—"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {pct(k / n)} ({pct(lo)}–{pct(hi)})"


def f3(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:.3f}".replace(".", ",")


def every(index: pd.DatetimeIndex, start: str, step: int) -> list[pd.Timestamp]:
    t, out, last = pd.Timestamp(start), [], index.max()
    while t <= last:
        out.append(t)
        t += pd.Timedelta(days=step)
    return out


# ---------- 1. Dải giá (thẻ Dự báo) ----------
def bands():
    from bot.models import forecast_regime as fr, price_forecast as pf
    cfg, p = pf.spec(), pf.daily_prices()
    old = {k: v for k, v in cfg.items() if k != "vol_long_days"}  # cách dùng đến 03/11/2026: chỉ độ dao động 30 ngày
    sig = np.log(p).diff().rolling(cfg["vol_days"], min_periods=cfg["vol_days"]).std()
    grp = fr.vol_group(p, cfg, fr.spec()["regime"])  # 0/1/2 = 1/3 êm nhất, giữa, 1/3 mạnh nhất so với 4 năm trước (chỉ quá khứ)
    L.extend(["## 1. Dự báo dải giá (thẻ Dự báo): giá thật có nằm trong dải bot đưa ra không", "",
              "Mỗi thời điểm: dải 8/10 lần (q10–q90) và 5/10 lần (q25–q75) tính bằng `price_forecast.bands`, so với giá đóng thật sau k ngày. "
              "\"Đang dùng\" = độ dao động trộn 30 ngày và 365 ngày (từ 03/11/2026); \"cũ\" = chỉ 30 ngày. "
              "Nhóm độ dao động: độ dao động 30 ngày lúc dự báo so với 4 năm trước đó. Dải đúng thì mọi nhóm đều gần 80%.", ""])
    worst = []
    for k in (1, 7, 30):
        res = {}
        for name, c in (("đang dùng", cfg), ("cũ (30 ngày)", old)):
            b = pf.bands(p, k, c)
            rows = []
            for t in every(p.index, "2018-01-01", k):
                a = p.get(t + pd.Timedelta(days=k), np.nan)
                if t not in b.index or not np.isfinite(b.loc[t, "q10"]) or not np.isfinite(a) or not np.isfinite(grp.get(t, np.nan)):
                    continue
                q = b.loc[t]
                rows.append({"t": t, "y": t.year, "in80": q["q10"] <= a <= q["q90"], "in50": q["q25"] <= a <= q["q75"], "above": a > q["q90"], "below": a < q["q10"],
                             "z": np.log(a / p.loc[t]) / (sig.loc[t] * np.sqrt(k)), "g": int(grp.loc[t]), "p0": p.loc[t], "a": a, "q10": q["q10"], "q90": q["q90"],
                             "w": q["q90"] / q["q10"] - 1})
            res[name] = pd.DataFrame(rows)
        d = res["đang dùng"]
        L.extend([f"### Kỳ hạn {k} ngày ({len(d)} lần không chồng nhau, từ {d.t.min():%m/%Y})", "",
                  "| Cách tính | Trong dải 8/10 | Trong dải 5/10 | Trên dải / dưới dải | Lúc êm (1/3) | Lúc giữa | Lúc mạnh (1/3) | Độ rộng dải 8/10 (trung vị) |",
                  "|---|---|---|---|---|---|---|---|"])
        for name, x in res.items():
            gs = [share(x[x.g == g].in80) for g in (0, 1, 2)]
            L.append(f"| {name} | **{share(x.in80)}** | {share(x.in50)} | {int(x.above.sum())} / {int(x.below.sum())} | " + " | ".join(gs) + f" | {pct(x.w.median(), 1)} |")
        L.extend(["", "Cách đang dùng theo năm:", "", "| Năm | Số lần | Trong dải 8/10 | Trong dải 5/10 | Trên dải | Dưới dải |", "|---|---|---|---|---|---|"])
        for y, g in d.groupby("y"):
            L.append(f"| {y} | {len(g)} | {share(g.in80)} | {share(g.in50)} | {int(g.above.sum())} | {int(g.below.sum())} |")
        L.append("")
        if k == 7:
            worst = d.reindex(d.z.abs().sort_values(ascending=False).index).head(8)
    L.extend(["### 8 lần trượt xa nhất (kỳ hạn 7 ngày, cách đang dùng)", "", "| Ngày dự báo | Giá lúc đó | Dải 8/10 lần | Giá thật sau 7 ngày | Lệch (lần độ dao động 30 ngày) |",
              "|---|---|---|---|---|"])
    for _, r in worst.iterrows():
        L.append(f"| {r.t:%d/%m/%Y} | {r.p0:,.0f} $ | {r.q10:,.0f} – {r.q90:,.0f} $ | {r.a:,.0f} $ | {r.z:+.1f} |".replace(",", "."))
    L.append("")


# ---------- 2. Khả năng chạm giá chờ mua / bán (thẻ Giá & ngày mua / bán) ----------
def touches():
    from bot.models import entry_timing as et, exit_timing as xt
    L.extend(["## 2. Giá chờ mua / bán (thẻ Giá & ngày mua / bán): bot nói x% khả năng chạm, thực tế chạm bao nhiêu", "",
              "Mỗi tuần một lần (7 ngày không chồng nhau) từ 2016, các mức ±1, 2, 3, 5, 8%. Dùng `z_quantiles`, `touch_prob`, `touch_up` của trang, nến ngày Bitstamp.", ""])
    out = {}
    for side, mod, nxt_f, col, sign in (("mua", et, et.next_min, "low", -1), ("bán", xt, xt.next_max, "high", 1)):
        d, cfg = mod.candles(), mod.spec()
        q, s, nx = mod.z_quantiles(d, 7, cfg), et.sigma(d["close"], cfg), nxt_f(d[col], 7)
        rows = []
        for t in every(d.index, "2016-01-04", 7):
            if t not in q.index or not np.isfinite(q.loc[t].to_numpy()).all() or not np.isfinite(nx.get(t, np.nan)):
                continue
            sk, z, c = float(s.loc[t]) * np.sqrt(7), q.loc[t].to_numpy(), float(d["close"].loc[t])
            ma = d["close"].loc[:t].tail(200).mean()
            for x in (0.01, 0.02, 0.03, 0.05, 0.08):
                thr = np.log(1 + sign * x) / sk
                prob = float(et.touch_prob(np.array([thr]), z[None, :])[0]) if sign < 0 else float(xt.touch_up(np.array([thr]), z[None, :])[0])
                hit = nx.loc[t] <= c * (1 - x) if sign < 0 else nx.loc[t] >= c * (1 + x)
                rows.append({"t": t, "y": t.year, "x": x, "p": prob, "hit": bool(hit), "above_ma": c > ma})
        r = pd.DataFrame(rows)
        out[side] = r
        L.extend([f"### Giá chờ {side} ({r.t.nunique()} tuần)", "", "| Bot nói | Số lần | Bot nói trung bình | Thực tế chạm (Wilson 95%) |", "|---|---|---|---|"])
        r["bin"] = pd.cut(r.p, [0, .2, .4, .6, .8, 1.0001], labels=["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"])
        for b, g in r.groupby("bin", observed=True):
            L.append(f"| {b} | {len(g)} | {pct(g.p.mean())} | {share(g.hit)} |")
        brier = float(((r.p - r.hit) ** 2).mean())
        L.extend(["", f"Sai số Brier {f3(brier)} (càng thấp càng tốt).", "",
                  f"Mức {'−' if sign < 0 else '+'}3% theo năm:", "", "| Năm | Bot nói trung bình | Thực tế chạm | Lệch |", "|---|---|---|---|"])
        g3 = r[r.x == 0.03]
        for y, g in g3.groupby("y"):
            L.append(f"| {y} | {pct(g.p.mean())} | {share(g.hit)} | {(g.hit.mean() - g.p.mean()) * 100:+.0f} điểm |".replace(".", ","))
        L.extend(["", "| Thị trường lúc đó | Bot nói trung bình | Thực tế chạm | Lệch |", "|---|---|---|---|"])
        for a, g in g3.groupby("above_ma"):
            L.append(f"| {'trên' if a else 'dưới'} MA 200 ngày | {pct(g.p.mean())} | {share(g.hit)} | {(g.hit.mean() - g.p.mean()) * 100:+.0f} điểm |")
        L.append("")
    return out


# ---------- 3. Xác suất có lãi (thẻ Dự báo, Xác suất có lãi) ----------
def calib():
    from bot.features import weekly_close as wc
    from bot.models import calib_prob as cp
    t = wc.load(None)
    L.extend(["## 3. Xác suất có lãi (mua tuần đó, giữ h tuần)", "",
              "Mỗi h tuần một lần (không chồng nhau). Cột \"tỷ lệ gốc\" là con số trang đang hiện; \"mô hình\" là hồi quy logistic trên 3 chỉ số rẻ (trang không dùng vì không thắng).", "",
              "| Kỳ hạn | Số lần | Bot nói (tỷ lệ gốc) | Thực tế có lãi | Brier tỷ lệ gốc | Brier mô hình | Brier nếu luôn nói 50% |", "|---|---|---|---|---|---|---|"])
    for h in (4, 13, 26, 52):
        pr = cp.predictions(t, h)
        pr = pr[np.isfinite(pr.base) & np.isfinite(pr.y)]
        pr = pr.iloc[::h]
        b1 = float(((pr.base - pr.y) ** 2).mean())
        m = pr[np.isfinite(pr.logit)]
        b2 = float(((m.logit - m.y) ** 2).mean()) if len(m) else np.nan
        L.append(f"| {h} tuần | {len(pr)} | {pct(pr.base.mean())} | {share(pr.y.astype(bool))} | {f3(b1)} | {f3(b2)} | {f3(float(((0.5 - pr.y) ** 2).mean()))} |")
    L.append("")


# ---------- 4. Xu hướng (thẻ Xu hướng) ----------
def trend():
    from bot.models import trend as tr
    cfg = tr.spec()
    d = tr.load()
    bs = tr.base_states(d, cfg)
    L.extend(["## 4. Xu hướng (thẻ Xu hướng): khi bot nghiêng một phía, có đúng hướng không", "",
              "Bot nghiêng tăng khi P(tăng) ≥ 55%, nghiêng giảm khi ≤ 45%. Mỗi k ngày một lần từ 2016. \"Mốc luôn nói tăng\" = tỷ lệ số lần giá thật tăng.", "",
              "| Kỳ hạn | Mô hình | Số lần nghiêng | Đúng hướng khi nghiêng | Mốc luôn nói tăng (cùng các lần đó) | Khoảng 8/10 lần chứa giá thật |", "|---|---|---|---|---|---|"])
    for k in (7, 30, 90):
        x = tr.predict(d, bs, k, cfg)
        for name in ("goc", "ket_hop"):
            m = x["models"][name]
            called, base_up, cover = [], [], []
            for t in every(d.index, "2016-01-01", k):
                if t not in m.index:
                    continue
                p, r = m.loc[t, "p"], x["r"].get(t, np.nan)
                if not (np.isfinite(p) and np.isfinite(r)):
                    continue
                sk = float(x["sig"].loc[t] * np.sqrt(k))
                cover.append(m.loc[t, 0.1] * sk <= r <= m.loc[t, 0.9] * sk)
                lab = tr.label(p, cfg)
                if lab != "khong_ro":
                    called.append((lab == "tang") == (r > 0))
                    base_up.append(r > 0)
            L.append(f"| {k} ngày | {'tỷ lệ gốc' if name == 'goc' else 'kết hợp 4 trạng thái'} | {len(called)} | {share(called)} | {share(base_up)} | {share(cover)} |")
    L.append("")


# ---------- 5. Long/Short (thẻ Long/Short) ----------
def long_short():
    from bot.models import perp_trade as pt
    cfg = pt.spec()
    b = pt.build(cfg)
    book, sigs = b["book"], b["sigs"]
    rs = pt.rules(cfg)
    trades = pt.standalone(book, sigs, rs)
    L.extend(["## 5. Long/Short có cắt lỗ / chốt lời: nếu mỗi tháng làm theo công thức bot chọn lúc đó", "",
              "Công thức của tháng chọn chỉ trên lệnh đã đóng trước tháng đó (`perp_trade.selection`), rồi vào lệnh thật trong tháng (`walk_forward`). R = số lần mức cắt lỗ.", "",
              "| Năm | Phía | Số lệnh | Thắng (sau phí) | Tổng R | R trung bình mỗi lệnh |", "|---|---|---|---|---|---|"])
    for sd in pt.SIDES:
        sel = pt.selection(book, trades, [r for r in rs if r.side == sd], cfg)
        wf, _ = pt.walk_forward(book, sigs, {m: v["rule"] for m, v in sel.items()})
        if not len(wf):
            L.append(f"| tất cả | {sd} | 0 | — | — | — |")
            continue
        wf = wf.assign(y=pd.to_datetime(wf["t"]).dt.year)
        for y, g in wf.groupby("y"):
            L.append(f"| {y} | {sd} | {len(g)} | {share(g.net > 0)} | {g.R.sum():+.1f}R | {g.R.mean():+.2f}R |".replace(".", ","))
        L.append(f"| **tất cả** | {sd} | {len(wf)} | {share(wf.net > 0)} | {wf.R.sum():+.1f}R | {wf.R.mean():+.2f}R |".replace(".", ","))
    L.append("")


# ---------- 6. Nhật ký trực tiếp: dự báo ghi thật lúc đó, nay đã đến hạn ----------
def live():
    from bot.models import price_forecast as pf, entry_timing as et, exit_timing as xt
    L.extend(["## 6. Nhật ký trực tiếp (dự báo ghi thật từ 28/10/2026, đã đến hạn)", "",
              "Đây là phép thử sạch nhất (bot không thể biết trước), nhưng mới vài ngày: các dự báo cùng ngày đích chồng lên nhau, chưa đủ để kết luận.", ""])
    p = pf.daily_prices()
    s = pf.score_log(p, recent=100)
    done = s["recent"]
    if done:
        df = pd.DataFrame(done)
        n_days = df.target.nunique()
        L.append(f"- Dải giá: {len(df)} dự báo đã đến hạn (từ {df.issued.nunique()} ngày ghi, {n_days} ngày đích). Trong dải 8/10 lần {share(df.in80)}; dải 5/10 lần {share(df.in50)}.")
        L.extend(["", "| Ghi ngày | Ngày đích | Kỳ hạn | Dải 8/10 lần | Giá thật | Trúng |", "|---|---|---|---|---|---|"])
        for r in done:
            L.append(f"| {r['issued']} | {r['target']} | {r['k']} | {float(r['q10']):,.0f} – {float(r['q90']):,.0f} $ | {r['actual']:,.0f} $ | {'có' if r['in80'] else '**không**'} |".replace(",", "."))
    for name, mod in (("Giá thấp nhất (giá chờ mua)", et), ("Giá cao nhất (giá chờ bán)", xt)):
        sc = mod.score_log(mod.candles(), recent=100)
        rec = sc.get("recent", [])
        if rec:
            L.append(f"- {name}: {len(rec)} dự báo đến hạn, trong dải 8/10 lần {share([r['in80'] for r in rec])}.")
    L.append("")


if __name__ == "__main__":
    import warnings
    warnings.simplefilter("ignore")
    L.extend(["# Hồi cứu mở rộng: dự báo tại các thời điểm quá khứ đúng hay sai", "",
              f"Tạo lúc {pd.Timestamp.now('UTC'):%d/%m/%Y %H:%M} UTC bằng `python tools/hoi_cuu_mo_rong.py`. Mỗi thời điểm chỉ dùng dữ liệu có đến lúc đó (cùng hàm của trang), "
              "rồi so với điều đã xảy ra. Các thời điểm cách nhau đúng bằng kỳ hạn nên không chồng nhau. Trong ngoặc là khoảng tin cậy Wilson 95%. "
              "Đây là kiểm tra sức khỏe, không phải kiểm định mới: phần lớn giai đoạn này các kiểm định của từng thẻ đã xem.", ""])
    for f in (bands, touches, calib, trend, long_short, live):
        try:
            f()
        except Exception as e:  # một phần lỗi thì ghi lại, các phần khác vẫn chạy
            L.extend([f"**Lỗi ở phần {f.__name__}: {type(e).__name__}: {e}**", ""])
            import traceback
            traceback.print_exc()
        print("xong", f.__name__, flush=True)
    L.append("Công cụ tham khảo, không phải lời khuyên đầu tư.")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(OUT)
