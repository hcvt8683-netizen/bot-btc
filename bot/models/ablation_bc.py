"""Phase 5 ablation of overlays B and C on top of the chosen layer A.

Group B and C data exist only for part of the history, so rules are evaluated inside their available data on the
development period (until 31/12/2022) with 52-week rolling windows (104-week windows would leave too few); the
holdout stays locked and is the real out-of-sample test. Keep a rule only if P10 improves and the median falls by
no more than 1%. Rules are added one at a time in a fixed order.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.backtest import metrics
from bot.config import cfg
from bot.features import build
from bot.features.panel import daily_cm
from bot.models import core, overlays
from bot.validation import evaluate, splits

WINDOW = 52


def layer_a(feat: pd.DataFrame) -> np.ndarray:
    a = cfg()["model"]["layer_a"]
    return core.step_map(core.composite(feat, a["features"]).to_numpy(), [tuple(x) for x in a["table"]])


def objective(dates, price, m, start) -> dict:
    df = metrics.rolling(dates, price, m, start, splits.dev_end(), WINDOW, 4)
    return metrics.roll_summary(df)


def keeps(new: dict, base: dict) -> bool:
    return new.get("n", 0) > 0 and new["er_p10"] > base["er_p10"] + 1e-9 and new["er_median"] >= base["er_median"] * 0.99


def run(log: bool = True) -> dict:
    end = splits.dev_end()
    feat = build.weekly(end)
    dates, price = feat.index, feat["price"].to_numpy()
    cm = daily_cm(end)
    raw = overlays.weekly_group_b(dates, cm.set_index("date")["price"], end)
    m_a = layer_a(feat)
    rows, kept, f_b = [], [], np.ones(len(dates))
    first_b = {n: raw[n].first_valid_index() for n in overlays.GROUP_B if n in raw}

    def trial(name, m, feats, params, start):
        obj = objective(dates, price, m, start)
        res = evaluate.evaluate(name, dates, price, m, features=feats, params=params, stage="phase5", heavy=False, log=log)
        return obj, res

    # fng: contrarian vs momentum on the training split only (section 4.1 note)
    fng_check = {}
    for name in ("fng", "fng_momentum"):
        f = overlays.rule(raw[name], overlays.GROUP_B[name])
        tr = (dates <= splits.split("train")[1]) & (f != 1.0)
        years = sorted({d.year for d in dates[tr]})
        effects = []
        for y in years:
            sel = dates.year == y
            if sel.sum() >= 26:
                effects.append(metrics.summary(price[sel], overlays.combine(m_a[sel], f[sel]))["equity_ratio"] -
                               metrics.summary(price[sel], m_a[sel])["equity_ratio"])
        fng_check[name] = {"years": years, "effects": effects, "stable": len(effects) >= 2 and (min(effects) > 0 or max(effects) < 0)}
    for name, cheap_when in overlays.GROUP_B.items():
        if name not in raw or first_b.get(name) is None:
            rows.append({"name": name, "status": "không có dữ liệu"})
            continue
        if name.startswith("fng") and not fng_check[name]["stable"]:
            rows.append({"name": name, "status": "bỏ: không ổn định trên giai đoạn huấn luyện", "check": fng_check[name]})
            continue
        f = overlays.rule(raw[name], cheap_when)
        eps = overlays.episodes(f)
        start = max(first_b[name] + pd.Timedelta(weeks=52), dates[0])
        base_m = overlays.combine(m_a, f_b)
        base, _ = trial(f"B:base_for:{name}", base_m, ["A"] + kept, {"step": "base"}, start)
        if eps < overlays.MIN_EPISODES:
            rows.append({"name": name, "status": f"chỉ hiển thị: {eps} đợt (< 10)", "episodes": eps})
            continue
        cand_m = overlays.combine(m_a, f_b, f)
        new, res = trial(f"B:{name}", cand_m, ["A"] + kept + [name], {"template": "pct104", "cheap_when": cheap_when}, start)
        ok = keeps(new, base)
        rows.append({"name": name, "status": "giữ" if ok else "bỏ", "episodes": eps, "base": base, "new": new, "from": start,
                     "share_active": float(np.mean(f != 1.0))})
        if ok:
            kept.append(name)
            f_b = f_b * f
    # layer C
    m_ab = overlays.combine(m_a, f_b)
    events = overlays.load_events(end)
    fill, delayed = overlays.event_delay(dates, cm.set_index("date")["price"], events)
    start_c = pd.Timestamp("2013-07-01")
    base_c = objective(dates, price, m_ab, start_c)
    with_delay = metrics.roll_summary(metrics.rolling_two_prices(dates, fill, price, m_ab, start_c, end, WINDOW, 4))
    if log:
        from bot.validation import registry
        registry.log("C:event_delay", "phase5", ["A"] + kept + ["event_window"], {"hours": 48}, {"roll_med": with_delay["er_median"], "roll_p10": with_delay["er_p10"]})
    cap = overlays.macro_cap(dates, end)
    m_cap = np.minimum(m_ab, cap)
    with_cap = objective(dates, price, m_cap, start_c)
    if log:
        evaluate.evaluate("C:macro_cap", dates, price, m_cap, features=["A"] + kept + ["macro_cap"], params={"cap": 1.25}, stage="phase5", heavy=False)
    c_rows = [
        {"name": "event_window", "status": "giữ" if keeps(with_delay, base_c) else "bỏ", "base": base_c, "new": with_delay,
         "share_active": float(delayed.mean()), "episodes": int(delayed.sum())},
        {"name": "macro_cap", "status": "giữ" if keeps(with_cap, base_c) else "bỏ", "base": base_c, "new": with_cap,
         "share_active": float(np.mean(np.isfinite(cap))), "binding": float(np.mean(m_cap < m_ab)), "episodes": overlays.episodes(np.where(np.isfinite(cap), 1.25, 1.0))},
    ]
    return {"b": rows, "c": c_rows, "kept_b": kept, "fng_check": fng_check, "raw": raw}


def report(r: dict) -> str:
    from bot.i18n import fmt
    d3 = lambda x: fmt.dec(x, 3)  # noqa: E731
    L = ["# Thử bỏ từng phần, lớp ngắn hạn (B) và lớp vĩ mô (C)", "",
         "Nền: lớp A đã chọn ở giai đoạn 4. Dữ liệu nhóm B chỉ có từ 2018–2020, nên mỗi quy tắc được chấm **trong khoảng có dữ liệu của nó**, đến "
         "31/12/2022, với khung trượt 52 tuần (khung 104 tuần sẽ còn quá ít). Khoảng này gồm cả giai đoạn kiểm định, nên với lớp B/C chỉ giai đoạn "
         "kiểm tra cuối mới là kiểm tra thật ngoài mẫu. Mẫu quy tắc cố định cho mọi chỉ số (không dò): phân vị 104 tuần; nhóm rẻ nhất 20% → hệ số "
         "× 1,25; nhóm đắt nhất 20% → × 0,75. Sự kiện đầu hàng (giảm > 10% trong tuần, khối lượng > 2 lần TB 20 tuần) → × 1,25 trong 4 tuần. "
         "Giữ quy tắc khi kịch bản xấu (P10) tốt hơn và trung vị không giảm quá 1%. Dưới 10 đợt độc lập → chỉ hiển thị.", "",
         "## Fear & Greed: ngược đám đông hay theo đà (chỉ dùng giai đoạn huấn luyện)", ""]
    for k, c in r["fng_check"].items():
        L.append(f"- {k}: năm có tín hiệu trong giai đoạn huấn luyện {', '.join(map(str, c['years'])) or 'không có'}; tác động lên tỷ số tài sản theo năm: "
                 f"{', '.join(fmt.dec(e, 3) for e in c['effects']) or 'không đủ dữ liệu'} → {'ổn định' if c['stable'] else 'không ổn định'}.")
    stable = [k for k, c in r["fng_check"].items() if c["stable"]]
    L += ["", (f"Ổn định: {', '.join(stable)}." if stable else
               "Không cách hiểu nào được chứng minh ổn định: Fear & Greed có từ 02/2018 và cần 52 tuần lịch sử phân vị, nên giai đoạn huấn luyện "
               "chỉ còn năm 2019 (cần ít nhất 2 năm cùng chiều). Theo mục 4.1, bỏ chỉ số này."), "",
          "## Lớp B", "", "| Quy tắc | Kết luận | Số đợt | Tỷ lệ tuần bật | Chấm từ | Trước: trung vị / P10 | Sau: trung vị / P10 |", "|---|---|---|---|---|---|---|"]
    for x in r["b"]:
        if "new" in x:
            L.append(f"| {x['name']} | {x['status']} | {x['episodes']} | {fmt.pct(x['share_active'])} | {fmt.date(x['from'])} | "
                     f"{d3(x['base']['er_median'])} / {d3(x['base']['er_p10'])} | {d3(x['new']['er_median'])} / {d3(x['new']['er_p10'])} |")
        else:
            L.append(f"| {x['name']} | {x['status']} | {x.get('episodes', '—')} | — | — | — | — |")
    for k, why in overlays.DISPLAY_ONLY.items():
        L.append(f"| {k} | chỉ hiển thị: {why} | — | — | — | — | — |")
    L += ["", "## Lớp C (chấm từ 07/2013 đến 31/12/2022, khung 52 tuần)", "", "| Quy tắc | Kết luận | Số lần / đợt | Tỷ lệ tuần bật | Trước: trung vị / P10 | Sau: trung vị / P10 |", "|---|---|---|---|---|---|"]
    for x in r["c"]:
        L.append(f"| {x['name']} | {x['status']} | {x['episodes']} | {fmt.pct(x['share_active'])} | {d3(x['base']['er_median'])} / {d3(x['base']['er_p10'])} | "
                 f"{d3(x['new']['er_median'])} / {d3(x['new']['er_p10'])} |")
    L += ["", f"Quy tắc lớp B được giữ: {', '.join(r['kept_b']) or 'không có'}. Lớp C được giữ: {', '.join(x['name'] for x in r['c'] if x['status'] == 'giữ') or 'không có'}.", ""]
    return "\n".join(L)
