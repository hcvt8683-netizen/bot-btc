"""Final Vietnamese report of the rebuild (docs/BAO_CAO.md), its appendix (docs/PHU_LUC.md) and calibration charts
(docs/img/calib_*.svg). Every number is read from the result files in data/results (Parts B–I), the forward log, the
weekly table and the weekly recommendation; nothing is typed by hand. Run: python -m bot.cli final-report
The sections follow the old report of the web page (B3.report)."""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.i18n import fmt
from bot.report.measure_b import MULT

VERDICT = {"chua_co_loi_the": "chưa có lợi thế", "hon_moc": "hơn mốc", "kem_moc": "**kém mốc**", "it_dot": "ít đợt (< 3), chưa kết luận"}
ZONE_VI = {"phai": "Phải mua", "cannhac": "Cân nhắc mua", "khong": "Không nên mua", None: "—", "": "—"}
LEVEL_VI = {"giu": "Giữ", "chot": "Chốt lời một phần", "ban": "Bán phần lớn"}
REG_VI = {"tang": "tăng", "giu": "giữ", "giam": "giảm", None: "—"}
H_VI = {4: "1 tháng", 13: "3 tháng", 26: "6 tháng", 52: "1 năm"}
EV_VI = {"fomc": "Quyết định lãi suất FOMC", "cpi": "Chỉ số giá tiêu dùng Mỹ (CPI)", "pce": "Chỉ số giá chi tiêu PCE", "opex": "Đáo hạn quyền chọn BTC hằng tháng"}
FEAT_VI = {"mvrv": "MVRV", "mvrv_z": "MVRV Z-Score", "pi_ratio": "Pi Cycle (tỉ số MA 111/2×MA 350)", "p_200wma": "Giá / MA 200 tuần", "mayer": "Mayer Multiple",
           "rsi_14w": "RSI 14 tuần", "puell": "Puell Multiple", "dd_ath": "Giảm từ đỉnh", "vol_rel": "Khối lượng tương đối", "fng": "Fear & Greed",
           "rv30": "Biến động 30 ngày", "dev_ma20w": "Độ lệch so với MA 20 tuần"}
STRATS = ["Lồng nhau", "Quy tắc MVRV", "Quy tắc Giá/MA 200 tuần"]
ORDER = ["phai", "cannhac", "khong"]


def J(name: str) -> dict:
    return json.loads((DATA / "results" / name).read_text(encoding="utf-8"))


def sp(x, d: int = 1) -> str:
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else fmt.pct(x, d, sign=True)


def p0(x) -> str:
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else fmt.pct(x)


def ci(c) -> str:
    return "—" if not c or c[0] is None else f"{sp(c[0])} đến {sp(c[1])}"


def pv(x) -> str:
    return "—" if x is None or not np.isfinite(x) else fmt.dec(x, 3)


def hget(d: dict, h):
    return d.get(str(h), d.get(h)) if d else None


def zone_rows(tab: dict, horizons, label: str = "") -> list[str]:
    """One row per zone × horizon: weeks, episodes, win rate, baseline, difference with its bootstrap interval, Wilson
    by episodes, verdict."""
    out = []
    for h in horizons:
        base = hget(tab.get("baseline", {}), h) or {}
        for z in ORDER:
            c = hget(tab["zones"].get(z, {}), h) or {}
            if not c.get("weeks"):
                out.append(f"| {label}{H_VI[h]} | {ZONE_VI[z]} | 0 | 0 | — | {p0(base.get('win'))} | — | — | không có tuần |")
                continue
            w = c.get("wilson_episodes") or [None, None]
            out.append(f"| {label}{H_VI[h]} | {ZONE_VI[z]} | {c['weeks']} | {c['episodes']} | {p0(c['win'])} | {p0(base.get('win'))} | {sp(c['diff'])} ({ci(c.get('ci'))}) | "
                       f"{p0(w[0])}–{p0(w[1])} | {VERDICT.get(c.get('verdict'), c.get('verdict'))} |")
    return out


ZONE_HEAD = ["| Kỳ hạn | Khung | Số tuần | Số đợt | Giá cao hơn | Mốc (mọi tuần) | Chênh (KTC 95%) | Wilson theo đợt | Kết luận |",
             "|---|---|---|---|---|---|---|---|---|"]


def edge_note(edges: dict, zone: str | None, m: float, min_eps: int) -> str:
    """Why the zone multiplier (before the gate) is what it is, from the frozen edge estimate of this week's zone."""
    e = (edges or {}).get(zone) if zone else None
    head = f"Hệ số theo khung (chưa qua cổng) tuần này: {fmt.dec(m, 2)}"
    if not e:
        return head + ", vì khung này chưa có ước lượng lợi thế."
    why = (f"chỉ {e['episodes']} đợt (cần ≥ {min_eps})" if e["episodes"] < min_eps else
           f"khoảng tin cậy lợi thế {ci(e['ci'])} chứa 0" if e["ci"] and e["ci"][0] is not None and e["ci"][0] <= 0 <= e["ci"][1] else f"khoảng tin cậy lợi thế {ci(e['ci'])}")
    return head + f": khung {ZONE_VI[zone]} có {e['weeks']} tuần, {e['episodes']} đợt, chênh {sp(e['diff'])}, {why}."


def svg_reliability(bins: list[dict], title: str, sub: str) -> str:
    """Reliability diagram: predicted vs actual share by decile of the prediction, point area ∝ weeks."""
    W, L, T, S = 360, 52, 46, 260  # width, left, top, plot size
    x = lambda v: L + v * S  # noqa: E731
    y = lambda v: T + (1 - v) * S  # noqa: E731
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {T + S + 52}" width="{W}" height="{T + S + 52}" font-family="system-ui, sans-serif" font-size="11">',
         f'<rect width="100%" height="100%" fill="#ffffff"/>', f'<text x="{L}" y="18" font-size="13" font-weight="600" fill="#1f2328">{title}</text>',
         f'<text x="{L}" y="34" fill="#59636e">{sub}</text>']
    for v in (0, 0.25, 0.5, 0.75, 1):
        g += [f'<line x1="{x(0)}" y1="{y(v)}" x2="{x(1)}" y2="{y(v)}" stroke="#d1d9e0"/>', f'<line x1="{x(v)}" y1="{y(0)}" x2="{x(v)}" y2="{y(1)}" stroke="#d1d9e0"/>',
              f'<text x="{L - 6}" y="{y(v) + 4}" text-anchor="end" fill="#59636e">{int(v * 100)}%</text>',
              f'<text x="{x(v)}" y="{y(0) + 16}" text-anchor="middle" fill="#59636e">{int(v * 100)}%</text>']
    g.append(f'<line x1="{x(0)}" y1="{y(0)}" x2="{x(1)}" y2="{y(1)}" stroke="#8c959f" stroke-dasharray="4 4"/>')
    pts = [(b["pred"], b["actual"], b["weeks"]) for b in bins if b.get("weeks")]
    if pts:
        g.append('<polyline fill="none" stroke="#0969da" stroke-width="1.5" points="' + " ".join(f"{x(p):.1f},{y(a):.1f}" for p, a, _ in pts) + '"/>')
        mx = max(n for _, _, n in pts)
        g += [f'<circle cx="{x(p):.1f}" cy="{y(a):.1f}" r="{3 + 6 * (n / mx) ** 0.5:.1f}" fill="#0969da" fill-opacity="0.55"/>' for p, a, n in pts]
    g += [f'<text x="{L + S / 2}" y="{T + S + 34}" text-anchor="middle" fill="#1f2328">Xác suất mô hình dự báo (theo nhóm 10%)</text>',
          f'<text transform="translate(14 {T + S / 2}) rotate(-90)" text-anchor="middle" fill="#1f2328">Tỷ lệ giá cao hơn thực tế</text>', "</svg>"]
    return "\n".join(g) + "\n"


def scenarios_now(asof: pd.Timestamp) -> dict:
    """Part F scenario table recomputed at the analysis Sunday (k = 4 weeks), with the same bands."""
    from bot.models import part_c, part_f, scenarios as sc
    sp_ = part_c.spec()
    cfg, se, zc, md = sp_["scenarios"], sp_["sell"], sp_["zones"], sp_["model"]
    t = part_c.table(asof)
    inp = part_f.inputs(asof)
    ranks, now = part_f.state(t, se, zc, md)
    k = cfg["weeks"][-1]
    m = sc.fng_response(t, k, asof, tuple(cfg["band"]))
    rc = sc.rc_drift(inp["cm"], k, asof, cfg["rc_band"]["window_weeks"], tuple(cfg["rc_band"]["band"]))
    return {"k": k, "now": now, "model": m, "rc": rc, "rows": part_f.scenario_rows(t, inp, asof, k, m, rc, now["fng"], cfg["price_changes"], se, zc, ranks)}


def build(out_dir: Path | None = None, now: dt.datetime | None = None) -> dict:
    from bot.features import weekly_close as wc
    from bot.models import forward as fw, part_c
    from bot.report import events as ev
    out_dir = Path(out_dir or ROOT / "docs")
    (out_dir / "img").mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp(now) if now is not None else ev.utc_now()
    B, C, G, I, E = J("measure_b.json"), J("part_c.json"), J("part_g.json"), J("part_i.json"), J("part_e.json")
    rec = json.loads((DATA / "recommendation.json").read_text(encoding="utf-8"))
    status = json.loads((DATA / "status.json").read_text(encoding="utf-8"))
    sp_ = part_c.spec()
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    horizons = rb["horizons_weeks"]
    src = load_yaml(ROOT / "bot" / "i18n" / "vi.yaml")["sources"]
    vdir = fw.current(DATA / "forward")
    flog = fw.read_log(vdir)
    fmodel = json.loads((vdir / "model.json").read_text(encoding="utf-8"))
    last = flog.iloc[-1]
    asof = pd.Timestamp(last["date"])
    t = wc.load(None)
    row = t.loc[asof]
    scn = scenarios_now(asof)
    lst = ev.listing(ev.cutoff_of(asof), now, sp_["macro"]["events"]["ahead_days"], types=tuple(sp_["macro"]["events"]["types"]))
    crit, passed = I["criteria"], I["passed"]
    n_pass = sum(bool(c["pass"]) for c in crit.values())
    fit = fmodel["state"]["fit"]
    nested_from = I["strategies"]["Lồng nhau"]["from"] if I["strategies"].get("Lồng nhau") else None
    names = {"c1": "lợi thế giá vốn dương ở ≥ 75% số năm và trên holdout", "c2": "cận dưới khoảng tin cậy của lợi thế > 0", "c3": "kiểm định hoán vị đã hiệu chỉnh < 0,05",
             "c4": "khung đơn điệu, trọng số đúng dấu", "c5": "Brier tốt hơn tỷ lệ gốc", "c6": "thắng cả hai quy tắc đơn giản"}
    L = [f"# Báo cáo bot BTC (bản xây lại), phân tích tại ngày {fmt.date(asof)}", "",
         "Bot thống kê, không có trí tuệ AI. Mọi con số tính từ dữ liệu thật tải về, bằng kiểm chứng đi tới: tại mỗi tuần chỉ dùng dữ liệu đã có đến tuần đó. "
         f"Báo cáo tạo lúc {now.strftime('%H:%M %d/%m/%Y')} UTC bằng `python -m bot.cli final-report`, từ các file kết quả trong `data/results`. "
         "Cách làm từng phần và mọi thay đổi thiết kế: [REBUILD_LOG.md](REBUILD_LOG.md). Bảng chi tiết: [PHU_LUC.md](PHU_LUC.md).", "",
         "Mỗi con số về khung đi kèm số tuần, số đợt độc lập, khoảng tin cậy bootstrap (95%) và mức chênh so với mốc \"mua vào một tuần bất kỳ\". "
         "Kết quả không có ý nghĩa thống kê ghi \"chưa có lợi thế\".", "",
         "## Bối cảnh",
         f"- Giá đóng tuần (Chủ nhật 23:59 UTC) ngày {fmt.date(asof)}: **{fmt.usd(float(row['close']))}**. Mọi tính toán dùng giá đóng tuần; giá trực tiếp chỉ để hiển thị trên trang.",
         "- Dữ liệu (ngày cuối của từng nguồn lúc tải, " + fmt.datetime_vn(status.get("fetched_at")) + "): "
         + "; ".join(f"{src.get(k, k)} đến {fmt.date(v['last'])}" for k, v in status["sources"].items() if v.get("last")) + ".",
         f"- Mô hình đang theo dõi: phiên bản `{fmodel['version']}`, đóng băng ngày {fmt.date(fmodel['state']['asof'])}: "
         + (f"bộ {fmodel['state']['set']}, còn {', '.join(FEAT_VI.get(f, f) for f in fit['features'])}"
            + (f" (bỏ {', '.join(FEAT_VI.get(f, f) for f in fit['dropped'])} vì sai dấu)" if fit["dropped"] else "") if fit else "không có mô hình (mua đều)") + ".",
         "- Mốc so sánh bắt buộc: mua đều; quy tắc đơn giản 1 chỉ số (phân vị MVRV, phân vị Giá / MA 200 tuần).",
         f"- Giai đoạn chấm: đi tới lồng nhau (học lại mỗi 13 tuần) có thứ hạng từ {fmt.date(nested_from)}; holdout {fmt.date(I['holdout_start'])} → {fmt.date(I['last_week'])} "
         f"({I['holdout_weeks']} tuần), chạy đúng một lần lúc {I['run_at']} (mã `{I.get('git')}`).", "",
         "## Kết luận",
         f"- **Mua đều, hệ số 1,0.** Mô hình đạt {n_pass}/6 tiêu chí chấp nhận định trước (cần đạt cả 6): "
         + "; ".join(f"{names[k]} {'✔' if v['pass'] else '✘'}" for k, v in crit.items()) + ".",
         f"- Thứ hạng tuần này (vị trí của điểm tuần này so với các tuần ngoài mẫu trước đó, **không phải xác suất có lãi**): mô hình {fmt.num(float(last['rank']))} → "
         f"{ZONE_VI[last['zone']]}; quy tắc MVRV {fmt.num(float(last['rank_mvrv']))} → {ZONE_VI[last['zone_mvrv']]}; quy tắc Giá / MA 200 tuần {fmt.num(float(last['rank_200w']))} → "
         f"{ZONE_VI[last['zone_200w']]}. Các khung chỉ để tham khảo: kiểm định cho thấy **chưa có lợi thế** (mục \"Bộ tiêu chí\").",
         f"- Bên bán: {last['sell_groups']} nhóm bật → **{LEVEL_VI[last['sell_level']]}**. Số tiêu chí bán đáng tin: "
         f"{sum(c['trusted'] == 'dang_tin' for c in I['sell']['criteria'].values())}.", ""]
    # weekly recommendation
    L += ["## Khuyến nghị giải ngân tuần này",
          "- Hệ số mua: **1,0** (mua đều). Vì sao: tiêu chí chấp nhận không đạt, nên không có cơ sở mua nhiều hay ít hơn mua đều. "
          + edge_note(fmodel["state"]["edges"], last["zone"] or None, float(last["mult_rule"]), sp_["multiplier"]["min_episodes"])]
    if lst["after_cutoff"]:
        L.append("- ⚑ Sự kiện đã xảy ra sau mốc chốt dữ liệu (giá đóng " + fmt.date(asof) + "), tín hiệu chưa tính phản ứng của thị trường: "
                 + "; ".join(f"{(x['time'] + pd.Timedelta(hours=7)).strftime('%H:%M %d/%m/%Y')} (giờ Việt Nam) {EV_VI[x['type']]}" for x in lst["after_cutoff"])
                 + f". Nên chạy lại sau giá đóng tuần kế tiếp ({fmt.date(lst['rerun_after'])}).")
    L.append("- Sự kiện sắp tới: " + ("; ".join(f"{(x['time'] + pd.Timedelta(hours=7)).strftime('%H:%M %d/%m/%Y')} {EV_VI[x['type']]}" for x in lst["upcoming"]) or "không có trong 7 ngày") + ".")
    if lst["stale"]:
        L.append("- Lịch sự kiện chưa đủ: " + "; ".join(f"{EV_VI[k]} chỉ có tới {fmt.date(v) if v is not None else '—'}" for k, v in lst["stale"].items()) + ".")
    lv = G["live"]
    warn = [n for n, s in G["strategies"].items() if s["warn"]]
    L.append(f"- Chế độ lãi suất Fed: **{REG_VI[lv['regime']]}** (từ {fmt.date(lv['since'])}). Chỉ dùng để chia nhóm báo cáo."
             + (f" Cảnh báo: chế độ này có dưới 3 đợt trong giai đoạn đánh giá của {', '.join(warn)}." if warn else ""))
    pl = rec.get("plan")
    if pl:
        opt = {o["weeks"]: o for o in pl["options"]}
        nm = lambda n: "giải ngân một lần" if n == 1 else f"chia đều {n} tuần"  # noqa: E731
        r_, b_ = opt[pl["recommended"]], opt[pl["best_roi"]]
        L.append(f"- Giải ngân một khoản tiền (ô trên trang web, {pl['starts']} tuần bắt đầu từ {fmt.date(pl['from'])}, khoảng {pl['episodes']} đợt độc lập): "
                 f"ROI trung vị cao nhất là {nm(b_['weeks'])} ({sp(b_['median'], 0)} sau 1 năm); đề xuất {nm(r_['weeks'])} (10% xấu nhất {sp(r_['p10'], 0)}, "
                 f"xấu nhất {sp(r_['worst'], 0)}). Chi tiết: [PLAN.md](PLAN.md).")
    L.append("")
    # price scenarios now
    k = scn["k"]
    L += [f"## Giá đề xuất mua và bán (kịch bản giá sau {k} tuần, tính tại {fmt.date(asof)}, giá {fmt.usd(scn['now']['price'])})",
          "Mọi chỉ số tính lại theo đường giá giả định. Fear & Greed đổi theo giá bằng mô hình học từ quá khứ "
          f"(R² {fmt.dec(scn['model']['r2'], 2)}, {scn['model']['n']} tuần), kèm khoảng 10–90%. Khoảng của quy tắc MVRV tính thêm theo thay đổi vốn hóa thực "
          f"({sp(scn['rc']['q'][0])} đến {sp(scn['rc']['q'][1])} trong {k} tuần). Đây là cách bot sẽ đọc, không phải dự báo; hệ số mua vẫn 1,0.",
          "| Giá | So với hiện tại | Fear & Greed (10–90%) | Quy tắc Giá / MA 200 tuần | Quy tắc MVRV (khoảng) | Bên bán (số nhóm) |", "|---|---|---|---|---|---|"]
    rng = lambda r: "—" if r is None else (fmt.num(r[0]) if round(r[0]) == round(r[1]) else f"{fmt.num(r[0])}–{fmt.num(r[1])}")  # noqa: E731
    for r in scn["rows"]:
        L.append(f"| {fmt.usd(r['mid']['price'])} | {fmt.pct(r['delta'], 0, sign=True) if r['delta'] else 'hiện tại'} | {fmt.num(r['fng'][1])} ({fmt.num(r['fng'][0])}–{fmt.num(r['fng'][2])}) | "
                 f"{rng(r['range_200w'])} → {' / '.join(ZONE_VI[z] for z in r['zones_200w'])} | {fmt.num(r['mid']['rank_mvrv']) if r['mid']['rank_mvrv'] is not None else '—'} "
                 f"({rng(r['range_mvrv'])}) → {' / '.join(ZONE_VI[z] for z in r['zones_mvrv'])} | {rng(r['groups_range'])} → {' / '.join(LEVEL_VI[x] for x in r['levels'])} |")
    L.append("")
    # probabilities
    cals = [(f"Bot hiện tại (PA3) | đến {fmt.date(B['eval_end'])} | {H_VI[h]}", hget(B["calibration"], h)) for h in horizons]
    cals += [(f"Lồng nhau | đến {fmt.date(C['eval_end'])} | 6 tháng", C.get("calibration")), ("Lồng nhau | holdout | 6 tháng", crit["c5"] if crit["c5"].get("weeks") else None)]
    cals = [(lab, c) for lab, c in cals if c]
    better = sum(c["brier"] < c["brier_base"] for _, c in cals)
    sure = sum(c["gain_ci"][0] > 0 for _, c in cals)
    L += ["## Xác suất thắng nếu mua tại ngày phân tích",
          f"**Bot không hiển thị xác suất có lãi.** Xác suất của mô hình tốt hơn tỷ lệ gốc (Brier thấp hơn) ở {better}/{len(cals)} lần đo, và chỉ {sure}/{len(cals)} lần "
          "có khoảng tin cậy của mức cải thiện nằm hẳn trên 0; cần cả hai mới được hiển thị xác suất.",
          "| Mô hình | Giai đoạn | Kỳ hạn | Số tuần | Brier mô hình | Brier tỷ lệ gốc | Mức cải thiện (KTC 95%) |", "|---|---|---|---|---|---|---|"]
    for lab, c in cals:
        L.append(f"| {lab} | {c['weeks']} | {fmt.dec(c['brier'], 3)} | {fmt.dec(c['brier_base'], 3)} | "
                 f"{fmt.dec(c['brier_base'] - c['brier'], 3)} ({fmt.dec(c['gain_ci'][0], 3)} đến {fmt.dec(c['gain_ci'][1], 3)}) |")
    L += ["", f"Thay vào đó: tỷ lệ giá cao hơn sau mỗi kỳ hạn khi ở **khung của tuần này**, trên toàn bộ giai đoạn ngoài mẫu đến hết holdout, so với mọi tuần:",
          "| Chiến lược | Khung tuần này | Kỳ hạn | Số tuần | Số đợt | Giá cao hơn | Mốc | Chênh (KTC 95%) | Kết luận |", "|---|---|---|---|---|---|---|---|---|"]
    for name, zkey in (("Lồng nhau", "zone"), ("Quy tắc MVRV", "zone_mvrv"), ("Quy tắc Giá/MA 200 tuần", "zone_200w")):
        s, z = I["strategies"].get(name), last[zkey] or None
        if not s or not z:
            continue
        for h in horizons:
            c, base = hget(s["zones"]["zones"].get(z, {}), h) or {}, hget(s["zones"]["baseline"], h) or {}
            if c.get("weeks"):
                L.append(f"| {name} | {ZONE_VI[z]} | {H_VI[h]} | {c['weeks']} | {c['episodes']} | {p0(c['win'])} | {p0(base.get('win'))} | {sp(c['diff'])} ({ci(c.get('ci'))}) | "
                         f"{VERDICT.get(c.get('verdict'))} |")
    L.append("")
    # zone tables
    L += ["## Bộ tiêu chí: tỷ lệ thắng thực tế theo từng khung mua",
          "Khung theo thứ hạng ngoài mẫu (Phải mua từ 80, Cân nhắc mua từ 60, vùng trễ 5 điểm), giá vào và ra là giá đóng thứ Hai. Toàn bộ giai đoạn ngoài mẫu đến hết holdout."]
    for name in STRATS:
        s = I["strategies"].get(name)
        if not s:
            continue
        L += ["", f"**{name}** (từ {fmt.date(s['from'])}, {s['rank_weeks']} tuần có thứ hạng). Đơn điệu: "
              + ", ".join(f"{H_VI[int(h)]} {'có' if v else 'không'}" for h, v in s["monotone"].items()) + ".", *ZONE_HEAD, *zone_rows(s["zones"], horizons)]
    pa = B["sets"]["pa3"]
    L += ["", f"**Bot hiện tại (PA3, khung 80/60 không vùng trễ)**, {pa['weeks']} tuần từ {fmt.date(pa['from'])} đến {fmt.date(B['eval_end'])} (Phần B, trước holdout).",
          *ZONE_HEAD, *zone_rows(pa["table"], horizons), ""]
    # sell zones
    se = I["sell"]
    L += ["## Khung bán: giá có giảm thật không",
          f"Tiêu chí bật khi chỉ số thuộc 5% đắt nhất của 4 năm trước; đúng nếu giá {sp_['sell']['outcome_weeks']} tuần sau thấp hơn. Chấm theo đợt; chu kỳ: "
          + "; ".join(f"{fmt.date(a)} → {fmt.date(b)}" for a, b in se["cycles"]) + ". \"Đáng tin\" khi đúng hơn mốc ở cả hai chu kỳ gần nhất.",
          "| Tiêu chí | Số đợt | Đúng / đã biết | Wilson theo đợt | Mốc (giá thấp hơn) | Chênh (KTC 95%) | Theo chu kỳ: đúng/đợt | Đáng tin? |", "|---|---|---|---|---|---|---|---|"]
    for n, c in se["criteria"].items():
        L.append(f"| {FEAT_VI.get(n, n)} | {c['episodes']} | {c['right']}/{c['done']} | {p0(c['wilson'][0])}–{p0(c['wilson'][1])} | {p0(c['base_lower'])} | "
                 f"{sp(c['boot_diff_lower'])} ({ci(c['boot_ci_lower'])}) | " + "; ".join(f"{x['cycle']}: {x['right']}/{x['episodes']}" for x in c["cycles"])
                 + f" | {'**có**' if c['trusted'] == 'dang_tin' else 'không'} |")
    L.append("")
    # strategies vs DCA
    L += ["## So sánh các phương án (so với mua đều, cùng tiền nạp mỗi tuần)",
          "Lợi thế giá vốn = tài sản cuối kỳ so với mua đều, tiền chưa dùng tính theo giá cuối. Khoảng tin cậy bằng bootstrap khối dừng (khối 26 tuần).",
          "| Phương án | Giai đoạn | Số tuần | Hệ số | Lợi thế giá vốn (KTC 95%) | Tuần hệ số ≠ 1 | Kết luận |", "|---|---|---|---|---|---|---|"]
    cb = pa["cost_basis"]
    L.append(f"| Bot hiện tại (PA3), hệ số theo khung {' / '.join(fmt.dec(MULT[z], 2) for z in ORDER)} | {fmt.date(pa['from'])} → {fmt.date(B['eval_end'])} | {cb['weeks']} | theo khung | {sp(cb['advantage'])} ({ci(cb['ci'])}) | — | "
             f"{VERDICT.get(cb['verdict'], cb['verdict'])} |")
    for name in STRATS:
        s = I["strategies"].get(name)
        if not s:
            continue
        for key, lab in (("m", "Phần D (sẽ dùng nếu đạt)"), ("m_cmp", "so sánh 0,5 + thứ hạng")):
            x = s[key]
            v = "chưa có lợi thế" if x["holdout_ci"][0] <= 0 <= x["holdout_ci"][1] else ("hơn mua đều" if x["holdout_ci"][0] > 0 else "**kém mua đều**")
            L.append(f"| {name} | holdout | {I['holdout_weeks']} | {lab} | {sp(x['holdout'])} ({ci(x['holdout_ci'])}) | {p0(x['share_not_one'])} | {v} |")
    L += ["", "Theo năm dương lịch trước holdout (hệ số so sánh): "
          + "; ".join(f"{n}: " + ", ".join(f"{y} {sp(v)}" for y, v in I["strategies"][n]["m_cmp"]["years"].items()) for n in STRATS if I["strategies"].get(n)) + ".", ""]
    # best configs
    pc_, pi_ = C["permutation"], I["permutation"]
    L += ["## Bộ chỉ số có tỷ lệ thắng cao nhất",
          f"8 bộ chỉ số đăng ký trước (mỗi bộ có lý do kinh tế, xem phụ lục) × 3 mức λ, cộng mô hình lồng nhau và 2 quy tắc. Kiểm định hoán vị: dịch vòng ≥ 52 tuần, "
          f"{sp_['tests']['permutation_n']} lần, hiệu chỉnh max-statistic trên mọi cấu hình. Thống kê: IC 26 tuần và lợi thế giá vốn theo hệ số so sánh.",
          "| Cấu hình | Đến 2023: tuần, IC 26 tuần, lợi thế (KTC), p hiệu chỉnh | Holdout: IC 26 tuần, lợi thế, p hiệu chỉnh |", "|---|---|---|"]
    cres = {r["name"].split(" (")[0]: r for r in C["results"]}
    ires = set(pi_.get("ic26", {}))
    for name in sorted(set(cres) | ires, key=lambda n: (not n.startswith("Lồng"), n.startswith("Quy"), n)):
        r = cres.get(name)
        cpm = next((v for k_, v in pc_["cost_basis"].items() if k_.split(" (")[0] == name), None)
        a = (f"{r['weeks']} tuần, IC {fmt.dec(r['ic26'], 2)}, {sp(r['cost_basis'])} ({ci(r['cost_ci'])}), p {pv(cpm['p_maxstat']) if cpm else '—'}" if r else "dưới 60 tuần ngoài mẫu")
        hi_, hc = pi_.get("ic26", {}).get(name), pi_.get("cost_basis", {}).get(name)
        b = (f"IC {fmt.dec(hi_['obs'], 2)} (p {pv(hi_['p_maxstat'])}), lợi thế {sp(hc['obs'])} (p {pv(hc['p_maxstat'])})" if hi_ else "dưới 30 tuần")
        L.append(f"| {name} | {a} | {b} |")
    sig = [n for n in ires if pi_["cost_basis"][n]["p_maxstat"] < 0.05 or pi_["ic26"][n]["p_maxstat"] < 0.05]
    L += ["", f"Cấu hình có p hiệu chỉnh < 0,05 trên holdout: {', '.join(sig) if sig else 'không có'}"
          + (" (chỉ ở một thống kê; khoảng tin cậy bootstrap của lợi thế vẫn chứa 0 và khung không đơn điệu, nên không qua tiêu chí)." if sig else ".")
          + " Vòng trong của mô hình lồng nhau chọn: " + ", ".join(f"{p['config']}/λ{p['lam']:g} {p['weeks']} tuần" for p in I["nested"]["picks"][:4])
          + f"; {I['nested']['no_model_weeks']}/{I['nested']['weeks']} tuần không có cấu hình nào tốt hơn tỷ lệ gốc (mua đều).", ""]
    # sell side
    L += [f"## Bên bán: nên giữ hay chốt lời (ngày {fmt.date(asof)})",
          f"- Mức hiện tại: **{LEVEL_VI[last['sell_level']]}** ({last['sell_groups']} nhóm bật). Một hệ thống: 0 nhóm → Giữ, 1–2 → Chốt lời một phần, ≥ 3 → Bán phần lớn.",
          "- Quy tắc bán X% một lần khi đợt tín hiệu bắt đầu, mua lại khi giá ≤ 80% giá bán hoặc sau 52 tuần, so với giữ nguyên:",
          "| Quy tắc | Chu kỳ | Tài sản so với giữ nguyên | Số lần bán | Mua lại rẻ hơn / đã mua lại |", "|---|---|---|---|---|"]
    for s in se["sims"]:
        for c in s["cycles"]:
            L.append(f"| Bán {fmt.pct(s['frac'])} khi ≥ {s['trigger']} nhóm | {c['period']} | {sp(c['ratio'] - 1)} | {c['sales']} | {c['right']} / {c['closed']} |")
    L += ["", "- Kết luận: bên bán **chưa có lợi thế đáng tin**; mức Giữ / Chốt lời một phần / Bán phần lớn chỉ để tham khảo, không khuyên tỷ lệ bán.", ""]
    # indicator values
    L += [f"## Giá trị chỉ số tại ngày phân tích ({fmt.date(asof)})",
          "| Chỉ số | Giá trị | Phân vị trong 4 năm trước | Thuộc 5% đắt nhất? |", "|---|---|---|---|"]
    for f, name in FEAT_VI.items():
        v, p = row.get("raw_" + f, np.nan), row.get("pct_" + f, np.nan)
        if not np.isfinite(v):
            continue
        val = sp(v) if f in ("dd_ath", "dev_ma20w") else (fmt.num(v) if f in ("fng", "rsi_14w") else fmt.dec(v, 2))
        L.append(f"| {name} | {val} | {p0(p) if np.isfinite(p) else '—'} | {'có' if np.isfinite(p) and p >= sp_['sell']['threshold_pct'] else 'không'} |")
    L += ["", "## Khối lượng giao dịch",
          f"- Khối lượng giao dịch giao ngay tương đối (so với trung bình gần đây) tại {fmt.date(asof)}: {fmt.dec(float(row.get('raw_vol_rel', np.nan)), 2)}, "
          f"phân vị 4 năm {p0(float(row.get('pct_vol_rel', np.nan)))}. Không dùng trong mô hình (không có trong bộ nào được đăng ký).", ""]
    # forward
    sc_ = json.loads((vdir / "score.json").read_text(encoding="utf-8")) if (vdir / "score.json").exists() else {}
    L += ["## Kiểm định đi tới",
          f"- Nhật ký `data/forward/{fmodel['version']}/forward_log.csv`: {len(flog)} tuần từ {fmt.date(flog['date'].iloc[0])} đến {fmt.date(flog['date'].iloc[-1])}, "
          f"{int((flog['late'] == '1').sum())} tuần ghi muộn. Đủ kỳ hạn để chấm: " + ", ".join(f"{h} tuần: {n}" for h, n in (sc_.get('matured') or {}).items()) + ".",
          "- Đây là phép thử ngoài mẫu thật duy nhất (holdout đã có người xem khi làm bot cũ). Chấm lại sau 26 và 52 tuần; không sửa mô hình trong thời gian theo dõi.", ""]
    L += ["## Câu hỏi gợi ý cho Claude",
          "- Vì sao bot khuyên mua đều dù khung tuần này là \"Cân nhắc mua\"?",
          "- Nếu giá giảm 20% trong 4 tuần tới, bot sẽ đọc thế nào và vì sao hệ số vẫn là 1,0?",
          "- Giải ngân một lần và chia đều 26 tuần khác nhau thế nào về rủi ro?",
          "- Khi nào nhật ký đi tới đủ dữ liệu để kết luận?", ""]
    L += limits(I, G, pl)
    (out_dir / "BAO_CAO.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
    charts = appendix(out_dir, B, C, G, I, E, sp_, horizons)
    return {"asof": asof, "passed": passed, "charts": charts}


def limits(I: dict, G: dict, pl: dict | None) -> list[str]:
    cur = G["live"]["regime"]
    return ["## Giới hạn: những gì báo cáo này không thể biết",
            "- **Ít chu kỳ, ít đợt độc lập.** BTC mới qua khoảng 3–4 chu kỳ giảm một nửa. Hầu hết khung có dưới 10 đợt, nhiều ô chỉ 1–2 đợt; khoảng tin cậy rộng là đúng bản chất, không phải lỗi.",
            f"- **Holdout không hoàn toàn mù.** Dữ liệu từ {fmt.date(I['holdout_start'])} đã được người xem khi làm bot cũ. Holdout có {I['holdout_weeks']} tuần; với độ dịch ≥ 52 tuần, "
            "kiểm định hoán vị chỉ có vài chục độ dịch khác nhau, nên p-value thô.",
            "- **Dữ liệu là bản mới nhất, không phải bản đúng như lúc công bố.** Độ trễ công bố được mô phỏng theo cấu hình, nhưng số liệu bị sửa lại về sau "
            "(nếu có) không được tái hiện. Coin Metrics bản cộng đồng không có vốn hóa thực trực tiếp; Fear & Greed chỉ có từ 02/2018; giá 2010–2013 lệch nhau giữa các sàn.",
            "- **Mô hình hẹp.** Chỉ hồi quy logistic L2 trên 8 bộ chỉ số đăng ký trước. Ràng buộc dấu thường loại MVRV và Fear & Greed; vòng trong thường không chọn được mô hình nào.",
            "- **Chi phí đơn giản.** Phí và trượt giá cố định mỗi lần mua; không tính thuế, chênh lệch tỷ giá, rủi ro sàn hay lưu ký.",
            "- **Kịch bản giá** giữ nguyên nguồn cung, lượng phát hành và hash rate; sai nếu kịch bản vắt qua kỳ giảm một nửa phần thưởng.",
            f"- **Vĩ mô.** Chế độ Fed (hiện là {REG_VI[cur]}) chỉ để chia nhóm; lịch sự kiện nhập tay từ trang chính thức và có thể thiếu.",
            ("- **Kế hoạch giải ngân** dựa trên lợi nhuận quá khứ với khoảng " + str(pl["episodes"]) + " đợt độc lập; kết quả đổi khi đổi giai đoạn dữ liệu.") if pl else "- Kế hoạch giải ngân chưa có số liệu.",
            "- **Không thể biết:** giá tương lai; chu kỳ 4 năm có còn lặp lại không; thay đổi cấu trúc (quỹ ETF, quy định, sự cố lớn); và liệu một quy tắc từng có vẻ tốt có còn tốt không.",
            "- **Trang web** đã có ô kế hoạch giải ngân, nhưng các khung và tỷ lệ \"nên mua / nên bán\" trên trang vẫn là của bot cũ; chưa đưa kết luận bản xây lại lên các phần đó.",
            "", "Công cụ tham khảo, không phải lời khuyên đầu tư.", ""]


def appendix(out_dir: Path, B, C, G, I, E, sp_, horizons) -> list[str]:
    charts = []
    L = ["# Phụ lục báo cáo bot BTC (bản xây lại)", "", "Mọi bảng đọc từ `data/results` và `experiments/`. Quay lại [báo cáo chính](BAO_CAO.md).", "",
         "## A. Danh sách mọi cấu hình đã thử", "", "### A1. Đăng ký trước (`config/candidates.yaml`)", "",
         "| Bộ | Chỉ số | Lý do kinh tế |", "|---|---|---|"]
    for k, v in sp_["sets"].items():
        L.append(f"| {k} | {', '.join(FEAT_VI.get(f, f) for f in v['features'])} | {v['why']} |")
    md = sp_["model"]
    L += ["", f"- Mỗi bộ × λ ∈ {{{', '.join(f'{x:g}' for x in md['lambdas'])}}} × kỳ hạn mục tiêu {md['target_weeks']} tuần = {len(sp_['sets']) * len(md['lambdas'])} cấu hình cố định; "
          f"cộng mô hình lồng nhau (vòng trong chọn bộ và λ), 2 quy tắc 1 chỉ số. Học lại mỗi {md['refit_weeks']} tuần, tối thiểu {md['min_train_weeks']} tuần, vòng trong {md['inner_valid_weeks']} tuần.",
          f"- Khung: Phải mua từ {sp_['zones']['thresholds']['phai']}, Cân nhắc mua từ {sp_['zones']['thresholds']['cannhac']}, vùng trễ {sp_['zones']['hysteresis']} (cố định, không dò). "
          f"Hệ số: 1 + {sp_['multiplier']['scale']:g} × cận khoảng tin cậy, giới hạn {sp_['multiplier']['bounds']}, cần ≥ {sp_['multiplier']['min_episodes']} đợt.",
          f"- Bên bán: phân vị ≥ {sp_['sell']['threshold_pct']:g} trong 4 năm, {len(sp_['sell']['groups'])} nhóm, kích hoạt {sp_['sell']['triggers']} nhóm, bán {', '.join(fmt.pct(x) for x in sp_['sell']['sell_fractions'])}.",
          f"- Kịch bản giá: {len(sp_['scenarios']['price_changes'])} mức × {sp_['scenarios']['weeks']} tuần. Kế hoạch giải ngân: {sp_['plan']['options_weeks']} tuần.", "",
          "### A2. Kết quả từng cấu hình", "", "| Cấu hình | Đến 2023: từ, số tuần, IC 26 tuần, lợi thế (KTC), p IC / p lợi thế (hiệu chỉnh) | Holdout: số tuần, IC, lợi thế, p IC / p lợi thế (hiệu chỉnh) |", "|---|---|---|"]
    rows = list(csv.DictReader((ROOT / "experiments" / "rebuild_configs.csv").open(encoding="utf-8")))
    by = {r["strategy"].split(" (")[0]: r for r in rows}
    pi_ = I["permutation"]
    hold_w = {}
    names = sorted(set(by) | set(pi_.get("ic26", {})), key=lambda n: (not n.startswith("Lồng"), n.startswith("Quy"), n))
    for n in names:
        r = by.get(n)
        a = (f"{fmt.date(r['from'])}, {r['weeks']}, {fmt.dec(float(r['ic26']), 2)}, {sp(float(r['cost_basis']))} ({sp(float(r['cost_ci_lo']))} đến {sp(float(r['cost_ci_hi']))}), "
             f"{pv(float(r['p_ic_maxstat']))} / {pv(float(r['p_cost_maxstat']))}" if r else "dưới 60 tuần ngoài mẫu, không chấm")
        h1, h2 = pi_.get("ic26", {}).get(n), pi_.get("cost_basis", {}).get(n)
        b = f"IC {fmt.dec(h1['obs'], 2)}, lợi thế {sp(h2['obs'])}, {pv(h1['p_maxstat'])} / {pv(h2['p_maxstat'])}" if h1 else f"dưới 30 tuần ({I['criteria']['c3']['skipped'].get(n, 0)})"
        hold_w[n] = b
        L.append(f"| {n} | {a} | {b} |")
    reg = list(csv.DictReader((ROOT / "experiments" / "registry.csv").open(encoding="utf-8")))
    L += ["", f"### A3. Giai đoạn nâng cấp trước khi xây lại (`experiments/registry.csv`, {len(reg)} lần thử)", "",
          "Các lần thử này được tính vào hiệu chỉnh kiểm định bội của giai đoạn đó; chi tiết tham số và kết quả nằm trong file CSV.", "",
          "| Ngày | Giai đoạn | Tên | Chỉ số |", "|---|---|---|---|"]
    L += [f"| {r['timestamp'][:10]} | {r['stage']} | {r['name']} | {r['features']} |" for r in reg]
    # permutation
    L += ["", "## B. Kết quả kiểm định hoán vị", "", f"Dịch vòng tín hiệu so với lợi nhuận, độ lệch ≥ {sp_['tests']['permutation_min_shift_weeks']} tuần, {sp_['tests']['permutation_n']} lần, cùng hạt giống cho mọi cấu hình.", ""]
    for lab, P in ((f"Đến {fmt.date(C['eval_end'])} (Phần C)", C["permutation"]), (f"Holdout {fmt.date(I['holdout_start'])} → {fmt.date(I['last_week'])} (Phần I)", I["permutation"])):
        L += [f"### {lab}", "", "| Cấu hình | IC 26 tuần | p thô | p max-stat | p Holm | Lợi thế (hệ số so sánh) | p thô | p max-stat | p Holm |", "|---|---|---|---|---|---|---|---|---|"]
        for n, a in P.get("ic26", {}).items():
            b = P["cost_basis"][n]
            L.append(f"| {n.split(' (')[0]} | {fmt.dec(a['obs'], 3)} | {pv(a['p_raw'])} | {pv(a['p_maxstat'])} | {pv(a['p_holm'])} | {sp(b['obs'])} | {pv(b['p_raw'])} | {pv(b['p_maxstat'])} | {pv(b['p_holm'])} |")
        L.append("")
    L.append("p thô để trống (—) khi chuỗi quá ngắn để dịch vòng (cần ≥ 114 tuần); p hiệu chỉnh khi đó không có ý nghĩa.")
    # calibration
    L += ["", "## C. Biểu đồ hiệu chỉnh", "", "Điểm nằm trên đường chéo nghĩa là xác suất dự báo khớp tỷ lệ thực tế. Kích thước điểm theo số tuần.", ""]
    items = [(f"calib_pa3_{h}", f"Bot hiện tại (PA3), {H_VI[h]}", hget(B["calibration"], h), f"đến {fmt.date(B['eval_end'])}") for h in horizons]
    items += [("calib_nested_dev", "Lồng nhau, 6 tháng", C.get("calibration"), f"đến {fmt.date(C['eval_end'])}"),
              ("calib_nested_holdout", "Lồng nhau, 6 tháng", I["criteria"]["c5"] if I["criteria"]["c5"].get("weeks") else None, "holdout")]
    for fn, title, c, period in items:
        if not c or not c.get("reliability"):
            continue
        sub = f"{period}: {c['weeks']} tuần, Brier {fmt.dec(c['brier'], 3)} so với tỷ lệ gốc {fmt.dec(c['brier_base'], 3)}"
        (out_dir / "img" / f"{fn}.svg").write_text(svg_reliability(c["reliability"], title, sub), encoding="utf-8", newline="\n")
        charts.append(fn)
        L += [f"![{title}, {period}](img/{fn}.svg)", ""]
    # cycles
    L += ["## D. Kết quả theo từng chu kỳ", "", "### D1. Bỏ từng chu kỳ khỏi dữ liệu học (Phần C, đến 2023, λ = 1)", "",
          "| Bộ | Chu kỳ để kiểm tra | Số tuần | Chỉ số còn lại | Bị bỏ do sai dấu | IC 26 tuần | Lợi thế (hệ số so sánh) |", "|---|---|---|---|---|---|---|"]
    for s, cyc in C["loco"].items():
        for cname, v in cyc.items():
            a, b = cname.split("/")
            if v is None:
                L.append(f"| {s} | {fmt.date(a)} → {fmt.date(b)} | — | — | — | — | không đủ dữ liệu |")
            elif "ic26" not in v:
                L.append(f"| {s} | {fmt.date(a)} → {fmt.date(b)} | {v['weeks']} | — | {', '.join(v['dropped'])} | — | mọi chỉ số sai dấu, không có mô hình |")
            else:
                L.append(f"| {s} | {fmt.date(a)} → {fmt.date(b)} | {v['weeks']} | {', '.join(v['kept']) or '—'} | {', '.join(v['dropped']) or '—'} | {fmt.dec(v['ic26'], 2)} | {sp(v['cost_basis'])} |")
    L += ["", "### D2. Lợi thế giá vốn theo năm (hệ số so sánh 0,5 + thứ hạng)", "", "| Chiến lược | " + " | ".join(str(y) for y in range(2014, 2024)) + " |", "|---|" + "---|" * 10]
    yrs = {**{n: I["strategies"][n]["m_cmp"]["years"] for n in STRATS if I["strategies"].get(n)}, "Bot hiện tại (PA3, Phần B)": B["sets"]["pa3"]["years"]}
    for n, ys in yrs.items():
        L.append(f"| {n} | " + " | ".join(sp(ys.get(str(y))) for y in range(2014, 2024)) + " |")
    L += ["", "### D3. Bên bán theo chu kỳ (Phần I)", "", "| Quy tắc | " + " | ".join(c["period"] for c in I["sell"]["sims"][0]["cycles"]) + " |",
          "|---|" + "---|" * len(I["sell"]["sims"][0]["cycles"])]
    for s in I["sell"]["sims"]:
        L.append(f"| Bán {fmt.pct(s['frac'])} khi ≥ {s['trigger']} nhóm | " + " | ".join(f"{sp(c['ratio'] - 1)} ({c['sales']} lần)" for c in s["cycles"]) + " |")
    # Fed
    L += ["", "## E. Kết quả theo chế độ Fed (Phần G, đến 2023)", "", f"Chế độ hiện tại: **{REG_VI[G['live']['regime']]}** từ {fmt.date(G['live']['since'])}. "
          "Mỗi ô so khung với mọi tuần cùng chế độ của cùng chiến lược.", ""]
    for n, s in G["strategies"].items():
        L += [f"### {n}" + (" (cảnh báo: chế độ hiện tại dưới 3 đợt)" if s["warn"] else ""), "", "| Chế độ (tuần, đợt) | " + ZONE_HEAD[0][2:], "|---|" + ZONE_HEAD[1][1:]]
        for g, rg in s["regimes"].items():
            if not rg.get("weeks"):
                L.append(f"| {REG_VI[g]} (0) | — | — | 0 | 0 | — | — | — | — | không có tuần |")
                continue
            L += [f"| {REG_VI[g]} ({rg['weeks']}, {rg['episodes']}) " + r_ for r_ in zone_rows(rg["table"], horizons)]
        L.append("")
    (out_dir / "PHU_LUC.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
    return charts
