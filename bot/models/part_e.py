"""Part E runner: the single sell system on data until eval_end (31/12/2023). Writes data/results/part_e.json and
docs/SELL_E.md (Vietnamese)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.i18n import fmt
from bot.models import part_c, sell_system as ss

CYCLES = [("2012-11-28", "2016-07-08"), ("2016-07-09", "2020-05-10"), ("2020-05-11", "2023-12-31")]
LEVEL_VI = {"giu": "Giữ", "chot": "Chốt lời một phần", "ban": "Bán phần lớn"}


def criterion(on: np.ndarray, price: np.ndarray, dates: pd.DatetimeIndex, h: int, gap: int, n_boot: int, seed: int) -> dict:
    """Episodes of a criterion, share of episodes whose price h weeks later is lower (Wilson), and the uniform
    bootstrap of the difference vs all weeks; also per cycle."""
    eps = ss.episode_starts(on, gap)
    r, _ = measure.forward(price, h)
    done = [a for a in eps if np.isfinite(r[a])]
    k = int(sum(r[a] < 0 for a in done))
    lo, hi = wilson(k, len(done))
    base = float(np.mean(r[np.isfinite(r)] < 0))
    z = pd.Series(np.where(on, "bat", "tat"), index=dates, dtype=object)
    tab = measure.zone_table(z, price, [h], ["bat", "tat"], n_boot=n_boot, seed=seed, gap=gap)["zones"]["bat"][h]
    per = []
    for a_, b_ in CYCLES:
        m = (dates >= a_) & (dates <= b_)
        e = [x for x in done if m[x]]
        rr = r[m]
        bl = float(np.mean(rr[np.isfinite(rr)] < 0)) if np.isfinite(rr).any() else None
        kk = int(sum(r[x] < 0 for x in e))
        per.append({"cycle": f"{a_[:4]}–{b_[:4]}", "episodes": len(e), "right": kk, "base_lower": bl,
                    "works": bool(len(e) >= 2 and bl is not None and kk / len(e) > bl)})
    works_recent = all(p["works"] for p in per[-2:])
    return {"episodes": len(eps), "weeks_on": int(on.sum()), "done": len(done), "right": k, "right_share": k / len(done) if done else None,
            "wilson": [lo, hi], "base_lower": base,
            "boot_diff_lower": None if tab.get("diff") is None else -tab["diff"], "boot_ci_lower": None if tab.get("ci", [None])[0] is None else [-tab["ci"][1], -tab["ci"][0]],
            "verdict": tab.get("verdict"), "cycles": per,
            "trusted": "cho_phan_i" if works_recent else "khong"}


def run(write: bool = True) -> dict:
    sp = part_c.spec()
    se = sp["sell"]
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    eval_end = pd.Timestamp(str(sp["model"]["eval_end"]))
    t = part_c.table(eval_end)
    t = t[t.index >= "2012-01-01"]
    t = t[np.isfinite(t["exec_monday"])]
    dates, close, fill = t.index, t["close"].to_numpy(dtype=float), t["exec_monday"].to_numpy(dtype=float)
    fl = ss.flags(t, se["groups"], se["threshold_pct"])
    cnt = ss.group_count(fl, se["groups"])
    h, gap = se["outcome_weeks"], rb["episode_gap_weeks"]
    crit = {f: criterion(fl[f].to_numpy(), fill, dates, h, gap, rb["bootstrap_n"], rb["seed"]) for f in fl.columns}
    trig = {f"≥{g} nhóm": criterion((cnt >= g).to_numpy(), fill, dates, h, gap, rb["bootstrap_n"], rb["seed"]) for g in se["triggers"]}
    sims = []
    bb = se["buyback"]
    for g in se["triggers"]:
        mask = (cnt >= g).to_numpy()
        for frac in se["sell_fractions"]:
            row = {"trigger": g, "frac": frac, "cycles": []}
            for a_, b_ in [("2012-11-28", "2023-12-31")] + CYCLES:
                m = (dates >= a_) & (dates <= b_)
                idx = np.where(m)[0]
                if len(idx) < 52:
                    continue
                st = ss.episode_starts(mask[idx], gap)  # already relative to the window
                r = ss.simulate(close[idx], fill[idx], st, frac, bb["price_below_sale"], bb["max_weeks"])
                tr = r["trades"]
                closed = [x for x in tr if "buy" in x]
                row["cycles"].append({"period": f"{a_[:4]}–{b_[:4]}", "ratio": float(r["equity"][-1] / r["equity_dca"][-1]),
                                      "mdd": ss.mdd(r["equity"]), "mdd_dca": ss.mdd(r["equity_dca"]), "sales": len(tr), "closed": len(closed),
                                      "right": int(sum(x["right"] for x in closed)), "open_end": len(tr) - len(closed)})
            sims.append(row)
    last = dates[-1]
    out = {"eval_end": eval_end.strftime("%Y-%m-%d"), "criteria": crit, "triggers": trig, "sims": sims,
           "last": {"date": last.strftime("%Y-%m-%d"), "groups_on": int(cnt.iloc[-1]), "level": ss.level_of(int(cnt.iloc[-1]), se["levels"]),
                    "criteria_on": [f for f in fl.columns if bool(fl[f].iloc[-1])]},
           "weeks": int(len(t)), "from": dates[0].strftime("%Y-%m-%d")}
    if write:
        (DATA / "results" / "part_e.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (ROOT / "docs" / "SELL_E.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    return out


def markdown(o: dict) -> str:
    se = part_c.spec()["sell"]
    p0 = lambda x: "—" if x is None else fmt.pct(x)  # noqa: E731
    sp = lambda x: "—" if x is None else fmt.pct(x, 1, sign=True)  # noqa: E731
    L = ["# Phần E: bên bán, một hệ thống", "",
         f"Dữ liệu từ {fmt.date(o['from'])} đến **{fmt.date(o['eval_end'])}** (holdout khóa). Đăng ký trước: `config/candidates.yaml` mục `sell` (commit `d7a47ce`).", "",
         f"- Tiêu chí bật khi chỉ số thuộc **5% đắt nhất của 4 năm trước** (phân vị trượt, không ngưỡng tuyệt đối). Đếm theo **nhóm**: "
         + "; ".join(f"{k.replace('_', ' ')}: {', '.join(v)}" for k, v in se["groups"].items()) + ".",
         "- **Một hệ thống duy nhất**: 0 nhóm → Giữ; 1–2 nhóm → Chốt lời một phần; ≥ 3 nhóm → Bán phần lớn (thay cho khung \"Nên bán\" và bảng tiêu chí chốt lời riêng).",
         f"- Quy tắc thực thi: bán X% BTC đang giữ **một lần khi đợt tín hiệu bắt đầu** (quyết định ở giá đóng Chủ nhật, khớp ở giá đóng thứ Hai); mua lại toàn bộ khi giá ≤ "
         f"{fmt.pct(se['buyback']['price_below_sale'])} giá bán bình quân hoặc sau {se['buyback']['max_weeks']} tuần. Vẫn mua đều mỗi tuần; so với mua đều không bán.",
         f"- Chấm từng tiêu chí: giá {se['outcome_weeks']} tuần sau thấp hơn lúc bật, theo **đợt** (Wilson), kèm bootstrap thống nhất của mức chênh so với mọi tuần.", "",
         "## 1. Từng tiêu chí và tín hiệu theo nhóm", "",
         "| Tiêu chí | Số đợt | Số tuần bật | Đợt đúng (giá thấp hơn sau 26 tuần) | Wilson theo đợt | Mốc (mọi tuần) | Chênh (bootstrap) | Theo chu kỳ: đúng/đợt | \"Đáng tin\" |",
         "|---|---|---|---|---|---|---|---|---|"]
    for name, c in {**o["criteria"], **o["triggers"]}.items():
        ci = c["boot_ci_lower"]
        cyc = "; ".join(f"{x['cycle']}: {x['right']}/{x['episodes']}" for x in c["cycles"])
        trust = "chờ chấm chu kỳ 2021–2025 ở Phần I" if c["trusted"] == "cho_phan_i" else "không"
        L.append(f"| {name} | {c['episodes']} | {c['weeks_on']} | {c['right']}/{c['done']} ({p0(c['right_share'])}) | {p0(c['wilson'][0])}–{p0(c['wilson'][1])} | "
                 f"{p0(c['base_lower'])} | {sp(c['boot_diff_lower'])} ({sp(ci[0]) if ci else '—'} đến {sp(ci[1]) if ci else '—'}) | {cyc} | {trust} |")
    L += ["", "\"Đáng tin\" chỉ khi tiêu chí đúng nhiều hơn mốc ở **2 chu kỳ gần nhất, có chu kỳ 2021–2025**. Dữ liệu 2024–2025 nằm trong holdout, nên tiêu chí "
          "qua được 2 chu kỳ có sẵn chỉ ở trạng thái \"chờ chấm ở Phần I\".", "",
          "## 2. Quy tắc bán so với giữ nguyên (cùng mua đều mỗi tuần)", "",
          "| Kích hoạt | Bán mỗi lần | Giai đoạn | Tài sản so với giữ nguyên | Sụt giảm lớn nhất: có bán / giữ nguyên | Số lần bán | Đã mua lại: đúng / tổng | Còn mở cuối kỳ |",
          "|---|---|---|---|---|---|---|---|"]
    for s in o["sims"]:
        for c in s["cycles"]:
            L.append(f"| ≥{s['trigger']} nhóm | {fmt.pct(s['frac'])} | {c['period']} | {fmt.pct(c['ratio'] - 1, 1, sign=True)} | {fmt.pct(c['mdd'])} / {fmt.pct(c['mdd_dca'])} | "
                     f"{c['sales']} | {c['right']} / {c['closed']} | {c['open_end']} |")
    lst = o["last"]
    L += ["", "## 3. Kết luận Phần E", "",
          f"- Tuần cuối trước holdout ({fmt.date(lst['date'])}): {lst['groups_on']} nhóm bật → **{LEVEL_VI[lst['level']]}**"
          + (f" (tiêu chí: {', '.join(lst['criteria_on'])})." if lst["criteria_on"] else "."),
          ]
    for s in o["sims"]:
        cyc = [c for c in s["cycles"] if c["period"] != "2012–2023"]
        whole = next(c for c in s["cycles"] if c["period"] == "2012–2023")
        pos = sum(c["ratio"] > 1 for c in cyc)
        L.append(f"- Bán {fmt.pct(s['frac'])} khi ≥{s['trigger']} nhóm: có lợi ở {pos}/{len(cyc)} chu kỳ; cả giai đoạn {fmt.pct(whole['ratio'] - 1, 1, sign=True)} "
                 f"với {whole['sales']} lần bán ({whole['right']}/{whole['closed']} lần mua lại rẻ hơn giá bán).")
    n_trust = sum(c["trusted"] == "cho_phan_i" for c in {**o["criteria"], **o["triggers"]}.values())
    L += [f"- Tiêu chí qua được 2 chu kỳ gần nhất có dữ liệu: {n_trust}. Mọi kết luận bên bán dựa trên rất ít đợt (dưới 10), nên **chưa có lợi thế đáng tin**; "
          "bên bán chỉ hiển thị mức Giữ / Chốt lời một phần / Bán phần lớn để tham khảo, kèm số đợt.", ""]
    return "\n".join(L)
