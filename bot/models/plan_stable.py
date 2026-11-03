"""How often the Giải ngân / Chốt lời dần cards changed their advice, week by week (config/candidates.yaml,
plan.stable.report and sell_plan.stable; registered 04/11/2026 before any number was computed).

For every weekly close since 2022-01-02 the plan tables are recomputed from the weeks up to that close only, as the
report run on the Tuesday after it (the Monday close of that week is the last price used). The old rule names the plan
with the highest 10th percentile among the plans not significantly worse; the new rule names the best plan only when
every other plan is significantly worse, and otherwise says the plans are a tie. Counted: weeks whose advice differs
from the week before, changes of the tie group, and reversals between at once and 52 weeks. Reporting only: the rule
does not change with the result.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.config import CONFIG, DATA, ROOT, cfg, load_yaml
from bot.models import deploy_plan as dp
from bot.models import sell_plan as sp

SINCE = "2022-01-02"   # plan.stable.report
ENDS = (1, 52)         # a reversal: the advice moves between these two plans
OUT = DATA / "results" / "plan_stable.json"
SIDES = {"plan": dp, "sell_plan": sp}


def weekly(t: pd.DataFrame, mod, sc: dict, fee: float, slip: float, n_boot: int, seed: int, data_from: pd.Timestamp, since: pd.Timestamp) -> list[dict]:
    """Advice of both rules at every weekly close from `since`, each computed from the weeks up to that close only."""
    rows = []
    for w in t.index[(t.index >= since) & np.isfinite(t["exec_monday"].to_numpy(dtype=float))]:
        r = mod.compute(t.loc[:w], sc, fee, slip, n_boot, seed, data_from)
        if r["options"]:
            rows.append({"week": w.strftime("%Y-%m-%d"), "old": dp.old_pick(r["options"]), "new": r["recommended"], "tied": r["tied"]})
    return rows


def count(rows: list[dict]) -> dict:
    pairs = list(zip(rows, rows[1:]))
    flip = lambda a, b: {a, b} == set(ENDS)  # noqa: E731
    return {"weeks": len(rows), "from": rows[0]["week"] if rows else None, "to": rows[-1]["week"] if rows else None,
            "old_changes": sum(a["old"] != b["old"] for a, b in pairs), "old_flips": sum(flip(a["old"], b["old"]) for a, b in pairs),
            "new_changes": sum(a["new"] != b["new"] for a, b in pairs), "new_flips": sum(flip(a["new"], b["new"]) for a, b in pairs),
            "tie_changes": sum(a["new"] is None and b["new"] is None and a["tied"] != b["tied"] for a, b in pairs),
            "tie_weeks": sum(r["new"] is None for r in rows)}


def segments(rows: list[dict]) -> list[dict]:
    """Consecutive weeks with the same advice under both rules."""
    out = []
    for r in rows:
        key = (r["old"], r["new"], tuple(r["tied"]))
        if out and out[-1]["key"] == key:
            out[-1]["to"] = r["week"]
        else:
            out.append({"key": key, "from": r["week"], "to": r["week"]})
    return [{"from": s["from"], "to": s["to"], "old": s["key"][0], "new": s["key"][1], "tied": list(s["key"][2])} for s in out]


def run(write: bool = True) -> dict:
    from bot.features import weekly_close as wc
    C = load_yaml(CONFIG / "candidates.yaml")
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    c = cfg()["costs"]
    t = wc.load(None)
    out = {"since": SINCE}
    for side, mod in SIDES.items():
        sc = C[side]
        rows = weekly(t, mod, sc, c["fee"], c["slippage"], rb["bootstrap_n"], rb["seed"], pd.Timestamp(str(sc["data_from"])), pd.Timestamp(SINCE))
        out[side] = {**count(rows), "segments": segments(rows), "rows": rows}
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        (ROOT / "docs" / "PLAN_ON_DINH.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    return out


def summary(side: str) -> dict | None:
    """Counts for the weekly report (KN.plan.stable / KN.sell_plan.stable); None before the first run."""
    if not OUT.exists():
        return None
    o = json.loads(OUT.read_text(encoding="utf-8")).get(side)
    return {k: v for k, v in o.items() if k not in ("segments", "rows")} if o else None


def markdown(o: dict) -> str:
    from bot.i18n import fmt
    nm = {"plan": lambda n: "một lần" if n == 1 else f"chia {n} tuần", "sell_plan": lambda n: "bán một lần" if n == 1 else f"chia {n} tuần"}
    title = {"plan": "Giải ngân", "sell_plan": "Chốt lời dần"}
    L = ["# Đề xuất Giải ngân / Chốt lời dần có ổn định không", "",
         "Đăng ký trước: `config/candidates.yaml` mục `plan.stable` và `sell_plan.stable` (commit `1f0756b`, 04/11/2026, trước khi tính số nào). "
         "Mã: `bot/models/plan_stable.py`, chạy lại bằng `python -m bot.cli plan-stable`.", "",
         f"- Mỗi tuần từ {fmt.date(o['since'])}: tính lại bảng so các cách chia chỉ với dữ liệu có đến tuần đó (như báo cáo chạy thứ Ba sau tuần đó).",
         "- Cách cũ (đến 03/11/2026): đề xuất cách có 10% xấu nhất ít thiệt nhất trong các cách không kém cách tốt nhất đáng kể.",
         "- Cách mới: chỉ đề xuất khi mọi cách khác đều kém cách tốt nhất đáng kể; nếu không, trang nói các cách gần như ngang nhau.",
         "- Chỉ để báo cáo: quy tắc không đổi theo kết quả này.", "",
         "| Thẻ | Số tuần | Cách cũ: số lần đổi đề xuất | Cách cũ: đảo hẳn (một lần ↔ 52 tuần) | Cách mới: số lần đổi lời | Cách mới: đảo hẳn | Nhóm ngang nhau đổi thành viên | Số tuần nói \"ngang nhau\" |",
         "|---|---|---|---|---|---|---|---|"]
    for side in SIDES:
        s = o[side]
        L.append(f"| {title[side]} | {s['weeks']} | {s['old_changes']} | {s['old_flips']} | {s['new_changes']} | {s['new_flips']} | {s['tie_changes']} | {s['tie_weeks']} |")
    for side in SIDES:
        n = nm[side]
        L += ["", f"## {title[side]}: lời của trang theo thời gian", "", "| Từ tuần | Đến tuần | Cách cũ nói | Cách mới nói |", "|---|---|---|---|"]
        for g in o[side]["segments"]:
            new = f"đề xuất {n(g['new'])}" if g["new"] is not None else "ngang nhau: " + ", ".join(n(x) for x in g["tied"])
            L.append(f"| {fmt.date(g['from'])} | {fmt.date(g['to'])} | đề xuất {n(g['old'])} | {new} |")
    L += ["", "Công cụ tham khảo, không phải lời khuyên đầu tư.", ""]
    return "\n".join(L)
