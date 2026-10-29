"""Plan for deploying a lump of money (settings in config/candidates.yaml, section plan).

For every past start week, 1 unit of money is invested in N equal weekly parts at the Monday close (fees and slippage as
the bot), idle cash earns nothing, and the total value is read 52 weeks after the first purchase. Each plan gets the
distribution of that ROI over all start weeks, the deepest fall of the total value, and how often it beat investing
everything at once. The "best ROI" plan has the highest median; the recommended plan is, among the best plan and the
plans not significantly worse than it (block-bootstrap interval of the median paired difference contains 0), the one
with the highest 10th percentile. No signal tilts the plans: the six acceptance criteria were not met.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, cfg, load_yaml


def outcomes(price: np.ndarray, starts: np.ndarray, n_weeks: int, horizon: int, fee: float, slip: float) -> tuple[np.ndarray, np.ndarray]:
    """ROI after `horizon` weeks and the deepest fall of BTC + idle cash, investing 1 in `n_weeks` equal weekly parts."""
    buys = np.zeros(horizon + 1)
    buys[:n_weeks] = 1.0 / n_weeks
    cash = 1.0 - np.cumsum(buys)
    roi, mdd = np.empty(len(starts)), np.empty(len(starts))
    for k, i in enumerate(starts):
        p = price[i:i + horizon + 1]
        v = np.cumsum(buys * (1 - fee) / (p * (1 + slip))) * p + cash
        roi[k] = v[-1] - 1
        mdd[k] = float(np.min(v / np.maximum.accumulate(v) - 1))
    return roi, mdd


def start_weeks(t: pd.DataFrame, horizon: int, data_from: pd.Timestamp) -> np.ndarray:
    price = t["exec_monday"].to_numpy(dtype=float)
    fin = np.isfinite(price)
    return np.array([i for i in range(len(price) - horizon) if t.index[i] >= data_from and fin[i:i + horizon + 1].all()], dtype=int)


def compute(t: pd.DataFrame, pc: dict, fee: float, slip: float, n_boot: int, seed: int, data_from: pd.Timestamp) -> dict:
    H = pc["horizon_weeks"]
    price = t["exec_monday"].to_numpy(dtype=float)
    starts = start_weeks(t, H, data_from)
    if len(starts) < 2 * H:
        return {"starts": int(len(starts)), "options": []}
    res = {n: outcomes(price, starts, n, H, fee, slip) for n in pc["options_weeks"]}
    lump = res[pc["options_weeks"][0]][0]
    best = max(res, key=lambda n: np.median(res[n][0]))
    idx = measure.stationary_indices(len(starts), H, n_boot, np.random.default_rng(seed))
    eps = max(1, len(starts) // H)
    opts = []
    for n, (roi, mdd) in res.items():
        d = res[best][0] - roi
        boot = np.median(d[idx], axis=1)
        ci = [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]
        beat = None if n == pc["options_weeks"][0] else float(np.mean(roi > lump))
        opts.append({"weeks": int(n), "median": float(np.median(roi)), "p10": float(np.quantile(roi, 0.10)), "p90": float(np.quantile(roi, 0.90)),
                     "worst": float(roi.min()), "loss_share": float(np.mean(roi < 0)), "mdd_median": float(np.median(mdd)), "mdd_worst": float(mdd.min()),
                     "beat_lump": beat, "beat_lump_ci": list(wilson(round(beat * eps), eps)) if beat is not None else None,
                     "diff_vs_best": float(np.median(d)), "diff_ci": ci, "not_worse": bool(n == best or ci[0] <= 0 <= ci[1])})
    rec = max((o for o in opts if o["not_worse"]), key=lambda o: o["p10"])
    return {"from": t.index[starts[0]].strftime("%Y-%m-%d"), "to": t.index[starts[-1]].strftime("%Y-%m-%d"), "starts": int(len(starts)), "episodes": eps,
            "horizon": H, "options": opts, "best_roi": int(best), "recommended": int(rec["weeks"])}


def for_report(t: pd.DataFrame | None = None) -> dict:
    """Block for data/recommendation.json: plan statistics on the main period, plus the acceptance verdict."""
    from bot.features import weekly_close as wc
    pc = load_yaml(CONFIG / "candidates.yaml")["plan"]
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    c = cfg()["costs"]
    t = wc.load(None) if t is None else t
    out = compute(t, pc, c["fee"], c["slippage"], rb["bootstrap_n"], rb["seed"], pd.Timestamp(str(pc["data_from"])))
    acc = DATA / "results" / "acceptance.json"
    out["signals_passed"] = json.loads(acc.read_text(encoding="utf-8")).get("passed") if acc.exists() else None
    out["cost"] = float(c["fee"] + c["slippage"])
    out["last_week"] = t.index[np.isfinite(t["exec_monday"].to_numpy(dtype=float))][-1].strftime("%Y-%m-%d")
    return out


def write_doc() -> dict:
    """docs/PLAN.md: main period and full history side by side (Vietnamese)."""
    from bot.features import weekly_close as wc
    from bot.i18n import fmt
    pc = load_yaml(CONFIG / "candidates.yaml")["plan"]
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    c = cfg()["costs"]
    t = wc.load(None)
    runs = {k: compute(t, pc, c["fee"], c["slippage"], rb["bootstrap_n"], rb["seed"], pd.Timestamp(str(pc[k]))) for k in ("data_from", "data_from_full")}
    name = lambda n: "Giải ngân một lần" if n == 1 else f"Chia đều {n} tuần"  # noqa: E731
    sp = lambda x: fmt.pct(x, 0, sign=True)  # noqa: E731
    L = ["# Kế hoạch giải ngân một khoản tiền", "",
         "Đăng ký trước: `config/candidates.yaml` mục `plan` (commit `0be9828`). Mã: `bot/models/deploy_plan.py`. Trang web hiện bảng này và lập lịch theo số tiền bạn nhập.", "",
         f"- Với mỗi tuần bắt đầu trong quá khứ: chia số tiền thành N phần, mua mỗi thứ Hai (giá đóng thứ Hai, phí {fmt.pct(c['fee'], 2)} + trượt giá {fmt.pct(c['slippage'], 2)}). "
         f"Tiền chưa mua giữ nguyên, lãi 0%. Đọc tổng giá trị {pc['horizon_weeks']} tuần sau lần mua đầu.",
         f"- ROI cao nhất: {pc['best_roi']}. Đề xuất: {pc['rule']}.", f"- {pc['signals'][0].upper() + pc['signals'][1:]}.", ""]
    for k, title in (("data_from", "3 chu kỳ gần nhất (dùng trên web)"), ("data_from_full", "Toàn bộ lịch sử (tham khảo)")):
        r = runs[k]
        L += [f"## {title}: {fmt.date(r['from'])} → {fmt.date(r['to'])}, {r['starts']} tuần bắt đầu, khoảng {r['episodes']} đợt độc lập", "",
              "| Phương án | Trung vị sau 1 năm | 10% xấu nhất | 10% tốt nhất | Xấu nhất | Tỷ lệ lỗ | Giảm sâu nhất (trung vị / tệ nhất) | Thắng giải ngân một lần (Wilson theo đợt) | Kém ROI cao nhất (KTC 95%) |",
              "|---|---|---|---|---|---|---|---|---|"]
        for o in r["options"]:
            beat = "—" if o["beat_lump"] is None else f"{fmt.pct(o['beat_lump'])} ({fmt.pct(o['beat_lump_ci'][0])}–{fmt.pct(o['beat_lump_ci'][1])})"
            tag = " **ROI cao nhất**" if o["weeks"] == r["best_roi"] else ""
            tag += " **← đề xuất**" if o["weeks"] == r["recommended"] else ""
            L.append(f"| {name(o['weeks'])}{tag} | {sp(o['median'])} | {sp(o['p10'])} | {sp(o['p90'])} | {sp(o['worst'])} | {fmt.pct(o['loss_share'])} | "
                     f"{sp(o['mdd_median'])} / {sp(o['mdd_worst'])} | {beat} | {sp(o['diff_vs_best'])} ({sp(o['diff_ci'][0])} đến {sp(o['diff_ci'][1])}) |")
        L.append("")
    L += ["Giới hạn: các cửa sổ 1 năm chồng lấn nhau nên số đợt độc lập ít (khoảng tin cậy rộng); BTC đã tăng mạnh trong lịch sử nên giải ngân sớm thường lợi hơn, "
          "nhưng không có gì bảo đảm điều đó lặp lại. Công cụ tham khảo, không phải lời khuyên đầu tư.", ""]
    (ROOT / "docs" / "PLAN.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
    return runs
