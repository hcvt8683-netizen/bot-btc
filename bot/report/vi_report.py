"""Weekly recommendation ("Khuyến nghị giải ngân tuần này"), written to data/recommendation.json for the web page.

Fail-safe: the multiplier is 1.0 (plain DCA) whenever the model did not pass the acceptance criteria or a
required data source is missing or stale; the reasons are listed. Only public numbers go into the JSON (amount per
100 $ of budget); a personal budget from config/personal.yaml is used only for local console output.
"""
from __future__ import annotations

import datetime as dt
import json
import re

from bot.config import DATA, cfg, personal
from bot.i18n import fmt, t

OUT = DATA / "recommendation.json"
SUMMARY = DATA / "results" / "final_summary.json"


def _last_sunday(status: dict) -> dt.date | None:
    """Data cut-off of the signal: the last Sunday up to the last Coin Metrics day in data/status.json."""
    last = ((status.get("sources") or {}).get("coinmetrics") or {}).get("last")
    if not last:
        return None
    d = dt.date.fromisoformat(last)
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def _events(now: dt.datetime, status: dict, days: int = 7) -> tuple[list[dict], dict]:
    """Events after the data cut-off (last Sunday close) up to now + days. Those already past at `now` are flagged:
    the signal does not contain the market's reaction to them (bot/report/events.py)."""
    import pandas as pd
    from bot.report import events as ev
    sunday = _last_sunday(status)
    cutoff = ev.cutoff_of(pd.Timestamp(sunday)) if sunday else pd.Timestamp(now)
    lst = ev.listing(cutoff, pd.Timestamp(now), days)
    iso = lambda x: x.strftime("%Y-%m-%dT%H:%MZ")  # noqa: E731
    events = [{"type": e["type"], "time": iso(e["time"]), "flag": e["flag"]} for e in lst["after_cutoff"] + lst["upcoming"]]
    meta = {"cutoff": sunday.isoformat() if sunday else None, "rerun_after": lst["rerun_after"].strftime("%Y-%m-%d") if lst["rerun_after"] is not None else None,
            "stale": {k: (v.strftime("%Y-%m-%d") if v is not None else None) for k, v in lst["stale"].items()}}
    return events, meta


_SCN: dict = {}


def _scenarios(asof: str) -> dict | None:
    """Price scenarios at the analysis Sunday (Part F method, Fear & Greed moving with price); computed once per process."""
    if asof not in _SCN:
        try:
            import pandas as pd
            from bot.report import final_report as fr
            sc = fr.scenarios_now(pd.Timestamp(asof))
            _SCN[asof] = {"k": sc["k"], "rows": [{"delta": r["delta"], "price": r["mid"]["price"], "fng": r["fng"], "range_200w": r["range_200w"],
                                                  "zones_200w": r["zones_200w"], "rank_mvrv": r["mid"]["rank_mvrv"], "range_mvrv": r["range_mvrv"],
                                                  "zones_mvrv": r["zones_mvrv"], "groups": r["groups_range"], "levels": r["levels"]} for r in sc["rows"]]}
        except Exception:  # noqa: BLE001
            _SCN[asof] = None
    return _SCN[asof]


def _rebuild() -> dict | None:
    """The rebuild's verdict for the page: the six acceptance criteria (Part I, single holdout run), this week's reading
    from the frozen forward model, how this week's zones did in the past (by episodes), the sell side, the Fed regime and
    the price scenarios. None when a result file is missing."""
    try:
        from bot.models import forward as fw
        R = DATA / "results"
        I = json.loads((R / "part_i.json").read_text(encoding="utf-8"))
        G = json.loads((R / "part_g.json").read_text(encoding="utf-8"))
        vdir = fw.current(DATA / "forward")
        log = fw.read_log(vdir)
        model = json.loads((vdir / "model.json").read_text(encoding="utf-8"))
        last = log.iloc[-1]
        num = lambda x: float(x) if str(x) not in ("", "nan") else None  # noqa: E731
        c = I["criteria"]
        crit = {"c1": {"years": c["c1"].get("years", {}), "holdout": c["c1"].get("holdout")},
                "c2": {"holdout": c["c2"].get("holdout"), "ci": c["c2"].get("ci")},
                "c3": {"p_ic": (c["c3"].get("ic26") or {}).get("p_maxstat"), "p_cost": (c["c3"].get("cost_basis") or {}).get("p_maxstat"),
                       "weeks": c["c3"].get("weeks"), "need": c["c3"].get("need_weeks")},
                "c4": {"monotone": c["c4"].get("monotone") or {}, "drops": c["c4"].get("weeks_with_drop"), "model_weeks": c["c4"].get("weeks_with_model")},
                "c5": {"brier": c["c5"].get("brier"), "brier_base": c["c5"].get("brier_base"), "weeks": c["c5"].get("weeks", 0)},
                "c6": {"holdout": c["c6"].get("holdout", {})}}
        for k in crit:
            crit[k]["pass"] = bool(c[k]["pass"])
        zones = []
        for name, key in (("Lồng nhau", "zone"), ("Quy tắc MVRV", "zone_mvrv"), ("Quy tắc Giá/MA 200 tuần", "zone_200w")):
            sz, z = I["strategies"].get(name), last[key] or None
            if not sz or not z:
                continue
            for h in (4, 13, 26, 52):
                row, base = sz["zones"]["zones"].get(z, {}).get(str(h), {}), sz["zones"]["baseline"].get(str(h), {})
                if row.get("weeks"):
                    zones.append({"strategy": name, "zone": z, "h": h, "weeks": row["weeks"], "episodes": row["episodes"], "win": row["win"],
                                  "base": base.get("win"), "diff": row["diff"], "ci": row.get("ci"), "verdict": row.get("verdict")})
        fit = model["state"]["fit"]
        lv = G["live"]
        return {"acceptance": {"passed": bool(I["passed"]), "run_at": I["run_at"], "holdout_start": I["holdout_start"], "last_week": I["last_week"],
                               "holdout_weeks": I["holdout_weeks"], "criteria": crit},
                "week": {"date": str(last["date"]), "close": num(last["close"]), "rank": num(last["rank"]), "zone": last["zone"] or None,
                         "rank_mvrv": num(last["rank_mvrv"]), "zone_mvrv": last["zone_mvrv"] or None, "rank_200w": num(last["rank_200w"]),
                         "zone_200w": last["zone_200w"] or None, "mult_rule": num(last["mult_rule"]), "sell_groups": int(last["sell_groups"]),
                         "sell_level": last["sell_level"]},
                "model": {"version": model["version"], "asof": model["state"]["asof"], "set": model["state"]["set"],
                          "features": fit["features"] if fit else [], "dropped": fit["dropped"] if fit else [], "weeks_logged": int(len(log))},
                "zones": zones, "sell_trusted": sum(x["trusted"] == "dang_tin" for x in I["sell"]["criteria"].values()),
                "fed": {"regime": lv["regime"], "since": str(lv["since"])[:10], "warn": [n for n, x in G["strategies"].items() if x["warn"]]},
                "scenarios": _scenarios(str(last["date"]))}
    except Exception:  # noqa: BLE001  the weekly report must never fail because of this block
        return None


def _friendly(err: str) -> str:
    """Vietnamese message for a source error shown on the page (raw details stay in data/status.json)."""
    if not err:
        return ""
    m = re.search(r"HTTP (451|403)", err)
    return t("sources.err_blocked", code=m.group(1)) if m else t("sources.err_other")


def _freshness(now: dt.datetime) -> tuple[dict, bool]:
    """Per source: last row, ok, age; and whether a required source is missing or stale."""
    path = DATA / "status.json"
    st = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"sources": {}}
    stale_days = int((cfg().get("risk") or {}).get("stale_data_days", 3))
    out, bad = {}, False
    for name, s in st.get("sources", {}).items():
        last = s.get("last")
        age = (now.date() - dt.date.fromisoformat(last)).days if last else None
        out[name] = {"last": last, "ok": bool(s.get("ok")), "age_days": age, "error": _friendly("; ".join(s.get("errors") or []))}
    for name, conf in cfg()["sources"].items():
        if conf.get("required"):
            s = out.get(name)
            if not s or not s["ok"] or s["age_days"] is None or s["age_days"] > stale_days:
                bad = True
    return out, bad


def _evidence(summary: dict) -> dict:
    def pick(x: dict) -> dict:
        sp = x["splits"]
        return {k: {"median": v.get("roll_er_median"), "p10": v.get("roll_er_p10"), "cba": v.get("cba"), "mdd": v.get("mdd"),
                    "mdd_dca": v.get("mdd_dca")} for k, v in (("validation", sp.get("Kiểm định", {})), ("holdout", sp.get("Kiểm tra cuối", {})))} | {
            "placebo_holdout": x["placebo_holdout"]["percentile"], "ci_holdout": x["bootstrap_holdout"]["er_ci"]}
    eps = next((c["eps"] for c in summary["criteria"] if c["id"] == 6), {})
    return {"candidate": pick(summary["candidate"]), "current_bot": pick(summary["current_bot"]), "episodes": eps,
            "trials": summary["trials"], "passed": summary["passed"], "run_at": summary["run_at"]}


def _plan() -> dict | None:
    """Lump-sum deployment plans (bot/models/deploy_plan.py); None when the data are missing, so the page says so."""
    try:
        from bot.models import deploy_plan
        out = deploy_plan.for_report()
        return out if out.get("options") else None
    except Exception:  # noqa: BLE001  the weekly report must never fail because of this block
        return None


def _calib(now: dt.datetime) -> dict | None:
    """Calibrated probability of profit for 1/3/6 months (bot/models/calib_prob.py); logs this week's values. None on failure."""
    try:
        from bot.models import calib_prob
        res = calib_prob.run(write=True)
        calib_prob.log_week(res, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
        keep = ("h", "weeks", "from", "to", "best", "pick", "now", "said80")
        return {h: {k: o[k] for k in keep} | {"methods": {m: {"brier": v["brier"], "gain_ci": v["gain_ci"]} for m, v in o["methods"].items()}} for h, o in res.items()}
    except Exception:  # noqa: BLE001  the weekly report must never fail because of this block
        return None


def _forecast() -> dict | None:
    """Daily price bands with their walk-forward check and the live log (bot/models/price_forecast.py); None on failure."""
    try:
        from bot.models import price_forecast
        out = price_forecast.for_report()
        srch = DATA / "results" / "forecast_search.json"
        if srch.exists():  # summary of the method search (bot/models/forecast_search.py), shown as a note on the page
            o = json.loads(srch.read_text(encoding="utf-8"))
            out["search"] = {k: o[k] for k in ("n_variants", "data_from", "selection", "confirm_from", "current", "best", "switch")} | {
                "diff": o["confirm"]["diff"], "ci": o["confirm"]["ci"]}
        return out
    except Exception:  # noqa: BLE001  the weekly report must never fail because of this block
        return None


def build(now: dt.datetime | None = None, write: bool = True) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None, microsecond=0)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else None
    fresh, data_bad = _freshness(now)
    status_path = DATA / "status.json"
    events, events_meta = _events(now, json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {})
    reasons = []
    if not summary or not summary.get("passed"):
        reasons.append("model_failed")
    if data_bad:
        reasons.append("data_stale")
    m, layer = 1.0, None
    if not reasons:  # only reachable once a model passes phase 7
        from bot.features import build as fb
        from bot.models import ablation_bc
        feat = fb.weekly(None)
        m, layer = float(ablation_bc.layer_a(feat)[-1]), "A"
    site = cfg().get("site") or {}
    rec = {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "multiplier": m, "mode": "safe" if reasons else "model", "layer": layer,
           "reasons": reasons, "amount_example_usd": site.get("amount_example_usd", 100),
           "stale_data_days": int((cfg().get("risk") or {}).get("stale_data_days", 3)),
           "events": events, "events_meta": events_meta, "event_delay": bool([r for r in cfg()["model"].get("layer_c") or [] if r == "event_window"]),
           "freshness": fresh, "evidence": _evidence(summary) if summary else None, "plan": _plan(), "forecast": _forecast(), "rebuild": _rebuild(), "calib": _calib(now)}
    if write:
        OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def console(rec: dict) -> str:
    """Vietnamese summary for the terminal; adds the personal budget from config/personal.yaml when present."""
    ex = rec["amount_example_usd"]
    lines = [t("report.title"), t("report.multiplier_line", m=fmt.dec(rec["multiplier"], 1), amount=fmt.usd(ex * rec["multiplier"]), budget=fmt.usd(ex)),
             t("report.mode_safe") if rec["mode"] == "safe" else t("report.mode_model", layer=rec["layer"])]
    for r in rec["reasons"]:
        lines.append("- " + t(f"report.reason_{r}"))
    b = (personal().get("budget") or {}).get("weekly_usd")
    if b:
        lines.append(t("report.personal_line", budget=fmt.usd(b), amount=fmt.usd(b * rec["multiplier"])))
    lines += [("⚑ " if e.get("flag") else "") + t("report.event_line", time=fmt.datetime_vn(e["time"]), name=t(f"report.{e['type']}")) for e in rec["events"]] or [t("report.events_none")]
    if (rec.get("events_meta") or {}).get("rerun_after"):
        lines.append(t("report.rerun", date=fmt.date(rec["events_meta"]["rerun_after"])))
    return "\n".join(lines)

