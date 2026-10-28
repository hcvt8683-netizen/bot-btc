"""Phase 2 benchmark: the current bot as a multiplier strategy vs plain DCA.

Development runs stop at the day before the holdout; `final=True` (CLI --final) includes it and is logged.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.backtest import baselines, current_bot, metrics
from bot.backtest.engine import SimConfig
from bot.config import cfg
from bot.features.panel import daily_cm, decision_dates, fill_prices
from bot.validation import splits

START = pd.Timestamp("2011-01-01")
STRATEGIES = {"auto": "Bot hiện tại (Tự động: phương án tốt nhất, chọn lại mỗi 4 tuần)", "pa3": "PA3 cố định (Pi + MVRV + F&G)",
              "pa1": "PA1 (Pi + MVRV)", "pa2": "PA2 (Pi + MVRV Z)", "pa4": "PA4 (Pi + Puell)", "pa5": "PA5 (F&G + MVRV + MA200)",
              "all": "Tất cả chỉ số"}


def grid(final: bool = False) -> tuple[pd.DatetimeIndex, np.ndarray]:
    end = splits.dev_end(final)
    daily = daily_cm(end)
    last = daily["date"].max()
    dates = decision_dates(START, last)
    return dates, fill_prices(daily, dates).to_numpy()


def periods(dates: pd.DatetimeIndex, final: bool) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    end = dates[-1]
    out = []
    for name, label in (("train", "Huấn luyện"), ("validation", "Kiểm định")) + ((("holdout", "Kiểm tra cuối"),) if final else ()):
        a, b = splits.split(name)
        out.append((label, a, min(b or end, end)))
    return out


def evaluate(dates: pd.DatetimeIndex, price: np.ndarray, mult: np.ndarray, final: bool = False, c: SimConfig | None = None) -> dict:
    """Per split: one simulation over the split + rolling windows; per halving cycle: one simulation."""
    v = cfg()["validation"]
    out: dict = {"splits": {}, "cycles": {}}
    for label, a, b in periods(dates, final):
        sel = (dates >= a) & (dates <= b)
        if sel.sum() < 8:
            continue
        full = metrics.summary(price[sel], mult[sel], c)
        roll = metrics.roll_summary(metrics.rolling(dates, price, mult, a, b, v["rolling_window_weeks"], v.get("rolling_step_weeks", 4), c))
        out["splits"][label] = {**full, **{"roll_" + k: x for k, x in roll.items()}}
    for name, a, b, complete in splits.cycles(dates[-1]):
        sel = (dates >= a) & (dates <= b)
        if sel.sum() >= 26:
            out["cycles"][name] = metrics.summary(price[sel], mult[sel], c) | {"complete": complete}
    return out


def current_bot_strategies(dates: pd.DatetimeIndex) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    res = current_bot.export()
    return {k: baselines.current_bot(current_bot.series(res, k), dates) for k in STRATEGIES}


def run(final: bool = False) -> dict:
    if final:
        splits.log_final_run({"command": "benchmark"})
    dates, price = grid(final)
    out = {"dates": (dates[0], dates[-1]), "strategies": {}}
    for k, (m, score) in current_bot_strategies(dates).items():
        r = evaluate(dates, price, m, final)
        r["active_from"] = dates[np.isfinite(score)][0] if np.isfinite(score).any() else None
        r["mult_share"] = {x: float(np.mean(m == x)) for x in (2.0, 1.25, 1.0, 0.25)}
        out["strategies"][k] = r
    return out


def table(res: dict) -> str:
    """Markdown summary (Vietnamese) of a benchmark run, used in PROGRESS/RESULTS."""
    from bot.i18n import fmt

    lines = ["| Chiến lược | Giai đoạn | Tỷ số tài sản so với mua đều | Trung vị khung 2 năm | Kịch bản xấu (10% tệ nhất) | Số khung | Lợi thế giá vốn | Tiền mặt chờ TB | Sụt giảm lớn nhất (bot / mua đều) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for k, v in res["strategies"].items():
        for s, x in v["splits"].items():
            lines.append(f"| {STRATEGIES.get(k, k)} | {s} | {fmt.dec(x['equity_ratio'], 3)} | {fmt.dec(x.get('roll_er_median'), 3)} | "
                         f"{fmt.dec(x.get('roll_er_p10'), 3)} | {x.get('roll_n', 0)} | {fmt.pct(x['cba'], 1, sign=True)} | {fmt.pct(x['idle_avg'])} | "
                         f"{fmt.pct(x['mdd'])} / {fmt.pct(x['mdd_dca'])} |")
    lines += ["", "| Chiến lược | " + " | ".join(n for n in next(iter(res["strategies"].values()))["cycles"]) + " |",
              "|---|" + "---|" * len(next(iter(res["strategies"].values()))["cycles"])]
    for k, v in res["strategies"].items():
        lines.append(f"| {STRATEGIES.get(k, k)} | " + " | ".join(fmt.dec(x["equity_ratio"], 3) + ("" if x["complete"] else " (chưa trọn)") for x in v["cycles"].values()) + " |")
    return "\n".join(lines)
