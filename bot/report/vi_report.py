"""Weekly recommendation ("Khuyến nghị giải ngân tuần này"), written to data/recommendation.json for the web page.

Fail-safe: the multiplier is 1.0 (plain DCA) whenever the model did not pass the acceptance criteria (phase 7) or a
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


def _events(now: dt.datetime, days: int = 7) -> list[dict]:
    from bot.config import CONFIG, load_yaml
    y = load_yaml(CONFIG / "events.yaml")
    out = []
    for k in ("fomc", "cpi", "pce"):
        for s in y.get(k) or []:
            out.append({"type": k, "time": s})
    from bot.data.fetchers import events as ev
    out += [{"type": "opex", "time": s} for s in ev.options_expiry(now.date(), (now + dt.timedelta(days=days)).date())]
    lo, hi = now, now + dt.timedelta(days=days)
    keep = [e for e in out if lo <= dt.datetime.fromisoformat(e["time"].replace("Z", "+00:00")).replace(tzinfo=None) <= hi]
    return sorted(keep, key=lambda e: e["time"])


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


def build(now: dt.datetime | None = None, write: bool = True) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None, microsecond=0)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else None
    fresh, data_bad = _freshness(now)
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
           "events": _events(now), "event_delay": bool([r for r in cfg()["model"].get("layer_c") or [] if r == "event_window"]),
           "freshness": fresh, "evidence": _evidence(summary) if summary else None}
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
    lines += [t("report.event_line", time=fmt.datetime_vn(e["time"]), name=t(f"report.{e['type']}")) for e in rec["events"]] or [t("report.events_none")]
    return "\n".join(lines)

