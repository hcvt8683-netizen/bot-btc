"""Part F runner: dynamic price scenarios at the last Sunday before the holdout. Writes data/results/part_f.json and
docs/SCENARIO_F.md (Vietnamese)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.config import DATA, ROOT
from bot.data import pit_store as ps
from bot.i18n import fmt
from bot.models import part_c, scenarios as sc, sell_system as ss, wf_logit as wf, zones as zn

LEVEL_VI = {"giu": "Giữ", "chot": "Chốt lời một phần", "ban": "Bán phần lớn"}
ZONE_VI = {"phai": "Phải mua", "cannhac": "Cân nhắc mua", "khong": "Không nên mua", None: "—"}
RULES = {"200w": "cheap_p_200wma", "mvrv": "cheap_mvrv"}
FNG_CASES, RC_CASES = ("lo", "mid", "hi"), ("lo", "0", "hi")


def inputs(end: pd.Timestamp) -> dict:
    cut = lambda df: df[df["date"] <= end].reset_index(drop=True) if len(df) else None  # noqa: E731
    return {"cm": cut(ps.load_history("coinmetrics")), "ext": cut(ps.load_history("coinmetrics_ext")), "fng": cut(ps.load_history("fng")),
            "fed": cut(ps.load_history("fred_DFEDTARU"))}


def groups_of(row: pd.Series, se: dict) -> int:
    return sum(int(any(row.get("pct_" + f, np.nan) >= se["threshold_pct"] for f in feats)) for feats in se["groups"].values())


def zone_after(ranks: pd.Series, x: float | None, zc: dict) -> str | None:
    """Zone of a scenario rank, stepping the hysteresis on from the zone of the last real week."""
    if x is None:
        return None
    s = pd.concat([ranks, pd.Series([x], index=[ranks.index[-1] + pd.Timedelta(weeks=1)])])
    return zn.hysteresis_zones(s, zc["thresholds"], zc["hysteresis"]).iloc[-1]


def read(row: pd.Series, t: pd.DataFrame, se: dict) -> dict:
    g = groups_of(row, se)
    out = {"groups": g, "level": ss.level_of(g, se["levels"]), "fng": float(row["raw_fng"]) if np.isfinite(row["raw_fng"]) else None,
           "on": [f for feats in se["groups"].values() for f in feats if row.get("pct_" + f, np.nan) >= se["threshold_pct"]],
           "mvrv": float(row["raw_mvrv"]), "price": float(row["close"])}
    for name, col in RULES.items():
        out["rank_" + name] = sc.rank_among(t[col], float(row[col]))
    return out


def run(write: bool = True) -> dict:
    sp = part_c.spec()
    cfg, se, zc, md = sp["scenarios"], sp["sell"], sp["zones"], sp["model"]
    eval_end = pd.Timestamp(str(md["eval_end"]))
    t = part_c.table(eval_end)
    asof = t.index[-1]
    inp = inputs(eval_end)
    band, rcb, chk = tuple(cfg["band"]), cfg["rc_band"], cfg["fng_check"]
    ranks = {n: (wf.oos_rank(t[c].dropna(), md["rank_min_weeks"]) * 100).dropna() for n, c in RULES.items()}
    g0 = groups_of(t.loc[asof], se)
    now = {"price": float(t["close"].iloc[-1]), "fng": float(t["raw_fng"].iloc[-1]), "mvrv": float(t["raw_mvrv"].iloc[-1]),
           "groups": g0, "level": ss.level_of(g0, se["levels"]),
           **{f"rank_{n}": float(r.iloc[-1]) for n, r in ranks.items()},
           **{f"zone_{n}": zn.hysteresis_zones(r, zc["thresholds"], zc["hysteresis"]).iloc[-1] for n, r in ranks.items()}}
    out = {"asof": asof.strftime("%Y-%m-%d"), "now": now, "models": {}, "checks": {}, "rc": {}, "rows": []}
    f_now = now["fng"]
    for k in cfg["weeks"]:
        m = sc.fng_response(t, k, asof, band)
        out["models"][k] = m
        out["checks"][k] = {kk: v for kk, v in sc.fng_check(t, k, pd.Timestamp(str(chk["fit_until"])),
                                                            tuple(pd.Timestamp(str(x)) for x in chk["test"]), band).items() if kk != "model"}
        rc = sc.rc_drift(inp["cm"], k, asof, rcb["window_weeks"], tuple(rcb["band"]))
        out["rc"][k] = rc
        rc_val = {"lo": rc["q"][0], "0": 0.0, "hi": rc["q"][1]}
        for d in cfg["price_changes"]:
            lo, mid, hi = sc.fng_predict(m, f_now, float(np.log(1 + d)))
            fe = {"lo": lo, "mid": mid, "hi": hi}
            grid = {f"{a}_{b}": read(sc.scenario_row(inp, asof, d, k, fng_end=fe[a], rc_change=rc_val[b]), t, se) for a in FNG_CASES for b in RC_CASES}
            res = {"k": k, "delta": d, "fng": [lo, mid, hi], "mid": grid["mid_0"],
                   "fixed": read(sc.scenario_row(inp, asof, d, k, fng_end=f_now), t, se)}
            for n in RULES:
                vals = [v["rank_" + n] for v in grid.values() if v["rank_" + n] is not None]
                res["range_" + n] = [min(vals), max(vals)] if vals else None
                res["zones_" + n] = sorted({zone_after(ranks[n], v["rank_" + n], zc) for v in grid.values()}, key=lambda z: zn.ORDER.index(z) if z else 9)
            gs = [v["groups"] for v in grid.values()]
            res["groups_range"] = [min(gs), max(gs)]
            res["levels"] = [lv for lv in ("giu", "chot", "ban") if any(v["level"] == lv for v in grid.values())]
            out["rows"].append(res)
    if write:
        (DATA / "results" / "part_f.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (ROOT / "docs" / "SCENARIO_F.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    return out


def markdown(o: dict) -> str:
    cfg = part_c.spec()["scenarios"]
    n0 = o["now"]
    num = lambda x, d=0: "—" if x is None else fmt.num(x, d)  # noqa: E731
    rng = lambda r: "—" if r is None else (num(r[0]) if round(r[0]) == round(r[1]) else f"{num(r[0])}–{num(r[1])}")  # noqa: E731
    zones = lambda zs: " / ".join(ZONE_VI[z] for z in zs)  # noqa: E731
    L = ["# Phần F: kịch bản giá động", "",
         f"Ngày phân tích: **{fmt.date(o['asof'])}**, Chủ nhật cuối trước holdout (Phần D, E dừng ở 24/12/2023 vì cần giá thứ Hai để chấm; kịch bản chỉ cần giá Chủ nhật). "
         f"Giá đóng {fmt.usd(n0['price'])}, Fear & Greed {num(n0['fng'])}, MVRV {fmt.dec(n0['mvrv'], 2)}.", "",
         f"- Quy tắc Giá/MA 200 tuần: thứ hạng {num(n0['rank_200w'])} → {ZONE_VI[n0['zone_200w']]}. Quy tắc MVRV: thứ hạng {num(n0['rank_mvrv'])} → {ZONE_VI[n0['zone_mvrv']]}. "
         f"Bên bán: {n0['groups']} nhóm → {LEVEL_VI[n0['level']]}.",
         f"- Đăng ký trước: `config/candidates.yaml` mục `scenarios` (commit `f44bab8`). Giá đi tới mức giả định sau k tuần theo đường đều trên thang log.",
         f"- {cfg['direct'][0].upper() + cfg['direct'][1:]}.",
         f"- Giữ nguyên ở trường hợp giữa: {cfg['hold_fixed']}.",
         "- Fear & Greed **không còn bị giữ nguyên**: dự báo theo mô hình phản ứng học chỉ từ dữ liệu đến ngày phân tích, kèm khoảng 10–90%.",
         "- Khoảng dao động của quy tắc MVRV và nhóm định giá bên bán còn tính theo thay đổi vốn hóa thực trong k tuần (10–90% của 4 năm trước; thêm sau lần chạy đầu, "
         "ghi trong nhật ký).",
         "- Thứ hạng là vị trí của điểm tuần đó trong các tuần trước, **không phải xác suất có lãi**. Khung dùng vùng trễ 5 điểm tính tiếp từ khung hiện tại.", "",
         "## 1. Fear & Greed phản ứng với giá thế nào", "",
         "Mô hình: thay đổi F&G sau k tuần = a + b × lợi suất log k tuần + c × (F&G hiện tại − 50).", "",
         "| Kỳ | Số tuần học | b (theo giá) | c (kéo về 50) | R² | Khoảng 10–90% phần dư | Kiểm ngoài mẫu 2022–2023 (học đến 2021): độ phủ khoảng | Sai số TB: mô hình / giữ nguyên F&G |",
         "|---|---|---|---|---|---|---|---|"]
    for k, m in o["models"].items():
        c = o["checks"][k]
        L.append(f"| {k} tuần | {m['n']} | {fmt.dec(m['b'], 1)} | {fmt.dec(m['c'], 2)} | {fmt.dec(m['r2'], 2)} | {fmt.dec(m['q'][0], 1)} đến {fmt.dec(m['q'][1], 1)} điểm | "
                 f"{fmt.pct(c.get('coverage'))} ({c.get('weeks', 0)} tuần) | {fmt.dec(c.get('mae_model'), 1)} / {fmt.dec(c.get('mae_constant'), 1)} điểm |")
    m4 = o["models"].get(4) or next(iter(o["models"].values()))
    L += ["", f"Đọc: kỳ 4 tuần, giá giảm 10% kéo F&G xuống khoảng {fmt.dec(-m4['b'] * np.log(0.9), 0)} điểm, cộng phần kéo về 50 "
          f"({fmt.dec(abs(m4['c']) * 100, 0)}% khoảng cách tới 50). Mô hình sai ít hơn hẳn cách giữ nguyên F&G.",
          "Độ phủ ngoài mẫu cao hơn mức 80% kỳ vọng: khoảng hơi rộng, tức thận trọng hơn cần thiết ở giai đoạn 2022–2023.", "",
          "Thay đổi vốn hóa thực trong k tuần (10–90%, 208 tuần trước ngày phân tích): "
          + "; ".join(f"{k} tuần: {fmt.pct(r['q'][0], 1, sign=True)} đến {fmt.pct(r['q'][1], 1, sign=True)}" for k, r in o["rc"].items()) + ".", ""]
    for k in cfg["weeks"]:
        L += [f"## Nếu giá đi tới mức này sau {k} tuần", "",
              "| Giá | So với hiện tại | F&G dự báo (10–90%) | Quy tắc Giá/MA 200 tuần: thứ hạng → khung | Quy tắc MVRV: thứ hạng (khoảng) → khung | "
              "Bên bán: số nhóm (khoảng) → mức | Cách cũ, giữ F&G: số nhóm |",
              "|---|---|---|---|---|---|---|"]
        for r in (x for x in o["rows"] if x["k"] == k):
            L.append(f"| {fmt.usd(r['mid']['price'])} | {fmt.pct(r['delta'], 0, sign=True) if r['delta'] else 'không đổi'} | {num(r['fng'][1])} ({num(r['fng'][0])}–{num(r['fng'][2])}) | "
                     f"{rng(r['range_200w'])} → {zones(r['zones_200w'])} | {num(r['mid']['rank_mvrv'])} ({rng(r['range_mvrv'])}) → {zones(r['zones_mvrv'])} | "
                     f"{r['mid']['groups']} ({rng(r['groups_range'])}) → {' / '.join(LEVEL_VI[x] for x in r['levels'])} | {r['fixed']['groups']} |")
        L.append("")
    four = [r for r in o["rows"] if r["k"] == cfg["weeks"][-1]]

    def first_buy(n):
        r = next((r for r in sorted(four, key=lambda x: -x["delta"]) if set(r["zones_" + n]) & {"phai", "cannhac"}), None)
        return f"giá giảm {fmt.pct(-r['delta'], 0)} (vào {zones(r['zones_' + n])})" if r else "không mức nào trong lưới"
    first_sell = next((r for r in sorted(four, key=lambda x: x["delta"]) if r["groups_range"][1] >= 1), None)
    diff = [r for r in o["rows"] if r["fixed"]["groups"] != r["mid"]["groups"]]
    L += ["## Kết luận Phần F", "",
          f"- Sau {cfg['weeks'][-1]} tuần, mức giá đầu tiên (đi từ trên xuống) làm quy tắc chạm khung mua: Giá/MA 200 tuần ở {first_buy('200w')}; "
          f"MVRV ở {first_buy('mvrv')}. Giá đi ngang hoặc tăng: cả hai ở Không nên mua.",
          (f"- Bên bán bắt đầu có nhóm bật (Chốt lời một phần) khi giá tăng từ {fmt.pct(first_sell['delta'], 0)} (tính cả khoảng); "
           f"tiêu chí bật ở trường hợp giữa: {', '.join(first_sell['mid']['on']) or '—'}." if first_sell
           else "- Bên bán không bật nhóm nào trong lưới giá."),
          f"- So với cách cũ (giữ nguyên F&G): số nhóm bên bán ở trường hợp giữa khác ở {len(diff)}/{len(o['rows'])} kịch bản"
          + (": " + "; ".join(f"{r['k']} tuần {fmt.pct(r['delta'], 0, sign=True)}: {r['fixed']['groups']} → {r['mid']['groups']} nhóm" for r in diff) + "." if diff else "."),
          "- Kiểm tra tự động: cho kịch bản đi đúng đường giá thật thì mọi chỉ số trùng bảng thật; kịch bản không đọc dữ liệu sau ngày phân tích.",
          "- Kịch bản chỉ mô tả bot **sẽ đọc thế nào** nếu giá đi tới mức đó, không dự báo giá. Theo Phần C–D, hệ số giải ngân vẫn là 1,0 (mua đều) ở mọi mức giá.",
          "- Giới hạn: nguồn cung và số BTC phát hành giữ nguyên, nên kịch bản vắt qua kỳ giảm một nửa phần thưởng (dự kiến 04/2024) sẽ sai Puell; khoảng F&G "
          "dựa trên dữ liệu từ 02/2018 (khoảng 300 tuần); khoảng vốn hóa thực không phụ thuộc hướng giá (4 năm trước có đợt tăng mạnh 2020–2021), "
          "nên phía trên của khoảng MVRV khi giá giảm có thể rộng quá.", ""]
    return "\n".join(L)
