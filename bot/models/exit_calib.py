"""R1: is the touch chance of the selling-price tool (bot/models/exit_timing.py) calibrated year by year and in both market
states (close above / below its 200-day mean)? config/candidates.yaml section exit_calib, registered before computing.
Uses exit_timing's own functions and changes nothing in it; writes docs/R1_GIA_CHO_BAN.md only."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.backtest.metrics import wilson
from bot.config import CONFIG, ROOT, load_yaml
from bot.models import exit_timing as xt

DOC = ROOT / "docs" / "R1_GIA_CHO_BAN.md"


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["exit_calib"]


def daily_calls(d: pd.DataFrame, k: int, xs: list[float], cfg_x: dict, start: pd.Timestamp) -> pd.DataFrame:
    """Every anchor day from `start` whose outcome is known: what the tool said for each premium, and whether it touched."""
    sig = xt.sigma(d["close"], cfg_x)
    m = xt.next_max(d["high"], k)
    q = xt.z_quantiles(d, k, cfg_x)
    ok = (d.index >= start) & m.notna().to_numpy() & q.notna().all(axis=1).to_numpy() & sig.notna().to_numpy()
    sk = (sig * np.sqrt(k))[ok].to_numpy()
    zr = np.log(m[ok] / d["close"][ok]).to_numpy()
    Q = q[ok].to_numpy()
    ma = d["close"].rolling(200, min_periods=200).mean()
    out = pd.DataFrame({"year": d.index[ok].year, "above": (d["close"] > ma)[ok].to_numpy()}, index=d.index[ok])
    for x in xs:
        out[f"pred_{x}"] = xt.touch_up(np.log(1 + x) / sk, Q)
        out[f"hit_{x}"] = (zr >= np.log(1 + x)).astype(float)
    return out


def cell(g: pd.DataFrame, x: float, k: int) -> dict:
    n = len(g)
    if not n:
        return {"n": 0}
    pred, hit = float(g[f"pred_{x}"].mean()), float(g[f"hit_{x}"].mean())
    eff = max(1, round(n / k))
    lo, hi = wilson(round(hit * eff), eff)
    return {"n": n, "n_eff": eff, "pred": pred, "actual": hit, "gap": hit - pred, "ci": [lo, hi],
            "side": "above" if lo > pred else "below" if hi < pred else "inside"}


def run(write: bool = True) -> dict:
    cfg, cx = spec(), xt.spec()
    d = xt.candles()
    start = pd.Timestamp(str(cx["check_from"]))
    out = {"horizons": {}}
    for k in cfg["horizons_days"]:
        calls = daily_calls(d, int(k), [float(x) for x in cfg["premiums"]], cx, start)
        mid = calls.index[len(calls) // 2]
        res = {"from": calls.index[0].strftime("%Y-%m-%d"), "to": calls.index[-1].strftime("%Y-%m-%d"), "split": mid.strftime("%Y-%m-%d"), "premiums": {}}
        for x in cfg["premiums"]:
            x = float(x)
            halves = [cell(calls[calls.index < mid], x, int(k)), cell(calls[calls.index >= mid], x, int(k))]
            systematic = halves[0].get("side") == halves[1].get("side") and halves[0].get("side") in ("above", "below")
            res["premiums"][x] = {"all": cell(calls, x, int(k)), "halves": halves, "systematic": halves[0]["side"] if systematic else None,
                                  "years": {int(y): cell(g, x, int(k)) for y, g in calls.groupby("year")},
                                  "state": {s: cell(calls[calls["above"] == (s == "tren")], x, int(k)) for s in ("tren", "duoi")}}
        out["horizons"][int(k)] = res
    out["systematic"] = [(k, x, v["systematic"]) for k, r in out["horizons"].items() for x, v in r["premiums"].items() if v["systematic"]]
    if write:
        DOC.write_text(markdown(out), encoding="utf-8")
    return out


def _p(x) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def _s(x) -> str:
    return "—" if x is None else ("+" if x > 0 else "−" if x < 0 else "") + f"{abs(x) * 100:.0f} điểm"


def markdown(o: dict) -> str:
    L = ["# R1: khả năng chạm giá chờ bán có đúng tỷ lệ không? (03/11/2026)", "",
         "Sinh bằng `python -m bot.cli exit-calib` (mục `exit_calib` của `config/candidates.yaml`, đăng ký trước). Dùng đúng hàm của "
         "`bot/models/exit_timing.py`, không sửa gì trong đó. Mỗi ngày gốc từ 01/01/2016: bot nói khả năng giá cao nhất k ngày tới chạm "
         "giá đóng × (1 + x) là bao nhiêu, và thực tế có chạm không. Khoảng tin cậy Wilson theo số lần độc lập (số ngày / k).", ""]
    sysl = o["systematic"]
    L += ["## Kết luận", ""]
    if sysl:
        L.append("**Lệch có hệ thống** (cả hai nửa giai đoạn, khoảng tin cậy nằm hẳn một phía) ở: " +
                 "; ".join(f"+{x * 100:.0f}% trong {k} ngày ({'thực tế chạm nhiều hơn bot nói' if s == 'above' else 'thực tế chạm ít hơn bot nói'})" for k, x, s in sysl) + ".")
        L.append("")
        L.append("Theo đăng ký: chỉ báo cáo, đề xuất cách sửa ở cuối và chờ người dùng duyệt; chưa đổi phương pháp.")
    else:
        L.append("**Không ô nào lệch có hệ thống** ở cả hai nửa giai đoạn: phần lệch thấy trong hồi cứu 24 thời điểm nằm trong dao động ngẫu nhiên "
                 "hoặc chỉ ở một giai đoạn. Không đề xuất đổi phương pháp.")
    L.append("")
    for k, r in o["horizons"].items():
        L += [f"## Kỳ hạn {k} ngày ({r['from']} → {r['to']}, chia đôi ở {r['split']})", "",
              "| Mức | Bot nói | Thực tế | Khoảng tin cậy | Nửa đầu (nói / thật) | Nửa sau (nói / thật) | Trên MA 200 (nói / thật) | Dưới MA 200 (nói / thật) |",
              "|---|---|---|---|---|---|---|---|"]
        for x, v in r["premiums"].items():
            a, h1, h2, up, dn = v["all"], v["halves"][0], v["halves"][1], v["state"]["tren"], v["state"]["duoi"]
            L.append(f"| +{x * 100:.0f}% | {_p(a['pred'])} | {_p(a['actual'])} | {_p(a['ci'][0])}–{_p(a['ci'][1])} | {_p(h1['pred'])} / {_p(h1['actual'])} | "
                     f"{_p(h2['pred'])} / {_p(h2['actual'])} | {_p(up.get('pred'))} / {_p(up.get('actual'))} | {_p(dn.get('pred'))} / {_p(dn.get('actual'))} |")
        L += ["", f"Theo năm, mức +3% (bot nói / thực tế, chênh lệch, số lần độc lập):", "", "| Năm | Bot nói | Thực tế | Chênh | Lần độc lập |", "|---|---|---|---|---|"]
        for y, c in r["premiums"][0.03]["years"].items():
            L.append(f"| {y} | {_p(c['pred'])} | {_p(c['actual'])} | {_s(c['gap'])} | {c['n_eff']} |")
        L.append("")
    L += ["## Đọc thế nào", "",
          "- \"Bot nói\" là trung bình khả năng bot đưa ra ở các ngày trong nhóm; \"thực tế\" là tỷ lệ ngày giá thật sự chạm mức đó.",
          "- Một năm lệch không có nghĩa là phương pháp sai: mỗi năm chỉ có khoảng 50 lần độc lập ở 7 ngày và 12 lần ở 30 ngày.",
          "- Năm tăng mạnh thường chạm mức bán nhiều hơn bot nói (bot không đoán hướng); năm giảm thì ngược lại.", ""]
    if sysl:
        L += ["## Đề xuất (chờ duyệt)", "",
              "1. Đăng ký trước một phiên bản mới của mục `exit` có điều chỉnh theo trạng thái MA 200 ngày (phân phối lấy riêng cho ngày trên / dưới MA), "
              "chấm đi tới bằng Brier so với bản hiện tại, chỉ đổi nếu tốt hơn ở cả hai nửa.",
              "2. Trong lúc chờ, trang ghi chú ở thẻ Giá & ngày bán rằng khả năng chạm đang thận trọng ở các mức đã lệch.", ""]
    L.append("Công cụ tham khảo, không phải lời khuyên đầu tư.")
    return "\n".join(L) + "\n"
