"""Layers B (timing overlay, Group B) and C (risk overlay, Group C), section 4.2.

One fixed template for every Group B feature, so nothing is tuned per feature: the point-in-time percentile over
the trailing 104 weekly values (min 52) → f_B = 1.25 on the cheap fifth, 0.75 on the expensive fifth, else 1.
Events (capitulation) give 1.25 for 4 weeks. A rule with fewer than 10 independent episodes is forced to 1.0.
m_t = clip(m_A × f_B × f_C, 0.25, 2.0).
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from bot.config import CONFIG, load_yaml
from bot.data import pit_store
from bot.data.fetchers import events as ev
from bot.features import normalize
from bot.features.panel import decision_time

F_LO, F_HI = 0.75, 1.25
MIN_EPISODES = 10
GROUP_B = {  # name: cheap_when
    "funding_7d": "low", "basis_ann": "low", "stable_supply_30d": "high", "fng": "low", "fng_momentum": "high",
    "rsi_14w": "low", "rsi_14d": "low", "capitulation": "event",
}
DISPLAY_ONLY = {"oi_to_mcap": "Binance chỉ giữ 30 ngày; đang ghi tiếp từ 28/10/2026, chưa đủ để kiểm định",
                "etf_flow_5d": "nguồn tùy chọn, chưa bật", "vol_rel_20w": "chỉ là bối cảnh (khối lượng cao ở cả đỉnh lẫn đáy)"}


def _asof(daily: pd.Series, avail: pd.Series, dates: pd.DatetimeIndex) -> np.ndarray:
    """Value of a daily series at each decision time, using only rows published by then."""
    pub = pd.DataFrame({"available_at": avail.to_numpy(), "v": daily.to_numpy()}).dropna().sort_values("available_at")
    j = pd.merge_asof(pd.DataFrame({"t": decision_time(dates)}), pub, left_on="t", right_on="available_at", direction="backward")
    stale = (j["t"] - j["available_at"]) > pd.Timedelta(days=10)
    return j["v"].where(~stale).to_numpy(dtype=float)


def _daily(source: str, col: str, freq: str = "D") -> tuple[pd.Series, pd.Series]:
    h = pit_store.with_available_at(pit_store.load_history(source), source, freq)
    h = h.set_index(pit_store.key_of(h)).sort_index()
    return h[col], h["available_at"]


def quarter_expiries(start: dt.date, end: dt.date) -> list[pd.Timestamp]:
    out = []
    for y in range(start.year, end.year + 2):
        for m in (3, 6, 9, 12):
            d = dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
            d -= dt.timedelta(days=(d.weekday() - 4) % 7)
            out.append(pd.Timestamp(d))
    return out


def weekly_group_b(dates: pd.DatetimeIndex, price_daily: pd.Series, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Raw Group B values at decision times (each from its own source and publication lag)."""
    cut = (lambda s: s[s.index <= end]) if end is not None else (lambda s: s)
    out = pd.DataFrame(index=dates)
    fr = pit_store.load_history("binance_funding")
    if len(fr):
        day = fr.assign(date=fr["time"].dt.normalize()).groupby("date")["funding_rate"].mean().asfreq("D")
        f7 = cut(day.rolling(7, min_periods=5).mean())
        out["funding_7d"] = _asof(f7, pd.Series(f7.index + pd.Timedelta(days=1), index=f7.index), dates)
    fut, fa = _daily("binance_basis", "fut_close")
    spot, _ = _daily("binance_spot", "close")
    if len(fut) and len(spot):
        b = pd.concat([fut, spot], axis=1, keys=["f", "s"]).dropna()
        exp = quarter_expiries(b.index.min().date(), b.index.max().date())
        nxt = np.array([min((e for e in exp if e >= d), default=pd.NaT) for d in b.index])
        days = pd.Series((pd.DatetimeIndex(nxt) - b.index).days, index=b.index).astype(float)
        ann = ((b["f"] / b["s"] - 1) * 365 / days).where(days >= 14)
        ann = cut(ann)
        out["basis_ann"] = _asof(ann, fa.reindex(ann.index), dates)
    st, sa = _daily("stablecoins", "stable_usd")
    if len(st):
        st = cut(st.asfreq("D").ffill())
        out["stable_supply_30d"] = _asof(st / st.shift(30) - 1, sa.reindex(st.index).ffill(), dates)
    fg, fga = _daily("fng", "fng")
    if len(fg):
        fg = cut(fg)
        out["fng"] = _asof(fg, fga.reindex(fg.index), dates)
        out["fng_momentum"] = out["fng"]
    p = cut(price_daily.asfreq("D").ffill())
    pa = pd.Series(p.index + pd.Timedelta(days=2), index=p.index)  # Coin Metrics lag
    out["rsi_14d"] = _asof(rsi(p, 14), pa, dates)
    out["rsi_14w"] = _asof(rsi(p, 14, step=7), pa, dates)
    qv, qa = _daily("binance_spot", "quote_volume")
    if len(qv):
        qv = cut(qv.asfreq("D"))
        wk = qv.rolling(7, min_periods=6).sum()
        rel = wk / wk.shift(7).rolling(140, min_periods=70).mean()  # previous 20 weeks
        chg = p / p.shift(7) - 1
        cap = ((chg.reindex(rel.index) < -0.10) & (rel > 2)).astype(float)
        cap4 = cap.rolling(28, min_periods=1).max()  # event seen within the last 4 weeks
        a = pd.Series(qv.index + pd.Timedelta(days=1), index=qv.index)
        out["capitulation"] = _asof(cap4.where(rel.notna()), a, dates)
        out["vol_rel_20w"] = _asof(rel, a, dates)
    return out


def rsi(p: pd.Series, n: int, step: int = 1) -> pd.Series:
    d = p - p.shift(step)
    up = d.clip(lower=0).rolling(n * step, min_periods=n * step).apply(lambda x: x[step - 1::step].sum() if step > 1 else x.sum(), raw=True)
    dn = (-d).clip(lower=0).rolling(n * step, min_periods=n * step).apply(lambda x: x[step - 1::step].sum() if step > 1 else x.sum(), raw=True)
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def rule(raw: pd.Series, cheap_when: str) -> np.ndarray:
    """Fixed template → f in {0.75, 1, 1.25}; NaN (no data) → 1."""
    if cheap_when == "event":
        return np.where(raw.to_numpy() > 0, F_HI, 1.0)
    pct = normalize.pit_percentile(raw, window=104, min_hist=52)
    cheap = normalize.cheapness(pct, cheap_when).to_numpy()
    return np.where(np.isnan(cheap), 1.0, np.where(cheap >= 0.8, F_HI, np.where(cheap <= 0.2, F_LO, 1.0)))


def episodes(f: np.ndarray) -> int:
    """Independent episodes: runs of consecutive non-neutral weeks with the same value."""
    f = np.asarray(f)
    act = f != 1.0
    starts = act & ~np.r_[False, act[:-1] & (f[1:] == f[:-1])]
    return int(starts.sum())


def gate(f: np.ndarray) -> np.ndarray:
    """Rules with fewer than MIN_EPISODES independent episodes are display only (f = 1)."""
    return f if episodes(f) >= MIN_EPISODES else np.ones_like(f)


def combine(m_a: np.ndarray, *fs: np.ndarray, lo: float = 0.25, hi: float = 2.0) -> np.ndarray:
    m = np.asarray(m_a, dtype=float).copy()
    for f in fs:
        m = m * np.clip(f, F_LO, F_HI) if f is not None else m
    return np.clip(m, lo, hi)


# ---------------------------------------------------------------- layer C
def load_events(end: pd.Timestamp | None = None) -> list[pd.Timestamp]:
    """FOMC, CPI, PCE times (UTC) from config/events.yaml plus monthly options expiry by rule."""
    y = load_yaml(CONFIG / "events.yaml")
    times = [pd.Timestamp(t.replace("Z", "")) for k in ("fomc", "cpi", "pce") for t in (y.get(k) or [])]
    times += [pd.Timestamp(t.replace("Z", "")) for t in ev.options_expiry(dt.date(2011, 1, 1), dt.date.today() + dt.timedelta(days=60))]
    return sorted(t for t in times if end is None or t <= end + pd.Timedelta(days=3))


def event_delay(dates: pd.DatetimeIndex, close: pd.Series, events: list[pd.Timestamp], hours: int = 48) -> tuple[np.ndarray, np.ndarray]:
    """Fill price per decision week: the planned buy (decision day close) is moved to the close of the first day after any
    event in the next `hours`. Returns (fill prices, delayed flag). The buy is never cancelled."""
    c = close.asfreq("D").ffill()
    ev_arr = np.array(sorted(events), dtype="datetime64[ns]")
    fill, delayed = np.empty(len(dates)), np.zeros(len(dates), dtype=bool)
    for k, d in enumerate(dates):
        t = d + pd.Timedelta(hours=1)
        lo, hi = np.searchsorted(ev_arr, np.datetime64(t)), np.searchsorted(ev_arr, np.datetime64(t + pd.Timedelta(hours=hours)), "right")
        day = d
        if hi > lo:
            day = pd.Timestamp(ev_arr[hi - 1]).normalize() + pd.Timedelta(days=1)
            delayed[k] = True
        fill[k] = c.get(day, c.iloc[-1] if day > c.index[-1] else np.nan)
    return fill, delayed


def macro_cap(dates: pd.DatetimeIndex, end: pd.Timestamp | None = None) -> np.ndarray:
    """Candidate rule: USD and real yields both rising fast (13-week change in their top fifth over 3 years) and Nasdaq
    below its 200-day average → cap m at 1.25. Returns the cap per week (np.inf when inactive)."""
    usd, ua = _daily("fred_DTWEXBGS", "usd_broad")
    ry, ra = _daily("fred_DFII10", "real_yield_10y")
    nq, na = _daily("fred_NASDAQCOM", "nasdaq")
    if end is not None:
        usd, ry, nq = usd[usd.index <= end], ry[ry.index <= end], nq[nq.index <= end]
    u = pd.Series(_asof(usd.asfreq("D").ffill(), ua.reindex(usd.asfreq("D").index).ffill(), dates), index=dates)
    r = pd.Series(_asof(ry.asfreq("D").ffill(), ra.reindex(ry.asfreq("D").index).ffill(), dates), index=dates)
    n_ = nq.asfreq("D").ffill()
    below = pd.Series(_asof((n_ < n_.rolling(200, min_periods=150).mean()).astype(float), na.reindex(n_.index).ffill(), dates), index=dates)
    uc, rc = u / u.shift(13) - 1, r - r.shift(13)
    fast = lambda s: normalize.pit_percentile(s, window=156, min_hist=52) >= 0.8  # noqa: E731
    on = fast(uc) & fast(rc) & (below > 0.5)
    return np.where(on.to_numpy(), 1.25, np.inf)
