"""Phase 4 ablation for layer A. Selection uses the TRAIN split only (rolling windows from 07/2013, when every
feature except P/200WMA exists); validation is reported afterwards, never used to choose.

Order: single features → forward selection (max 4, skip any feature with |ρ| > 0.8 to one already chosen) →
sign-constrained ridge on the chosen set → comparison with the current bot. Every evaluation is a registry trial.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.backtest import benchmark, metrics
from bot.config import cfg
from bot.features import build
from bot.models import core
from bot.validation import evaluate, splits

SEL_FROM = pd.Timestamp("2013-07-01")
CANDIDATES = ["mvrv", "mvrv_z", "pi_ratio", "p_200wma", "mayer", "puell", "dd_ath", "hash_ribbon_buy"]  # nupl ≡ mvrv in rank


def train_objective(dates: pd.DatetimeIndex, price: np.ndarray, m: np.ndarray) -> dict:
    v = cfg()["validation"]
    a, b = splits.split("train")
    df = metrics.rolling(dates, price, m, max(a, SEL_FROM), b, v["rolling_window_weeks"], v.get("rolling_step_weeks", 4))
    return metrics.roll_summary(df)


def degenerate(x: dict) -> bool:
    """A multiplier that never changes the outcome (every window equals DCA) carries no signal and cannot be chosen."""
    return abs(x.get("er_min", 1) - 1) < 1e-9 and abs(x.get("er_p10", 1) - 1) < 1e-9 and x.get("share_above_1", 0) == 0


def better(x: dict, y: dict | None, tol: float = 0.01) -> bool:
    """Prefer the better bad case (P10) unless medians differ by more than `tol` (section 1: optimise the bad case)."""
    if y is None:
        return True
    if abs(x["er_median"] - y["er_median"]) <= tol:
        return x["er_p10"] > y["er_p10"]
    return x["er_median"] > y["er_median"] and x["er_p10"] >= y["er_p10"] - tol


TABLES = {
    "T0": core.STEP_TABLE,                                                   # spec starting point (mean < 1: often idle cash)
    "T1": [(0.80, 2.0), (0.60, 1.25), (0.20, 1.0), (0.0, 0.5)],               # neutral = 1, cut only in the most expensive fifth
    "T2": [(0.80, 1.75), (0.60, 1.25), (0.40, 1.0), (0.20, 0.75), (0.0, 0.25)],  # symmetric around 1
}


def run(log: bool = True) -> dict:
    """log=False re-runs the same ablation for a report without counting the trials twice."""
    feat = build.weekly(splits.dev_end(), write=True)
    dates, price = feat.index, feat["price"].to_numpy()
    rho = feat.loc[:"2019-12-31", ["cheap_" + c for c in CANDIDATES if c != "hash_ribbon_buy"]].corr(method="spearman")
    trials: list[dict] = []

    def trial(name: str, names: list[str], m: np.ndarray, params: dict, heavy: bool = False) -> dict:
        obj = train_objective(dates, price, m)
        res = evaluate.evaluate(name, dates, price, m, features=names, params=params, stage="phase4", heavy=heavy, log=log)
        row = {"name": name, "features": names, "train": obj, "res": res, "mult": m, "params": params}
        trials.append(row)
        return row

    per_table = {}
    for tk, table in TABLES.items():
        mk = lambda names: core.step_map(core.composite(feat, names).to_numpy(), table)  # noqa: E731
        singles = {c: trial(f"A1:{tk}:{c}", [c], mk([c]), {"model": "composite", "table": tk}) for c in CANDIDATES}
        chosen: list[str] = []
        best = None
        steps = []
        while len(chosen) < 4:
            pick, pick_row = None, None
            for c in CANDIDATES:
                if c in chosen:
                    continue
                if c != "hash_ribbon_buy" and any(o != "hash_ribbon_buy" and abs(rho.loc["cheap_" + c, "cheap_" + o]) > 0.8 for o in chosen):
                    continue
                names = chosen + [c]
                row = singles[c] if len(names) == 1 else trial(f"A1:{tk}:{'+'.join(names)}", names, mk(names), {"model": "composite", "table": tk})
                if degenerate(row["train"]):
                    continue
                if pick_row is None or better(row["train"], pick_row["train"]):
                    pick, pick_row = c, row
            if pick is None or (best is not None and not better(pick_row["train"], best["train"])):
                steps.append({"stop": True, "candidate": pick, "train": pick_row["train"] if pick_row else None})
                break
            chosen.append(pick)
            best = pick_row
            steps.append({"add": pick, "train": pick_row["train"]})
        per_table[tk] = {"singles": singles, "steps": steps, "chosen": chosen, "best": best}
    # pick the table + set with the better bad case on TRAIN
    win = None
    for tk, x in per_table.items():
        if win is None or better(x["best"]["train"], per_table[win]["best"]["train"]):
            win = tk
    chosen, best = per_table[win]["chosen"], per_table[win]["best"]
    # model 2 on the uncorrelated pool, only to see if fitting beats the composite
    pool = [c for c in CANDIDATES if c != "hash_ribbon_buy"]
    sc, info = core.ridge_signed(feat, pool)
    ridge_row = trial("A2:ridge:pool", pool, core.step_map(sc.to_numpy(), TABLES[win]), {"model": "ridge_signed", "lam": 1.0, "table": win})
    ridge_row["info"] = info
    final_row = trial(f"A:final:{win}:{'+'.join(chosen)}", chosen, best["mult"], {"model": "composite", "table": win}, heavy=True)
    return {"feat": feat, "rho": rho, "tables": per_table, "table": win, "chosen": chosen, "ridge": ridge_row, "final": final_row, "trials": trials}


def report(r: dict, bench: dict | None = None, gbm: dict | None = None) -> str:
    """Vietnamese ablation report (docs/ABLATION_A.md)."""
    from bot.i18n import fmt
    d3 = lambda x: fmt.dec(x, 3)  # noqa: E731
    L = ["# Thử bỏ từng phần, lớp chu kỳ (lớp A)", "",
         "Chỉ chọn bằng giai đoạn huấn luyện: khung 2 năm trượt mỗi 4 tuần, từ 07/2013 (khi đủ 104 tuần phân vị cho mọi chỉ số trừ Giá/MA 200 tuần) "
         "đến 12/2019. Giai đoạn kiểm định 2020–2022 chỉ để xem sau, không dùng để chọn. Quy tắc chọn: ưu tiên kịch bản xấu (P10) khi trung vị chênh "
         "không quá 0,01. Loại chiến lược trùng hệt mua đều (mọi khung bằng 1,000). Mỗi lần đánh giá là một lần thử trong `experiments/registry.csv`.", "",
         "Mô hình 1 = trung bình \"độ rẻ\" (phân vị 208 tuần đã đổi chiều) của các chỉ số. Ba bảng hệ số được thử:", ""]
    for tk, table in TABLES.items():
        L.append(f"- **{tk}**: " + "; ".join(f"từ {fmt.dec(a, 2)} → {fmt.dec(m, 2)}" for a, m in table))
    for tk, x in r["tables"].items():
        L += ["", f"## Bảng {tk}", "", "| Chỉ số riêng | Huấn luyện: trung vị | Huấn luyện: P10 | Kiểm định: tỷ số | Kiểm định: trung vị | Kiểm định: P10 |",
              "|---|---|---|---|---|---|"]
        for c, row in x["singles"].items():
            v = row["res"]["splits"].get("Kiểm định", {})
            L.append(f"| {c} | {d3(row['train']['er_median'])} | {d3(row['train']['er_p10'])} | {d3(v.get('equity_ratio'))} | {d3(v.get('roll_er_median'))} | {d3(v.get('roll_er_p10'))} |")
        L.append("")
        for k, s in enumerate(x["steps"]):
            L.append(f"{k + 1}. " + (f"Dừng: thêm {s['candidate']} không cải thiện trên giai đoạn huấn luyện." if s.get("stop") else
                                     f"Thêm {s['add']}: huấn luyện trung vị {d3(s['train']['er_median'])}, P10 {d3(s['train']['er_p10'])}."))
        b = x["best"]
        v = b["res"]["splits"].get("Kiểm định", {})
        L.append(f"\nBộ của bảng {tk}: **{' + '.join(x['chosen'])}**. Kiểm định: tỷ số {d3(v.get('equity_ratio'))}, trung vị {d3(v.get('roll_er_median'))}, "
                 f"P10 {d3(v.get('roll_er_p10'))}. Chu kỳ halving: " + ", ".join(f"{n} {d3(c['equity_ratio'])}" for n, c in b["res"]["cycles"].items()) + ".")
    rr = r["ridge"]
    v = rr["res"]["splits"].get("Kiểm định", {})
    signs = ", ".join(f"{n} {fmt.dec(s, 2)}" for n, s in rr["info"]["signs"].items() if s is not None)
    L += ["", "## Mô hình 2 và 3", "",
          f"- Mô hình 2 (ridge ràng buộc dấu, đi tới, học lại mỗi 13 tuần, cắt bỏ nhãn chồng): dấu trung bình của hệ số tự do qua các lần học: {signs}. "
          f"Chỉ số đổi dấu hoặc ngược chiều kinh tế bị bỏ, còn lại: {', '.join(rr['info']['kept']) or 'không chỉ số nào'}. "
          f"Kết quả: huấn luyện trung vị {d3(rr['train'].get('er_median'))}, kiểm định {d3(v.get('equity_ratio'))}. Không hơn mô hình 1."]
    if gbm:
        L.append(f"- Mô hình 3 (boosting đơn điệu, sklearn, cài đặt cố định): huấn luyện trung vị {d3(gbm['train']['er_median'])}, P10 {d3(gbm['train']['er_p10'])}, "
                 f"kiểm định {d3(gbm['val'])}. Không hơn mô hình 1, nên không dùng.")
    f = r["final"]
    v, tr = f["res"]["splits"].get("Kiểm định", {}), f["res"]["splits"].get("Huấn luyện", {})
    L += ["", "## Kết luận lớp A", "",
          f"Theo quy tắc chọn định trước, bảng **{r['table']}** với **{' + '.join(r['chosen'])}** thắng trên giai đoạn huấn luyện "
          f"(trung vị {d3(f['train']['er_median'])}, P10 {d3(f['train']['er_p10'])}). Kiểm định: tỷ số {d3(v.get('equity_ratio'))}, "
          f"trung vị {d3(v.get('roll_er_median'))}, P10 {d3(v.get('roll_er_p10'))}, tiền mặt chờ TB {fmt.pct(v.get('idle_avg'))}.", "",
          "Đọc kết quả: không chỉ số chu kỳ nào, dùng riêng hay kết hợp, thắng mua đều một cách vững trên giai đoạn huấn luyện. Bảng mặc định T0 kém rõ "
          "(trung vị 0,92–0,97) vì hệ số trung bình dưới 1 làm tiền nằm chờ khi giá đi lên. Mua gấp đôi lúc rẻ chỉ làm được khi đã để dành từ trước. "
          "Bảng T1 và T2 gần như trung tính nên kết quả sát 1,000. Bộ T2 (Puell + Hash Ribbon) có kiểm định đẹp hơn (1,006), nhưng chọn nó sau khi "
          "đã xem kiểm định là thiên lệch chọn lựa, nên không đổi.", ""]
    if bench:
        a = bench["strategies"]["auto"]["splits"]["Kiểm định"]
        L.append(f"So với bot hiện tại (Tự động) ở kiểm định: tỷ số {d3(a['equity_ratio'])}, trung vị {d3(a['roll_er_median'])}, P10 {d3(a['roll_er_p10'])}.")
    return "\n".join(L) + "\n"
