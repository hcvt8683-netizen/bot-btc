"""Price action on Bitstamp daily candles (config/candidates.yaml, section price_action; registered before any number
was computed).

Ten criteria, five kinds × two directions: touch and hold at the nearest support / rejection at the nearest resistance
(levels from swing lows / highs with 5 candles on each side, known only once the 5th candle after them has closed; zone
± 0.5 ATR), market structure (higher highs and higher lows / lower highs and lower lows), pin bar and inside bar at a
level, false breakout (pierce the level beyond the zone, close back inside), plus two confluence sets (at least 2 of the
5 criteria of one direction on the same day). A criterion at day T uses candles up to T only. For 1, 3, 7 and 30 days:
how often the close k days later went the announced way, against every day of the same period; Wilson over independent
episodes, stationary block bootstrap of the difference, Holm over the 48 pairs, same sign in both halves. The final
test on signals from the registration date runs once, logged, when a year of outcomes exists (`run_final`).
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.i18n import fmt

PHASE = "price_action_final"
N_BOOT, SEED = 2000, 0
MIN_EPISODES, MIN_HALF = 30, 5   # registered verdict: fewer independent episodes than this (overall / in a half) → no conclusion
NAMES = {"ho_tro": "Chạm hỗ trợ và giữ", "khang_cu": "Chạm kháng cự và bị đẩy xuống",
         "cau_truc_tang": "Cấu trúc tăng (đỉnh cao hơn, đáy cao hơn)", "cau_truc_giam": "Cấu trúc giảm (đỉnh thấp hơn, đáy thấp hơn)",
         "pin_bar_ho_tro": "Pin bar tăng tại hỗ trợ", "pin_bar_khang_cu": "Pin bar giảm tại kháng cự",
         "inside_bar_ho_tro": "Inside bar tại hỗ trợ", "inside_bar_khang_cu": "Inside bar tại kháng cự",
         "pha_vo_gia_duoi": "Phá vỡ giả phía dưới", "pha_vo_gia_tren": "Phá vỡ giả phía trên",
         "bo_tang": "Bộ tiêu chí tăng (≥ 2/5)", "bo_giam": "Bộ tiêu chí giảm (≥ 2/5)"}
VERDICT = {"hon": "**hơn mốc**", "kem": "**kém mốc**", "chua": "chưa có lợi thế", "it_dot": "ít đợt (không kết luận)"}


class AlreadyRun(RuntimeError):
    """The final test of price action is allowed once."""


class NotReady(RuntimeError):
    """Not enough days after the registration date for the final test."""


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["price_action"]


def direction(cfg: dict) -> dict[str, int]:
    """+1 for a criterion said to announce a rise, −1 for a fall (first word of its registered definition); the two
    confluence sets come last."""
    return {k: (1 if v.strip().startswith("tăng") else -1) for k, v in {**cfg["criteria"], **cfg["combo"]}.items()}


def daily(end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Bitstamp daily candles on a gap-free calendar (row d = candle opening d 00:00 UTC); an impossible candle (a price
    not positive, low above the body, high below it) is missing as a whole."""
    from bot.data import pit_store as ps
    b = ps.load_history("bitstamp")
    d = b.assign(date=pd.to_datetime(b["date"])).drop_duplicates("date", keep="last").set_index("date").sort_index()
    d = d[["open", "high", "low", "close"]].astype(float)
    o, h, lo, c = (d[x] for x in ("open", "high", "low", "close"))
    d.loc[~((d > 0).all(axis=1) & (lo <= np.minimum(o, c)) & (h >= np.maximum(o, c)))] = np.nan
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="D"))
    return d if end is None else d[d.index <= end]


def atr(d: pd.DataFrame, n: int) -> pd.Series:
    """Mean true range of the n candles ending at T (price units); needs every one of them and the close before each."""
    pc = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"], (d["high"] - pc).abs(), (d["low"] - pc).abs()], axis=1).max(axis=1, skipna=False)
    return tr.rolling(n, min_periods=n).mean()


def swings(d: pd.DataFrame, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Swing highs / lows at day j: the highest high of the 2n + 1 candles j − n..j + n and above each of the n before
    it (lows mirrored). This looks at the n candles AFTER j, so a swing may only be used from the close of j + n on."""
    H, L = d["high"], d["low"]
    hi = (H > H.shift(1).rolling(n, min_periods=n).max()) & (H >= H.shift(-n).rolling(n, min_periods=n).max())
    lo = (L < L.shift(1).rolling(n, min_periods=n).min()) & (L <= L.shift(-n).rolling(n, min_periods=n).min())
    return hi.to_numpy(), lo.to_numpy()


def known_after(n: int) -> int:
    """Days after its own candle at which a swing is known: the n candles on its right must have closed."""
    return n


def levels(d: pd.DataFrame, hi: np.ndarray, lo: np.ndarray, n: int, lookback: int) -> tuple[np.ndarray, np.ndarray]:
    """Nearest support S (highest swing low below the close of T − 1) and resistance R (lowest swing high above it),
    fixed before candle T: swings known at the close of T − 1 whose day is within `lookback` days of T − 1."""
    H, L, C = (d[x].to_numpy() for x in ("high", "low", "close"))
    ph, pl, lag = np.flatnonzero(hi), np.flatnonzero(lo), known_after(n)
    S, R = np.full(len(d), np.nan), np.full(len(d), np.nan)
    for T in range(1, len(d)):
        ref = C[T - 1]
        if not np.isfinite(ref):
            continue
        a, b = T - 1 - lookback, T - 1 - lag
        v = L[pl[np.searchsorted(pl, a):np.searchsorted(pl, b, side="right")]]
        v = v[v < ref]
        if len(v):
            S[T] = v.max()
        v = H[ph[np.searchsorted(ph, a):np.searchsorted(ph, b, side="right")]]
        v = v[v > ref]
        if len(v):
            R[T] = v.min()
    return S, R


def structure(d: pd.DataFrame, hi: np.ndarray, lo: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """From the last two swing highs and lows known at the close of T: higher high + higher low with the close above the
    last swing low (up); lower high + lower low with the close below the last swing high (down)."""
    H, L, C = (d[x].to_numpy() for x in ("high", "low", "close"))
    ph, pl = np.flatnonzero(hi), np.flatnonzero(lo)
    if len(ph) < 2 or len(pl) < 2:
        return np.zeros(len(d), bool), np.zeros(len(d), bool)
    t = np.arange(len(d)) - known_after(n)
    bh, bl = np.searchsorted(ph, t, side="right"), np.searchsorted(pl, t, side="right")
    ok = (bh >= 2) & (bl >= 2)
    h1, h2 = H[ph[np.maximum(bh - 2, 0)]], H[ph[np.maximum(bh - 1, 0)]]
    l1, l2 = L[pl[np.maximum(bl - 2, 0)]], L[pl[np.maximum(bl - 1, 0)]]
    with np.errstate(invalid="ignore"):
        return ok & (h2 > h1) & (l2 > l1) & (C > l2), ok & (h2 < h1) & (l2 < l1) & (C < h2)


def rules(x: pd.DataFrame, p: dict) -> pd.DataFrame:
    """The ten criteria at each row T from candle T, candle T − 1 (the row before) and what was fixed before T
    (columns open, high, low, close, S, R, w, up, down); a missing value gives False."""
    O, H, L, C, S, R, w = (x[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "S", "R", "w"))
    C1, H1, L1 = (np.r_[np.nan, a[:-1]] for a in (C, H, L))
    rng, lower, upper, pin = H - L, np.minimum(O, C) - L, H - np.maximum(O, C), float(p["pin_wick"])
    with np.errstate(invalid="ignore"):
        inside = (H < H1) & (L > L1)
        out = {"ho_tro": (L >= S - w) & (L <= S + w) & (C > S) & (C1 > S + w),
               "khang_cu": (H <= R + w) & (H >= R - w) & (C < R) & (C1 < R - w),
               "cau_truc_tang": x["up"].to_numpy(dtype=bool),
               "cau_truc_giam": x["down"].to_numpy(dtype=bool),
               "pin_bar_ho_tro": (rng > 0) & (lower >= pin * rng) & (L <= S + w) & (C > S),
               "pin_bar_khang_cu": (rng > 0) & (upper >= pin * rng) & (H >= R - w) & (C < R),
               "inside_bar_ho_tro": inside & (L1 <= S + w),
               "inside_bar_khang_cu": inside & (H1 >= R - w),
               "pha_vo_gia_duoi": (L < S - w) & (C > S),
               "pha_vo_gia_tren": (H > R + w) & (C < R)}
    return pd.DataFrame(out, index=x.index)


def flags(d: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Every criterion and both confluence sets at each day T, from candles up to T only."""
    p = cfg["params"]
    n = int(p["swing_n"])
    hi, lo = swings(d, n)
    S, R = levels(d, hi, lo, n, int(p["level_lookback_days"]))
    up, down = structure(d, hi, lo, n)
    w = float(p["zone_atr"]) * atr(d, int(p["atr_days"])).shift(1).to_numpy()
    f = rules(d.assign(S=S, R=R, w=w, up=up, down=down), p)
    dirs = direction(cfg)
    for name in cfg["combo"]:
        f[name] = f[[c for c in cfg["criteria"] if dirs[c] == dirs[name]]].sum(axis=1) >= int(p["combo_m"])
    return f


def episodes(dates: pd.DatetimeIndex, k: int) -> np.ndarray:
    """Position of the first signal of each episode: a signal at most k days after the previous one joins its episode."""
    if not len(dates):
        return np.array([], dtype=int)
    gap = np.diff(dates.values).astype("timedelta64[D]").astype(int)
    return np.r_[0, np.flatnonzero(gap > k) + 1]


def holm(rows: list[dict], key: str = "p") -> None:
    """Holm step-down over `rows`, kept monotone, written to <key>_holm."""
    run, M = 0.0, len(rows)
    for i, j in enumerate(np.argsort([r[key] for r in rows], kind="stable")):
        run = max(run, min(1.0, (M - i) * rows[j][key]))
        rows[j][key + "_holm"] = run


def _pair(y: np.ndarray, f: np.ndarray, g: np.ndarray, dates: pd.DatetimeIndex, k: int, Y: np.ndarray, Ym: np.ndarray,
          idx: np.ndarray, n_boot: int) -> dict:
    """One criterion × horizon: y = hit of every day, f = signal, g = log return in the criterion's direction; Y = y on
    the bootstrap days (runs × days), Ym = its mean per run, idx = those days."""
    n, half = len(y), len(y) // 2
    sig = np.flatnonzero(f)
    first = sig[episodes(dates[sig], k)]
    halves = []
    for a, b in ((0, half), (half, n)):
        fh, yh = f[a:b], y[a:b]
        hit = float(yh[fh].mean()) if fh.any() else None
        halves.append({"from": dates[a].strftime("%Y-%m-%d"), "to": dates[b - 1].strftime("%Y-%m-%d"), "n": int(fh.sum()),
                       "episodes": int(((first >= a) & (first < b)).sum()), "base": float(yh.mean()), "hit": hit,
                       "diff": None if hit is None else hit - float(yh.mean())})
    r = {"days": int(n), "n": int(len(sig)), "episodes": int(len(first)), "base": float(y.mean()), "base_ret": float(g.mean()),
         "halves": halves}
    none = {"hit": None, "diff": None, "ret": None, "hit_first": None, "wilson": [None, None], "ci": [None, None],
            "p": 1.0, "p_gt": 1.0, "p_lt": 1.0}
    if not len(sig):
        return {**r, **none}
    F = f[idx]
    nf = F.sum(axis=1)
    keep = nf > 0
    db = (Y & F).sum(axis=1)[keep] / nf[keep] - Ym[keep]
    hit, kf = float(y[sig].mean()), int(y[first].sum())
    r.update(hit=hit, diff=hit - r["base"], ret=float(g[sig].mean()), hit_first=kf / len(first), wilson=list(wilson(kf, len(first))))
    if not len(db):
        return {**none, **r}
    p_gt, p_lt = max(1.0 / n_boot, float((db <= 0).mean())), max(1.0 / n_boot, float((db >= 0).mean()))
    return {**r, "ci": [float(np.quantile(db, 0.025)), float(np.quantile(db, 0.975))], "p": min(1.0, 2 * min(p_gt, p_lt)),
            "p_gt": p_gt, "p_lt": p_lt}


def verdict(r: dict) -> str:
    """Registered verdict; too few independent episodes overrides the test (no conclusion)."""
    if r["episodes"] < MIN_EPISODES or min(h["episodes"] for h in r["halves"]) < MIN_HALF:
        return "it_dot"
    diffs = [h["diff"] for h in r["halves"]]
    if r["p_holm"] < 0.05 and all(x is not None and x > 0 for x in diffs):
        return "hon"
    if r["p_holm"] < 0.05 and all(x is not None and x < 0 for x in diffs):
        return "kem"
    return "chua"


def table(d: pd.DataFrame, f: pd.DataFrame, cfg: dict, start: pd.Timestamp, end: pd.Timestamp | None, n_boot: int = N_BOOT,
          seed: int = SEED) -> list[dict]:
    """Every criterion and set × horizon on signal days T with start ≤ T and T + k ≤ end (None = end of data), Holm over
    all of them and the registered verdict."""
    dirs, C = direction(cfg), d["close"].to_numpy()
    rows = []
    for k in [int(x) for x in cfg["horizons_days"]]:
        later = d["close"].shift(-k).to_numpy()
        ok = (d.index >= start) & np.isfinite(C) & np.isfinite(later)
        if end is not None:
            ok &= d.index + pd.Timedelta(days=k) <= end
        pos = np.flatnonzero(ok)
        if len(pos) < 2:
            continue
        dates, lr = d.index[pos], np.log(later[pos] / C[pos])
        idx = measure.stationary_indices(len(pos), k, n_boot, np.random.default_rng(seed))
        ys = {s: s * lr > 0 for s in (1, -1)}
        Ys = {s: ys[s][idx] for s in (1, -1)}
        Ym = {s: Ys[s].mean(axis=1) for s in (1, -1)}
        for name, s in dirs.items():
            rows.append({"k": k, "crit": name, "dir": s, "combo": name in cfg["combo"],
                         **_pair(ys[s], f[name].to_numpy()[pos], s * lr, dates, k, Ys[s], Ym[s], idx, n_boot)})
    holm(rows)
    for r in rows:
        r["verdict"] = verdict(r)
    return rows


def _ts(x) -> pd.Timestamp:
    return pd.Timestamp(str(x))


def final_status(d: pd.DataFrame, cfg: dict, log_path=None) -> dict:
    """How many signal days from the registration date have a known 30-day outcome, and whether the run happened."""
    ft = cfg["final_test"]
    start, kmax, C = _ts(ft["from"]), max(int(k) for k in cfg["horizons_days"]), d["close"]
    days = int(((d.index >= start) & np.isfinite(C.to_numpy()) & np.isfinite(C.shift(-kmax).to_numpy())).sum())
    return {"from": start.strftime("%Y-%m-%d"), "days": days, "need": int(ft["min_days"]), "ready": days >= int(ft["min_days"]),
            "done": already_run(log_path)}


def already_run(log_path=None) -> bool:
    from bot.validation import splits
    p = log_path or splits.FINAL_LOG
    if not p.exists():
        return False
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            if json.loads(line).get("phase") == PHASE:
                return True
        except ValueError:
            continue
    return False


def _log(log_path, args: dict) -> None:
    if log_path is None:
        from bot.validation import splits
        splits.log_final_run(args)
    else:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"time": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **args}, ensure_ascii=False) + "\n")


def run_final(d: pd.DataFrame | None = None, cfg: dict | None = None, log_path=None, out_path=None, n_boot: int = N_BOOT) -> dict:
    """The one logged final test: confirm only the research pairs better or worse than the baseline (one-sided bootstrap
    p, Holm over those pairs); without such pairs the final period is reported as a description only. Refuses before a
    year of outcomes and after a first run."""
    cfg = cfg or spec()
    d = daily() if d is None else d
    st = final_status(d, cfg, log_path)
    if st["done"]:
        raise AlreadyRun("kiểm tra cuối của price action đã chạy một lần (experiments/final_runs.log)")
    if not st["ready"]:
        raise NotReady(f"mới có {st['days']}/{st['need']} ngày từ {fmt.date(st['from'])} đã biết kết quả 30 ngày")
    f, rs = flags(d, cfg), cfg["research"]
    todo = [r for r in table(d, f, cfg, _ts(rs["from"]), _ts(rs["to"]), n_boot) if r["verdict"] in ("hon", "kem")]
    _log(log_path, {"command": "price-action --final", "phase": PHASE, "status": "start", "pairs": len(todo)})
    fin = table(d, f, cfg, _ts(st["from"]), None, n_boot)
    by = {(r["crit"], r["k"]): r for r in fin}
    check = []
    for r in todo:
        x = dict(by.get((r["crit"], r["k"])) or {"n": 0, "diff": None, "p_gt": 1.0, "p_lt": 1.0})
        x.update(crit=r["crit"], k=r["k"], research=r["verdict"], p_one=x["p_gt"] if r["verdict"] == "hon" else x["p_lt"])
        check.append(x)
    holm(check, "p_one")
    for x in check:
        same = x["diff"] is not None and (x["diff"] > 0 if x["research"] == "hon" else x["diff"] < 0)
        x["confirmed"] = bool(same and x["p_one_holm"] < 0.05)
    out = {"from": st["from"], "data_end": d["close"].dropna().index[-1].strftime("%Y-%m-%d"), "pairs": check, "describe": fin,
           "confirmed": sum(x["confirmed"] for x in check)}
    _log(log_path, {"command": "price-action --final", "phase": PHASE, "status": "done", "confirmed": out["confirmed"]})
    (out_path or DATA / "results" / "price_action_final.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return out


def run(write: bool = True, n_boot: int = N_BOOT) -> dict:
    """The research run on data up to the registration date: data/results/price_action.json and docs/PRICE_ACTION.md."""
    cfg = spec()
    d = daily()
    f = flags(d, cfg)
    rs = cfg["research"]
    a, b = _ts(rs["from"]), _ts(rs["to"])
    rows = table(d, f, cfg, a, b, n_boot)
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    span = (f.index >= a) & (f.index <= b)
    out = {"run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "git": git,
           "research": {"from": a.strftime("%Y-%m-%d"), "to": b.strftime("%Y-%m-%d")},
           "data_end": d["close"].dropna().index[-1].strftime("%Y-%m-%d"), "n_pairs": len(rows),
           "counts": {v: sum(r["verdict"] == v for r in rows) for v in VERDICT}, "fired": {c: int(f.loc[span, c].sum()) for c in f.columns},
           "rows": rows, "final": final_status(d, cfg)}
    if write:
        (DATA / "results").mkdir(exist_ok=True)
        (DATA / "results" / "price_action.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (ROOT / "docs" / "PRICE_ACTION.md").write_text(markdown(out, cfg), encoding="utf-8", newline="\n")
    return out


def _p(x: float | None) -> str:
    return fmt.DASH if x is None else ("< 0,001" if x < 0.001 else fmt.dec(x, 3))


def _pp(x: float | None, sign: bool = False) -> str:
    return fmt.pct(x, 1, sign)


def markdown(o: dict, cfg: dict) -> str:
    """docs/PRICE_ACTION.md from the result (every number computed, nothing typed by hand)."""
    rows, cnt = o["rows"], o["counts"]
    lab = lambda r: f"{NAMES[r['crit']]} ({r['k']} ngày)"  # noqa: E731
    good, bad = [r for r in rows if r["verdict"] == "hon"], [r for r in rows if r["verdict"] == "kem"]
    near = min(rows, key=lambda r: r["p"] if r["diff"] is not None and r["diff"] > 0 else 2.0)
    L = ["# Price action so với \"một ngày bất kỳ\"", "",
         f"Sinh tự động bằng `python -m bot.cli price-action` lúc {fmt.datetime_vn(o['run_at'])} (mã `{o['git']}`), nến ngày Bitstamp đến "
         f"{fmt.date(o['data_end'])}. Cách làm đăng ký trước trong `config/candidates.yaml` mục `price_action`, lưu git trước khi tính "
         "(xem `docs/REBUILD_LOG.md`). Công cụ tham khảo, không phải lời khuyên đầu tư.", "",
         "## Price action là gì", "",
         "Price action (hành động giá) là cách đọc chính biểu đồ giá, không dùng chỉ báo: giá hay dừng ở đâu (hỗ trợ, kháng cự), "
         "đang đi lên hay xuống (chuỗi đỉnh và đáy), và hình dạng cây nến tại những chỗ đó (pin bar có bóng dài, inside bar nằm gọn "
         "trong nến trước, phá vỡ giả). Người dùng price action tin rằng những hình ảnh này báo trước hướng giá. Ở đây mỗi ý được viết "
         "thành một quy tắc bằng số, rồi đếm xem sau khi quy tắc bật, giá có đi đúng hướng nhiều hơn một ngày bất kỳ hay không.", "",
         "## Kết luận", ""]
    if good:
        L.append(f"- **{len(good)}/{o['n_pairs']} cặp tiêu chí × kỳ hạn đoán đúng hướng nhiều hơn một ngày bất kỳ** (đã hiệu chỉnh Holm, "
                 "cùng chiều ở hai nửa): " + "; ".join(lab(r) for r in good) + ".")
    else:
        L.append(f"- **Không tiêu chí price action nào đoán hướng giá tốt hơn một ngày bất kỳ**: 0/{o['n_pairs']} cặp tiêu chí × kỳ hạn "
                 "hơn mốc sau hiệu chỉnh Holm.")
    if bad:
        L.append(f"- {len(bad)} cặp **kém hơn** một ngày bất kỳ (đoán ngược nhiều hơn, cả hai nửa): " + "; ".join(lab(r) for r in bad) + ".")
    L.append(f"- Chưa có lợi thế: {cnt['chua']} cặp; ít đợt, không kết luận: {cnt['it_dot']} cặp.")
    if near["diff"] is not None and near["diff"] > 0:
        w = near["wilson"]
        L.append(f"- Gần nhất với \"hơn mốc\" là {lab(near)}, xếp loại {VERDICT[near['verdict']].replace('**', '')}. Đúng {_pp(near['hit'])} "
                 f"so với mốc {_pp(near['base'])} ({fmt.num(near['n'])} lần, {near['episodes']} đợt; tính theo đợt chỉ đúng {_pp(near['hit_first'])}, "
                 f"Wilson {_pp(w[0])}–{_pp(w[1])}), p trước hiệu chỉnh {_p(near['p'])}, sau Holm {_p(near['p_holm'])}; nửa đầu "
                 f"{_pp(near['halves'][0]['diff'], True)}, nửa sau {_pp(near['halves'][1]['diff'], True)}.")
    nom = [r for r in rows if r["p"] < 0.05 and r["diff"] is not None]
    L.append(f"- Trước hiệu chỉnh có {len(nom)}/{o['n_pairs']} cặp p < 0,05 ({sum(r['diff'] > 0 for r in nom)} hơn, "
             f"{sum(r['diff'] < 0 for r in nom)} kém mốc). Chỉ do may rủi, {o['n_pairs']} phép thử đã cho khoảng "
             f"{fmt.dec(0.05 * o['n_pairs'], 1)} cặp như vậy, nên chừng đó chưa nói lên lợi thế.")
    sets = [r for r in rows if r["combo"]]
    L.append(f"- Bộ tiêu chí (ít nhất 2 trong 5 tiêu chí cùng hướng), {len(sets)} cặp: "
             + "; ".join(f"{VERDICT[v]} {sum(r['verdict'] == v for r in sets)}" for v in VERDICT if any(r["verdict"] == v for r in sets)) + ".")
    L += ["- \"Mốc\" là tỷ lệ của mọi ngày trong cùng giai đoạn: BTC tăng giá nên một ngày bất kỳ đã có hơn một nửa số lần giá cao hơn "
          "sau k ngày. Tiêu chí tăng phải vượt tỷ lệ đó; tiêu chí giảm phải vượt tỷ lệ giá thấp hơn.",
          "- " + ("Theo đăng ký trước: có cặp hơn mốc, nên có thể đề xuất bộ tiêu chí price action trên trang, nhưng phải hỏi người dùng "
                  "trước khi đưa lên." if good else
                  "Theo đăng ký trước: không có cặp nào hơn mốc, nên **không đưa price action lên trang**; kết quả chỉ ghi ở đây và "
                  "trong `docs/REBUILD_LOG.md`."), "",
          "## Cách kiểm định", "",
          f"- Giai đoạn nghiên cứu: ngày tín hiệu và ngày kết quả từ {fmt.date(o['research']['from'])} đến {fmt.date(o['research']['to'])}. "
          "Nến trước 2016 (từ 08/2011) chỉ dùng để tính ATR, đỉnh và đáy.",
          "- Tín hiệu ở ngày T chỉ dùng nến đến T. Đỉnh / đáy cục bộ cần 5 nến bên phải, nên chỉ được dùng từ khi nến thứ 5 sau nó đóng; "
          "mức hỗ trợ / kháng cự chốt trước nến T (đỉnh / đáy đã biết đến T − 1, so với giá đóng T − 1).",
          "- Kết quả: giá đóng ngày sau k ngày cao hơn (tiêu chí tăng) hoặc thấp hơn (tiêu chí giảm) giá đóng ngày T; bằng nhau là sai.",
          "- Số đợt: tín hiệu cách nhau không quá k ngày gộp thành một đợt (kết quả chồng nhau). Khoảng Wilson 95% tính theo số đợt.",
          f"- Khoảng tin cậy của chênh lệch: bootstrap khối dừng ({N_BOOT} lần, khối trung bình k ngày). p đã hiệu chỉnh Holm trên cả "
          f"{o['n_pairs']} cặp. \"Hơn / kém mốc\" khi p Holm < 0,05 và chênh lệch cùng dấu ở cả hai nửa giai đoạn; dưới {MIN_EPISODES} đợt "
          f"hoặc dưới {MIN_HALF} đợt ở một nửa thì không kết luận.",
          f"- Với {N_BOOT} lần lấy lại, p nhỏ nhất là {_p(2 / N_BOOT)}, sau Holm trên {o['n_pairs']} cặp là {_p(min(1.0, 2 / N_BOOT * o['n_pairs']))}: "
          "một cặp chỉ \"hơn mốc\" khi gần như mọi lần lấy lại đều cho chênh lệch dương. Ngưỡng này tương đương đòi hỏi của hiệu chỉnh "
          "nhiều phép thử, không khắt khe hơn.", "",
          "## Định nghĩa (đăng ký trước)", "",
          f"Mức hỗ trợ / kháng cự: {cfg['levels']}", "",
          "| Tiêu chí | Hướng | Định nghĩa | Số ngày bật (giai đoạn nghiên cứu) |", "|---|---|---|---|"]
    for name, text in {**cfg["criteria"], **cfg["combo"]}.items():
        sgn, _, rule = text.partition(";")
        L.append(f"| {NAMES[name]} | {sgn.strip()} | {rule.strip()} | {fmt.num(o['fired'][name])} |")
    L += ["", "## Từng tiêu chí × kỳ hạn", "",
          "| Tiêu chí | Kỳ hạn | Số lần | Số đợt | Đúng | Đúng theo đợt (Wilson 95%) | Mốc | Chênh lệch (KTC 95%) | p Holm | Nửa đầu / nửa sau | Kết luận |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    order = list(NAMES)
    for r in sorted(rows, key=lambda r: (order.index(r["crit"]), r["k"])):
        w, ci, h = r["wilson"], r["ci"], r["halves"]
        L.append(f"| {NAMES[r['crit']]} | {r['k']} ngày | {fmt.num(r['n'])} | {r['episodes']} | {_pp(r['hit'])} | "
                 f"{_pp(r['hit_first'])} ({_pp(w[0])}–{_pp(w[1])}) | {_pp(r['base'])} | {_pp(r['diff'], True)} "
                 f"({_pp(ci[0], True)} đến {_pp(ci[1], True)}) | {_p(r['p_holm'])} | {_pp(h[0]['diff'], True)} / {_pp(h[1]['diff'], True)} | "
                 f"{VERDICT[r['verdict']]} |")
    fin = o["final"]
    L += ["", "## Đã biết trước, không thử lại", "", cfg["known_before"][:1].upper() + cfg["known_before"][1:] + ".", "",
          "## Giai đoạn kiểm tra cuối mới", "",
          f"- Tín hiệu từ {fmt.date(fin['from'])} (ngày đăng ký). Chỉ chạy một lần bằng `python -m bot.cli price-action --final` khi có ít nhất "
          f"{fin['need']} ngày đã biết kết quả 30 ngày (hiện có {fin['days']}); lệnh ghi vào `experiments/final_runs.log` và từ chối lần chạy thứ hai.",
          "- Chỉ xác nhận các cặp hơn / kém mốc ở giai đoạn nghiên cứu; không có cặp nào thì chỉ báo cáo mô tả.", ""]
    return "\n".join(L)
