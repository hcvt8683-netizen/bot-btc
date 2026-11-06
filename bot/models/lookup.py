"""Tra cứu tại ngày t (mục lookup) và Tình huống tương tự (mục analog) của config/candidates.yaml, đăng ký trước ngày
06/11/2026 khi chưa tính con số nào.

Tại một ngày t bất kỳ từ 2016 và một kỳ hạn h do người dùng chọn: tình trạng giá, dải giá ngày t + h (đúng cách của
price_forecast.bands, kỳ hạn bất kỳ), mua ở t giữ h có lãi bao nhiêu lần trong 4 năm ngày mua trước đó, hỗ trợ / kháng cự,
tình huống tương tự; khi t + h đã qua thì điều đã xảy ra. Mọi con số tại t chỉ dùng giá đến hết ngày t. Kiểm chứng quá khứ
cho đúng h: mỗi h ngày một ngày gốc từ 2018, không chồng nhau.

Trang tính lại tất cả trong trình duyệt (src/lookup.js) từ chuỗi giá nhúng trong data/results/lookup.json; hai bên phải
cho cùng kết quả (tests/test_lookup.py). Ở đây là bản đối chiếu và phần nghiên cứu (Holm 72), chạy bằng
`python -m bot.cli lookup` → data/results/lookup.json và docs/TRA_CUU.md.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math

import numpy as np
import pandas as pd

from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml

OUT = DATA / "results" / "lookup.json"
REPORT = ROOT / "docs" / "TRA_CUU.md"
FEATS = ("r7", "r30", "ma200", "dd", "vol")
NB = {"r7": 5, "r30": 5, "ma200": 2, "dd": 3, "vol": 3}
LEVEL_DAYS = (7, 30, 90, 360)             # = sr_levels tuan|1, thang|1, thang|3, thang|12
LEVEL_FRAMES = ("tuan|1", "thang|1", "thang|3", "thang|12")
HOLD_DAYS = 1461                          # 4 năm ngày mua gần nhất đã biết kết quả
MIN_HOLD = 365
RANK_DAYS, RANK_MIN = 1461, 365
REPORT_H = (1, 7, 30, 90, 180, 365, 730, 1461)


def spec() -> dict:
    c = load_yaml(CONFIG / "candidates.yaml")
    return {"lookup": c["lookup"], "analog": c["analog"], "forecast": c["forecast"], "costs": float(c["long_hold"]["costs"])}


def version(cfg: dict) -> str:
    code = (ROOT / "bot" / "models" / "lookup.py").read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def rnd(x: float) -> int:
    """Làm tròn nửa lên (như Math.round của trang), không làm tròn kiểu ngân hàng của round()."""
    return int(math.floor(x + 0.5))


def r8(x) -> float:
    return float("nan") if x is None or not np.isfinite(x) else float(f"{float(x):.8g}")


# ----- dữ liệu: giá đóng Coin Metrics và cao / thấp Bitstamp trên cùng lịch ngày liền, làm tròn 8 chữ số như trang -----
def load(end: pd.Timestamp | None = None) -> dict:
    from bot.models import price_action as pa
    from bot.models import price_forecast as pf
    p = pf.daily_prices(end)
    b = pa.daily(end)[["high", "low"]].reindex(p.index)
    return {"start": p.index[0], "close": np.array([r8(x) for x in p.to_numpy()]),
            "high": np.array([r8(x) for x in b["high"].to_numpy()]), "low": np.array([r8(x) for x in b["low"].to_numpy()])}


def day(D: dict, i: int) -> pd.Timestamp:
    return D["start"] + pd.Timedelta(days=int(i))


def index_of(D: dict, date) -> int:
    return int((pd.Timestamp(date) - D["start"]).days)


# ----- chuỗi tính một lần -----
def _rolling_std(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).rolling(n, min_periods=n).std().to_numpy()


def series(D: dict, cfg: dict) -> dict:
    """Lợi suất log ngày, độ dao động 30 ngày và độ dao động trộn 30 + 365 ngày (như price_forecast), mọi ngày."""
    p = D["close"]
    lr = np.r_[np.nan, np.diff(np.log(p))]
    fc = cfg["forecast"]
    s30 = _rolling_std(lr, int(fc["vol_days"]))
    mix = np.sqrt((s30 ** 2 + _rolling_std(lr, int(fc["vol_long_days"])) ** 2) / 2) if fc.get("vol_long_days") else s30
    return {"lr": lr, "s30": s30, "mix": mix}


def features(D: dict, S: dict, cfg: dict) -> dict:
    """Nhóm của 5 đặc trưng mọi ngày T (−1 khi chưa đủ dữ liệu), chỉ dùng giá đến T."""
    p, n = D["close"], len(D["close"])
    A = cfg["analog"]["features"]
    ps = pd.Series(p)
    r7, r30 = ps / ps.shift(7) - 1, ps / ps.shift(30) - 1
    ma = ps.rolling(200, min_periods=200).mean()
    ath = ps.cummax()
    dd = 1 - ps / ath
    s30 = S["s30"]
    rank = np.full(n, np.nan)
    for t in range(n):
        if not np.isfinite(s30[t]):
            continue
        w = s30[max(0, t - RANK_DAYS + 1):t + 1]
        w = w[np.isfinite(w)]
        if len(w) >= RANK_MIN:
            rank[t] = float((w <= s30[t]).sum()) / len(w)

    def cut5(x: np.ndarray, c: list) -> np.ndarray:
        out = np.full(n, -1)
        f = np.isfinite(x)
        out[f & (x <= c[0])] = 0
        out[f & (x > c[0]) & (x <= c[1])] = 1
        out[f & (x > c[1]) & (x < c[2])] = 2
        out[f & (x >= c[2]) & (x < c[3])] = 3
        out[f & (x >= c[3])] = 4
        return out

    out = {"r7": cut5(r7.to_numpy(), A["r7"]["cuts"]), "r30": cut5(r30.to_numpy(), A["r30"]["cuts"])}
    m = np.full(n, -1)
    f = ma.notna().to_numpy() & np.isfinite(p)
    m[f & (p > ma.to_numpy())] = 0
    m[f & ~(p > ma.to_numpy())] = 1
    out["ma200"] = m
    d = np.full(n, -1)
    x, c = dd.to_numpy(), A["dd"]["cuts"]
    f = np.isfinite(x)
    d[f & (x < c[0])] = 0
    d[f & (x >= c[0]) & (x < c[1])] = 1
    d[f & (x >= c[1])] = 2
    out["dd"] = d
    v = np.full(n, -1)
    f = np.isfinite(rank)
    v[f & (rank <= 1 / 3)] = 0
    v[f & (rank > 1 / 3) & (rank <= 2 / 3)] = 1
    v[f & (rank > 2 / 3)] = 2
    out["vol"] = v
    out["_raw"] = {"r7": r7.to_numpy(), "r30": r30.to_numpy(), "ma": ma.to_numpy(), "dd": x, "rank": rank}
    return out


# ----- từng phần tại t -----
def state_at(D: dict, S: dict, F: dict, t: int) -> dict:
    p, R = D["close"], F["_raw"]
    val = lambda a: None if not np.isfinite(a[t]) else float(a[t])  # noqa: E731
    return {"date": day(D, t).strftime("%Y-%m-%d"), "close": val(p), "dd": val(R["dd"]), "ma200": val(R["ma"]),
            "vs_ma": None if not np.isfinite(R["ma"][t]) else float(p[t] / R["ma"][t] - 1), "r7": val(R["r7"]), "r30": val(R["r30"]),
            "vol": None if not np.isfinite(S["s30"][t]) else float(S["s30"][t] * math.sqrt(365)), "vol_rank": val(R["rank"]),
            "groups": {f: int(F[f][t]) for f in FEATS}}


def band_at(D: dict, S: dict, t: int, h: int, cfg: dict) -> dict | None:
    """Dải giá ngày t + h: phân vị của lợi suất chuẩn hóa h ngày của các ngày gốc T' ≤ t − h (đã biết kết quả tại t),
    max(window_days − h, min_obs) ngày gốc gần nhất, nhân lại với độ dao động tại t (= price_forecast.bands khi h ≤ 1096)."""
    p, mix, fc = D["close"], S["mix"], cfg["forecast"]
    W, mo = int(fc["window_days"]), int(fc["min_obs"])
    M = max(W - h, mo)
    hi = t - h
    if hi < 0 or not (np.isfinite(p[t]) and np.isfinite(mix[t])):
        return None
    i = np.arange(max(0, hi - M + 1), hi + 1)
    z = np.log(p[i + h] / p[i]) / (mix[i] * math.sqrt(h))
    z = z[np.isfinite(z)]
    if len(z) < mo:
        return None
    s = mix[t] * math.sqrt(h)
    return {f"q{rnd(q * 100)}": float(p[t] * math.exp(float(np.quantile(z, q)) * s)) for q in fc["quantiles"]} | {"n": int(len(z))}


def gains(D: dict, h: int, cost: float) -> np.ndarray:
    """Lợi nhuận mua ở giá đóng T, bán ở giá đóng T + h, sau phí hai chiều (NaN khi chưa biết)."""
    p, n = D["close"], len(D["close"])
    g = np.full(n, np.nan)
    if h < n:
        g[:n - h] = p[h:] * (1 - cost) / (p[:n - h] * (1 + cost)) - 1
    return g


def hold_at(D: dict, t: int, h: int, cost: float, G: np.ndarray | None = None) -> dict | None:
    """Tỷ lệ ngày mua T' trong [t − h − 1460, t − h] có lãi sau phí khi giữ h ngày."""
    G = gains(D, h, cost) if G is None else G
    hi = t - h
    if hi < 0:
        return None
    g = G[max(0, hi - HOLD_DAYS + 1):hi + 1]
    g = g[np.isfinite(g)]
    n = len(g)
    if n < MIN_HOLD:
        return None
    win = float((g > 0).mean())
    eff = max(1, rnd(n / h))
    lo, up = wilson(rnd(win * eff), eff)
    q10, q50, q90 = (float(x) for x in np.quantile(g, [0.10, 0.50, 0.90]))
    return {"n": n, "n_eff": eff, "p": win, "ci": [lo, up], "median": q50, "p10": q10, "p90": q90}


def levels_at(D: dict, t: int) -> list[dict]:
    """Hỗ trợ / kháng cự Bitstamp của 7, 30, 90, 360 ngày đến t; thiếu nến trong cửa sổ thì không có mức (như sr_levels)."""
    out = []
    for W, fr in zip(LEVEL_DAYS, LEVEL_FRAMES):
        hi, lo = D["high"][max(0, t - W + 1):t + 1], D["low"][max(0, t - W + 1):t + 1]
        ok = t - W + 1 >= 0 and np.isfinite(hi).all() and np.isfinite(lo).all()
        out.append({"frame": fr, "days": W, "R": float(hi.max()) if ok else None, "S": float(lo.min()) if ok else None})
    return out


def outcome_at(D: dict, t: int, h: int, band: dict | None, cost: float) -> dict | None:
    p = D["close"]
    if t + h >= len(p) or not (np.isfinite(p[t]) and np.isfinite(p[t + h])):
        return None
    a = float(p[t + h])
    hi, lo = D["high"][t + 1:t + h + 1], D["low"][t + 1:t + h + 1]
    return {"date": day(D, t + h).strftime("%Y-%m-%d"), "close": a, "ret": a / float(p[t]) - 1,
            "gain": a * (1 - cost) / (float(p[t]) * (1 + cost)) - 1,
            "in80": None if band is None else bool(band["q10"] <= a <= band["q90"]),
            "in50": None if band is None else bool(band["q25"] <= a <= band["q75"]),
            "high": float(np.nanmax(hi)) if np.isfinite(hi).any() else None, "low": float(np.nanmin(lo)) if np.isfinite(lo).any() else None}


# ----- tình huống tương tự -----
def _ups(D: dict, h: int) -> np.ndarray:
    p, n = D["close"], len(D["close"])
    u = np.full(n, np.nan)
    if h < n:
        ok = np.isfinite(p[h:]) & np.isfinite(p[:n - h])
        u[:n - h] = np.where(ok, (p[h:] > p[:n - h]).astype(float), np.nan)
    return u


def _lr(D: dict, h: int) -> np.ndarray:
    p, n = D["close"], len(D["close"])
    r = np.full(n, np.nan)
    if h < n:
        r[:n - h] = np.log(p[h:] / p[:n - h])
    return r


def _desc(u: np.ndarray, r: np.ndarray, h: int) -> dict:
    """Số ngày, P(lên), Wilson theo số lần độc lập = số ngày / h, trung vị lợi suất log."""
    n = len(u)
    if not n:
        return {"n": 0, "n_eff": 0, "p": None, "ci": [None, None], "median": None}
    p = float(u.mean())
    eff = max(1, rnd(n / h))
    lo, hi = wilson(rnd(p * eff), eff)
    return {"n": n, "n_eff": eff, "p": p, "ci": [lo, hi], "median": float(np.median(r))}


def two_prop(a: dict, b: dict) -> float | None:
    """p hai phía của kiểm định hai tỷ lệ (z) trên số lần độc lập."""
    if not a["n"] or not b["n"]:
        return None
    x1, n1, x2, n2 = rnd(a["p"] * a["n_eff"]), a["n_eff"], rnd(b["p"] * b["n_eff"]), b["n_eff"]
    pp = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    return math.erfc(abs(x1 / n1 - x2 / n2) / se / math.sqrt(2))


def holm(rows: list[dict]) -> None:
    idx = [i for i, r in enumerate(rows) if r["p_value"] is not None]
    run, M = 0.0, len(idx)
    for k, i in enumerate(sorted(idx, key=lambda j: rows[j]["p_value"])):
        run = max(run, min(1.0, (M - k) * rows[i]["p_value"]))
        rows[i]["p_holm"] = run
    for r in rows:
        r.setdefault("p_holm", None)


def verdict(r: dict) -> str:
    if r["cond"]["n_eff"] < 30 or any(x["cond"]["n_eff"] < 5 for x in r["halves"]):
        return "it_du_lieu"
    if r["p_holm"] is not None and r["p_holm"] < 0.05 and all(x["diff"] is not None for x in r["halves"]):
        if r["diff"] > 0 and all(x["diff"] > 0 for x in r["halves"]):
            return "hon"
        if r["diff"] < 0 and all(x["diff"] < 0 for x in r["halves"]):
            return "kem"
    return "nhu_bat_ky"


def research(D: dict, F: dict, cfg: dict) -> dict:
    A = cfg["analog"]
    n = len(D["close"])
    start = max(0, index_of(D, str(A["period"]["from"])))
    idx = np.arange(n)
    rows = []
    for h in A["horizons_days"]:
        h = int(h)
        u, r = _ups(D, h), _lr(D, h)
        valid = (idx >= start) & np.isfinite(u)
        days = np.where(valid)[0]
        if not len(days):
            continue
        mid = int(days[len(days) // 2])
        for f in FEATS:
            fv = F[f]
            ok = valid & (fv >= 0)
            for b in range(NB[f]):
                m, rest = ok & (fv == b), ok & (fv != b)
                c, o = _desc(u[m], r[m], h), _desc(u[rest], r[rest], h)
                halves = []
                for part in (idx < mid, idx >= mid):
                    hc, ho = _desc(u[m & part], r[m & part], h), _desc(u[rest & part], r[rest & part], h)
                    halves.append({"cond": hc, "rest": ho, "diff": None if hc["p"] is None or ho["p"] is None else hc["p"] - ho["p"]})
                rows.append({"feature": f, "group": b, "h": h, "cond": c, "rest": o,
                             "diff": None if c["p"] is None or o["p"] is None else c["p"] - o["p"],
                             "p_value": two_prop(c, o), "halves": halves, "split": day(D, mid).strftime("%Y-%m-%d")})
    holm(rows)
    for x in rows:
        x["verdict"] = verdict(x)
    last = {}
    for h in A["horizons_days"]:
        u = _ups(D, int(h))
        k = np.where(np.isfinite(u))[0]
        last[str(int(h))] = day(D, int(k[-1])).strftime("%Y-%m-%d") if len(k) else None
    return {"from": day(D, start).strftime("%Y-%m-%d"), "to": last, "tests": len(rows), "rows": rows,
            "summary": {v: sum(x["verdict"] == v for x in rows) for v in ("hon", "kem", "nhu_bat_ky", "it_du_lieu")}}


def analog_at(D: dict, F: dict, t: int, h: int, cfg: dict) -> dict:
    """Chỉ mô tả, kỳ hạn h bất kỳ: các ngày T' từ 2014 đến t − h (đã biết kết quả tại t) cùng nhóm với t."""
    n = len(D["close"])
    start = max(0, index_of(D, str(cfg["analog"]["period"]["from"])))
    idx = np.arange(n)
    u, r = _ups(D, h), _lr(D, h)
    valid = (idx >= start) & (idx <= t - h) & np.isfinite(u)
    out = {"all": _desc(u[valid], r[valid], h), "features": {}}
    same = valid.copy()
    for f in FEATS:
        g = int(F[f][t])
        if g < 0:
            out["features"][f] = None
            same &= False
            continue
        m = valid & (F[f] == g)
        same &= (F[f] == g)
        out["features"][f] = {"group": g, **_desc(u[m], r[m], h)}
    out["combo"] = _desc(u[same], r[same], h)
    return out


# ----- tra cứu đầy đủ và kiểm chứng quá khứ -----
def lookup(D: dict, S: dict, F: dict, t: int, h: int, cfg: dict) -> dict:
    band = band_at(D, S, t, h, cfg)
    return {"t": day(D, t).strftime("%Y-%m-%d"), "h": h, "target": day(D, t + h).strftime("%Y-%m-%d"), "state": state_at(D, S, F, t),
            "band": band, "hold": hold_at(D, t, h, cfg["costs"]), "levels": levels_at(D, t), "analog": analog_at(D, F, t, h, cfg),
            "outcome": outcome_at(D, t, h, band, cfg["costs"])}


def check(D: dict, S: dict, h: int, cfg: dict) -> dict:
    """Ngày gốc t' từ check_from, cách nhau h ngày (không chồng nhau), t' + h ≤ ngày cuối."""
    p, n = D["close"], len(D["close"])
    t0 = max(0, index_of(D, str(cfg["forecast"]["check_from"])))
    G = gains(D, h, cfg["costs"])
    years: dict[str, list] = {}
    rows = []
    for t in range(t0, n - h, h):
        if not (np.isfinite(p[t]) and np.isfinite(p[t + h])):
            continue
        b, ho = band_at(D, S, t, h, cfg), hold_at(D, t, h, cfg["costs"], G)
        a = float(p[t + h])
        rows.append({"t": t, "in80": None if b is None else b["q10"] <= a <= b["q90"], "in50": None if b is None else b["q25"] <= a <= b["q75"],
                     "said": None if ho is None else ho["p"], "win": bool(G[t] > 0)})
        years.setdefault(day(D, t).strftime("%Y"), []).append(rows[-1])

    def cover(rs: list, key: str) -> dict:
        x = [r[key] for r in rs if r[key] is not None]
        k = int(sum(x))
        lo, hi = wilson(k, len(x))
        return {"n": len(x), "k": k, "p": k / len(x) if x else None, "ci": [lo, hi]}

    said = [r for r in rows if r["said"] is not None]
    groups = []
    for lo_, hi_ in ((0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)):
        g = [r for r in said if lo_ <= r["said"] < hi_]
        k = int(sum(r["win"] for r in g))
        a, b = wilson(k, len(g))
        groups.append({"from": lo_, "to": min(hi_, 1.0), "n": len(g), "said": float(np.mean([r["said"] for r in g])) if g else None,
                       "k": k, "p": k / len(g) if g else None, "ci": [a, b]})
    k = int(sum(r["win"] for r in said))
    a, b = wilson(k, len(said))
    hold = {"n": len(said), "said": float(np.mean([r["said"] for r in said])) if said else None, "k": k, "p": k / len(said) if said else None,
            "ci": [a, b], "brier": float(np.mean([(r["said"] - r["win"]) ** 2 for r in said])) if said else None,
            "brier50": float(np.mean([(0.5 - r["win"]) ** 2 for r in said])) if said else None, "groups": groups}
    return {"h": h, "from": day(D, rows[0]["t"]).strftime("%Y-%m-%d") if rows else None, "to": day(D, rows[-1]["t"]).strftime("%Y-%m-%d") if rows else None,
            "anchors": len(rows), "in80": cover(rows, "in80"), "in50": cover(rows, "in50"),
            "years": [{"year": y, "in80": cover(v, "in80"), "in50": cover(v, "in50")} for y, v in sorted(years.items())], "hold": hold}


def _sr_verdicts() -> dict:
    """Kết luận đã có của sr_levels cho 4 khung (đọc sr.json, không tính mới)."""
    path = DATA / "results" / "sr.json"
    if not path.exists():
        return {}
    sr = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for r in sr.get("frames", []):
        k = f"{r['unit']}|{r['n']}"
        if k in LEVEL_FRAMES:
            out.setdefault(k, {})[r["side"]] = {"verdict": r["verdict"], "real": r["real"].get("p"), "fake": r["fake"].get("p")}
    return {"frames": out, "summary": sr.get("summary"), "tests": sr.get("tests")}


def page_data(D: dict, cfg: dict, res: dict) -> dict:
    """Chuỗi giá và cấu hình cho trang (src/lookup.js tính lại mọi thứ từ đây)."""
    fc, A, L = cfg["forecast"], cfg["analog"], cfg["lookup"]
    nn = lambda a: [None if not np.isfinite(x) else x for x in a]  # noqa: E731
    last = int(np.where(np.isfinite(D["close"]))[0][-1])
    return {"version": version(cfg), "made": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "start": D["start"].strftime("%Y-%m-%d"), "last": day(D, last).strftime("%Y-%m-%d"),
            "close": nn(D["close"][:last + 1]), "high": nn(D["high"][:last + 1]), "low": nn(D["low"][:last + 1]),
            "cfg": {"t_from": str(L["t_range"]["from"]), "max_h": 1461, "quantiles": fc["quantiles"], "window_days": fc["window_days"],
                    "min_obs": fc["min_obs"], "vol_days": fc["vol_days"], "vol_long_days": fc.get("vol_long_days"), "costs": cfg["costs"],
                    "check_from": str(fc["check_from"]), "hold_days": HOLD_DAYS, "min_hold": MIN_HOLD, "rank_days": RANK_DAYS, "rank_min": RANK_MIN,
                    "level_days": list(LEVEL_DAYS), "level_frames": list(LEVEL_FRAMES), "period_from": str(A["period"]["from"]),
                    "cuts": {f: A["features"][f].get("cuts") for f in FEATS}, "horizons": [int(h) for h in A["horizons_days"]]},
            "research": res, "sr": _sr_verdicts()}


def _round(x, nd: int = 5):
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, nd)
    if isinstance(x, dict):
        return {k: _round(v, nd) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v, nd) for v in x]
    return x


def run(write: bool = True, end: pd.Timestamp | None = None) -> dict:
    cfg = spec()
    D = load(end)
    S = series(D, cfg)
    F = features(D, S, cfg)
    res = research(D, F, cfg)
    page = page_data(D, cfg, _round(res))
    if write:
        OUT.parent.mkdir(exist_ok=True)
        rr = {k: v for k, v in page.items() if k not in ("close", "high", "low")}
        OUT.write_text(json.dumps({**_round(rr), "close": page["close"], "high": page["high"], "low": page["low"]},
                                  ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        REPORT.write_text(report(D, S, F, cfg, res), encoding="utf-8")
    return {"D": D, "S": S, "F": F, "cfg": cfg, "research": res}


# ----- báo cáo -----
GROUP_NAMES = {"r7": ["giảm mạnh (≤ −10%)", "giảm (−10% … −3%)", "đi ngang (−3% … +3%)", "tăng (+3% … +10%)", "tăng mạnh (≥ +10%)"],
               "r30": ["giảm mạnh (≤ −20%)", "giảm (−20% … −7%)", "đi ngang (−7% … +7%)", "tăng (+7% … +20%)", "tăng mạnh (≥ +20%)"],
               "ma200": ["trên MA 200 ngày", "dưới MA 200 ngày"], "dd": ["cách đỉnh < 20%", "cách đỉnh 20–50%", "cách đỉnh ≥ 50%"],
               "vol": ["dao động thấp (1/3 dưới)", "dao động vừa", "dao động cao (1/3 trên)"]}
FEAT_NAMES = {"r7": "Lợi suất 7 ngày", "r30": "Lợi suất 30 ngày", "ma200": "MA 200 ngày", "dd": "Giảm từ đỉnh", "vol": "Độ dao động 30 ngày"}
VERDICT = {"hon": "**sau đó lên nhiều hơn**", "kem": "**sau đó lên ít hơn**", "nhu_bat_ky": "như ngày bất kỳ", "it_du_lieu": "ít dữ liệu"}


def _pc(x, d: int = 0) -> str:
    return "—" if x is None else f"{x * 100:.{d}f}%".replace(".", ",")


def _ci(c) -> str:
    return "—" if c[0] is None else f"{_pc(c[0])}–{_pc(c[1])}"


def report(D: dict, S: dict, F: dict, cfg: dict, res: dict) -> str:
    last = int(np.where(np.isfinite(D["close"]))[0][-1])
    L = [f"# Tra cứu tại ngày t và Tình huống tương tự",
         "",
         f"Sinh tự động bằng `python -m bot.cli lookup` lúc {dt.datetime.now(dt.timezone.utc).strftime('%H:%M %d/%m/%Y')} UTC, giá đóng Coin Metrics đến "
         f"{day(D, last).strftime('%d/%m/%Y')}. Cách làm đăng ký trước trong `config/candidates.yaml` mục `lookup` và `analog` (06/11/2026), "
         "lưu git trước khi tính. Trong ngoặc là khoảng tin cậy Wilson 95% theo số lần độc lập.",
         "",
         "## 1. Tình huống tương tự: sau đó giá lên nhiều hơn các ngày còn lại không",
         "",
         f"Mỗi ngày T từ {res['from'][8:10]}/{res['from'][5:7]}/{res['from'][:4]}, xếp nhóm theo 5 đặc trưng (chỉ dùng giá đến T), đếm số lần giá "
         f"sau h ngày cao hơn. So với các ngày còn lại, kiểm định hai tỷ lệ, Holm trên {res['tests']} phép thử, phải cùng dấu ở hai nửa giai đoạn.",
         "",
         f"Kết quả: {res['summary']['hon']} điều kiện sau đó lên nhiều hơn, {res['summary']['kem']} lên ít hơn, {res['summary']['nhu_bat_ky']} như ngày bất kỳ, "
         f"{res['summary']['it_du_lieu']} ít dữ liệu.",
         "",
         "| Đặc trưng | Nhóm | Kỳ hạn | Số ngày | Sau đó lên | Các ngày còn lại | Chênh | p Holm | Kết luận |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        c, o = r["cond"], r["rest"]
        diff = "—" if r["diff"] is None else "{:+.0f} điểm".format(r["diff"] * 100)
        ph = "—" if r["p_holm"] is None else "{:.3f}".format(r["p_holm"]).replace(".", ",")
        L.append(f"| {FEAT_NAMES[r['feature']]} | {GROUP_NAMES[r['feature']][r['group']]} | {r['h']} ngày | {c['n']} | {_pc(c['p'])} ({_ci(c['ci'])}) | "
                 f"{_pc(o['p'])} | {diff} | {ph} | {VERDICT[r['verdict']]} |")
    L += ["", "Dữ liệu giá từ 2014 đã được các kiểm định khác của dự án xem trước (xu hướng, price action), nên đây chưa phải kiểm định ngoài "
          "mẫu mới. Kiểm tra cuối: từ 06/11/2026, chạy một lần khi đủ 1 năm (từ 11/2027).", "",
          "## 2. Kiểm chứng quá khứ của bảng tra cứu theo kỳ hạn", "",
          f"Mỗi h ngày một ngày gốc từ {str(cfg['forecast']['check_from'])[8:10]}/{str(cfg['forecast']['check_from'])[5:7]}/{str(cfg['forecast']['check_from'])[:4]}, "
          "không chồng nhau, mỗi ngày gốc chỉ dùng dữ liệu đến ngày đó. Dải 8/10 lần đúng thì gần 80%, dải 5/10 lần gần 50%. "
          "Mua giữ: bot nói (tỷ lệ có lãi của 4 năm ngày mua trước đó) so với thực tế; sai số Brier càng thấp càng tốt, luôn nói 50% là 0,25.", "",
          "| Kỳ hạn | Số ngày gốc | Trong dải 8/10 | Trong dải 5/10 | Mua giữ: bot nói | Thực tế có lãi | Brier | Brier nếu luôn nói 50% |",
          "|---|---|---|---|---|---|---|---|"]
    for h in REPORT_H:
        c = check(D, S, h, cfg)
        ho = c["hold"]
        br = "—" if ho["brier"] is None else "{:.3f}".format(ho["brier"]).replace(".", ",")
        b50 = "—" if ho["brier50"] is None else "{:.3f}".format(ho["brier50"]).replace(".", ",")
        L.append(f"| {h} ngày | {c['anchors']} | {_pc(c['in80']['p'])} ({_ci(c['in80']['ci'])}) | {_pc(c['in50']['p'])} ({_ci(c['in50']['ci'])}) | "
                 f"{_pc(ho['said'])} | {_pc(ho['p'])} ({_ci(ho['ci'])}) | {br} | {b50} |")
    L += ["", "Kỳ hạn dài có ít ngày gốc không chồng nhau (ví dụ 4 năm chỉ vài lần), nên mọi con số ở đó rất không chắc.", "",
          "## 3. Không phải lời khuyên", "",
          "Không phần nào ở đây chọn được thời điểm mua: khuyến nghị tuần vẫn là mua đều. Bảng tra cứu cho biết lịch sử nói gì tại ngày t, "
          "để đặt kỳ vọng và cắt lỗ có kỷ luật.", "", "Công cụ tham khảo, không phải lời khuyên đầu tư.", ""]
    return "\n".join(L)
