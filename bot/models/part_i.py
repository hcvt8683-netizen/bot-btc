"""Part I: the six acceptance criteria (fixed in config/candidates.yaml, section acceptance) and the single run on the
holdout from 01/01/2024. `rehearse()` runs the same code with a pretend holdout inside already-seen data;
`run_final()` is the one logged run: it refuses if experiments/final_runs.log already holds one."""
from __future__ import annotations

import datetime as dt
import json
import subprocess

import numpy as np
import pandas as pd

from bot.backtest import measure
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.i18n import fmt
from bot.models import part_c, part_d, part_e, sell_system as ss, wf_logit as wf, zones as zn
from bot.validation import splits

PHASE = "rebuild_part_i"
NESTED, RULE_MVRV, RULE_200W = "Lồng nhau", "Quy tắc MVRV", "Quy tắc Giá/MA 200 tuần"


class AlreadyRun(RuntimeError):
    """The holdout run of Part I is allowed once."""


def already_run(log_path=None) -> bool:
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


def strategy(t: pd.DataFrame, p: pd.Series, sp: dict, rb: dict) -> dict | None:
    """Contiguous weeks from the first out-of-sample rank to the last week with a Monday price: rank, zones with
    hysteresis, Part D multipliers (walk-forward, ungated) and the comparison multiplier 0.5 + rank."""
    md, zc, mc = sp["model"], sp["zones"], sp["multiplier"]
    rank = (wf.oos_rank(p.dropna(), md["rank_min_weeks"]) * 100).dropna()
    if not len(rank):
        return None
    ok = np.isfinite(t["exec_monday"].to_numpy(dtype=float))
    idx = t.index[ok & (t.index >= rank.index[0])]
    r = rank.reindex(idx)
    z = zn.hysteresis_zones(r, zc["thresholds"], zc["hysteresis"])
    price = t["exec_monday"].reindex(idx).to_numpy(dtype=float)
    m, hist = zn.walk_multipliers(z, price, md["target_weeks"], mc["refit_weeks"], mc["scale"], tuple(mc["bounds"]), mc["min_episodes"],
                                  rb["bootstrap_n"], rb["seed"], rb["episode_gap_weeks"])
    return {"idx": idx, "rank": r, "zones": z, "price": price, "m": m, "m_cmp": np.where(np.isfinite(r.to_numpy()), 0.5 + r.to_numpy() / 100, 1.0),
            "edges_last": hist[-1]["edges"] if hist else None, "refits": len(hist)}


def on_window(s: dict, window: pd.DatetimeIndex, key: str) -> np.ndarray:
    """Multiplier on `window`; weeks before the strategy exists are plain DCA (1.0)."""
    return pd.Series(s[key], index=s["idx"]).reindex(window).fillna(1.0).to_numpy()


def cba(price: np.ndarray, m: np.ndarray) -> float:
    return part_c.cost_basis(price, m)


def years(s: dict, key: str, before: pd.Timestamp, min_weeks: int = 26) -> dict[str, float]:
    out = {}
    for y in sorted({d.year for d in s["idx"] if d < before}):
        msk = (s["idx"].year == y) & (s["idx"] < before)
        if msk.sum() >= min_weeks:
            out[str(y)] = cba(s["price"][msk], s[key][msk])
    return out


def run(holdout_start: pd.Timestamp, data_end: pd.Timestamp | None, mode: str) -> dict:
    sp = part_c.spec()
    md, ac, se, ts = sp["model"], sp["acceptance"], sp["sell"], sp["tests"]
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    seed, n_boot, horizons, gap, h = rb["seed"], rb["bootstrap_n"], rb["horizons_weeks"], rb["episode_gap_weeks"], md["target_weeks"]
    t = part_c.table(data_end) if data_end is not None else part_c.table(None)
    sets = {k: v["features"] for k, v in sp["sets"].items()}
    nested = wf.nested_oos(t, sets, md["lambdas"], h=h, refit=md["refit_weeks"], min_train=md["min_train_weeks"], inner_valid=md["inner_valid_weeks"])
    fixed = {f"{k}/λ{lam:g}": wf.config_oos(t, f, lam, h=h, refit=md["refit_weeks"], min_train=md["min_train_weeks"])["p"]
             for k, f in sets.items() for lam in md["lambdas"]}
    scores = {NESTED: nested["p"], RULE_MVRV: t["cheap_mvrv"], RULE_200W: t["cheap_p_200wma"]}
    strat = {k: strategy(t, v, sp, rb) for k, v in scores.items()}
    ok = np.isfinite(t["exec_monday"].to_numpy(dtype=float))
    H = t.index[ok & (t.index >= holdout_start)]
    PH = t["exec_monday"].reindex(H).to_numpy(dtype=float)
    out = {"mode": mode, "run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "holdout_start": holdout_start.strftime("%Y-%m-%d"),
           "last_week": H[-1].strftime("%Y-%m-%d") if len(H) else None, "holdout_weeks": int(len(H)), "criteria": {}, "supplementary": {}, "strategies": {}}
    s0 = strat[NESTED]
    # per strategy: holdout cost basis (decisive multiplier and comparison multiplier), years before the holdout, zones
    for name, s in strat.items():
        if s is None or not len(H):
            out["strategies"][name] = None
            continue
        row = {"from": s["idx"][0].strftime("%Y-%m-%d"), "weeks": int(len(s["idx"])), "rank_weeks": int(s["rank"].notna().sum()), "refits": s["refits"]}
        for key in ("m", "m_cmp"):
            m = on_window(s, H, key)
            c = part_d.cost(PH, m, n_boot, rb["cost_block_weeks"], seed)
            row[key] = {"holdout": c["advantage"], "holdout_ci": c["ci"], "share_not_one": float(np.mean(m != 1.0)), "years": years(s, key, holdout_start)}
        tab = measure.zone_table(s["zones"], s["price"], horizons, zn.ORDER, n_boot=n_boot, seed=seed, gap=gap)
        hz = s["zones"].where(s["idx"] >= holdout_start, None)
        tab_h = measure.zone_table(hz, s["price"], horizons, zn.ORDER, n_boot=n_boot, seed=seed, gap=gap)
        row.update({"zones": tab, "monotone": measure.monotone(tab, ["phai", "cannhac", "__baseline__", "khong"]), "zones_holdout": tab_h,
                    "monotone_holdout": measure.monotone(tab_h, ["phai", "cannhac", "__baseline__", "khong"]), "edges_last": s["edges_last"]})
        out["strategies"][name] = row
    S = out["strategies"]
    n0 = S[NESTED]

    def c1(key):
        if not n0:
            return {"pass": False, "reason": "không có thứ hạng ngoài mẫu"}
        ys = n0[key]["years"]
        share = (sum(v > 0 for v in ys.values()) / len(ys)) if ys else None
        return {"years": ys, "share_positive": share, "holdout": n0[key]["holdout"],
                "pass": bool(ys) and share >= 0.75 and n0[key]["holdout"] > 0, "reason": None if ys else "không có năm nào đủ 26 tuần trước holdout"}

    def c2(key):
        if not n0:
            return {"pass": False}
        return {"holdout": n0[key]["holdout"], "ci": n0[key]["holdout_ci"], "pass": n0[key]["holdout_ci"][0] > 0}

    def c6(key):
        if not n0 or not S[RULE_MVRV] or not S[RULE_200W]:
            return {"pass": False}
        v = {k: S[k][key]["holdout"] for k in (NESTED, RULE_MVRV, RULE_200W)}
        return {"holdout": v, "pass": v[NESTED] > v[RULE_MVRV] and v[NESTED] > v[RULE_200W]}

    # c3: permutation on the holdout over every configuration tried
    allp = {NESTED: nested["p"], **fixed, RULE_MVRV: t["cheap_mvrv"], RULE_200W: t["cheap_p_200wma"]}
    results, skipped = [], {}
    for name, p in allp.items():
        p = p.dropna()
        rank = wf.oos_rank(p, md["rank_min_weeks"]).dropna()
        rh = rank[(rank.index >= holdout_start) & np.isfinite(t["exec_monday"].reindex(rank.index).to_numpy(dtype=float))]
        if len(rh) < 30:
            skipped[name] = int(len(rh))
            continue
        results.append(part_c.evaluate_strategy(name, p.reindex(rh.index), rh, t, horizons, seed, n_boot))
    perm = part_c.permutation(results, ts["permutation_n"], ts["permutation_min_shift_weeks"], seed) if results else {}
    nres = next((r for r in results if r["name"] == NESTED), None)
    need = 2 * ts["permutation_min_shift_weeks"] + 10
    c3 = {"weeks": nres["weeks"] if nres else 0, "need_weeks": need, "configs": len(results), "skipped": skipped,
          "ic26": perm.get("ic26", {}).get(NESTED), "cost_basis": perm.get("cost_basis", {}).get(NESTED)}
    c3["pass"] = bool(nres and nres["weeks"] >= need and all(c3[k] and np.isfinite(c3[k]["p_raw"]) and c3[k]["p_maxstat"] < 0.05 for k in ("ic26", "cost_basis")))
    # c4: monotone zones over the whole out-of-sample period, weights ≥ 0 (enforced by the sign constraint)
    drops = nested["dropped"].dropna()
    c4 = {"monotone": n0["monotone"] if n0 else None, "sign_ok": True, "weeks_with_model": int(nested["p"].notna().sum()), "weeks_with_drop": int((drops != "").sum()),
          "dropped": sorted({x for d in drops for x in str(d).split("+") if x})}
    c4["pass"] = bool(n0) and all(n0["monotone"].values())
    # c5: Brier on holdout weeks with a model and a known 26-week label
    y = pd.Series(wf.labels(t, h), index=t.index)
    nh = nested[(nested.index >= holdout_start)].dropna(subset=["p"])
    c5 = {"weeks": 0, "pass": False}
    if len(nh):
        yy = y.reindex(nh.index).to_numpy()
        if np.isfinite(yy).sum():
            cal = measure.calibration(nh["p"].to_numpy(), nh["p0"].to_numpy(), yy, h, n_boot, seed)
            c5 = {**cal, "pass": cal["weeks"] > 0 and cal["brier"] < cal["brier_base"]}
    out["criteria"] = {"c1": c1("m"), "c2": c2("m"), "c3": c3, "c4": c4, "c5": c5, "c6": c6("m")}
    out["supplementary"] = {"c1": c1("m_cmp"), "c2": c2("m_cmp"), "c6": c6("m_cmp")}
    out["passed"] = all(c["pass"] for c in out["criteria"].values())
    out["permutation"] = perm
    nH = nested.reindex(H)
    out["nested"] = {"weeks": int(len(nested)), "no_model_weeks": int(nested["config"].isna().sum()),
                     "holdout_weeks": int(len(H)), "holdout_no_model": int(nH["config"].isna().sum()),
                     "picks": nested.dropna(subset=["config"]).groupby(["config", "lam"]).size().sort_values(ascending=False).reset_index(name="weeks").to_dict("records")}
    out["sell"] = sell(t, se, ac["sell"], rb)
    return out


def sell(t: pd.DataFrame, se: dict, sc: dict, rb: dict) -> dict:
    """Part E criteria and rules re-scored with the cycles that include the holdout; trusted = works in the last two cycles."""
    t = t[(t.index >= "2012-01-01") & np.isfinite(t["exec_monday"])]
    dates, close, fill = t.index, t["close"].to_numpy(dtype=float), t["exec_monday"].to_numpy(dtype=float)
    last = dates[-1].strftime("%Y-%m-%d")
    cycles = [(str(a), min(str(b), last) if b else last) for a, b in sc["cycles"] if str(a) <= last]
    fl = ss.flags(t, se["groups"], se["threshold_pct"])
    cnt = ss.group_count(fl, se["groups"])
    hh, gap = se["outcome_weeks"], rb["episode_gap_weeks"]
    crit = {f: part_e.criterion(fl[f].to_numpy(), fill, dates, hh, gap, rb["bootstrap_n"], rb["seed"], cycles) for f in fl.columns}
    crit.update({f"≥{g} nhóm": part_e.criterion((cnt >= g).to_numpy(), fill, dates, hh, gap, rb["bootstrap_n"], rb["seed"], cycles) for g in se["triggers"]})
    for c in crit.values():
        c["trusted"] = "dang_tin" if all(p["works"] for p in c["cycles"][-2:]) else "khong"
    sims = part_e.simulate_rules(dates, close, fill, cnt, se, gap, cycles)
    return {"cycles": cycles, "criteria": crit, "sims": sims, "last": {"date": dates[-1].strftime("%Y-%m-%d"), "groups_on": int(cnt.iloc[-1]),
            "level": ss.level_of(int(cnt.iloc[-1]), se["levels"]), "criteria_on": [f for f in fl.columns if bool(fl[f].iloc[-1])]}}


def rehearse() -> dict:
    r = part_c.spec()["acceptance"]["rehearsal"]
    out = run(pd.Timestamp(str(r["holdout_start"])), pd.Timestamp(str(r["data_end"])), "dien_tap")
    (DATA / "results" / "part_i_rehearsal.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (DATA / "results" / "part_i_rehearsal.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    return out


def run_final(log_path=None) -> dict:
    if already_run(log_path):
        raise AlreadyRun("Phần I đã chạy holdout một lần (experiments/final_runs.log)")
    ac = part_c.spec()["acceptance"]
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    _log(log_path, {"command": "acceptance --final", "phase": PHASE, "status": "start"})
    out = run(pd.Timestamp(str(ac["holdout_start"])), None, "that")
    out["git"] = git
    st = json.loads((DATA / "status.json").read_text(encoding="utf-8"))
    out["data"] = {"fetched_at": st.get("fetched_at"), "last": {k: v.get("last") for k, v in st["sources"].items()}}
    (DATA / "results" / "part_i.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (DATA / "results" / "acceptance.json").write_text(json.dumps({"passed": out["passed"], "run_at": out["run_at"], "git": git,
                                                                  "criteria": {k: bool(v["pass"]) for k, v in out["criteria"].items()}},
                                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "docs" / "ACCEPTANCE_I.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    _log(log_path, {"command": "acceptance --final", "phase": PHASE, "status": "done", "passed": out["passed"],
                    "criteria": {k: bool(v["pass"]) for k, v in out["criteria"].items()}})
    return out


def _log(log_path, args: dict) -> None:
    if log_path is None:
        splits.log_final_run(args)
    else:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **args}, ensure_ascii=False) + "\n")


NAMES = {"c1": "Lợi thế giá vốn > 0 ở ≥ 75% số năm trước holdout và trên holdout", "c2": "Cận dưới khoảng tin cậy của lợi thế trên holdout > 0",
         "c3": "p hoán vị đã hiệu chỉnh < 0,05 (IC 26 tuần và lợi thế giá vốn)", "c4": "Khung đơn điệu ở mọi kỳ hạn, trọng số đúng dấu",
         "c5": "Brier tốt hơn tỷ lệ gốc", "c6": "Thắng cả hai quy tắc đơn giản 1 chỉ số"}
ZONE_VI = {"phai": "Phải mua", "cannhac": "Cân nhắc mua", "khong": "Không nên mua"}
VERDICT = {"chua_co_loi_the": "chưa có lợi thế", "hon_moc": "hơn mốc", "kem_moc": "**kém mốc**", "it_dot": "ít đợt (< 3)"}


def markdown(o: dict) -> str:
    sp_ = lambda x: "—" if x is None else fmt.pct(x, 1, sign=True)  # noqa: E731
    p0 = lambda x: "—" if x is None else fmt.pct(x)  # noqa: E731
    pv = lambda d: ("không tính được" if not d or not np.isfinite(d["p_raw"]) else  # noqa: E731
                    f"{fmt.dec(d['p_maxstat'], 3)} (thô {fmt.dec(d['p_raw'], 3)})")
    C, S = o["criteria"], o["strategies"]
    title = "# Phần I: tiêu chí chấp nhận và lần chạy holdout duy nhất" if o["mode"] == "that" else "# Phần I: DIỄN TẬP (holdout giả, dữ liệu đã xem)"
    L = [title, "",
         f"Đăng ký trước: `config/candidates.yaml` mục `acceptance` (commit `60ddb0a`), trước khi đọc bất kỳ số nào của holdout. "
         f"Holdout: {fmt.date(o['holdout_start'])} → {fmt.date(o['last_week']) if o['last_week'] else '—'} ({o['holdout_weeks']} tuần). Chạy lúc {o['run_at']}"
         + (f", mã `{o.get('git')}`, ghi trong `experiments/final_runs.log`." if o["mode"] == "that" else "."), "",
         f"## Kết luận: {'**ĐẠT** cả 6 tiêu chí' if o['passed'] else '**KHÔNG ĐẠT** → giữ mua đều (hệ số 1,0)'}", "",
         "| # | Tiêu chí | Kết quả | Đạt? |", "|---|---|---|---|"]
    c = C["c1"]
    L.append(f"| 1 | {NAMES['c1']} | năm có lợi: {sum(v > 0 for v in c.get('years', {}).values())}/{len(c.get('years', {}))}"
             f" ({', '.join(f'{y}: {sp_(v)}' for y, v in c.get('years', {}).items()) or 'không có năm đủ tuần'}); holdout {sp_(c.get('holdout'))} | {'✔' if c['pass'] else '✘'} |")
    c = C["c2"]
    L.append(f"| 2 | {NAMES['c2']} | {sp_(c.get('holdout'))}, KTC 95% {sp_((c.get('ci') or [None])[0])} đến {sp_((c.get('ci') or [None, None])[1])} | {'✔' if c['pass'] else '✘'} |")
    c = C["c3"]
    L.append(f"| 3 | {NAMES['c3']} | IC: {pv(c.get('ic26'))}; lợi thế: {pv(c.get('cost_basis'))}; {c['weeks']} tuần có mô hình (cần ≥ {c['need_weeks']}), "
             f"{c['configs']} cấu hình | {'✔' if c['pass'] else '✘'} |")
    c = C["c4"]
    mono = c.get("monotone") or {}
    L.append(f"| 4 | {NAMES['c4']} | đơn điệu: " + (", ".join(f"{h} tuần {'có' if v else 'không'}" for h, v in mono.items()) or "—")
             + f"; trọng số ≥ 0 nhờ ràng buộc dấu; {c['weeks_with_drop']}/{c['weeks_with_model']} tuần có mô hình đã phải bỏ chỉ số sai dấu ({', '.join(c['dropped']) or '—'}) | {'✔' if c['pass'] else '✘'} |")
    c = C["c5"]
    L.append(f"| 5 | {NAMES['c5']} | " + (f"Brier {fmt.dec(c['brier'], 3)} so với {fmt.dec(c['brier_base'], 3)} ({c['weeks']} tuần)" if c.get("weeks") else "không có tuần holdout nào có mô hình và nhãn")
             + f" | {'✔' if c['pass'] else '✘'} |")
    c = C["c6"]
    L.append(f"| 6 | {NAMES['c6']} | " + ("; ".join(f"{k}: {sp_(v)}" for k, v in c.get("holdout", {}).items()) or "—") + f" | {'✔' if c['pass'] else '✘'} |")
    n = o["nested"]
    L += ["", f"Mô hình lồng nhau: {n['weeks']} tuần ngoài mẫu, {n['no_model_weeks']} tuần không có mô hình (mua đều); trong holdout {n['holdout_no_model']}/{n['holdout_weeks']} tuần không có mô hình.", "",
          "## Tham khảo (không quyết định): hệ số so sánh 0,5 + thứ hạng", "",
          "Cùng tiêu chí 1, 2, 6 nhưng dùng hệ số so sánh của Phần C (tuần có thứ hạng luôn lệch khỏi 1,0), để biết riêng tín hiệu có giá trị không.", "",
          "| Tiêu chí | Kết quả | Đạt? |", "|---|---|---|"]
    s1, s2, s6 = o["supplementary"]["c1"], o["supplementary"]["c2"], o["supplementary"]["c6"]
    L += [f"| 1 | năm có lợi {sum(v > 0 for v in s1.get('years', {}).values())}/{len(s1.get('years', {}))}; holdout {sp_(s1.get('holdout'))} | {'✔' if s1['pass'] else '✘'} |",
          f"| 2 | {sp_(s2.get('holdout'))}, KTC 95% {sp_((s2.get('ci') or [None])[0])} đến {sp_((s2.get('ci') or [None, None])[1])} | {'✔' if s2['pass'] else '✘'} |",
          f"| 6 | " + ("; ".join(f"{k}: {sp_(v)}" for k, v in s6.get("holdout", {}).items()) or "—") + f" | {'✔' if s6['pass'] else '✘'} |", "",
          "## Từng chiến lược trên holdout", "",
          "| Chiến lược | Từ | Lợi thế giá vốn, hệ số Phần D (KTC 95%) | Tuần hệ số ≠ 1 | Lợi thế, hệ số so sánh (KTC 95%) | Đơn điệu cả giai đoạn | Đơn điệu riêng holdout |",
          "|---|---|---|---|---|---|---|"]
    for name, s in S.items():
        if not s:
            L.append(f"| {name} | — | không có thứ hạng | — | — | — | — |")
            continue
        md_, mc_ = s["m"], s["m_cmp"]
        L.append(f"| {name} | {fmt.date(s['from'])} | {sp_(md_['holdout'])} ({sp_(md_['holdout_ci'][0])} đến {sp_(md_['holdout_ci'][1])}) | {fmt.pct(md_['share_not_one'])} | "
                 f"{sp_(mc_['holdout'])} ({sp_(mc_['holdout_ci'][0])} đến {sp_(mc_['holdout_ci'][1])}) | "
                 f"{'có' if all(s['monotone'].values()) else 'không'} | {'có' if all(s['monotone_holdout'].values()) else 'không'} |")
    L += ["", "## Khung trên holdout (giá cao hơn sau 26 tuần, so với mọi tuần holdout)", "",
          "| Chiến lược | Mốc | Khung | Số tuần | Số đợt | Tỷ lệ | Chênh (KTC 95%) | Kết luận |", "|---|---|---|---|---|---|---|---|"]
    for name, s in S.items():
        if not s:
            continue
        tab = s["zones_holdout"]
        base = tab.get("baseline", {}).get(26)
        for z in zn.ORDER:
            c = tab["zones"].get(z, {}).get(26, {})
            if not c.get("weeks"):
                L.append(f"| {name} | {p0(base['win']) if base else '—'} | {ZONE_VI[z]} | 0 | 0 | — | — | không có tuần |")
                continue
            ci = c.get("ci") or [None, None]
            L.append(f"| {name} | {p0(base['win']) if base else '—'} | {ZONE_VI[z]} | {c['weeks']} | {c['episodes']} | {p0(c['win'])} | {sp_(c['diff'])} ({sp_(ci[0])} đến {sp_(ci[1])}) | "
                     f"{VERDICT.get(c.get('verdict'), c.get('verdict'))} |")
    se = o["sell"]
    L += ["", "## Bên bán: chấm lại với chu kỳ có holdout", "",
          "Chu kỳ: " + "; ".join(f"{a[:7]} → {b[:7]}" for a, b in se["cycles"]) + ". \"Đáng tin\" chỉ khi tiêu chí đúng nhiều hơn mốc ở CẢ hai chu kỳ gần nhất.", "",
          "| Tiêu chí | Số đợt | Đúng / đã biết kết quả | Theo chu kỳ: đúng/đợt (mốc) | Đáng tin? |", "|---|---|---|---|---|"]
    for name, c in se["criteria"].items():
        cyc = "; ".join(f"{x['cycle']}: {x['right']}/{x['episodes']} ({p0(x['base_lower'])})" for x in c["cycles"])
        L.append(f"| {name} | {c['episodes']} | {c['right']}/{c['done']} | {cyc} | {'**có**' if c['trusted'] == 'dang_tin' else 'không'} |")
    L += ["", "| Quy tắc | Giai đoạn | Tài sản so với giữ nguyên | Số lần bán | Mua lại rẻ hơn / đã mua lại |", "|---|---|---|---|---|"]
    for s in se["sims"]:
        for c in s["cycles"]:
            L.append(f"| Bán {fmt.pct(s['frac'])} khi ≥{s['trigger']} nhóm | {c['period']} | {fmt.pct(c['ratio'] - 1, 1, sign=True)} | {c['sales']} | {c['right']} / {c['closed']} |")
    lst = se["last"]
    n_tr = sum(c["trusted"] == "dang_tin" for c in se["criteria"].values())
    L += ["", f"Tiêu chí bên bán đáng tin: **{n_tr}**. Tuần cuối ({fmt.date(lst['date'])}): {lst['groups_on']} nhóm bật"
          + (f" ({', '.join(lst['criteria_on'])})" if lst["criteria_on"] else "") + ".", ""]
    return "\n".join(L)
