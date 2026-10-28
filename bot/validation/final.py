"""Phase 7: the single logged run on the locked holdout, and the acceptance criteria of section 5."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.backtest import baselines, benchmark, current_bot, metrics
from bot.features import build
from bot.models import ablation_bc, overlays
from bot.validation import evaluate, registry, splits

FULL_CYCLES = 4  # pre-2012, 2012–2016, 2016–2020, 2020–2024 (2024–now is still running)


def bucket_episodes(m: np.ndarray) -> dict[float, int]:
    """Independent episodes of each non-neutral multiplier bucket (consecutive weeks at the same value = one)."""
    out = {}
    for v in sorted(set(np.round(m, 4))):
        if abs(v - 1.0) < 1e-9:
            continue
        on = np.isclose(m, v)
        out[float(v)] = int(np.sum(on & ~np.r_[False, on[:-1]]))
    return out


def criteria(cand: dict, bench: dict, m: np.ndarray) -> list[dict]:
    """Evaluate the 8 acceptance criteria. Each item: id, text, ok (True/False/None = waiting), detail values."""
    sv, sh = cand["splits"]["Kiểm định"], cand["splits"]["Kiểm tra cuối"]
    bv, bh = bench["splits"]["Kiểm định"], bench["splits"]["Kiểm tra cuối"]
    cyc = list(cand["cycles"].items())[:FULL_CYCLES]
    bcyc = list(bench["cycles"].items())[:FULL_CYCLES]
    c_above = sum(1 for _, c in cyc if c["equity_ratio"] > 1.0)
    b_above = sum(1 for _, c in bcyc if c["equity_ratio"] > 1.0)
    mdd_gap = max((s["mdd_dca"] - s["mdd"]) for s in cand["splits"].values())  # positive = worse than DCA
    idle = max(s["idle_avg"] for s in cand["splits"].values())
    eps = bucket_episodes(m)
    c1 = sv["roll_er_median"] > 1 and sh["roll_er_median"] > 1 and sv["roll_er_p10"] >= 0.97 and sh["roll_er_p10"] >= 0.97
    b1 = bv["roll_er_median"] > 1 and bh["roll_er_median"] > 1 and bv["roll_er_p10"] >= 0.97 and bh["roll_er_p10"] >= 0.97
    pv, ph = cand["placebo"]["percentile"], cand["placebo_holdout"]["percentile"]
    better1 = (sv["roll_er_median"] > bv["roll_er_median"] and sh["roll_er_median"] > bh["roll_er_median"]
               and sv["roll_er_p10"] >= bv["roll_er_p10"] and sh["roll_er_p10"] >= bh["roll_er_p10"])
    return [
        {"id": 1, "ok": bool(c1), "val": (sv["roll_er_median"], sv["roll_er_p10"]), "hold": (sh["roll_er_median"], sh["roll_er_p10"])},
        {"id": 2, "ok": c_above >= 3, "n": c_above, "cycles": {n: c["equity_ratio"] for n, c in cyc}},
        {"id": 3, "ok": mdd_gap <= 0.05, "gap": mdd_gap},
        {"id": 4, "ok": pv >= 0.95 and ph >= 0.95, "val": pv, "hold": ph},
        {"id": 5, "ok": idle <= 0.25, "idle": idle},
        {"id": 6, "ok": all(v >= 10 for v in eps.values()), "eps": eps},
        {"id": 7, "ok": bool(better1 and c_above >= b_above), "bench_c1": b1, "bench_cycles": b_above,
         "bench_val": (bv["roll_er_median"], bv["roll_er_p10"]), "bench_hold": (bh["roll_er_median"], bh["roll_er_p10"])},
        {"id": 8, "ok": None},
    ]


def run() -> dict:
    splits.log_final_run({"command": "final", "model": "layer_a (config)", "trials_before": registry.n_trials()})
    feat = build.weekly(None)
    dates, price = feat.index, feat["price"].to_numpy()
    m = ablation_bc.layer_a(feat)
    cand = evaluate.evaluate("FINAL:layer_a", dates, price, m, final=True, features="layer_a", params={"stage": "final"}, stage="final")
    s = current_bot.series(current_bot.export(force=True), "auto")
    bm, _ = baselines.current_bot(s, dates)
    bench = evaluate.evaluate("FINAL:bot_hien_tai", dates, price, bm, final=True, features="auto", params={"stage": "final"}, stage="final")
    crit = criteria(cand, bench, m)
    return {"dates": (dates[0], dates[-1]), "cand": cand, "bench": bench, "criteria": crit, "m": m, "bm": bm,
            "trials": registry.n_trials(), "passed": all(c["ok"] for c in crit if c["ok"] is not None)}


CRIT_TEXT = {
    1: "Trung vị tỷ số tài sản (khung 2 năm) > 1,00 ở kiểm định và kiểm tra cuối, kịch bản xấu P10 ≥ 0,97",
    2: "Tỷ số tài sản > 1,00 ở ít nhất 3/4 chu kỳ halving trọn vẹn",
    3: "Sụt giảm lớn nhất không tệ hơn mua đều quá 5 điểm %",
    4: "Hơn ít nhất 95% số lần chạy với tín hiệu ngẫu nhiên",
    5: "Tiền mặt chờ trung bình ≤ 25% số tiền đã nạp",
    6: "Mọi quy tắc đang dùng có ≥ 10 đợt độc lập",
    7: "Tốt hơn bot hiện tại ở tiêu chí 1 và 2",
    8: "Mọi bài kiểm tra đạt và phần khác biệt của báo cáo đã được duyệt",
}


def results_md(s: dict) -> str:
    """docs/RESULTS.md (Vietnamese) from data/results/final_summary.json."""
    from bot.i18n import fmt
    d3 = lambda x: fmt.dec(x, 3)  # noqa: E731
    c, b = s["candidate"], s["current_bot"]
    cr = {x["id"]: x for x in s["criteria"]}

    def detail(x: dict) -> str:
        i = x["id"]
        if i == 1:
            return f"kiểm định {d3(x['val'][0])} / {d3(x['val'][1])}; kiểm tra cuối {d3(x['hold'][0])} / {d3(x['hold'][1])}"
        if i == 2:
            return f"{x['n']}/4: " + ", ".join(f"{k} {d3(v)}" for k, v in x["cycles"].items())
        if i == 3:
            return f"chênh lớn nhất {fmt.num(x['gap'] * 100, 1)} điểm %"
        if i == 4:
            return f"kiểm định {fmt.pct(x['val'])}, kiểm tra cuối {fmt.pct(x['hold'])}"
        if i == 5:
            return f"lớn nhất {fmt.pct(x['idle'], 1)}"
        if i == 6:
            return ", ".join(f"hệ số {fmt.dec(float(k), 2)}: {v} đợt" for k, v in x["eps"].items())
        if i == 7:
            return (f"bot hiện tại: kiểm định {d3(x['bench_val'][0])} / {d3(x['bench_val'][1])}, kiểm tra cuối {d3(x['bench_hold'][0])} / "
                    f"{d3(x['bench_hold'][1])}, {x['bench_cycles']}/4 chu kỳ")
        return "chờ bạn duyệt ở giai đoạn 9"

    mark = lambda ok: "đạt" if ok else ("chờ duyệt" if ok is None else "**không đạt**")  # noqa: E731
    L = ["# Kết quả nâng cấp \"Best ROI for Invest\" (giai đoạn 7)", "",
         f"Lần chạy duy nhất trên giai đoạn kiểm tra cuối (từ 01/01/2023), lúc {fmt.datetime_vn(s['run_at'])}, ghi trong `experiments/final_runs.log`. "
         f"Dữ liệu từ {fmt.date(s['data_from'])} đến {fmt.date(s['data_to'])}. Không có gì được chỉnh sau khi xem kết quả này. "
         f"Tổng số lần thử trong sổ (`experiments/registry.csv`): **{s['trials']}**.", "",
         "Mô hình được chấm: lớp A, trung bình \"độ rẻ\" của Pi Cycle, Giá/MA 200 tuần, Hash Ribbon; bảng hệ số ≥ 0,8 → 2,0; 0,6–0,8 → 1,25; "
         "0,2–0,6 → 1,0; < 0,2 → 0,5. Lớp B và C không giữ quy tắc nào. Bên bán chỉ là lời khuyên dạng chữ. "
         "Mốc so sánh: bot hiện tại (chế độ Tự động) dựng lại thành hệ số Phải mua 2,0, Cân nhắc mua 1,25, Không nên mua 0,25.", "",
         f"## Kết luận: mô hình mới {'ĐẠT' if s['passed'] else 'KHÔNG ĐẠT'} tiêu chí chấp nhận", "",
         "| # | Tiêu chí | Kết quả | Số liệu |", "|---|---|---|---|"]
    for i in range(1, 9):
        L.append(f"| {i} | {CRIT_TEXT[i]} | {mark(cr[i]['ok'])} | {detail(cr[i])} |")
    L += ["", "## So sánh với mua đều (cùng tiền nạp mỗi tuần)", "",
          "| Chiến lược | Giai đoạn | Tỷ số tài sản | Trung vị khung 2 năm | Kịch bản xấu (P10) | Lợi thế giá vốn | Tiền mặt chờ | Sụt giảm lớn nhất (chiến lược / mua đều) |",
          "|---|---|---|---|---|---|---|---|"]
    for name, x in (("Mô hình mới", c), ("Bot hiện tại", b)):
        for sp, v in x["splits"].items():
            L.append(f"| {name} | {sp} | {d3(v['equity_ratio'])} | {d3(v.get('roll_er_median'))} | {d3(v.get('roll_er_p10'))} | {fmt.pct(v['cba'], 1, sign=True)} | "
                     f"{fmt.pct(v['idle_avg'], 1)} | {fmt.pct(v['mdd'])} / {fmt.pct(v['mdd_dca'])} |")
    L += ["", "| Chiến lược | " + " | ".join(c["cycles"]) + " |", "|---|" + "---|" * len(c["cycles"])]
    for name, x in (("Mô hình mới", c), ("Bot hiện tại", b)):
        L.append(f"| {name} | " + " | ".join(d3(v["equity_ratio"]) + ("" if v["complete"] else " (đang chạy)") for v in x["cycles"].values()) + " |")
    L += ["", "## Độ bất định", "",
          "| Chiến lược | Khoảng tin cậy 95% tỷ số tài sản (kiểm định / kiểm tra cuối) | Khoảng tin cậy 95% lợi thế giá vốn (kiểm định / kiểm tra cuối) | Hơn tín hiệu ngẫu nhiên (kiểm định / kiểm tra cuối) | Deflated Sharpe |",
          "|---|---|---|---|---|"]
    for name, x in (("Mô hình mới", c), ("Bot hiện tại", b)):
        ci = lambda k: f"{d3(x[k]['er_ci'][0])}–{d3(x[k]['er_ci'][1])}"  # noqa: E731
        cb = lambda k: f"{fmt.pct(x[k]['cba_ci'][0], 1)} đến {fmt.pct(x[k]['cba_ci'][1], 1)}"  # noqa: E731
        dsr = x["dsr"].get("dsr")
        L.append(f"| {name} | {ci('bootstrap')} / {ci('bootstrap_holdout')} | {cb('bootstrap')} / {cb('bootstrap_holdout')} | "
                 f"{fmt.pct(x['placebo']['percentile'])} / {fmt.pct(x['placebo_holdout']['percentile'])} | {fmt.dec(dsr, 3) if dsr is not None else 'không tính được (không khác mua đều)'} |")
    L += ["", "## Vì sao không đạt", "",
          "1. **Chỉ số chu kỳ không cho lợi thế vững so với mua đều** khi đo bằng tài sản cuối kỳ thay vì tỷ lệ thắng. Muốn mua gấp đôi lúc rẻ thì phải "
          "để dành tiền từ trước. Để dành trong lúc giá đang lên lại làm mất phần tăng. Trên giai đoạn huấn luyện, mọi bộ chỉ số với bảng hệ số mặc định "
          "đều kém mua đều. Bảng trung tính hơn chỉ đưa kết quả về sát mua đều.",
          "2. **Quan hệ giữa \"rẻ\" và lợi suất sau đó không ổn định.** Trong hồi quy đi tới, hệ số của mọi chỉ số định giá đổi dấu giữa các lần học. "
          "Chu kỳ 2013 và 2017 tăng rất mạnh ngay khi chỉ số đã báo \"đắt\".",
          "3. **Quá ít đợt độc lập.** Khung mua gấp đôi chỉ có 9 đợt, khung bán bớt 3 đợt từ 2011. Tiêu chí bán duy nhất đủ 10 đợt (RSI tuần ≥ 80) sai cả 11 lần.",
          "4. **Lớp ngắn hạn và vĩ mô** (funding, basis, stablecoin, RSI, hoãn mua sát sự kiện, trần vĩ mô) không cải thiện kịch bản xấu, và chỉ có dữ liệu từ 2018–2020.",
          "", "Điều đáng chú ý: **bot hiện tại cũng thua mua đều** ở cả kiểm định (0,988) và kiểm tra cuối (trung vị 0,940, kịch bản xấu 0,898). "
          "Lợi thế của nó không phân biệt được với may rủi (hơn 62% và 87% số lần chạy ngẫu nhiên). Mô hình mới \"tốt hơn\" bot hiện tại chỉ vì "
          "nó gần như mua đều.", "",
          "## Quyết định (theo mục 5 và điểm dừng 2 của mục 11)", "",
          "- **Không giao mô hình mới.** Logic bot hiện tại giữ nguyên trên trang web (tỷ lệ nên mua/bán, phương án, bên bán).",
          "- Chỉ giao phần an toàn: chữ hiển thị tập trung ở `bot/i18n/vi.yaml`, định dạng số và ngày kiểu Việt Nam, chế độ an toàn, triển khai tự động.",
          "- Phần mới \"Khuyến nghị giải ngân tuần này\" luôn cho **hệ số 1,0 (Chế độ an toàn: mua đều)**. Phần này nói rõ lý do và hiện bảng so sánh "
          "ở trên, để người dùng biết các khung của bot hiện tại chưa được chứng minh tốt hơn mua đều.",
          "- Thất bại này là kết quả chấp nhận được. Một bản nâng cấp gây hiểu lầm thì không.", ""]
    return "\n".join(L)
