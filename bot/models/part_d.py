"""Part D runner: zones with hysteresis and the walk-forward multiplier for the nested model and the two simple rules,
data until eval_end (31/12/2023). Writes data/results/part_d.json and docs/ZONES_D.md."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.backtest import measure, metrics
from bot.backtest.engine import simulate
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.i18n import fmt
from bot.models import part_c, wf_logit as wf, zones as zn
from bot.report.measure_b import sim_config

NAMES = {"phai": "Phải mua", "cannhac": "Cân nhắc mua", "khong": "Không nên mua"}
HNAME = {4: "1 tháng", 13: "3 tháng", 26: "6 tháng", 52: "1 năm"}
GATE_TEXT = {"chua_kiem_dinh": "chưa chạy kiểm định Phần I", "chua_dat_phan_i": "chưa đạt tiêu chí Phần I", "dat_phan_i": "đạt tiêu chí Phần I"}


def cost(price: np.ndarray, m: np.ndarray, n_boot: int, block: int, seed: int) -> dict:
    c = sim_config()
    er = float(metrics.equity_ratio(simulate(price, m, c), simulate(price, None, c))[0])
    rng = np.random.default_rng(seed)
    lr = np.diff(np.log(price))
    idx = measure.stationary_indices(len(lr), block, n_boot, rng)
    P = np.concatenate([np.full((n_boot, 1), price[0]), price[0] * np.exp(np.cumsum(lr[idx], axis=1))], axis=1)
    M = np.concatenate([np.full((n_boot, 1), m[0]), m[1:][idx]], axis=1)
    b = metrics.equity_ratio(simulate(P, M, c), simulate(P, None, c)) - 1
    return {"advantage": er - 1, "ci": [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))]}


def run(write: bool = True) -> dict:
    sp = part_c.spec()
    md, zc, mc = sp["model"], sp["zones"], sp["multiplier"]
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    seed, n_boot = rb["seed"], rb["bootstrap_n"]
    eval_end = pd.Timestamp(str(md["eval_end"]))
    t = part_c.table(eval_end)
    sets = {k: v["features"] for k, v in sp["sets"].items()}
    nested = wf.nested_oos(t, sets, md["lambdas"], h=md["target_weeks"], refit=md["refit_weeks"], min_train=md["min_train_weeks"],
                           inner_valid=md["inner_valid_weeks"])
    scores = {"Mô hình lồng nhau": nested["p"], "Quy tắc MVRV": t["cheap_mvrv"], "Quy tắc Giá/MA 200 tuần": t["cheap_p_200wma"]}
    bounds = tuple(mc["bounds"])
    out = {"eval_end": eval_end.strftime("%Y-%m-%d"), "rank_note": zc["rank_note"], "strategies": {}}
    for name, p in scores.items():
        rank = (wf.oos_rank(p.dropna(), md["rank_min_weeks"]) * 100).dropna()
        price = t["exec_monday"].reindex(rank.index).to_numpy(dtype=float)
        ok = np.isfinite(price)
        rank, price = rank[ok], price[ok]
        zp, zh = zn.plain_zones(rank, zc["thresholds"]), zn.hysteresis_zones(rank, zc["thresholds"], zc["hysteresis"])
        tab = measure.zone_table(zh, price, rb["horizons_weeks"], zn.ORDER, n_boot=n_boot, seed=seed, gap=rb["episode_gap_weeks"])
        mono = measure.monotone(tab, ["phai", "cannhac", "__baseline__", "khong"])
        m, hist = zn.walk_multipliers(zh, price, md["target_weeks"], mc["refit_weeks"], mc["scale"], bounds, mc["min_episodes"], n_boot, seed,
                                      rb["episode_gap_weeks"])
        ungated = cost(price, m, n_boot, rb["cost_block_weeks"], seed)
        gm, reason = zn.gate(1.0)
        last = rank.index[-1]
        out["strategies"][name] = {
            "from": rank.index[0].strftime("%Y-%m-%d"), "weeks": int(len(rank)), "flips_plain": zn.flips(zp), "flips_hysteresis": zn.flips(zh),
            "zones": tab, "monotone": mono, "share_not_one": float(np.mean(m != 1.0)), "avg_mult": float(np.mean(m)),
            "mult_values": {f"{v:.2f}": int(c) for v, c in zip(*np.unique(np.round(m, 2), return_counts=True))},
            "ungated": ungated, "last": {"date": last.strftime("%Y-%m-%d"), "rank": float(rank.iloc[-1]), "zone": zh.iloc[-1],
                                         "mult_rule": float(m[-1]), "mult_used": gm, "reason": reason},
            "edges_last": hist[-1]["edges"] if hist else None}
    if write:
        (DATA / "results" / "part_d.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (ROOT / "docs" / "ZONES_D.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    return out


def markdown(o: dict) -> str:
    sp = part_c.spec()
    zc, mc = sp["zones"], sp["multiplier"]
    pct = lambda x, d=0: "—" if x is None else fmt.pct(x, d, sign=True)  # noqa: E731
    L = ["# Phần D: khung mua và hệ số giải ngân", "",
         f"Dữ liệu đến **{fmt.date(o['eval_end'])}** (holdout khóa). Tham số đăng ký trước trong `config/candidates.yaml` (commit `c7eeb48`).", "",
         f"- **{o['rank_note']}**",
         f"- Khung: Phải mua từ {zc['thresholds']['phai']}, Cân nhắc mua từ {zc['thresholds']['cannhac']} (thang thứ hạng 0–100). **Vùng trễ {zc['hysteresis']} điểm**: "
         f"vào khung khi vượt ngưỡng, chỉ ra khi lùi quá ngưỡng {zc['hysteresis']} điểm. Tính trên giá đóng tuần.",
         f"- Hệ số trong khoảng {fmt.dec(mc['bounds'][0], 1)}–{fmt.dec(mc['bounds'][1], 1)}: lệch khỏi 1,0 theo **cận** khoảng tin cậy của lợi thế khung "
         f"(tỷ lệ thắng 26 tuần trừ mốc cùng giai đoạn): m = 1 + {fmt.dec(mc['scale'], 1)} × cận dưới (khung mua) hoặc cận trên (Không nên mua). "
         f"Cận chứa 0, hoặc dưới {mc['min_episodes']} đợt → 1,0. Lợi thế ước lượng lại mỗi {mc['refit_weeks']} tuần, chỉ bằng các tuần đã biết kết quả.",
         "- **Cổng Phần I**: chỉ dùng hệ số khác 1,0 khi đạt tất cả tiêu chí Phần I; chưa đạt → 1,0 kèm lý do.", ""]
    for name, s in o["strategies"].items():
        tab = s["zones"]
        u = s["ungated"]
        L += [f"## {name}", "",
              f"Từ {fmt.date(s['from'])}, {s['weeks']} tuần có thứ hạng ngoài mẫu. Số lần đổi khung: **không vùng trễ {s['flips_plain']} lần, có vùng trễ {s['flips_hysteresis']} lần**.", "",
              "| Kỳ hạn | Mốc (thắng) | " + " | ".join(NAMES[z] for z in zn.ORDER) + " | Đơn điệu? |", "|---|---|" + "---|" * len(zn.ORDER) + "---|"]
        for h in tab["horizons"]:
            cells = []
            for z in zn.ORDER:
                c = tab["zones"][z][h]
                if not c.get("weeks"):
                    cells.append("không có")
                    continue
                ci = c["ci"]
                verdict = {"chua_co_loi_the": "chưa có lợi thế", "hon_moc": "hơn mốc", "kem_moc": "kém mốc", "it_dot": "ít đợt"}[c["verdict"]]
                cells.append(f"{fmt.pct(c['win'])} ({pct(c['diff'])}; {pct(ci[0]) if ci[0] is not None else '—'} đến {pct(ci[1]) if ci[1] is not None else '—'}; "
                             f"{c['weeks']} tuần, {c['episodes']} đợt) {verdict}")
            L.append(f"| {HNAME[h]} | {fmt.pct(tab['baseline'][h]['win'])} | " + " | ".join(cells) + f" | {'có' if s['monotone'][h] else 'không'} |")
        lst = s["last"]
        L += ["", f"- Hệ số theo quy tắc (chưa qua cổng): khác 1,0 ở **{fmt.pct(s['share_not_one'])}** số tuần, trung bình {fmt.dec(s['avg_mult'], 3)}; "
              f"các giá trị: " + ", ".join(f"{k.replace('.', ',')} ({v} tuần)" for k, v in s["mult_values"].items()) + ".",
              f"- Nếu dùng hệ số đó (chưa qua cổng): lợi thế giá vốn {pct(u['advantage'], 1)} (khoảng tin cậy {pct(u['ci'][0], 1)} đến {pct(u['ci'][1], 1)}).",
              f"- Tuần cuối trước holdout ({fmt.date(lst['date'])}): thứ hạng {fmt.num(lst['rank'], 0)}, khung {NAMES.get(lst['zone'], '—')}, hệ số theo quy tắc "
              f"{fmt.dec(lst['mult_rule'], 2)}, **hệ số dùng {fmt.dec(lst['mult_used'], 1)}** ({GATE_TEXT[lst['reason']]}).", ""]
    L += ["## Kết luận Phần D", "",
          "- Vùng trễ làm khung bớt nhảy qua lại (xem số lần đổi khung ở trên), sửa lỗi nhãn đổi liên tục khi giá sát ngưỡng.",
          "- Hệ số tính theo cận khoảng tin cậy nên tự co về 1,0 khi chưa chắc chắn. Với dữ liệu đến 2023, phần lớn các tuần hệ số theo quy tắc là 1,0.",
          "- Cổng Phần I chưa mở, nên **hệ số dùng thực tế là 1,0 (mua đều)**. Phần I sẽ chấm đủ 6 tiêu chí một lần.", ""]
    return "\n".join(L)
