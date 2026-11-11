"""RSI 14 as a criterion for the Trend, Long/Short and Price action views (config/candidates.yaml, section rsi_check;
registered before any number was computed).

Wilder RSI 14 on Bitstamp daily closes (scored from 2016) and on hourly closes of the BTCUSDT perpetual (scored from
07/2020), textbook bands (< 20, 20–30, 70–80, > 80) with the direction they are said to announce. For each band and
horizon: how often the move went the announced way on independent occurrences (at least k candles apart), against the
same share on any candle of the period (one-sided binomial), halves, Holm over 4 × 16 + 4 × 12 = 112 tests. A separate
Holm-corrected family of 56 two-proportion tests checks the user's belief that a deeper band wins more often.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from scipy.stats import binom, norm

from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.models import candles as cd
from bot.models import perp_signal as ps

N_RSI = 14
MIN_N = 30
BANDS = {"qua_ban_sau": 1, "qua_ban": 1, "qua_mua": -1, "qua_mua_sau": -1}   # band -> announced direction
PAIRS = (("qua_ban_sau", "qua_ban"), ("qua_mua_sau", "qua_mua"))             # deep band vs shallow band, same side
HORIZONS = {"daily": [1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 30, 60, 90, 120, 150, 180],
            "hourly": [1, 2, 3, 4, 6, 8, 12, 24, 48, 72, 120, 168]}
FROM = {"daily": pd.Timestamp("2016-01-01"), "hourly": pd.Timestamp("2020-07-01")}


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["rsi_check"]


def version(cfg: dict) -> str:
    code = (ROOT / "bot" / "models" / "rsi_check.py").read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def rsi(values: np.ndarray, n: int = N_RSI) -> np.ndarray:
    """Wilder RSI on an array of closes without gaps: seed = plain mean of the first n changes, then a(t) = (a(t−1) × (n−1) + x(t)) / n."""
    v = np.asarray(values, dtype=float)
    out = np.full(len(v), np.nan)
    if len(v) <= n:
        return out
    ch = np.diff(v)
    up = np.where(ch > 0, ch, 0.0)
    dn = np.where(ch < 0, -ch, 0.0)
    au, ad = up[:n].mean(), dn[:n].mean()
    out[n] = 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)
    for i in range(n, len(ch)):
        au = (au * (n - 1) + up[i]) / n
        ad = (ad * (n - 1) + dn[i]) / n
        out[i + 1] = 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)
    return out


def band_of(x: float) -> str | None:
    if not np.isfinite(x):
        return None
    if x < 20:
        return "qua_ban_sau"
    if x < 30:
        return "qua_ban"
    if 70 < x <= 80:
        return "qua_mua"
    if x > 80:
        return "qua_mua_sau"
    return None


def closes(kind: str, end: pd.Timestamp | None = None) -> pd.Series:
    """Closes on the gap-free grid (daily Bitstamp / hourly perpetual); a missing candle stays NaN."""
    return cd.load(end)["close"] if kind == "daily" else ps.hourly({"start": "2020-01-01"}, end)["close"]


def rsi_series(c: pd.Series) -> pd.Series:
    """RSI on the grid: computed over the candles that exist (a change is vs the previous existing candle), NaN on gaps."""
    have = c.dropna()
    return pd.Series(rsi(have.to_numpy()), index=have.index).reindex(c.index)


def evaluate(c: pd.Series, kind: str, res: dict, pv: dict) -> None:
    """Every band and horizon of this candle kind: hits on independent occurrences against any candle, halves (like candles.evaluate)."""
    R = rsi_series(c)
    start = FROM[kind]
    in_band = {b: np.fromiter((band_of(x) == b for x in R.to_numpy()), dtype=bool, count=len(R)) for b in BANDS}
    for k in HORIZONS[kind]:
        r = (c.shift(-k) / c - 1).to_numpy()
        known = np.isfinite(r) & (c.index >= start)
        idx = np.flatnonzero(known)
        if not len(idx):
            continue
        half = idx[len(idx) // 2]
        base = {1: float((r[known] > 0).mean()), -1: float((r[known] < 0).mean())}
        base_h = [{s: float(((r[idx[idx < half]] * s) > 0).mean()) for s in (1, -1)},
                  {s: float(((r[idx[idx >= half]] * s) > 0).mean()) for s in (1, -1)}]
        for b, sgn in BANDS.items():
            pos = cd._spaced(np.flatnonzero(in_band[b] & known), k)
            hit = (r[pos] * sgn) > 0
            n, h = len(pos), int(hit.sum())
            p = float(binom.sf(h - 1, n, base[sgn])) if n else 1.0
            first, second = hit[pos < half], hit[pos >= half]
            res.setdefault(b, {"dir": sgn, "per_k": {}}).setdefault("per_k", {})[f"{kind}|{k}"] = {
                "n": n, "hits": h, "rate": h / n if n else None, "ci": list(wilson(h, n)) if n else [None, None], "base": base[sgn], "p": p,
                "halves": [float(first.mean()) if len(first) else None, base_h[0][sgn], float(second.mean()) if len(second) else None, base_h[1][sgn]]}
            pv[(b, kind, k)] = p


def two_prop(a: dict, b: dict) -> float | None:
    """Two-sided p of the pooled two-proportion z test on the independent-occurrence hit shares of two cells."""
    if not a["n"] or not b["n"]:
        return None
    p = (a["hits"] + b["hits"]) / (a["n"] + b["n"])
    se = np.sqrt(p * (1 - p) * (1 / a["n"] + 1 / b["n"]))
    if se == 0:
        return 1.0
    return float(2 * norm.sf(abs(a["rate"] - b["rate"]) / se))


def claim_tests(res: dict) -> list[dict]:
    """The registered check of 'a deeper band wins more often': deep vs shallow, same side, per kind × horizon, Holm over 56."""
    rows = []
    for kind in HORIZONS:
        for k in HORIZONS[kind]:
            for deep, shallow in PAIRS:
                a, b = res[deep]["per_k"][f"{kind}|{k}"], res[shallow]["per_k"][f"{kind}|{k}"]
                rows.append({"kind": kind, "k": k, "deep": deep, "shallow": shallow,
                             "rate_deep": a["rate"], "n_deep": a["n"], "rate_shallow": b["rate"], "n_shallow": b["n"],
                             "diff": (a["rate"] - b["rate"]) if a["n"] and b["n"] else None, "p": two_prop(a, b)})
    adj = cd.holm({i: r["p"] for i, r in enumerate(rows) if r["p"] is not None})
    for i, r in enumerate(rows):
        r["p_holm"] = adj.get(i)
        r["deeper_better"] = bool(r["p_holm"] is not None and r["p_holm"] < 0.05 and r["diff"] > 0
                                  and r["n_deep"] >= MIN_N and r["n_shallow"] >= MIN_N)
    return rows


def today(c: pd.Series) -> dict:
    R = rsi_series(c)
    T = c.dropna().index[-1]
    x = R.loc[T]
    return {"anchor": T.strftime("%Y-%m-%d %H:%M") if T.hour or T.minute else T.strftime("%Y-%m-%d"),
            "rsi": None if pd.isna(x) else float(x), "band": band_of(x), "close": float(c.loc[T])}


def report(out: dict) -> str:
    """docs/RSI_KIEM_TRA.md: the honest result in plain Vietnamese."""
    L = ["# RSI 14 so với một ngày (giờ) bất kỳ", "",
         f"Đăng ký trước trong `config/candidates.yaml` mục `rsi_check`; chạy `python -m bot.cli rsi`. Phiên bản {out['version']}.", "",
         f"- Số phép thử: {out['tests']} (dải × kỳ hạn, cả nến ngày và nến giờ), hiệu chỉnh Holm.",
         f"- Ô có lợi thế (p Holm < 0,05 và hơn tỷ lệ gốc ở cả hai nửa): **{len(out['edges'])}**.",
         f"- Ô ít dữ liệu (dưới {MIN_N} lần độc lập): {out['summary']['few']}.",
         f"- Niềm tin 'dải càng sâu thắng càng cao': {out['claim_summary']['deeper_better']}/{out['claim_summary']['n']} cặp sâu hơn nông"
         f" một cách chắc chắn sau Holm.", ""]
    for kind, name in (("daily", "Nến ngày Bitstamp (từ 2016)"), ("hourly", "Nến giờ vĩnh cửu (từ 07/2020)")):
        L += [f"## {name}", "", "| Dải | Kỳ hạn | Số lần | Đúng hướng | Tỷ lệ gốc | p Holm | Kết luận |", "|---|---|---|---|---|---|---|"]
        for b in BANDS:
            for k in HORIZONS[kind]:
                x = out["bands"][b]["per_k"][f"{kind}|{k}"]
                v = "có lợi thế" if x["edge"] else ("ít dữ liệu" if x["few"] else "không hơn")
                L.append(f"| {b} | {k} | {x['n']} | {x['rate']:.0%} |" if x["rate"] is not None else f"| {b} | {k} | {x['n']} | — |")
                L[-1] += f" {x['base']:.0%} | {x['holm']:.2f} | {v} |"
        L.append("")
    L += ["Kết quả không có lợi thế chỉ ghi ở đây; trang chỉ hiện giá trị RSI kèm ghi chú trung thực, không đổi kết luận.", ""]
    return "\n".join(L)


def run(write: bool = True, end: pd.Timestamp | None = None) -> dict:
    cfg = spec()
    res: dict = {}
    pv: dict = {}
    data = {kind: closes(kind, end) for kind in HORIZONS}
    for kind in HORIZONS:
        evaluate(data[kind], kind, res, pv)
    adj = cd.holm(pv)
    for (b, kind, k), a in adj.items():
        x = res[b]["per_k"][f"{kind}|{k}"]
        h = x["halves"]
        x["holm"] = a
        x["few"] = x["n"] < MIN_N
        x["edge"] = bool(not x["few"] and a < 0.05 and h[0] is not None and h[2] is not None and h[0] > h[1] and h[2] > h[3])
    claim = claim_tests(res)
    out = {"version": version(cfg), "tests": len(pv), "n_rsi": N_RSI,
           "horizons": HORIZONS, "from": {k: v.strftime("%Y-%m-%d") for k, v in FROM.items()},
           "to": {kind: data[kind].dropna().index[-1].strftime("%Y-%m-%d %H:%M") for kind in HORIZONS},
           "today": {kind: today(data[kind]) for kind in HORIZONS},
           "bands": res, "claim": claim,
           "claim_summary": {"n": len(claim), "deeper_better": sum(r["deeper_better"] for r in claim)},
           "edges": sorted(f"{b}|{key}" for b, x in res.items() for key, v in x["per_k"].items() if v.get("edge"))}
    out["summary"] = {"edge": len(out["edges"]), "few": sum(v["few"] for x in res.values() for v in x["per_k"].values())}
    if write:
        (DATA / "results").mkdir(exist_ok=True)
        (DATA / "results" / "rsi.json").write_text(json.dumps(ps._round(out, 5), ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
        (ROOT / "docs" / "RSI_KIEM_TRA.md").write_text(report(ps._round(out, 5)), encoding="utf-8", newline="\n")
    return out
