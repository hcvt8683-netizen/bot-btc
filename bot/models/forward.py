"""Part H: forward test (settings in config/candidates.yaml, section forward).

freeze  fit the nested model ONCE at a Sunday, store the frozen state and a sha256 version hash of code + config + state
        in <root>/<version>/model.json and start an empty <root>/<version>/forward_log.csv.
log     append one row per Sunday close with the frozen model (no refit): score, rank among earlier scores, zone (with
        hysteresis), multiplier, plus the two simple rules and the sell level. Rows are only appended, never rewritten.
        If code, config or the stored state no longer match the hash, logging stops: a new freeze starts a new log.
score   score every row whose 26- or 52-week outcome is known (Monday close, as in Part B) with the uniform measure.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.config import CONFIG, ROOT, load_yaml
from bot.models import part_c, sell_system as ss, wf_logit as wf, zones as zn
from bot.models.scenarios import rank_among

CODE = ["bot/features/weekly_close.py", "bot/models/wf_logit.py", "bot/models/zones.py", "bot/models/sell_system.py", "bot/models/scenarios.py",
        "bot/models/forward.py"]
COLUMNS = ["date", "close", "score", "rank", "zone", "mult_rule", "mult_used", "model_version", "rank_mvrv", "zone_mvrv", "rank_200w", "zone_200w",
           "sell_groups", "sell_level", "logged_at", "late"]
RULES = {"mvrv": "cheap_mvrv", "200w": "cheap_p_200wma"}
TableFn = Callable[[pd.Timestamp], pd.DataFrame]


class ModelChanged(RuntimeError):
    """Code, config or frozen state differ from the version hash: freeze a new version (new log) instead."""


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(o) -> str:
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def code_hashes() -> dict[str, str]:
    """sha256 of every file that computes a logged value, with line endings normalised (Windows and Linux agree)."""
    return {p: _sha((ROOT / p).read_bytes().replace(b"\r\n", b"\n")) for p in CODE}


def config_part() -> dict:
    sp = part_c.spec()
    return {**{k: sp[k] for k in ("model", "sets", "zones", "multiplier", "sell")}, "rebuild": load_yaml(CONFIG / "bot.yaml")["rebuild"]}


def model_hash(code: dict, config: dict, state: dict) -> str:
    return _sha(canonical({"code": code, "config": config, "state": state}).encode("utf-8"))


def _fit_json(f: wf.Fit | None) -> dict | None:
    if f is None:
        return None
    return {"features": f.features, "coef": [float(x) for x in f.coef], "intercept": f.intercept, "mu": [float(x) for x in f.mu],
            "sd": [float(x) for x in f.sd], "dropped": f.dropped, "lam": f.lam}


def frozen_state(t: pd.DataFrame, config: dict) -> dict:
    """Everything the log needs, from data up to the last Sunday of `t` only."""
    md, zc, mc = config["model"], config["zones"], config["multiplier"]
    rb = config["rebuild"]
    sets = {k: v["features"] for k, v in config["sets"].items()}
    name, fit, p0 = wf.freeze_fit(t, sets, md["lambdas"], md["target_weeks"], md["min_train_weeks"], md["inner_valid_weeks"])
    oos = wf.nested_oos(t, sets, md["lambdas"], h=md["target_weeks"], refit=md["refit_weeks"], min_train=md["min_train_weeks"],
                        inner_valid=md["inner_valid_weeks"])["p"].iloc[:-1]  # earlier weeks only: the freeze week is the first logged row
    rank = (wf.oos_rank(oos.dropna(), md["rank_min_weeks"]) * 100).dropna()
    zones = zn.hysteresis_zones(rank, zc["thresholds"], zc["hysteresis"])
    price = t["exec_monday"].reindex(zones.index).to_numpy(dtype=float)  # NaN where the Monday price is not known yet
    edges = zn.edges(zones, price, md["target_weeks"], rb["bootstrap_n"], rb["seed"], rb["episode_gap_weeks"]) if len(zones) else {}
    prev = {"model": zones.iloc[-1] if len(zones) else None}
    for n, col in RULES.items():
        r = (wf.oos_rank(t[col].iloc[:-1].dropna(), md["rank_min_weeks"]) * 100).dropna()
        prev[n] = zn.hysteresis_zones(r, zc["thresholds"], zc["hysteresis"]).iloc[-1] if len(r) else None
    return {"asof": t.index[-1].strftime("%Y-%m-%d"), "set": name, "fit": _fit_json(fit), "p0": None if not np.isfinite(p0) else float(p0),
            "score_history": [float(x) for x in oos.dropna()], "prev_zone": prev, "edges": edges, "gate": zn.gate(1.0)[1]}


def _versions(root: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(root.glob("*/model.json"))]


def freeze(root: Path, asof: pd.Timestamp, table_fn: TableFn = part_c.table, mode: str = "that", now: pd.Timestamp | None = None) -> tuple[str, bool]:
    """Freeze the model at Sunday `asof`. Returns (version id, created). The same hash never creates a second version."""
    root = Path(root)
    t = table_fn(asof)
    if t.index[-1] != asof:
        raise ValueError(f"no weekly close for {asof:%Y-%m-%d} (last {t.index[-1]:%Y-%m-%d})")
    code, config = code_hashes(), config_part()
    state = frozen_state(t, config)
    h = model_hash(code, config, state)
    old = _versions(root)
    same = next((v for v in old if v["hash"] == h), None)
    if same:
        (root / "current.txt").write_text(same["version"], encoding="utf-8")
        return same["version"], False
    vid = f"v{len(old) + 1}-{h[:10]}"
    d = root / vid
    d.mkdir(parents=True)
    now = now or _utc_now()
    (d / "model.json").write_text(json.dumps({"version": vid, "hash": h, "mode": mode, "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              "code": code, "config": config, "state": state}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    with open(d / "forward_log.csv", "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerow(COLUMNS)
    (root / "current.txt").write_text(vid, encoding="utf-8")
    return vid, True


def current(root: Path) -> Path:
    return Path(root) / (Path(root) / "current.txt").read_text(encoding="utf-8").strip()


def check(vdir: Path) -> list[str]:
    """Parts that no longer match the version hash (empty = unchanged)."""
    m = json.loads((Path(vdir) / "model.json").read_text(encoding="utf-8"))
    changed = [p for p, h in code_hashes().items() if m["code"].get(p) != h] + [p for p in m["code"] if p not in CODE]
    cfg = config_part()
    changed += [f"config.{k}" for k in sorted(set(cfg) | set(m["config"])) if canonical(cfg.get(k)) != canonical(m["config"].get(k))]
    if model_hash(m["code"], m["config"], m["state"]) != m["hash"]:
        changed.append("model.json")
    return changed


def read_log(vdir: Path) -> pd.DataFrame:
    df = pd.read_csv(Path(vdir) / "forward_log.csv", encoding="utf-8-sig", keep_default_na=False, dtype=str)
    return df


def _num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _predict(fit: dict | None, row: pd.Series) -> float:
    if fit is None:
        return float("nan")
    x = np.array([row.get("cheap_" + f, np.nan) for f in fit["features"]], dtype=float)
    if not np.isfinite(x).all():
        return float("nan")
    z = (x - np.array(fit["mu"])) / np.array(fit["sd"])
    return float(1 / (1 + np.exp(-(z @ np.array(fit["coef"]) + fit["intercept"]))))


def _fmt(x, d=6) -> str:
    return "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def log_week(root: Path, asof: pd.Timestamp, table_fn: TableFn = part_c.table, now: pd.Timestamp | None = None) -> dict | None:
    """Append the row of Sunday `asof` to the current version's log; None when that week (or a later one) is already logged."""
    vdir = current(root)
    changed = check(vdir)
    if changed:
        raise ModelChanged(", ".join(changed))
    m = json.loads((vdir / "model.json").read_text(encoding="utf-8"))
    st, cfg = m["state"], m["config"]
    log = read_log(vdir)
    if len(log) and pd.Timestamp(log["date"].iloc[-1]) >= asof:
        return None
    if asof < pd.Timestamp(st["asof"]):
        raise ValueError("week before the freeze date")
    t = table_fn(asof)
    if t.index[-1] != asof:
        raise ValueError(f"no weekly close for {asof:%Y-%m-%d}")
    row = t.iloc[-1]
    zc, mc, md, se = cfg["zones"], cfg["multiplier"], cfg["model"], cfg["sell"]
    score = _predict(st["fit"], row)
    hist = st["score_history"] + [v for v in (_num(x) for x in log["score"]) if np.isfinite(v)] if len(log) else list(st["score_history"])
    rank = rank_among(pd.Series(hist, dtype=float), score) if np.isfinite(score) and len(hist) >= md["rank_min_weeks"] else None
    prev = lambda col, key: (log[col].iloc[-1] or None) if len(log) else st["prev_zone"][key]  # noqa: E731
    zone = zn.step(prev("zone", "model"), np.nan if rank is None else rank, zc["thresholds"], zc["hysteresis"])
    mult_rule = zn.zone_multiplier(zone, st["edges"].get(zone) if zone else None, mc["scale"], tuple(mc["bounds"]), mc["min_episodes"])
    out = {"date": asof.strftime("%Y-%m-%d"), "close": _fmt(float(row["close"]), 2), "score": _fmt(score), "rank": _fmt(rank, 2), "zone": zone or "",
           "mult_rule": _fmt(mult_rule, 4), "mult_used": _fmt(mult_rule if st["gate"] == "dat_phan_i" else 1.0, 4), "model_version": m["version"]}
    for n, col in RULES.items():
        r = rank_among(t[col].iloc[:-1], float(row[col])) if np.isfinite(row[col]) else None
        out["rank_" + n] = _fmt(r, 2)
        out["zone_" + n] = zn.step(prev("zone_" + n, n), np.nan if r is None else r, zc["thresholds"], zc["hysteresis"]) or ""
    g = sum(int(any(row.get("pct_" + f, np.nan) >= se["threshold_pct"] for f in feats)) for feats in se["groups"].values())
    out["sell_groups"], out["sell_level"] = str(g), ss.level_of(g, se["levels"])
    now = now or _utc_now()
    out["logged_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    out["late"] = "1" if now > asof + pd.Timedelta(days=8) - pd.Timedelta(seconds=1) else "0"  # after the next Sunday close
    with open(vdir / "forward_log.csv", "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow([out[c] for c in COLUMNS])
    return out


def score(vdir: Path, t: pd.DataFrame, horizons: list[int], n_boot: int, seed: int, gap: int) -> dict:
    """Uniform zone tables of the logged zones on every row whose outcome is known in `t` (Monday close)."""
    log = read_log(vdir)
    if not len(log):
        return {"rows": 0}
    dates = pd.to_datetime(log["date"])
    idx = t.index[t.index >= dates.iloc[0]]
    price = t["exec_monday"].reindex(idx).to_numpy(dtype=float)
    out = {"rows": int(len(log)), "from": log["date"].iloc[0], "to": log["date"].iloc[-1], "late": int((log["late"] == "1").sum()), "matured": {}, "zones": {}}
    for h in horizons:
        r, _ = measure.forward(price, h)
        pos = idx.get_indexer(dates)
        out["matured"][h] = int(np.isfinite(r[pos[pos >= 0]]).sum())
    for name, col in (("model", "zone"), ("mvrv", "zone_mvrv"), ("200w", "zone_200w")):
        z = pd.Series([v or None for v in log[col]], index=dates, dtype=object).reindex(idx)
        z = z.where(z.notna(), None)
        out["zones"][name] = measure.zone_table(z, price, horizons, zn.ORDER, n_boot=n_boot, seed=seed, gap=gap)
    return out


def _utc_now() -> pd.Timestamp:
    return pd.Timestamp(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
