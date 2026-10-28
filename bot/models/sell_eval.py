"""Phase 6: evaluate the take-profit rules against holding (development data until 31/12/2022)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.backtest import baselines, current_bot
from bot.features import build
from bot.features.panel import daily_cm
from bot.models import ablation_bc, overlays, sell
from bot.validation import registry, splits


def table(end: pd.Timestamp | None) -> pd.DataFrame:
    feat = build.weekly(end)
    cm = daily_cm(end)
    raw = overlays.weekly_group_b(feat.index, cm.set_index("date")["price"], end)
    t = feat.join(raw[["rsi_14w", "fng"]])
    s = current_bot.series(current_bot.export(), "auto")
    t["bot_sell"] = baselines.asof_scores(s, feat.index, "sell")
    return t


def run(log: bool = True, final: bool = False) -> dict:
    end = splits.dev_end(final)
    t = table(end)
    dates, price = t.index, t["price"].to_numpy()
    fl = sell.flags(t)
    stats = {c.id: sell.criterion_stats(fl[c.id].to_numpy(), price) for c in sell.CRITERIA}
    base_down = float(np.mean([price[j + 26] < price[j] for j in range(len(price) - 26)]))
    active = [i for i, s in stats.items() if s["episodes"] >= sell.MIN_EPISODES]
    frac, on_g = sell.sell_fractions(fl, active)
    m = ablation_bc.layer_a(build.weekly(end))
    cmp = sell.compare(dates, price, m, frac)
    n_better = sum(1 for x in cmp.values() if x["better"])
    decision = "action" if n_better >= 3 else "advisory"
    if log:
        registry.log("SELL:rule", "final" if final else "phase6", active, {"rule": "10%/30%, cap 50%/26w", "min_episodes": sell.MIN_EPISODES},
                     {"cycles_better": n_better, "sells": int((frac > 0).sum())})
    return {"stats": stats, "active": active, "base_down": base_down, "frac": frac, "on_groups": on_g, "cmp": cmp, "n_better": n_better,
            "decision": decision, "dates": dates}


NAMES = {"pi_cat": "Pi Cycle cắt lên (tỉ số ≥ 1)", "mvrvz_7": "MVRV Z-Score ≥ 7", "mvrv_3": "MVRV ≥ 3", "mayer_24": "Mayer Multiple ≥ 2,4",
         "rsiw_80": "RSI 14 tuần ≥ 80", "fng_90": "Fear & Greed ≥ 90", "puell_4": "Puell Multiple ≥ 4",
         "mvrvz_p": "MVRV Z-Score thuộc 5% cao nhất 4 năm", "mvrv_p": "MVRV thuộc 5% cao nhất 4 năm", "mayer_p": "Mayer Multiple thuộc 5% cao nhất 4 năm",
         "wma_p": "Giá / MA 200 tuần thuộc 5% cao nhất 4 năm", "puell_p": "Puell Multiple thuộc 5% cao nhất 4 năm", "bot_nb": "Bot báo Nên bán (tỷ lệ nên bán ≥ 85%)"}
GROUPS = {"valuation": "Định giá", "momentum": "Xu hướng giá", "positioning": "Tâm lý, vị thế", "model": "Mô hình của bot"}


def report(r: dict) -> str:
    from bot.i18n import fmt
    d3 = lambda x: fmt.dec(x, 3)  # noqa: E731
    groups = {c.id: c.group for c in sell.CRITERIA}
    L = ["# Bên bán: chốt lời so với giữ nguyên", "",
         "Dữ liệu từ 2011 đến 31/12/2022 (giai đoạn kiểm tra cuối vẫn khóa). Đợt = các tuần bật cách nhau dưới 8 tuần, như trên trang web. "
         "\"Đúng\" = giá 26 tuần sau thấp hơn lúc bật (chỉ để tham khảo). Tiêu chí dưới 10 đợt độc lập → chỉ hiển thị, không bao giờ dẫn tới hành động.", "",
         f"Mốc: bán vào một tuần bất kỳ thì giá 26 tuần sau thấp hơn {fmt.pct(r['base_down'])} số lần.", "",
         "| Tiêu chí | Nhóm | Số đợt | Số tuần bật | Đúng sau 26 tuần | Khoảng tin cậy 95% | Vai trò |", "|---|---|---|---|---|---|---|"]
    for i, s in r["stats"].items():
        L.append(f"| {NAMES[i]} | {GROUPS[groups[i]]} | {s['episodes']} | {s['weeks_on']} | {fmt.pct(s['right'])} ({s['n']}) | {fmt.pct(s['lo'])}–{fmt.pct(s['hi'])} | "
                 f"{'dùng cho quy tắc' if i in r['active'] else 'chỉ hiển thị (ít bằng chứng)'} |")
    L += ["", "Quy tắc hành động trên các tiêu chí đủ đợt: bán 10% lượng BTC khi nhóm định giá bật cùng nhóm xu hướng hoặc tâm lý; bán 30% khi từ 3 nhóm "
          "bật; không bán quá 50% trong 26 tuần; tiền bán vào quỹ dự trữ và chỉ mua lại qua lớp mua. Nền mua là lớp A đã chọn.", "",
          "| Chu kỳ halving | Số tuần bán | P10 khung 52 tuần: giữ / có bán | Trung vị: giữ / có bán | Sụt giảm lớn nhất: giữ / có bán | Tỷ số cả chu kỳ: giữ / có bán | Cải thiện cả hai? |",
          "|---|---|---|---|---|---|---|"]
    for n, x in r["cmp"].items():
        L.append(f"| {n}{'' if x['complete'] else ' (chưa trọn)'} | {x['sells']} | {d3(x['p10_hold'])} / {d3(x['p10_sell'])} | {d3(x['med_hold'])} / {d3(x['med_sell'])} | "
                 f"{fmt.pct(x['mdd_hold'])} / {fmt.pct(x['mdd_sell'])} | {d3(x['er_cycle_hold'])} / {d3(x['er_cycle_sell'])} | {'có' if x['better'] else 'không'} |")
    L += ["", f"Số chu kỳ cải thiện cả kịch bản xấu lẫn sụt giảm: {r['n_better']}/{len(r['cmp'])}. Kết luận: "
          + ("**bên bán được dùng như hành động**." if r["decision"] == "action" else
             "**bên bán chỉ là lời khuyên dạng chữ** (chưa đạt điều kiện 3/4 chu kỳ). Trang web vẫn hiển thị các tiêu chí như hiện nay."), ""]
    return "\n".join(L)
