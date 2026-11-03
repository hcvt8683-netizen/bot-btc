"""Price bands by volatility regime (settings in config/candidates.yaml, section forecast_regime).

The band in use divides the k-day log return by the 30-day volatility. Volatility mean-reverts, so after calm weeks the
band is too narrow and after turbulent weeks too wide, although it covers 80% overall. Two registered fixes are compared
with the method in use, with the scoring of forecast_search (pinball loss on log price, 5 quantiles × 8 horizons):
  tron       volatility = sqrt of the mean of the 30-day and 365-day variances (weights 1/2, not tuned);
  theo_nhom  the quantiles come only from past anchors in the same volatility tercile as today.
The better one on 2014–2021 replaces the method in use only if, on 2022 → today, its score is lower with a block-bootstrap
interval entirely below 0, its 80% band covers 75–85%, and its coverage is closer to 80% inside each volatility tercile.
The single registered run (03/11/2026) chose `tron` and passed all three; price_forecast.bands now uses it (vol_long_days).
`hien_tai` here stays the 30-day method, so a rerun repeats the same comparison.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.models.forecast_search import QS, pinball

VARIANTS = ["hien_tai", "tron", "theo_nhom"]
NEW = ["tron", "theo_nhom"]
GROUP_VI = {0: "1/3 êm nhất", 1: "giữa", 2: "1/3 mạnh nhất"}


def spec() -> dict:
    sp = load_yaml(CONFIG / "candidates.yaml")
    return {"regime": sp["forecast_regime"], "forecast": sp["forecast"]}


def vol(p: pd.Series, days: int) -> pd.Series:
    """Daily volatility known at T (log returns up to T only)."""
    return np.log(p).diff().rolling(days, min_periods=days).std()


def vol_group(p: pd.Series, F: dict, R: dict) -> pd.Series:
    """0 / 1 / 2 = lowest third, middle, highest third of today's 30-day volatility among the 1461 days up to T."""
    rank = vol(p, F["vol_days"]).rolling(F["window_days"], min_periods=F["min_obs"]).rank(pct=True)
    n = int(R["groups"])
    return pd.Series(np.where(rank.notna(), np.clip(np.ceil(rank * n) - 1, 0, n - 1), np.nan), index=p.index)


def log_quantiles(p: pd.Series, k: int, name: str, F: dict, R: dict, group: pd.Series | None = None) -> pd.DataFrame:
    """Log price quantiles for day T + k at every anchor T, from prices up to T (columns = QS)."""
    lp = np.log(p)
    s = vol(p, F["vol_days"])
    if name == "tron":
        s = np.sqrt((s ** 2 + vol(p, int(R["vol_long_days"])) ** 2) / 2)
    scale = s * np.sqrt(k)
    known = ((lp.shift(-k) - lp) / scale).shift(k)  # standardised return of T − k, whose outcome is the price of T
    W = int(F["window_days"]) - k
    Q = {q: known.rolling(W, min_periods=F["min_obs"]).quantile(q) for q in QS}
    if name == "theo_nhom":
        g = vol_group(p, F, R) if group is None else group
        gk = g.shift(k)  # the group each known window had on its own anchor day
        for v in range(int(R["groups"])):
            now = g == v
            for q in QS:
                qg = known.where(gk == v).rolling(W, min_periods=int(R["group_min_obs"])).quantile(q)
                Q[q] = Q[q].where(~(now & qg.notna()), qg)
    return pd.DataFrame({q: lp + Q[q] * scale for q in QS}, index=p.index)


def run(write: bool = True) -> dict:
    from bot.models import price_forecast as pf
    sp = spec()
    R, F = sp["regime"], sp["forecast"]
    p = pf.daily_prices()
    lp = np.log(p)
    hz = F["horizons_days"]
    grp = vol_group(p, F, R)
    loss, st = {}, {}
    for k in hz:
        y = lp.shift(-k)
        lqs = {v: log_quantiles(p, k, v, F, R, grp) for v in VARIANTS}
        ok = y.notna() & grp.notna()
        for lq in lqs.values():
            ok &= lq.notna().all(axis=1)
        for v, lq in lqs.items():
            loss[(v, k)] = pinball(y, lq).where(ok)
            st[(v, k)] = pd.DataFrame({"in80": ((y >= lq[0.10]) & (y <= lq[0.90])).astype(float), "in50": ((y >= lq[0.25]) & (y <= lq[0.75])).astype(float),
                                       "width80": np.exp(lq[0.90] - lq[0.10]) - 1, "g": grp}).where(ok)
    periods = {"chon": (pd.Timestamp(str(R["selection"]["from"])), pd.Timestamp(str(R["selection"]["to"]))),
               "xac_nhan": (pd.Timestamp(str(R["confirm_from"])), p.index[-1])}
    table = {}
    for v in VARIANTS:
        row = {"name": v, "desc": R["variants"][v]}
        for pn, (a, b) in periods.items():
            m = (p.index >= a) & (p.index <= b)
            rel, per_h = [], {}
            for k in hz:
                rel.append(loss[(v, k)][m].mean() / loss[("hien_tai", k)][m].mean())
                s = st[(v, k)][m].dropna()
                by_g = {int(g): float(x["in80"].mean()) for g, x in s.groupby("g")}
                per_h[k] = {"n": int(len(s)), "cover80": float(s["in80"].mean()), "cover50": float(s["in50"].mean()), "width80": float(s["width80"].median()),
                            "groups": by_g, "group_dev": float(np.mean([abs(c - 0.8) for c in by_g.values()]))}
            row[pn] = {"score": float(np.mean(rel)), "cover80": float(np.mean([x["cover80"] for x in per_h.values()])),
                       "cover50": float(np.mean([x["cover50"] for x in per_h.values()])), "group_dev": float(np.mean([x["group_dev"] for x in per_h.values()])),
                       "h": per_h}
        table[v] = row
    best = min(NEW, key=lambda v: table[v]["chon"]["score"])
    m = p.index >= periods["xac_nhan"][0]
    ref = {k: loss[("hien_tai", k)][m].mean() for k in hz}
    d = pd.concat([((loss[(best, k)] - loss[("hien_tai", k)]) / ref[k])[m] for k in hz], axis=1).dropna().mean(axis=1)
    rng = np.random.default_rng(load_yaml(CONFIG / "bot.yaml")["rebuild"]["seed"])
    boot = d.to_numpy()[measure.stationary_indices(len(d), 30, 2000, rng)].mean(axis=1)
    ci = [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]
    cb, cc = table[best]["xac_nhan"], table["hien_tai"]["xac_nhan"]
    checks = {"a": ci[1] < 0, "b": 0.75 <= cb["cover80"] <= 0.85, "c": cb["group_dev"] < cc["group_dev"]}
    out = {"run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "data_from": p.dropna().index[0].strftime("%Y-%m-%d"),
           "last": p.dropna().index[-1].strftime("%Y-%m-%d"), "selection": [x.strftime("%Y-%m-%d") for x in periods["chon"]],
           "confirm_from": periods["xac_nhan"][0].strftime("%Y-%m-%d"), "best": best, "confirm": {"days": int(len(d)), "diff": float(d.mean()), "ci": ci},
           "checks": checks, "switch": bool(all(checks.values())), "table": table}
    if write:
        (DATA / "results" / "forecast_regime.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (ROOT / "docs" / "FORECAST_REGIME.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    return out


H_VI = {1: "1 ngày", 2: "2 ngày", 3: "3 ngày", 4: "4 ngày", 5: "5 ngày", 6: "6 ngày", 7: "7 ngày", 30: "30 ngày"}
NAME_VI = {"hien_tai": "chỉ 30 ngày (cách dùng đến 03/11/2026)", "tron": "trộn ngắn + dài hạn", "theo_nhom": "theo nhóm độ dao động"}


def markdown(o: dict) -> str:
    from bot.i18n import fmt
    R = spec()["regime"]
    T = o["table"]
    sp = lambda x: fmt.pct(x, 1, sign=True)  # noqa: E731
    yes = lambda b: "đạt" if b else "**không đạt**"  # noqa: E731
    L = ["# Dải giá theo nhóm độ dao động", "",
         f"Đăng ký trước: `config/candidates.yaml` mục `forecast_regime` (commit `8fd2b9c`). Dữ liệu giá Coin Metrics từ {fmt.date(o['data_from'])} đến {fmt.date(o['last'])}. "
         "Mã: `bot/models/forecast_regime.py`; chạy lại: `python -m bot.cli forecast-regime`.", "",
         f"- **Vì sao:** {R['why']}.",
         f"- **Thước đo:** {R['metric']}; thêm {R['group_metric']}.",
         f"- **Quy tắc:** {R['rule']}.", "",
         f"## Kết luận: **{'đổi sang ' + NAME_VI[o['best']] if o['switch'] else 'giữ nguyên cách đang dùng'}**", "",
         f"- Tốt hơn ở giai đoạn chọn ({fmt.date(o['selection'][0])} → {fmt.date(o['selection'][1])}): **{NAME_VI[o['best']]}**, điểm {fmt.dec(T[o['best']]['chon']['score'], 4)} "
         f"(cách đang dùng = 1,0000; cách còn lại {fmt.dec(T[[v for v in NEW if v != o['best']][0]]['chon']['score'], 4)}).",
         f"- Giai đoạn xác nhận ({fmt.date(o['confirm_from'])} → nay, {o['confirm']['days']} ngày): chênh điểm {sp(o['confirm']['diff'])}, "
         f"khoảng tin cậy 95% {sp(o['confirm']['ci'][0])} đến {sp(o['confirm']['ci'][1])} → (a) {yes(o['checks']['a'])}.",
         f"- Dải 80% phủ {fmt.pct(T[o['best']]['xac_nhan']['cover80'], 1)} (cần 75–85%) → (b) {yes(o['checks']['b'])}.",
         f"- Độ lệch phủ theo nhóm {fmt.pct(T[o['best']]['xac_nhan']['group_dev'], 1)} so với {fmt.pct(T['hien_tai']['xac_nhan']['group_dev'], 1)} của cách đang dùng "
         f"→ (c) {yes(o['checks']['c'])}.",
         ("- Đạt cả ba: đổi `price_forecast.bands`, nhật ký dự báo sang phiên bản mới." if o["switch"]
          else "- Không đạt đủ cả ba: giữ nguyên. Chọn lại theo kết quả giai đoạn xác nhận sẽ là chọn may rủi, nên không làm."), "",
         "## Tỷ lệ trúng dải 8/10 lần theo nhóm độ dao động lúc dự báo", "",
         "| Kỳ hạn | Giai đoạn | Cách tính | Số ngày | Trúng chung | " + " | ".join(GROUP_VI.values()) + " | Độ lệch theo nhóm | Độ rộng dải 80% (trung vị) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for k in (1, 7, 30):
        for pn, lab in (("chon", "2014–2021"), ("xac_nhan", "2022–nay")):
            for v in VARIANTS:
                h = T[v][pn]["h"][k] if k in T[v][pn]["h"] else T[v][pn]["h"][str(k)]
                g = {int(a): b for a, b in h["groups"].items()}
                L.append(f"| {H_VI[k]} | {lab} | {NAME_VI[v]} | {h['n']} | {fmt.pct(h['cover80'], 1)} | " + " | ".join(fmt.pct(g.get(i), 1) for i in GROUP_VI)
                         + f" | {fmt.pct(h['group_dev'], 1)} | {fmt.pct(h['width80'], 1)} |")
    L += ["", "## Tóm tắt 8 kỳ hạn", "", "| Cách tính | Điểm 2014–2021 | Trúng 80% / 50% | Lệch theo nhóm | Điểm 2022–nay | Trúng 80% / 50% | Lệch theo nhóm |",
          "|---|---|---|---|---|---|---|"]
    for v in VARIANTS:
        a, b = T[v]["chon"], T[v]["xac_nhan"]
        L.append(f"| {NAME_VI[v]} | {fmt.dec(a['score'], 4)} | {fmt.pct(a['cover80'], 1)} / {fmt.pct(a['cover50'], 1)} | {fmt.pct(a['group_dev'], 1)} | "
                 f"{fmt.dec(b['score'], 4)} | {fmt.pct(b['cover80'], 1)} / {fmt.pct(b['cover50'], 1)} | {fmt.pct(b['group_dev'], 1)} |")
    L += ["", "Điểm dưới 1 là tốt hơn cách đang dùng. Độ lệch theo nhóm = trung bình |tỷ lệ trúng − 80%| của 3 nhóm; 0 là đúng tỷ lệ ở mọi lúc.", "",
          "Công cụ tham khảo, không phải lời khuyên đầu tư.", ""]
    return "\n".join(L)
