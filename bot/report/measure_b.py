"""Part B: re-measure the current bot with the uniform method (data up to the day before the new holdout, 31/12/2023).

Zones from the current bot's weekly buy score (Phải mua ≥ 80, Cân nhắc mua 60–80, Không nên mua < 60) at the Sunday
close; entry and exit at the Monday close (config rebuild.execution). Win-rate tables per zone vs the baseline of the
same weeks, with stationary-bootstrap intervals of the difference and Wilson intervals over episodes; calibration of
the bot's probabilities; cost-basis advantage of the zones used as multipliers (1,5 / 1,25 / 0,5) against DCA.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.backtest import current_bot, measure, metrics
from bot.backtest.engine import SimConfig, simulate
from bot.config import DATA, ROOT, cfg
from bot.features import weekly_close as wc
from bot.i18n import fmt

ORDER = ["phai", "cannhac", "khong"]
NAMES = {"phai": "Phải mua", "cannhac": "Cân nhắc mua", "khong": "Không nên mua"}
MULT = {"phai": 1.5, "cannhac": 1.25, "khong": 0.5}
HNAME = {4: "1 tháng", 13: "3 tháng", 26: "6 tháng", 52: "1 năm"}


def rb() -> dict:
    return cfg()["rebuild"]


def sim_config() -> SimConfig:
    b, c, r = cfg()["budget"], cfg()["costs"], rb()
    return SimConfig(b["weekly_usd"], r["multiplier_min"], r["multiplier_max"], 1e9, c["fee"], c["slippage"], 0.0)


def zones_from(scores: pd.DataFrame, weeks: pd.DatetimeIndex) -> pd.Series:
    s = scores.set_index("date")["buy"].reindex(weeks)
    z = np.where(s.isna(), None, np.where(s >= 80, "phai", np.where(s >= 60, "cannhac", "khong")))
    return pd.Series(z, index=weeks, dtype=object)


def cost_basis(price: np.ndarray, mult: np.ndarray, n_boot: int, block: int, seed: int) -> dict:
    """Strategy vs DCA with identical weekly contributions and a cash reserve (no borrowing); leftover cash counted at
    the final price. Stationary-bootstrap 95% interval of the advantage."""
    c = sim_config()
    s, d = simulate(price, mult, c), simulate(price, None, c)
    er = float(metrics.equity_ratio(s, d)[0])
    rng = np.random.default_rng(seed)
    r = np.diff(np.log(price))
    idx = measure.stationary_indices(len(r), block, n_boot, rng)
    P = np.concatenate([np.full((n_boot, 1), price[0]), price[0] * np.exp(np.cumsum(r[idx], axis=1))], axis=1)
    M = np.concatenate([np.full((n_boot, 1), mult[0]), mult[1:][idx]], axis=1)
    ers = metrics.equity_ratio(simulate(P, M, c), simulate(P, None, c))
    lo, hi = float(np.quantile(ers - 1, 0.025)), float(np.quantile(ers - 1, 0.975))
    return {"weeks": len(price), "advantage": measure.cost_basis_with_cash(er), "advantage_deployed": float(metrics.cba(s, d)[0]),
            "ci": [lo, hi], "cash_end_share": float(s.cash[0, -1] / s.contributed[0, -1]), "avg_mult": float(np.mean(s.mult)),
            "verdict": measure.NO_EDGE if lo <= 0 <= hi else ("hon_moc" if lo > 0 else "kem_moc")}


def run(write: bool = True) -> dict:
    r = rb()
    end = pd.Timestamp(str(r["holdout_start"])) - pd.Timedelta(days=1)
    t = wc.load(end + pd.Timedelta(days=1))  # Monday 01/01/2024 is needed only as the exit price of the last week
    t = t[t.index <= end]
    price = t["exec_monday"].to_numpy(dtype=float)
    res = current_bot.export()
    out = {"eval_end": end.strftime("%Y-%m-%d"), "execution": r["execution"], "sets": {}}
    for key in ("pa3", "auto"):
        z = zones_from(current_bot.series(res, key), t.index)
        first = z.first_valid_index()
        zz, pp = z.loc[first:], price[t.index >= first]
        tab = measure.zone_table(zz, pp, r["horizons_weeks"], ORDER, n_boot=r["bootstrap_n"], seed=r["seed"], gap=r["episode_gap_weeks"])
        tab["monotone"] = measure.monotone(tab, ["phai", "cannhac", "__baseline__", "khong"])
        mult = np.array([MULT.get(v, 1.0) if v else 1.0 for v in zz])
        cb = cost_basis(pp, mult, r["bootstrap_n"], r["cost_block_weeks"], r["seed"])
        years = {}
        for y in sorted({d.year for d in zz.index}):
            m = zz.index.year == y
            if m.sum() >= 26:
                c = sim_config()
                s, d = simulate(pp[m], mult[m], c), simulate(pp[m], None, c)
                years[str(y)] = measure.cost_basis_with_cash(float(metrics.equity_ratio(s, d)[0]))
        out["sets"][key] = {"from": first.strftime("%Y-%m-%d"), "weeks": int(zz.notna().sum()), "table": tab, "cost_basis": cb, "years": years}
    # calibration of the bot's own probabilities (PA3, its label: Sunday close to Sunday close h weeks later)
    close = t["close"]
    cal = {}
    for wp in res["wp"]:
        h = wp["h"]
        df = pd.DataFrame(wp["preds"], columns=["date", "p", "p0"])
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"].isin(t.index)].set_index("date")
        fut = close.shift(-h).reindex(df.index)
        y = (fut / close.reindex(df.index) > 1).astype(float).where(fut.notna())
        cal[h] = measure.calibration(df["p"].to_numpy(), df["p0"].to_numpy(), y.to_numpy(), h, r["bootstrap_n"], r["seed"])
    out["calibration"] = cal
    if write:
        (DATA / "results" / "measure_b.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (ROOT / "docs" / "MEASURE_B.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    return out


VERDICT = {"chua_co_loi_the": "chưa có lợi thế", "hon_moc": "hơn mốc", "kem_moc": "**kém mốc**", "it_dot": "ít đợt (< 3), chưa kết luận"}


def markdown(o: dict) -> str:
    pp = lambda x, d=0: fmt.pct(x, d)  # noqa: E731
    sp = lambda x, d=0: fmt.pct(x, d, sign=True)  # noqa: E731
    L = ["# Phần B: đo lại bot hiện tại bằng thước đo thống nhất", "",
         f"Dữ liệu đến **{fmt.date(o['eval_end'])}** (holdout từ 01/01/2024 vẫn khóa). Tín hiệu ở giá đóng Chủ nhật; mua và chấm ở **giá đóng thứ Hai**. "
         "Mốc so sánh luôn là **mọi tuần trong cùng giai đoạn** của chính bảng đó. Khoảng tin cậy 95%: bootstrap khối dừng, độ dài khối trung bình bằng kỳ hạn, "
         "2.000 lần, tính cho **mức chênh so với mốc**. Đối chiếu: Wilson theo đợt (mỗi đợt một quan sát, lấy tuần đầu). "
         "Đợt = các tuần cùng khung, cách nhau ≤ 4 tuần gộp một đợt. Khoảng tin cậy của mức chênh chứa 0 → \"chưa có lợi thế\"; dưới 3 đợt → "
         "\"ít đợt, chưa kết luận\" (bootstrap theo tuần không đo được bất định khi chỉ có 1–2 đợt).", ""]
    for key, label in (("pa3", "PA3 cố định (Pi + MVRV + Fear & Greed, bộ bot đang dùng)"), ("auto", "Chế độ Tự động (chọn lại phương án mỗi 4 tuần)")):
        s = o["sets"][key]
        tab = s["table"]
        L += [f"## {label}", "", f"Từ {fmt.date(s['from'])}, {s['weeks']} tuần có điểm.", ""]
        for h in tab["horizons"]:
            b = tab["baseline"][h]
            L += [f"### Giữ {HNAME[h]} (mốc: {pp(b['win'])} thắng, {b['weeks']} tuần; lãi trung vị {sp(b['median'])})", "",
                  "| Khung | Số tuần | Số đợt | Thắng | Chênh so với mốc | Khoảng tin cậy của mức chênh | Wilson theo đợt | Lãi trung vị (tứ phân vị) | Sụt giảm trung vị trong kỳ | Kết luận |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
            for z in ORDER:
                c = tab["zones"][z][h]
                if not c.get("weeks"):
                    L.append(f"| {NAMES[z]} | 0 | 0 | — | — | — | — | — | — | không có tín hiệu |")
                    continue
                ci = c["ci"]
                L.append(f"| {NAMES[z]} | {c['weeks']} | {c['episodes']} | {pp(c['win'])} | {sp(c['diff'])} | "
                         f"{(sp(ci[0]) + ' đến ' + sp(ci[1])) if ci[0] is not None else '—'} | {pp(c['wilson_episodes'][0])}–{pp(c['wilson_episodes'][1])} ({c['episodes']} đợt) | "
                         f"{sp(c['median'])} ({sp(c['q1'])} đến {sp(c['q3'])}) | {sp(c['mdd_median'])} | {VERDICT[c['verdict']]} |")
            L.append(f"\nCác khung có xếp đúng thứ tự (Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua)? **{'có' if tab['monotone'][h] else 'không'}**.\n")
        cb = s["cost_basis"]
        L += [f"**Lợi thế giá vốn khi dùng khung làm hệ số** (Phải mua × 1,5; Cân nhắc mua × 1,25; Không nên mua × 0,5), cùng tiền nạp mỗi tuần, có quỹ dự trữ, không vay, "
              f"tiền dư cuối kỳ tính theo giá cuối: **{sp(cb['advantage'], 1)}** (khoảng tin cậy {sp(cb['ci'][0], 1)} đến {sp(cb['ci'][1], 1)}, {cb['weeks']} tuần) → "
              f"{VERDICT[cb['verdict']]}. Chỉ tính phần đã giải ngân: {sp(cb['advantage_deployed'], 1)}; tiền dư cuối kỳ {pp(cb['cash_end_share'], 1)} tổng nạp.",
              "Theo từng năm: " + ", ".join(f"{y}: {sp(v, 1)}" for y, v in s["years"].items()) + ".", ""]
    L += ["## Xác suất của mô hình hiện tại có đáng tin không (PA3)", "",
          "Brier score: càng thấp càng tốt. Mốc là tỷ lệ thắng nền trong cửa sổ huấn luyện tại từng thời điểm. Chỉ hiển thị xác suất khi khoảng tin cậy của "
          "(Brier mốc − Brier mô hình) nằm hẳn trên 0; nếu không, chỉ hiển thị thứ hạng.", "",
          "| Kỳ hạn | Số tuần | Brier mô hình | Brier mốc | Điểm kỹ năng | Khoảng tin cậy của mức cải thiện | Hiển thị xác suất? |", "|---|---|---|---|---|---|---|"]
    for h, c in o["calibration"].items():
        h = int(h)
        L.append(f"| {HNAME[h]} | {c['weeks']} | {fmt.dec(c['brier'], 3)} | {fmt.dec(c['brier_base'], 3)} | {fmt.dec(c['skill'], 3)} | "
                 f"{fmt.dec(c['gain_ci'][0], 3)} đến {fmt.dec(c['gain_ci'][1], 3)} | {'có' if c['show_probability'] else '**không, chỉ thứ hạng**'} |")
    L += ["", "Biểu đồ độ tin cậy (dạng bảng) của mô hình 6 tháng, theo nhóm thập phân vị của xác suất dự báo:", "",
          "| Nhóm | Xác suất dự báo TB | Tỷ lệ thắng thực tế | Số tuần |", "|---|---|---|---|"]
    for b in o["calibration"]["26"]["reliability"] if "26" in o["calibration"] else o["calibration"][26]["reliability"]:
        L.append(f"| {b['decile']} | {pp(b['pred'])} | {pp(b['actual'])} | {b['weeks']} |")
    return "\n".join(L) + "\n"
