"""Search for the most accurate daily price-band method (settings in config/candidates.yaml, section forecast_search).

Hit rate alone rewards wide bands, so methods are ranked by the pinball loss of the 5 quantiles on log price (a proper
score: calibrated AND narrow wins). Each horizon's loss is divided by the loss of the method in use over the same days,
then averaged over the 8 horizons (below 1 = better). The best method on 2014–2021 replaces the one in use only if it is
still better on 2022 → today with a block-bootstrap interval of the difference entirely below 0, and its 80% band covers
75–85% (mean over the 8 horizons, fixed before running). Every configuration is logged in experiments/forecast_configs.csv.
"""
from __future__ import annotations

import csv
import datetime as dt
import json

import numpy as np
import pandas as pd
from scipy.stats import norm

from bot.backtest import measure
from bot.config import CONFIG, DATA, ROOT, load_yaml

QS = [0.10, 0.25, 0.50, 0.75, 0.90]


def spec() -> dict:
    sp = load_yaml(CONFIG / "candidates.yaml")
    return {"search": sp["forecast_search"], "forecast": sp["forecast"]}


def variants(grid: dict) -> list[dict]:
    out = [{"vol": v, "window": w, "center": c, "dist": "empirical"} for v in grid["vol"] for w in grid["window_days"] for c in grid["center"]]
    out += [{"vol": v, "window": None, "center": "zero", "dist": "normal"} for v in grid["normal"]]
    for v in out:
        v["name"] = f"chuẩn/{v['vol']}" if v["dist"] == "normal" else f"{v['vol']}/{v['window']}/{v['center']}"
    return out


def sigma(p: pd.Series, vol: str) -> pd.Series:
    """Daily volatility known at T (returns up to T only)."""
    lr = np.log(p).diff()
    if vol == "none":
        return pd.Series(1.0, index=p.index)
    if vol.startswith("std"):
        n = int(vol[3:])
        return lr.rolling(n, min_periods=n).std()
    lam = int(vol[4:]) / 100
    return np.sqrt((lr ** 2).ewm(alpha=1 - lam, adjust=False, min_periods=30).mean())


def log_quantiles(p: pd.Series, k: int, v: dict, min_obs: int = 365) -> pd.DataFrame:
    """Log price quantiles for day T + k at every anchor T, from prices up to T."""
    lp = np.log(p)
    scale = sigma(p, v["vol"]) * np.sqrt(k) if v["vol"] != "none" else pd.Series(1.0, index=p.index)
    if v["dist"] == "normal":
        return pd.DataFrame({q: lp + scale * norm.ppf(q) for q in QS}, index=p.index)
    known = ((lp.shift(-k) - lp) / scale).shift(k)  # standardised return of T − k, outcome known at T
    roll = known.expanding(min_periods=min_obs) if v["window"] == "all" else known.rolling(int(v["window"]) - k, min_periods=min_obs)
    Q = {q: roll.quantile(q) for q in QS}
    if v["center"] == "zero":
        mid = Q[0.5]
        Q = {q: Q[q] - mid for q in QS}
    return pd.DataFrame({q: lp + Q[q] * scale for q in QS}, index=p.index)


def pinball(y: pd.Series, lq: pd.DataFrame) -> pd.Series:
    d = pd.DataFrame({q: y - lq[q] for q in QS})
    return pd.DataFrame({q: np.maximum(q * d[q], (q - 1) * d[q]) for q in QS}).mean(axis=1)


def run(write: bool = True) -> dict:
    from bot.models import price_forecast as pf
    sp = spec()
    S, F = sp["search"], sp["forecast"]
    p = pf.daily_prices()
    lp = np.log(p)
    hz = F["horizons_days"]
    vs = variants(S["grid"])
    cur = next(v for v in vs if v["dist"] == "empirical" and v["vol"] == S["current"]["vol"] and v["window"] == S["current"]["window_days"]
               and v["center"] == S["current"]["center"])
    sel = (pd.Timestamp(str(S["selection"]["from"])), pd.Timestamp(str(S["selection"]["to"])))
    conf_from = pd.Timestamp(str(S["confirm_from"]))
    # per horizon: loss series and band statistics of every variant on the same valid days
    loss, stats_rows = {}, {}
    for k in hz:
        y = lp.shift(-k)
        lqs = {v["name"]: log_quantiles(p, k, v, F["min_obs"]) for v in vs}
        ok = y.notna()
        for lq in lqs.values():
            ok &= lq.notna().all(axis=1)
        for v in vs:
            lq = lqs[v["name"]]
            loss[(v["name"], k)] = pinball(y, lq).where(ok)
            stats_rows[(v["name"], k)] = pd.DataFrame({"in80": ((y >= lq[0.10]) & (y <= lq[0.90])).astype(float), "in50": ((y >= lq[0.25]) & (y <= lq[0.75])).astype(float),
                                                      "width80": np.exp(lq[0.90] - lq[0.10]) - 1, "abs_err": np.abs(np.exp(y - lq[0.50]) - 1),
                                                      "above": (y > lq[0.50]).astype(float), "dir_hit": ((y > lp) == (lq[0.50] > lp)).astype(float)}).where(ok, np.nan)
    periods = {"chon": sel, "xac_nhan": (conf_from, p.index[-1])}
    table = {}
    for v in vs:
        row = {"name": v["name"], **{x: v[x] for x in ("vol", "window", "center", "dist")}}
        for pn, (a, b) in periods.items():
            rel, per_h = [], {}
            for k in hz:
                m = (p.index >= a) & (p.index <= b)
                lv, lr_ = loss[(v["name"], k)][m], loss[(cur["name"], k)][m]
                rel.append(lv.mean() / lr_.mean())
                st = stats_rows[(v["name"], k)][m]
                per_h[k] = {"n": int(lv.notna().sum()), "loss": float(lv.mean()), "cover80": float(st["in80"].mean()), "cover50": float(st["in50"].mean()),
                            "width80": float(st["width80"].median()), "abs_err": float(st["abs_err"].median()), "above": float(st["above"].mean()),
                            "dir_hit": float(st["dir_hit"].mean()) if v["center"] == "empirical" and v["dist"] == "empirical" else None}
            row[pn] = {"score": float(np.mean(rel)), "cover80": float(np.mean([x["cover80"] for x in per_h.values()])),
                       "cover50": float(np.mean([x["cover50"] for x in per_h.values()])), "width80_7": per_h[7]["width80"] if 7 in per_h else None, "h": per_h}
        table[v["name"]] = row
    best = min(table.values(), key=lambda r: r["chon"]["score"])
    # confirmation: daily relative difference of the winner vs the method in use, averaged over horizons
    m = p.index >= conf_from
    ref_mean = {k: loss[(cur["name"], k)][m].mean() for k in hz}
    d = pd.concat([((loss[(best["name"], k)] - loss[(cur["name"], k)]) / ref_mean[k])[m] for k in hz], axis=1).dropna().mean(axis=1)
    rng = np.random.default_rng(load_yaml(CONFIG / "bot.yaml")["rebuild"]["seed"])
    idx = measure.stationary_indices(len(d), 30, 2000, rng)
    boot = d.to_numpy()[idx].mean(axis=1)
    ci = [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]
    cov = best["xac_nhan"]["cover80"]
    switch = best["name"] != cur["name"] and ci[1] < 0 and 0.75 <= cov <= 0.85
    out = {"run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "data_from": p.dropna().index[0].strftime("%Y-%m-%d"),
           "last": p.dropna().index[-1].strftime("%Y-%m-%d"), "selection": [sel[0].strftime("%Y-%m-%d"), sel[1].strftime("%Y-%m-%d")],
           "confirm_from": conf_from.strftime("%Y-%m-%d"), "current": cur["name"], "best": best["name"], "n_variants": len(vs),
           "confirm": {"days": int(len(d)), "diff": float(d.mean()), "ci": ci, "cover80": cov}, "switch": bool(switch), "table": table}
    if write:
        (DATA / "results" / "forecast_search.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (ROOT / "docs" / "FORECAST_SEARCH.md").write_text(markdown(out), encoding="utf-8", newline="\n")
        with open(ROOT / "experiments" / "forecast_configs.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["run_at", "config", "vol", "window", "center", "dist", "score_selection", "cover80_selection", "cover50_selection",
                        "score_confirm", "cover80_confirm", "cover50_confirm", "width80_7d_confirm"])
            for r in table.values():
                w.writerow([out["run_at"], r["name"], r["vol"], r["window"], r["center"], r["dist"], f"{r['chon']['score']:.4f}", f"{r['chon']['cover80']:.3f}",
                            f"{r['chon']['cover50']:.3f}", f"{r['xac_nhan']['score']:.4f}", f"{r['xac_nhan']['cover80']:.3f}", f"{r['xac_nhan']['cover50']:.3f}",
                            f"{r['xac_nhan']['width80_7']:.4f}"])
    return out


H_VI = {1: "1 ngày", 2: "2 ngày", 3: "3 ngày", 4: "4 ngày", 5: "5 ngày", 6: "6 ngày", 7: "7 ngày", 30: "30 ngày"}


def markdown(o: dict) -> str:
    from bot.i18n import fmt
    S = spec()["search"]
    cur, best = o["table"][o["current"]], o["table"][o["best"]]
    sp = lambda x: fmt.pct(x, 1, sign=True)  # noqa: E731
    L = ["# Dự báo dải giá: so 32 cách tính", "",
         f"Đăng ký trước: `config/candidates.yaml` mục `forecast_search` (commit `c3b4f52`). Dữ liệu giá Coin Metrics từ {fmt.date(o['data_from'])} đến {fmt.date(o['last'])}. "
         f"Mã: `bot/models/forecast_search.py`; mọi cấu hình: `experiments/forecast_configs.csv`.", "",
         f"- **Vì sao không chọn theo tỷ lệ trúng:** {S['why']}.",
         f"- **Thước đo:** {S['metric']}.",
         f"- **Quy tắc:** {S['rule']} (\"phủ 75–85%\" tính trung bình qua 8 kỳ hạn, chốt trước khi chạy).", "",
         f"## Kết luận: **{'đổi sang ' + o['best'] if o['switch'] else 'giữ nguyên cách đang dùng (' + o['current'] + ')'}**", "",
         f"- Tốt nhất ở giai đoạn chọn ({fmt.date(o['selection'][0])} → {fmt.date(o['selection'][1])}): **{o['best']}**, điểm {fmt.dec(best['chon']['score'], 4)} "
         f"(cách đang dùng = 1,0000).",
         f"- Ở giai đoạn xác nhận ({fmt.date(o['confirm_from'])} → nay, {o['confirm']['days']} ngày): chênh {sp(o['confirm']['diff'])} so với cách đang dùng, "
         f"khoảng tin cậy 95% {sp(o['confirm']['ci'][0])} đến {sp(o['confirm']['ci'][1])}; dải 80% phủ {fmt.pct(o['confirm']['cover80'], 1)}.",
         ("- Khoảng tin cậy chứa 0: không đủ bằng chứng cách mới tốt hơn, nên giữ nguyên. Chọn lại theo kết quả giai đoạn xác nhận sẽ là chọn may rủi, nên không làm."
          if not o["switch"] else "- Đạt quy tắc: thay phương pháp, bắt đầu phiên bản mới của nhật ký dự báo."), "",
         "## Cách đang dùng theo từng kỳ hạn", "",
         "| Kỳ hạn | Giai đoạn | Số ngày | Trúng dải 80% | Trúng dải 50% | Độ rộng dải 80% (trung vị) | Sai số của giữa (trung vị) | Đoán đúng hướng |", "|---|---|---|---|---|---|---|---|"]
    for pn, lab in (("chon", "2014–2021"), ("xac_nhan", "2022–nay")):
        for k, h in cur[pn]["h"].items():
            L.append(f"| {H_VI[int(k)]} | {lab} | {h['n']} | {fmt.pct(h['cover80'], 1)} | {fmt.pct(h['cover50'], 1)} | {fmt.pct(h['width80'], 1)} | {fmt.pct(h['abs_err'], 1)} | "
                     f"{fmt.pct(h['dir_hit'], 1) if h['dir_hit'] is not None else '—'} |")
    L += ["", "\"Đoán đúng hướng\" (giữa cao hơn giá gốc thì coi là đoán tăng) chỉ quanh 50–55%: dải giá không biết giá sẽ lên hay xuống; nó chỉ cho biết giá có thể đi xa đến đâu.", "",
          "## Cả 32 cách (điểm dưới 1 là tốt hơn cách đang dùng)", "",
          "| Cách tính | Độ dao động | Lịch sử | Trung tâm | Phân phối | Điểm 2014–2021 | Trúng 80% / 50% | Điểm 2022–nay | Trúng 80% / 50% | Độ rộng 80%, 7 ngày |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(o["table"].values(), key=lambda r: r["chon"]["score"]):
        tag = " **(đang dùng)**" if r["name"] == o["current"] else (" **(tốt nhất giai đoạn chọn)**" if r["name"] == o["best"] else "")
        L.append(f"| {r['name']}{tag} | {r['vol']} | {r['window'] or '—'} | {r['center']} | {'chuẩn' if r['dist'] == 'normal' else 'thực nghiệm'} | "
                 f"{fmt.dec(r['chon']['score'], 4)} | {fmt.pct(r['chon']['cover80'], 1)} / {fmt.pct(r['chon']['cover50'], 1)} | {fmt.dec(r['xac_nhan']['score'], 4)} | "
                 f"{fmt.pct(r['xac_nhan']['cover80'], 1)} / {fmt.pct(r['xac_nhan']['cover50'], 1)} | {fmt.pct(r['xac_nhan']['width80_7'], 1)} |")
    L += ["", "Ghi chú: `none` = không chuẩn hóa theo độ dao động; `std30`, `std60` = độ lệch chuẩn 30, 60 ngày; `ewma94`, `ewma97` = trung bình trượt mũ (λ 0,94, 0,97); "
          "lịch sử 730 / 1461 ngày hoặc `all` (từ 2010); `zero` = không giả định xu hướng. Cách không chuẩn hóa với toàn bộ lịch sử có dải quá rộng (trúng hơn 90% ở 2022–nay).",
          "", "Công cụ tham khảo, không phải lời khuyên đầu tư.", ""]
    return "\n".join(L)
