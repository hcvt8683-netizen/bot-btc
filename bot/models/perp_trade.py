"""Long/Short with an entry price, a stop-loss and a take-profit on the BTCUSDT perpetual (config/candidates.yaml, section
perp_trade; registered before any number was computed).

A family of 1152 rules: signal (6) × side × entry (now, or a limit order 0.5 ATR away for 6 hours) × stop (0.5–2 ATR)
× target (1–3 R) × max hold (24/72/168 hours). Each rule trades its own account on hourly candles, one position at a time;
a candle that touches both the stop and the target counts as the stop. At the start of every month the rule with the
highest t-statistic of R over its trades closed before that moment is picked (none when t < 2), and one account walks
forward month by month trading only the picked rule: those out-of-sample trades give the verdict. The same procedure on
the 96 always-long / always-short rules is the baseline. Nothing here changes perp_signal.py or its log.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from bot.backtest.metrics import wilson
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.models import perp_signal as ps

LOG = DATA / "perp_trade" / "select_log.csv"
LOG_COLS = ["month", "scope", "rule", "t", "n_train", "version", "logged_at"]
SCOPES = ("tat_ca", "long", "short")   # the pick over all 1152 rules, and the pick within each side
SIGNALS = ("moc", "xu_huong", "pha_vo", "qua_da", "funding_nguoc", "hoi_xu_huong")
SIDES = ("long", "short")
ENTRIES = ("ngay", "cho")
KINDS = ("sl", "tp", "time")          # 0, 1, 2; 3 = limit order not filled (no trade); -1 = outcome not known yet
HOUR = pd.Timedelta(hours=1)
FUNDING_EVERY = pd.Timedelta(hours=8)
START = "2020-01-01"
LOOKBACK, MIN_HIST = 365 * 24, 180 * 24
TREND, ATR_DAYS = 480, 14
FORWARD_FROM = pd.Timestamp("2026-11-03")
NEVER = 1 << 30


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["perp_trade"]


def version(cfg: dict) -> str:
    """Hash of the settings, of this module and of perp_signal.py (candles, funding and percentiles come from it)."""
    code = b"".join((ROOT / "bot" / "models" / f).read_bytes().replace(b"\r\n", b"\n") for f in ("perp_trade.py", "perp_signal.py"))
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def _num(x: float) -> str:
    return f"{x:g}"


@dataclass(frozen=True)
class Rule:
    sig: str
    side: str
    entry: str
    k: float      # stop distance in ATR
    r: float      # target distance in multiples of the stop distance
    h: int        # max hold in hours

    @property
    def id(self) -> str:
        return f"{self.sig}|{self.side}|{self.entry}|{_num(self.k)}|{_num(self.r)}|{self.h}"

    @property
    def combo(self) -> tuple:
        return (self.side, self.entry, self.k, self.r, self.h)

    def as_dict(self) -> dict:
        return {"id": self.id, "sig": self.sig, "side": self.side, "entry": self.entry, "k": self.k, "r": self.r, "h": self.h}


def rules(cfg: dict, signals: tuple[str, ...] = SIGNALS) -> list[Rule]:
    """Every rule in the registered order (signal, side, entry, stop, target, hold): ties go to the earlier one."""
    assert tuple(cfg["signals"]) == SIGNALS
    return [Rule(s, sd, e, float(k), float(r), int(h)) for s in signals for sd in SIDES for e in ENTRIES
            for k in cfg["stop_atr"] for r in cfg["target_r"] for h in cfg["max_hold_hours"]]


def parse(rule_id: str) -> Rule:
    s, sd, e, k, r, h = rule_id.split("|")
    return Rule(s, sd, e, float(k), float(r), int(h))


# ----- features and signals (only data up to t) -----
def features(h: pd.DataFrame, f24: pd.Series) -> pd.DataFrame:
    """ATR, 20-day mean, 20-day range before t, 24-hour return, funding, and their past percentiles, at every close t."""
    c, hi, lo = h["close"], h["high"], h["low"]
    rng = hi.rolling(24, min_periods=24).max() - lo.rolling(24, min_periods=24).min()
    atr = sum(rng.shift(24 * k) for k in range(ATR_DAYS)) / ATR_DAYS / c
    r24 = c / c.shift(24) - 1
    out = pd.DataFrame({"close": c, "atr": atr, "ma": c.rolling(TREND, min_periods=TREND).mean(),
                        "hh": hi.shift(1).rolling(TREND, min_periods=TREND).max(), "ll": lo.shift(1).rolling(TREND, min_periods=TREND).min(),
                        "r24": r24, "f24": f24.reindex(c.index)}, index=c.index)
    for q in (0.1, 0.2, 0.8, 0.9):
        out[f"q{round(q * 100)}"] = ps._past_q(r24, q, LOOKBACK, MIN_HIST)
    for q in (0.2, 0.8):
        out[f"fq{round(q * 100)}"] = ps._past_q(out["f24"], q, LOOKBACK, MIN_HIST)
    return out


def first_decision(F: pd.DataFrame) -> int:
    """All rules start together: the first close with the 24-hour-return and funding percentiles and the ATR known."""
    ok = F[["atr", "q10", "fq20"]].notna().all(axis=1).to_numpy()
    return int(np.argmax(ok)) if ok.any() else len(F)


def signals(F: pd.DataFrame) -> dict[tuple[str, str], np.ndarray]:
    """(signal, side) → fires at t. A comparison with an unknown input is False."""
    c, ma, r24, f24 = (F[k].to_numpy(dtype=float) for k in ("close", "ma", "r24", "f24"))
    q = {k: F[k].to_numpy(dtype=float) for k in ("q10", "q20", "q80", "q90", "fq20", "fq80", "hh", "ll")}
    with np.errstate(invalid="ignore"):
        above, below = c > ma, c <= ma
        out = {("moc", "long"): np.ones(len(F), dtype=bool), ("moc", "short"): np.ones(len(F), dtype=bool),
               ("xu_huong", "long"): above, ("xu_huong", "short"): below,
               ("pha_vo", "long"): c > q["hh"], ("pha_vo", "short"): c < q["ll"],
               ("qua_da", "long"): r24 <= q["q10"], ("qua_da", "short"): r24 >= q["q90"],
               ("funding_nguoc", "long"): f24 <= q["fq20"], ("funding_nguoc", "short"): f24 >= q["fq80"],
               ("hoi_xu_huong", "long"): above & (r24 <= q["q20"]), ("hoi_xu_huong", "short"): below & (r24 >= q["q80"])}
    ok = np.array(F["atr"].notna().to_numpy(), dtype=bool, copy=True)
    ok[:first_decision(F)] = False
    return {k: v & ok for k, v in out.items()}


# ----- outcomes of a trade opened at every t -----
def _windows(x: np.ndarray, J: int) -> np.ndarray:
    """W[t, j−1] = x[t + j] for j = 1..J (NaN past the end)."""
    return np.lib.stride_tricks.sliding_window_view(np.r_[x[1:], np.full(J, np.nan)], J)[:len(x)]


def _first(m: np.ndarray, start: np.ndarray) -> np.ndarray:
    """First column j (1-based) ≥ start where m is True, NEVER when none."""
    m = m & (np.arange(1, m.shape[1] + 1)[None, :] >= start[:, None])
    return np.where(m.any(axis=1), m.argmax(axis=1) + 1, NEVER)


class Book:
    """Candles, funding and the outcome arrays of every (side, entry, stop, target, hold) for a trade opened at each t."""

    def __init__(self, h: pd.DataFrame, rate: pd.Series, last_f: pd.Timestamp | None, cfg: dict):
        self.h, self.cfg, self.index = h, cfg, h.index
        self.N = len(h)
        self.c = h["close"].to_numpy(dtype=float)
        self.cum = np.r_[rate.reindex(h.index).fillna(0.0).cumsum().to_numpy()]
        self.f_ok = (h.index < last_f + FUNDING_EVERY) if last_f is not None else np.zeros(self.N, dtype=bool)
        self.cost = 2 * (cfg["costs"]["fee"] + cfg["costs"]["slippage"])
        self.nb = int(cfg["limit_bars"])
        self.J = self.nb + max(int(x) for x in cfg["max_hold_hours"])
        self._oc: dict[tuple, dict] = {}
        self._hit: dict[tuple, dict] = {}
        self._sl: dict[tuple, np.ndarray] = {}
        self._fills: dict[tuple, tuple] = {}

    def prepare(self, atr: np.ndarray) -> None:
        self.atr = atr
        self.L, self.H = _windows(self.h["low"].to_numpy(dtype=float), self.J) / self.c[:, None], \
            _windows(self.h["high"].to_numpy(dtype=float), self.J) / self.c[:, None]

    def _fill(self, side: str, entry: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Entry price (relative to the close at t), fill column (0 = at the close of t, NEVER = not filled) and whether
        an unfilled order is known to have expired."""
        N, t = self.N, np.arange(self.N)
        if entry == "ngay":
            return np.ones(N), np.zeros(N, dtype=np.int64), np.ones(N, dtype=bool)
        d = float(self.cfg["limit_atr"]) * self.atr
        e = 1 - d if side == "long" else 1 + d
        with np.errstate(invalid="ignore"):
            hit = (self.L[:, :self.nb] <= e[:, None]) if side == "long" else (self.H[:, :self.nb] >= e[:, None])
        f = np.where(hit.any(axis=1), hit.argmax(axis=1) + 1, NEVER)
        return e, f, (t + self.nb < N) & ~np.isnan(self.L[:, self.nb - 1])

    def _hits(self, side: str, entry: str, k: float, r: float) -> dict:
        """Fill, stop and target levels (relative to the close at t) and the first candle touching each, for one side,
        entry, stop and target (any hold is then cheap). Cached: the stop hits per stop, the target hits per target."""
        key = (side, entry, float(k), float(r))
        if key in self._hit:
            return self._hit[key]
        if (side, entry) not in self._fills:
            self._fills[(side, entry)] = self._fill(side, entry)
        e, f, expired_known = self._fills[(side, entry)]
        filled = f < NEVER
        fz = np.where(filled, f, 0)
        sgn = 1.0 if side == "long" else -1.0
        s = float(k) * self.atr
        sl_lvl, tp_lvl = e * (1 - sgn * s), e * (1 + sgn * float(r) * s)
        if (side, entry, float(k)) not in self._sl:
            with np.errstate(invalid="ignore"):
                self._sl[(side, entry, float(k))] = _first(self.L <= sl_lvl[:, None] if side == "long" else self.H >= sl_lvl[:, None],
                                                           np.where(filled, np.maximum(fz, 1), NEVER)).astype(np.int32)
        with np.errstate(invalid="ignore"):
            tp = _first(self.H >= tp_lvl[:, None] if side == "long" else self.L <= tp_lvl[:, None], np.where(filled, fz + 1, NEVER)).astype(np.int32)
        self._hit[key] = {"e": e, "fz": fz, "filled": filled, "expired_known": expired_known, "sgn": sgn, "s": s,
                          "sl_lvl": sl_lvl, "tp_lvl": tp_lvl, "sl": self._sl[(side, entry, float(k))], "tp": tp}
        return self._hit[key]

    def _finish(self, x: dict, H: int) -> dict:
        """Outcome of a trade opened at every t with max hold H: kind, exit position, net gain and R."""
        N, t = self.N, np.arange(self.N)
        e, fz, filled, sgn, sl, tp = x["e"], x["fz"], x["filled"], x["sgn"], x["sl"], x["tp"]
        b = fz + int(H)
        is_tp = filled & (tp < sl) & (tp <= b)
        is_sl = filled & ~is_tp & (sl <= b)
        col = np.where(is_tp, tp, np.where(is_sl, sl, b))
        pos = t + col
        inside = pos < N
        pc = np.where(inside, pos, 0)
        c_end = np.where(inside, self.c[pc], np.nan)
        out_px = np.where(is_tp, x["tp_lvl"], np.where(is_sl, x["sl_lvl"], c_end / self.c))
        gross = sgn * (out_px / e - 1)
        fund = self.cum[pc] - self.cum[np.minimum(t + np.maximum(fz - 1, 0), N - 1)]
        net = gross - self.cost - sgn * fund
        known = inside & ~np.isnan(c_end) & self.f_ok[pc] & ~np.isnan(self.atr)
        kind = np.where(is_tp, 1, np.where(is_sl, 0, 2))
        kind = np.where(filled, np.where(known, kind, -1), np.where(x["expired_known"], 3, -1))
        exit_pos = np.where(filled, pos, t + self.nb)
        return {"kind": kind.astype(np.int8), "exit": exit_pos.astype(np.int32), "net": np.where(kind >= 0, net, np.nan),
                "R": np.where(kind >= 0, net / x["s"], np.nan)}

    def oc(self, combo: tuple, keep: bool = True) -> dict:
        """Outcome arrays of (side, entry, stop, target, hold); keep=False for a one-off hold (the page's hold view)."""
        if combo in self._oc:
            return self._oc[combo]
        side, entry, k, r, H = combo
        out = self._finish(self._hits(side, entry, k, r), int(H))
        if keep:
            self._oc[combo] = out
        return out


# ----- one account trading one rule -----
def _next_pos(mask: np.ndarray) -> list[int]:
    """nxt[p] = first position ≥ p where mask is True (len(mask) when none)."""
    n = len(mask)
    nxt = np.where(np.r_[mask, True], np.arange(n + 1), n + 1)
    return np.minimum.accumulate(nxt[::-1])[::-1].tolist()


def walk(sig: np.ndarray, oc: dict, start: int = 0, stop: int | None = None, nxt: list[int] | None = None) -> tuple[list[int], int, bool]:
    """Positions of the trades one account takes on signals in [start, stop), one at a time. Returns (positions, the
    position from which the account is free again, whether it ran into an outcome not known yet)."""
    n = len(sig)
    stop = n if stop is None else stop
    nxt = nxt if nxt is not None else _next_pos(sig)
    kind, ex = oc["kind"], oc["exit"]
    out, cur = [], start
    while cur < stop:
        i = nxt[cur]
        if i >= stop:
            break
        k = int(kind[i])
        if k < 0:
            return out, NEVER, True
        if k != 3:
            out.append(i)
        cur = int(ex[i])
    return out, max(cur, start), False


def trade_table(pos: list[int], oc: dict, book: Book, rule: Rule) -> pd.DataFrame:
    p = np.asarray(pos, dtype=np.int64)
    ex = oc["exit"][p].astype(np.int64)
    return pd.DataFrame({"t": book.index[p], "exit_t": book.index[ex], "exit_pos": ex, "kind": oc["kind"][p].astype(int),
                         "net": oc["net"][p], "R": oc["R"][p], "hours": (ex - p).astype(int), "rule": rule.id})


# ----- statistics -----
def trade_stats(tr: pd.DataFrame) -> dict:
    n = len(tr)
    if not n:
        return {"n": 0}
    win = tr["net"].to_numpy() > 0
    R = tr["R"].to_numpy()
    cum = np.cumsum(R)
    dd = float(np.max(np.maximum.accumulate(np.r_[0.0, cum])[1:] - cum)) if n else 0.0
    sd = float(R.std(ddof=1)) if n > 1 else float("nan")
    kinds = tr["kind"].to_numpy()
    return {"n": n, "p": float(win.mean()), "ci": list(wilson(int(win.sum()), n)), "p_tp": float((kinds == 1).mean()),
            "p_sl": float((kinds == 0).mean()), "p_time": float((kinds == 2).mean()),
            "p_time_win": float(((kinds == 2) & win).mean()), "mean": float(tr["net"].mean()), "meanR": float(R.mean()),
            "sumR": float(cum[-1]), "t": float(R.mean() / (sd / np.sqrt(n))) if n > 1 and sd > 0 else None, "maxdd": dd,
            "hours": float(tr["hours"].mean())}


def boot_months(tr: pd.DataFrame, months: list[pd.Timestamp], n: int = 10000, seed: int = 0) -> list[float | None]:
    """95% interval of the mean R by resampling whole months (months without a trade included)."""
    if tr.empty:
        return [None, None]
    m = tr["t"].dt.to_period("M")
    keys = [x.to_period("M") for x in months]
    s = tr.groupby(m)["R"].sum().reindex(keys).fillna(0.0).to_numpy()
    c = tr.groupby(m)["R"].size().reindex(keys).fillna(0).to_numpy()
    idx = np.random.default_rng(seed).integers(0, len(keys), size=(n, len(keys)))
    num, den = s[idx].sum(axis=1), c[idx].sum(axis=1)
    mean = num[den > 0] / den[den > 0]
    return [float(np.quantile(mean, 0.025)), float(np.quantile(mean, 0.975))]


# ----- every rule on its own, then the monthly pick -----
def standalone(book: Book, sigs: dict, rs: list[Rule]) -> dict[str, pd.DataFrame]:
    nxt: dict[tuple, list[int]] = {}
    out = {}
    for r in rs:
        key = (r.sig, r.side)
        if key not in nxt:
            nxt[key] = _next_pos(sigs[key])
        oc = book.oc(r.combo)
        pos, _, _ = walk(sigs[key], oc, nxt=nxt[key])
        out[r.id] = trade_table(pos, oc, book, r)
    return out


def pick(trades: dict[str, pd.DataFrame], rs: list[Rule], at_pos: int, cfg: dict) -> tuple[Rule | None, float | None, int, Rule | None]:
    """Rule with the highest t over its trades closed by position `at_pos` (the selection time), and whether it passes
    the gate. Returns (picked rule or None when below the gate, its t, its trade count, the best rule regardless)."""
    sel = cfg["select"]
    best, best_t, best_n = None, -np.inf, 0
    for r in rs:
        tr = trades[r.id]
        k = int(np.searchsorted(tr["exit_pos"].to_numpy(), at_pos, side="right"))
        if k < int(sel["min_trades"]):
            continue
        R = tr["R"].to_numpy()[:k]
        sd = R.std(ddof=1)
        t = R.mean() / (sd / np.sqrt(k)) if sd > 0 else -np.inf
        if t > best_t:
            best, best_t, best_n = r, float(t), k
    if best is None:
        return None, None, 0, None
    return (best if best_t >= float(sel["gate_t"]) else None), best_t, best_n, best


def months_of(book: Book, cfg: dict) -> list[pd.Timestamp]:
    last = book.index[-1]
    return list(pd.date_range(pd.Timestamp(str(cfg["select"]["first"])), last, freq="MS"))


def walk_forward(book: Book, sigs: dict, plan: dict[pd.Timestamp, Rule | None], start: pd.Timestamp | None = None) -> tuple[pd.DataFrame, dict]:
    """One account month by month, trading only the rule planned for that month. Returns the trades and, per month,
    how many trades and the R they made."""
    idx = book.index
    months = sorted(plan)
    cur = int(idx.searchsorted(start)) if start is not None else 0
    rows, per = [], {}
    for i, m in enumerate(months):
        a = int(idx.searchsorted(m))
        b = int(idx.searchsorted(months[i + 1])) if i + 1 < len(months) else len(idx)
        r = plan[m]
        per[m] = {"rule": r.id if r else None, "n": 0, "sumR": 0.0}
        if r is None:
            continue
        oc = book.oc(r.combo)
        pos, free, stuck = walk(sigs[(r.sig, r.side)], oc, start=max(a, cur), stop=b)
        t = trade_table(pos, oc, book, r)
        rows.append(t)
        per[m].update(n=len(t), sumR=float(t["R"].sum()))
        if stuck:
            break
        cur = free
    tr = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        {"t": pd.DatetimeIndex([]), "exit_t": pd.DatetimeIndex([]), "exit_pos": np.zeros(0, dtype=np.int64), "kind": np.zeros(0, dtype=int),
         "net": np.zeros(0), "R": np.zeros(0), "hours": np.zeros(0, dtype=int), "rule": np.zeros(0, dtype=object)})
    return tr, per


def selection(book: Book, trades: dict, rs: list[Rule], cfg: dict) -> dict[pd.Timestamp, dict]:
    out = {}
    for m in months_of(book, cfg):
        at = int(book.index.searchsorted(m, side="right")) - 1     # last close ≤ m
        r, t, n, best = pick(trades, rs, at, cfg)
        out[m] = {"rule": r, "t": t, "n": n, "best": best}
    return out


def verdict(stats: dict, boot: list, halves: list[dict], cfg: dict) -> bool:
    return bool(stats.get("n", 0) >= 100 and boot[0] is not None and boot[0] > 0
                and all(h.get("n", 0) and h["meanR"] > 0 for h in halves))


def checklist_static(side: dict, cur: dict) -> dict:
    """Criteria c1–c4 of one side (known at the start of the month); c5 (signal on) and c6 (liquidation beyond the
    stop) depend on the moment and the leverage, so the page checks them."""
    h = side["halves"]
    return {"c1": cur["rule"] is not None, "c2": side["n"] >= 100, "c3": side["boot"][0] is not None and side["boot"][0] > 0,
            "c4": all(x.get("n", 0) and x["meanR"] > 0 for x in h)}


def checklist_history(wf: pd.DataFrame, sel: dict, months: list[pd.Timestamp], cfg: dict) -> dict:
    """The checklist applied in the past: at each month start c1–c4 from what was known then (c2–c4 on this side's
    walk-forward trades closed by that moment, halves split at the middle of those months); a trade happens only when
    the signal is on (c5 counts when the month had a trade) and c6 holds at 1x. The month's trades grouped by how many
    criteria were met."""
    rows = []
    for i, m in enumerate(months):
        past = wf[wf["exit_t"] <= m]
        pm = months[:i] or [m]
        if len(past):
            half = pm[len(pm) // 2]
            side = {**trade_stats(past), "boot": boot_months(past, pm), "halves": [trade_stats(past[past["t"] < half]), trade_stats(past[past["t"] >= half])]}
        else:
            side = {"n": 0, "boot": [None, None], "halves": [{"n": 0}, {"n": 0}]}
        c = checklist_static(side, {"rule": sel[m]["rule"]})
        end = months[i + 1] if i + 1 < len(months) else pd.Timestamp.max
        tm = wf[(wf["t"] >= m) & (wf["t"] < end)]
        rows.append({"score": sum(c.values()) + 1 + (1 if len(tm) else 0), "n": len(tm), "win": int((tm["net"] > 0).sum()), "R": float(tm["R"].sum())})
    df = pd.DataFrame(rows)
    out = []
    for sc, g in df.groupby("score"):
        n = int(g["n"].sum())
        out.append({"score": int(sc), "months": len(g), "n": n, "p": float(g["win"].sum() / n) if n else None,
                    "ci": list(wilson(int(g["win"].sum()), n)) if n else [None, None], "meanR": float(g["R"].sum() / n) if n else None})
    return {"by_score": out, "max": int(df["score"].max()) if len(df) else 0, "full": int((df["score"] == 6).sum())}


def summary(tr: pd.DataFrame, months: list[pd.Timestamp], cfg: dict) -> dict:
    half = months[len(months) // 2]
    halves = [trade_stats(tr[tr["t"] < half]), trade_stats(tr[tr["t"] >= half])]
    st, bt = trade_stats(tr), boot_months(tr, months)
    return {**st, "boot": bt, "halves": halves, "split": half.strftime("%Y-%m-%d"), "edge": verdict(st, bt, halves, cfg)}


def hold_view(book: Book, sigs: dict, rule: Rule, hours: list[int]) -> dict:
    """The same signal, side, entry, stop and target with every hold the page offers (descriptive, in-sample), columnwise."""
    nxt = _next_pos(sigs[(rule.sig, rule.side)])
    cols: dict[str, list] = {k: [] for k in ("h", "n", "p", "lo", "hi", "p_tp", "p_sl", "p_tw", "mean", "meanR", "hours")}
    for H in hours:
        r = Rule(rule.sig, rule.side, rule.entry, rule.k, rule.r, int(H))
        oc = book.oc(r.combo, keep=False)
        pos, _, _ = walk(sigs[(r.sig, r.side)], oc, nxt=nxt)
        st = trade_stats(trade_table(pos, oc, book, r))
        cols["h"].append(int(H))
        cols["n"].append(st["n"])
        for k, src in (("p", "p"), ("p_tp", "p_tp"), ("p_sl", "p_sl"), ("p_tw", "p_time_win"), ("mean", "mean"), ("meanR", "meanR"), ("hours", "hours")):
            cols[k].append(st.get(src))
        cols["lo"].append(st["ci"][0] if st["n"] else None)
        cols["hi"].append(st["ci"][1] if st["n"] else None)
    return cols


# ----- now -----
def now_state(F: pd.DataFrame, sigs: dict) -> dict:
    T = F["close"].dropna().index[-1]
    i = int(F.index.get_loc(T))
    row = F.iloc[i]
    val = lambda k: None if pd.isna(row[k]) else float(row[k])  # noqa: E731
    fired = {f"{s}|{sd}": (None if s == "funding_nguoc" and val("f24") is None else bool(sigs[(s, sd)][i])) for s, sd in sigs}
    return {"anchor": T.strftime("%Y-%m-%d %H:%M"), "close": val("close"), "atr": val("atr"), "ma": val("ma"), "hh": val("hh"),
            "ll": val("ll"), "r24": val("r24"), "f24": val("f24"), "signals": fired}


def thresholds(F: pd.DataFrame) -> dict:
    """Percentiles over the 365 days up to the last row (inclusive), for the state the page computes after it."""
    def last(s: pd.Series, q: float) -> float | None:
        w = s.iloc[-LOOKBACK:].dropna()
        return float(w.quantile(q)) if len(w) >= MIN_HIST else None
    return {"r24": {f"q{round(q * 100)}": last(F["r24"], q) for q in (0.1, 0.2, 0.8, 0.9)},
            "f24": {f"q{round(q * 100)}": last(F["f24"], q) for q in (0.2, 0.8)}}


# ----- everything -----
def build(cfg: dict, end: pd.Timestamp | None = None) -> dict:
    h = ps.hourly({"start": START}, end)
    rate, mark, last_f = ps.funding(h.index, end)
    f24 = ps.funding_24h(rate, mark, last_f)
    F = features(h, f24)
    book = Book(h, rate, last_f, cfg)
    book.prepare(F["atr"].to_numpy(dtype=float))
    return {"h": h, "F": F, "book": book, "sigs": signals(F), "last_f": last_f}


def run(write: bool = True, end: pd.Timestamp | None = None) -> dict:
    """Everything the page shows (window LT); `end` cuts the data (frozen fixtures for the page tests)."""
    cfg = spec()
    b = build(cfg, end)
    book, sigs = b["book"], b["sigs"]
    rs_all, rs_base = rules(cfg), rules(cfg, ("moc",))
    trades = standalone(book, sigs, rs_all)
    sel = selection(book, trades, rs_all, cfg)
    sel_b = selection(book, trades, rs_base, cfg)
    months = sorted(sel)
    wf, per = walk_forward(book, sigs, {m: v["rule"] for m, v in sel.items()})
    wb, per_b = walk_forward(book, sigs, {m: v["rule"] for m, v in sel_b.items()})
    side_out, side_ids = {}, []
    for sd in SIDES:
        rs_sd = [r for r in rs_all if r.side == sd]
        sel_sd = selection(book, trades, rs_sd, cfg)
        w_sd, per_sd = walk_forward(book, sigs, {m: v["rule"] for m, v in sel_sd.items()})
        c = sel_sd[months[-1]]
        cur_sd = {"rule": c["rule"].as_dict() if c["rule"] else None, "best": c["best"].as_dict() if c["best"] else None, "t": c["t"], "n_train": c["n"]}
        summ = {**summary(w_sd, months, cfg), "stand_aside": sum(sel_sd[m]["rule"] is None for m in months)}
        acc_sd = np.cumsum([per_sd[m]["sumR"] for m in months])
        side_out[sd] = {**summ, "current": cur_sd, "check": checklist_static(summ, cur_sd), "curve": [round(float(x), 4) for x in acc_sd],
                        "picks": [per_sd[m]["rule"] for m in months], "past": checklist_history(w_sd, sel_sd, months, cfg)}
        side_ids += [x["id"] for x in (cur_sd["rule"], cur_sd["best"]) if x]
    hours = [int(x) for x in cfg["hold_view"]["hours"]]
    cur = sel[months[-1]]
    shown = cur["rule"] or cur["best"]
    by_rule = {r.id: trade_stats(trades[r.id]) for r in rs_all}
    top = sorted(by_rule, key=lambda k: -(by_rule[k].get("t") or -np.inf))
    per_signal = []
    for s in SIGNALS:
        for sd in SIDES:
            best = max((r for r in rs_all if r.sig == s and r.side == sd), key=lambda r: by_rule[r.id].get("t") or -np.inf)
            per_signal.append(best.id)
    keep = list(dict.fromkeys(top[:10] + per_signal + ([shown.id] if shown else []) + side_ids))
    cum, cum_b, acc, acc_b = [], [], 0.0, 0.0
    for m in months:
        acc += per[m]["sumR"]
        acc_b += per_b[m]["sumR"]
        cum.append(round(acc, 4))
        cum_b.append(round(acc_b, 4))
    out = {
        "version": version(cfg), "rules_n": len(rs_all), "base_n": len(rs_base), "costs": cfg["costs"],
        "mmr": ps.spec()["leverage"]["mmr"], "limit_atr": cfg["limit_atr"], "limit_bars": cfg["limit_bars"],
        "gate_t": cfg["select"]["gate_t"], "min_trades": cfg["select"]["min_trades"], "hold_hours": hours,
        "data": {"from": book.index[first_decision(b["F"])].strftime("%Y-%m-%d %H:%M"), "to": book.index[-1].strftime("%Y-%m-%d %H:%M"),
                 "funding_last": b["last_f"].strftime("%Y-%m-%d %H:%M") if b["last_f"] is not None else None},
        "wf": {**summary(wf, months, cfg), "from": months[0].strftime("%Y-%m-%d"), "months": len(months),
               "stand_aside": sum(sel[m]["rule"] is None for m in months)},
        "base": {**summary(wb, months, cfg), "stand_aside": sum(sel_b[m]["rule"] is None for m in months)},
        "sides": side_out, "checklist": list(cfg["checklist"]["items"]),
        "curve": {"months": [m.strftime("%Y-%m") for m in months], "wf": cum, "base": cum_b},
        "history": [{"month": m.strftime("%Y-%m"), "rule": per[m]["rule"], "t": sel[m]["t"], "n": per[m]["n"], "sumR": per[m]["sumR"]} for m in months],
        "current": {"month": months[-1].strftime("%Y-%m"), "rule": cur["rule"].as_dict() if cur["rule"] else None,
                    "best": cur["best"].as_dict() if cur["best"] else None, "t": cur["t"], "n_train": cur["n"],
                    "oos": trade_stats(wf[wf["rule"] == shown.id]) if shown is not None and not wf.empty else {"n": 0}},
        "rules": {k: {**parse(k).as_dict(), **by_rule[k], "oos": trade_stats(wf[wf["rule"] == k]) if not wf.empty else {"n": 0},
                      "holds": hold_view(book, sigs, parse(k), hours)} for k in keep},
        "top": top[:10], "per_signal": per_signal,
        "now": now_state(b["F"], sigs), "thresholds": thresholds(b["F"]),
    }
    out["log"] = score_log(book, sigs, out["version"])
    if write:
        (DATA / "results").mkdir(exist_ok=True)
        (DATA / "results" / "perp_trade.json").write_text(json.dumps(ps._round(out, 6), ensure_ascii=False, separators=(",", ":"), default=str),
                                                         encoding="utf-8")
    out["_sel"], out["_trades"], out["_wf"] = sel, trades, wf
    return out


# ----- forward log (new final test period from 03/11/2026) -----
def read_log(path: Path = LOG) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def log_month(res: dict, now: pd.Timestamp, path: Path = LOG) -> list[dict]:
    """Append this month's picks (all rules, long only, short only) once per version. Never rewrites and never
    back-fills a past month."""
    path = Path(path)
    v, month = res["version"], res["current"]["month"]
    if month != now.strftime("%Y-%m") or any(r["month"] == month and r["version"] == v for r in read_log(path)):
        return []
    picks = [("tat_ca", res["current"])] + [(sd, res["sides"][sd]["current"]) for sd in SIDES if sd in res.get("sides", {})]
    rows = [{"month": month, "scope": sc, "rule": c["rule"]["id"] if c["rule"] else "", "t": "" if c["t"] is None else f"{c['t']:.4f}",
             "n_train": c["n_train"], "version": v, "logged_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")} for sc, c in picks]
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLS)
        if new:
            w.writeheader()
        w.writerows(rows)
    return rows


def score_log(book: Book, sigs: dict, v: str, path: Path = LOG) -> dict:
    """Trades from 03/11/2026 of the picks logged for this version (per scope), recomputed from the data."""
    out = {}
    for sc in SCOPES:
        rows = [r for r in read_log(path) if r["version"] == v and r.get("scope") == sc]
        if not rows:
            out[sc] = {"months": 0, "n": 0}
            continue
        logged = {pd.Timestamp(r["month"] + "-01"): (parse(r["rule"]) if r["rule"] else None) for r in rows}
        plan = {m: logged.get(m) for m in pd.date_range(min(logged), book.index[-1], freq="MS")}   # a month not logged: no trades
        tr, _ = walk_forward(book, sigs, plan, start=FORWARD_FROM)
        out[sc] = {"months": len(rows), **trade_stats(tr[tr["t"] >= FORWARD_FROM])}
    return out


def utc_now() -> pd.Timestamp:
    return pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
