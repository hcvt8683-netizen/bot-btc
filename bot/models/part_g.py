"""Part G runner: zone results split by Fed regime (data until eval_end, 31/12/2023) and the macro event listing relative
to the latest data cut-off. Writes data/results/part_g.json and docs/MACRO_G.md (Vietnamese)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.backtest import current_bot, measure
from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.data import pit_store as ps
from bot.features import weekly_close as wc
from bot.i18n import fmt
from bot.models import part_c, part_d, zones as zn
from bot.report import events as ev
from bot.report.measure_b import zones_from

REGIMES = ["tang", "giu", "giam"]
REG_VI = {"tang": "tăng", "giu": "giữ", "giam": "giảm", None: "—"}
ZONE_VI = {"phai": "Phải mua", "cannhac": "Cân nhắc mua", "khong": "Không nên mua"}
EV_VI = {"fomc": "Quyết định lãi suất FOMC", "cpi": "Chỉ số giá tiêu dùng Mỹ (CPI)", "pce": "Chỉ số giá chi tiêu PCE", "opex": "Đáo hạn quyền chọn BTC hằng tháng"}
VERDICT = {"chua_co_loi_the": "chưa có lợi thế", "hon_moc": "hơn mốc", "kem_moc": "**kém mốc**", "it_dot": "ít đợt (< 3)"}


def strategies(sp: dict, rb: dict) -> dict[str, tuple[pd.Series, np.ndarray]]:
    """Zone per week and execution price per week: PA3 as in Part B, the three Part D strategies with hysteresis."""
    end = pd.Timestamp(str(rb["holdout_start"])) - pd.Timedelta(days=1)
    tb = wc.load(end + pd.Timedelta(days=1))  # Monday 01/01/2024 only as the exit price of the last week (as in Part B)
    tb = tb[tb.index <= end]
    z = zones_from(current_bot.series(current_bot.export(), "pa3"), tb.index)
    first = z.first_valid_index()
    out = {"Bot hiện tại (PA3)": (z.loc[first:], tb["exec_monday"].to_numpy(dtype=float)[tb.index >= first])}
    t = part_c.table(pd.Timestamp(str(sp["model"]["eval_end"])))
    zc = sp["zones"]
    for name, (rank, price) in part_d.strategy_ranks(t, sp).items():
        out[name] = (zn.hysteresis_zones(rank, zc["thresholds"], zc["hysteresis"]), price)
    return out


def by_regime(z: pd.Series, price: np.ndarray, reg: pd.Series, horizons: list[int], n_boot: int, seed: int, gap: int) -> dict:
    """Uniform zone table inside each regime: forward returns use the full price path, the baseline is every week of the
    same regime in the same sample."""
    known = z.notna().to_numpy()
    r = reg.reindex(z.index).to_numpy(dtype=object)
    out = {}
    for g in REGIMES:
        m = (r == g) & known
        eps = measure.episodes(m, gap)
        if not m.any():
            out[g] = {"weeks": 0, "episodes": 0}
            continue
        tab = measure.zone_table(z.where(m, None), price, horizons, zn.ORDER, n_boot=n_boot, seed=seed, gap=gap)
        out[g] = {"weeks": int(m.sum()), "episodes": len(eps), "from": z.index[m][0].strftime("%Y-%m-%d"), "to": z.index[m][-1].strftime("%Y-%m-%d"),
                  "table": tab, "monotone": measure.monotone(tab, ["phai", "cannhac", "__baseline__", "khong"])}
    return out


def live_state(mc: dict) -> dict:
    """Latest Sunday close in the stored data, the Fed regime then (Fed series only, no BTC outcomes) and the event listing."""
    cm = ps.load_history("coinmetrics")
    last_day = pd.Timestamp(cm["date"].max())
    sunday = last_day - pd.Timedelta(days=(last_day.weekday() + 1) % 7)
    fed = ps.load_history("fred_DFEDTARU")
    fed = fed[fed["date"] <= sunday]
    sundays = pd.date_range("2011-01-02", sunday, freq="W-SUN")
    reg = wc.fed_regime(fed, sundays)
    r = reg.to_numpy(dtype=object)
    cur = r[-1]
    since = sundays[max(i for i in range(len(r)) if i == 0 or r[i - 1] != cur) if cur is not None else -1]
    full = {g: len(measure.episodes(r == g, 4)) for g in REGIMES}
    lst = ev.listing(ev.cutoff_of(sunday), ev.utc_now(), mc["events"]["ahead_days"], types=tuple(mc["events"]["types"]))
    return {"sunday": sunday, "regime": cur, "since": since, "episodes_full": full, "fed_last": float(fed["fed_upper"].iloc[-1]),
            "fed_last_date": pd.Timestamp(fed["date"].iloc[-1]), "events": lst}


def run(write: bool = True) -> dict:
    sp = part_c.spec()
    mc = sp["macro"]
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    eval_end = pd.Timestamp(str(sp["model"]["eval_end"]))
    t = part_c.table(eval_end)
    live = live_state(mc)
    out = {"eval_end": eval_end.strftime("%Y-%m-%d"), "regime_eval_end": t["fed_regime"].iloc[-1], "live": live, "strategies": {}}
    for name, (z, price) in strategies(sp, rb).items():
        res = by_regime(z, price, t["fed_regime"], rb["horizons_weeks"], rb["bootstrap_n"], rb["seed"], rb["episode_gap_weeks"])
        cur = res.get(live["regime"], {})
        out["strategies"][name] = {"from": z.first_valid_index().strftime("%Y-%m-%d"), "weeks": int(z.notna().sum()), "regimes": res,
                                   "current_episodes": cur.get("episodes", 0), "warn": cur.get("episodes", 0) < mc["warn_below_episodes"]}
    if write:
        (DATA / "results" / "part_g.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (ROOT / "docs" / "MACRO_G.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    return out


def markdown(o: dict) -> str:
    mc = part_c.spec()["macro"]
    h = mc["horizon_main"]
    lv = o["live"]
    sp = lambda x: "—" if x is None else fmt.pct(x, 1, sign=True)  # noqa: E731
    p0 = lambda x: "—" if x is None else fmt.pct(x)  # noqa: E731
    L = ["# Phần G: vĩ mô và sự kiện", "",
         f"Đăng ký trước: `config/candidates.yaml` mục `macro` (commit `1548ac2`). Kết quả tính đến **{fmt.date(o['eval_end'])}** (holdout khóa).", "",
         f"- Chế độ Fed: {mc['regime']}.",
         f"- Mốc so sánh: {mc['baseline']}. Đếm đợt và bootstrap như mọi bảng khác; dưới 3 đợt thì \"ít đợt\", không kết luận.", "",
         "## 1. Chế độ Fed hiện tại", "",
         f"- Số liệu Fed mới nhất: trần lãi suất {fmt.dec(lv['fed_last'], 2)}% (ngày {fmt.date(lv['fed_last_date'])}). "
         f"Chế độ tại Chủ nhật {fmt.date(lv['sunday'])}: **{REG_VI[lv['regime']]}** (từ {fmt.date(lv['since'])}).",
         "- Số đợt mỗi chế độ từ 2011 đến nay (chỉ dùng chuỗi lãi suất): " + ", ".join(f"{REG_VI[g]} {n}" for g, n in lv["episodes_full"].items()) + ".",
         f"- Tại {fmt.date(o['eval_end'])} (cuối giai đoạn đánh giá): {REG_VI[o['regime_eval_end']]}.", ""]
    warn = [(n, s) for n, s in o["strategies"].items() if s["warn"]]
    for n, s in o["strategies"].items():
        L.append(f"- {n}: chế độ {REG_VI[lv['regime']]} có **{s['current_episodes']} đợt** trong giai đoạn đánh giá ({fmt.date(s['from'])} → {fmt.date(o['eval_end'])}).")
    if warn:
        L += ["", f"> **Cảnh báo:** chế độ hiện tại ({REG_VI[lv['regime']]}) có dưới {mc['warn_below_episodes']} đợt trong lịch sử đánh giá của "
              + ", ".join(n for n, _ in warn) + ". Kết quả của các chiến lược này trong chế độ hiện tại không đủ để tin."]
    L += ["", f"## 2. Kết quả các khung theo chế độ Fed (giá cao hơn sau {h} tuần)", "",
          "Mỗi ô so khung với mọi tuần **cùng chế độ** của cùng chiến lược. Chênh = tỷ lệ của khung trừ mốc, khoảng tin cậy 95% bằng bootstrap khối.", ""]
    count = {}
    for n, s in o["strategies"].items():
        L += [f"### {n}", "", "| Chế độ | Tuần (đợt chế độ) | Mốc cùng chế độ | Khung | Số tuần | Số đợt | Tỷ lệ của khung | Chênh (KTC 95%) | Kết luận |",
              "|---|---|---|---|---|---|---|---|---|"]
        for g in REGIMES:
            rg = s["regimes"][g]
            if not rg["weeks"]:
                L.append(f"| {REG_VI[g]} | 0 | — | — | — | — | — | — | không có tuần nào |")
                continue
            base = rg["table"]["baseline"][h] if "baseline" in rg["table"] else None
            for z in zn.ORDER:
                c = rg["table"]["zones"][z][h]
                if not c.get("weeks"):
                    cell = "| — | — | không có tuần |"
                else:
                    count[c.get("verdict")] = count.get(c.get("verdict"), 0) + 1
                    ci = c.get("ci") or [None, None]
                    cell = (f"| {p0(c['win'])} | {sp(c['diff'])} ({sp(ci[0])} đến {sp(ci[1])}) | {VERDICT.get(c.get('verdict'), c.get('verdict'))} |")
                L.append(f"| {REG_VI[g]} | {rg['weeks']} ({rg['episodes']}) | {p0(base['win']) if base else '—'} | {ZONE_VI[z]} | {c.get('weeks', 0)} | {c.get('episodes', 0)} {cell}")
        L.append("")
    tot = sum(count.values())
    L += [f"Tổng cộng {tot} ô có tuần ở kỳ {h} tuần: " + ", ".join(f"{VERDICT[k]} {v}" for k, v in count.items() if k in VERDICT) + ". "
          f"Cả phụ lục có {len(o['strategies'])} chiến lược × 3 chế độ × 3 khung × 4 kỳ hạn; với chừng ấy phép so, vài ô \"hơn mốc\" hoặc \"kém mốc\" "
          "đứng riêng lẻ có thể chỉ do may rủi.", ""]
    e = lv["events"]
    L += ["## 3. Sự kiện sau mốc chốt dữ liệu", "",
          f"- Mốc chốt dữ liệu: giá đóng Chủ nhật {fmt.date(lv['sunday'])} (23:59:59 UTC). Lúc tạo báo cáo: {e['now'].strftime('%d/%m/%Y %H:%M')} UTC. "
          f"Chỉ liệt kê sự kiện sau mốc chốt, tới {e['until'].strftime('%d/%m/%Y %H:%M')} UTC; sự kiện trước mốc chốt không bao giờ được liệt kê.", ""]
    if e["after_cutoff"]:
        L += ["**Đã xảy ra sau mốc chốt, trước lúc phát hành (gắn cờ):**", ""]
        L += [f"- ⚑ {(x['time'] + pd.Timedelta(hours=7)).strftime('%d/%m/%Y %H:%M')} giờ Việt Nam: {EV_VI[x['type']]}" for x in e["after_cutoff"]]
        L += ["", f"> Tín hiệu tuần này **chưa tính** phản ứng của thị trường với các sự kiện trên. Nên chạy lại bot sau giá đóng tuần kế tiếp "
              f"(Chủ nhật {fmt.date(e['rerun_after'])})."]
    else:
        L.append("- Không có sự kiện nào giữa mốc chốt và lúc phát hành.")
    L += ["", "**Sắp tới:**", ""]
    L += [f"- {(x['time'] + pd.Timedelta(hours=7)).strftime('%d/%m/%Y %H:%M')} giờ Việt Nam: {EV_VI[x['type']]}" for x in e["upcoming"]] or ["- Không có sự kiện trong cửa sổ."]
    if e["stale"]:
        L += ["", "> **Lịch chưa đủ:** " + "; ".join(f"{EV_VI[k]} chỉ có tới {fmt.date(v) if v is not None else '—'}" for k, v in e["stale"].items())
              + ". Cần chạy `python tools/update_events.py` rồi duyệt khác biệt; trước đó, \"không có sự kiện\" của các loại này không đáng tin."]
    L += ["", "## 4. Kết luận Phần G", ""]
    hm = count.get("hon_moc", 0)
    L += [f"- Theo chế độ Fed, ở kỳ {h} tuần có {hm} ô \"hơn mốc\" trên {tot} ô. "
          + ("Không ô nào đủ để nói khung có lợi thế trong một chế độ riêng." if hm == 0 else "Các ô này rời rạc, ít đợt, nên chưa đủ để nói khung có lợi thế trong chế độ đó."),
          "- Chế độ Fed chỉ dùng để chia nhóm báo cáo, không đưa vào mô hình hay hệ số giải ngân.",
          "- Sự kiện: giờ chỉ liệt kê sau mốc chốt dữ liệu; sự kiện rơi vào khoảng giữa mốc chốt và lúc phát hành được gắn cờ kèm đề nghị chạy lại.", ""]
    return "\n".join(L)
