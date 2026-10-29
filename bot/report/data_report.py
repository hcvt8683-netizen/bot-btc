"""Part A data-quality report: coverage of every weekly feature, outliers, cross-source price gaps, Coin Metrics fields,
publication delay, Fed regimes and the long-history substitutes for Fear & Greed. Writes data/results/data_quality.json
and docs/DATA_REPORT.md (Vietnamese)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from bot.config import DATA, ROOT
from bot.data import crosscheck, http
from bot.data import pit_store as ps
from bot.features import weekly_close as wc
from bot.i18n import fmt

WANTED_CM = ["PriceUSD", "CapMrktCurUSD", "CapMVRVCur", "CapRealUSD", "IssTotUSD", "IssTotNtv", "SplyCur", "HashRate", "RevUSD",
             "AssetEODCompletionTime", "volume_reported_spot_usd_1d"]
REGIME_VI = {"tang": "tăng", "giu": "giữ", "giam": "giảm"}


def cm_fields() -> dict:
    try:
        j = http.get_json("https://community-api.coinmetrics.io/v4/catalog-v2/asset-metrics?assets=btc&page_size=10000")
        have = sorted(m["metric"] for a in j["data"] for m in a["metrics"])
    except http.FetchError:
        have = []
    return {"available": have, "wanted": {m: m in have for m in WANTED_CM}}


def coverage(t: pd.DataFrame) -> list[dict]:
    rows = []
    for f in wc.FEATURES:
        raw, pct = t["raw_" + f], t["pct_" + f]
        first = raw.first_valid_index()
        rows.append({"feature": f, "first_raw": first.strftime("%Y-%m-%d") if first is not None else None,
                     "first_pct": pct.first_valid_index().strftime("%Y-%m-%d") if pct.first_valid_index() is not None else None,
                     "weeks": int(pct.notna().sum()), "gaps": int(raw.loc[first:].isna().sum()) if first is not None else None})
    return rows


def outliers(t: pd.DataFrame) -> dict:
    lr = np.log(t["close"]).diff()
    z = (lr - lr.mean()) / lr.std()
    big = z[z.abs() > 5]
    feats = {}
    for f in wc.FEATURES:
        dd = t["raw_" + f].diff()
        if dd.std() and np.isfinite(dd.std()):
            zz = (dd - dd.mean()) / dd.std()
            feats[f] = int((zz.abs() > 5).sum())
    return {"price_weeks": [{"date": d.strftime("%Y-%m-%d"), "change": float(np.expm1(lr.loc[d]))} for d in big.index], "feature_jumps": feats}


def episodes(lab: pd.Series) -> dict:
    out = {}
    prev = None
    for v in lab:
        if v is not None and v != prev:
            out[v] = out.get(v, 0) + 1
        prev = v
    return out


def regimes(t: pd.DataFrame) -> dict:
    lab = t["fed_regime"].where(t.index >= "2011-01-01")
    weeks = lab.value_counts().to_dict()
    cur = lab.dropna().iloc[-1] if lab.notna().any() else None
    return {"weeks": {k: int(v) for k, v in weeks.items()}, "episodes": episodes(lab.dropna()), "current": cur,
            "current_since": (lab[lab != cur].dropna().index.max() + pd.Timedelta(weeks=1)).strftime("%Y-%m-%d") if cur else None}


def fng_substitutes(t: pd.DataFrame) -> dict:
    """Rank correlation with Fear & Greed over the weeks where both exist (all as 'cheapness' or raw percentile)."""
    out = {}
    for f in ("rv30", "dd_ath", "dev_ma20w", "rsi_14w"):
        j = t[["pct_fng", "pct_" + f]].dropna()
        out[f] = {"weeks": int(len(j)), "spearman": float(j.corr(method="spearman").iloc[0, 1]) if len(j) > 20 else None}
    return out


def publication_lag() -> dict:
    ext = ps.load_history("coinmetrics_ext").set_index("date")
    c = ext["eod_completed_at"].dropna()
    h = ((c - c.index).dt.total_seconds() / 3600).iloc[-365:]
    return {"median_h": float(h.median()), "p90_h": float(h.quantile(0.9)), "max_h": float(h.max()), "rows": int(len(h))}


def build(write: bool = True) -> dict:
    t = wc.load()
    status = json.loads((DATA / "status.json").read_text(encoding="utf-8"))["sources"]
    res = {"weekly": {"from": t.index.min().strftime("%Y-%m-%d"), "to": t.index.max().strftime("%Y-%m-%d"), "weeks": int(len(t)),
                      "missing_close": int(t["close"].isna().sum())},
           "coverage": coverage(t), "outliers": outliers(t), "crosscheck": crosscheck.compare(), "cm_fields": cm_fields(),
           "publication": publication_lag(), "regimes": regimes(t), "fng_substitutes": fng_substitutes(t),
           "sources": {k: {"ok": v.get("ok"), "last": v.get("last"), "rows": v.get("rows"), "warnings": v.get("warnings") or [],
                           "errors": v.get("errors") or []} for k, v in status.items()}}
    if write:
        (DATA / "results").mkdir(exist_ok=True)
        (DATA / "results" / "data_quality.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        (ROOT / "docs" / "DATA_REPORT.md").write_text(markdown(res), encoding="utf-8", newline="\n")
    return res


def markdown(r: dict) -> str:
    p = lambda x, d=2: fmt.pct(x, d)  # noqa: E731
    w = r["weekly"]
    L = ["# Báo cáo dữ liệu (Phần A)", "",
         f"Bảng tuần theo **giá đóng cửa Chủ nhật**: {fmt.date(w['from'])} → {fmt.date(w['to'])}, {fmt.num(w['weeks'])} tuần, "
         f"thiếu giá đóng tuần: {w['missing_close']} tuần. Giá trực tiếp chỉ để hiển thị, không vào bảng này.", "",
         "## 1. Mỗi chỉ số có từ khi nào", "",
         "Phân vị trượt 4 năm (208 tuần) chỉ dùng dữ liệu quá khứ và cần tối thiểu 104 tuần, nên luôn có sau giá trị gốc khoảng 2 năm.", "",
         "| Chỉ số | Có giá trị gốc từ | Có phân vị từ | Số tuần có phân vị | Tuần bị thiếu sau khi bắt đầu |", "|---|---|---|---|---|"]
    for c in r["coverage"]:
        L.append(f"| {c['feature']} | {fmt.date(c['first_raw']) if c['first_raw'] else '—'} | {fmt.date(c['first_pct']) if c['first_pct'] else '—'} | {c['weeks']} | {c['gaps']} |")
    L += ["", "## 2. Đối chiếu giá giữa các nguồn (cùng ngày = cùng giá đóng cửa ngày)", "",
          "Nguồn chính: Coin Metrics `PriceUSD` (từ 18/07/2010). Đã đo: dòng ngày d của Coin Metrics khớp giá đóng cửa ngày d của sàn "
          "(lệch 1 ngày thì sai lệch trung vị tăng lên khoảng 1,5%).", "",
          "| Nguồn so với Coin Metrics | Đoạn chồng lấn | Số ngày | Lệch trung vị | Lệch 99% | Lệch lớn nhất | Số ngày lệch > 2% |", "|---|---|---|---|---|---|---|"]
    for n, x in r["crosscheck"].items():
        L.append(f"| {n} | {fmt.date(x['from'])} → {fmt.date(x['to'])} | {fmt.num(x['days'])} | {p(x['median'])} | {p(x['p99'])} | {p(x['max'])} | {x['above']} |")
    L += ["", "Theo giai đoạn:", "", "| Nguồn | Giai đoạn | Số ngày | Lệch trung vị | Lệch 99% | Số ngày lệch > 2% |", "|---|---|---|---|---|---|"]
    for n, x in r["crosscheck"].items():
        for e in x["eras"]:
            L.append(f"| {n} | {e['era']} | {fmt.num(e['days'])} | {p(e['median'])} | {p(e['p99'])} | {e['above']} |")
    L += ["", "Ngày lệch nhiều nhất:", ""]
    for n, x in r["crosscheck"].items():
        L.append(f"- {n}: " + "; ".join(f"{fmt.date(k['date'])} ({fmt.usd(k['primary'], 2)} so với {fmt.usd(k['other'], 2)}, {fmt.pct(k['diff'], 1, sign=True)})" for k in x["worst"][:3]))
    cmf = r["cm_fields"]["wanted"]
    L += ["", "## 3. Trường của Coin Metrics bản community", "",
          "| Trường | Có không | Dùng cho |", "|---|---|---|"]
    use = {"PriceUSD": "giá đóng cửa ngày", "CapMrktCurUSD": "vốn hóa, MVRV Z", "CapMVRVCur": "MVRV", "CapRealUSD": "vốn hóa thực (thiếu → tính bằng vốn hóa / MVRV)",
           "IssTotUSD": "Puell", "IssTotNtv": "kiểm tra Puell", "SplyCur": "nguồn cung", "HashRate": "Hash Ribbon", "RevUSD": "doanh thu thợ đào (thiếu → dùng phát hành)",
           "AssetEODCompletionTime": "giờ chốt số liệu (chỉ đúng cho dữ liệu gần đây)", "volume_reported_spot_usd_1d": "khối lượng tương đối, lịch sử dài"}
    for k, ok in cmf.items():
        L.append(f"| `{k}` | {'có' if ok else '**không có**'} | {use.get(k, '')} |")
    pb = r["publication"]
    L += ["", f"Độ trễ công bố của Coin Metrics (365 ngày gần nhất): số liệu ngày d có sau 00:00 UTC ngày d khoảng **{fmt.num(pb['median_h'], 0)} giờ** (trung vị), "
          f"90% trong {fmt.num(pb['p90_h'], 0)} giờ, chậm nhất {fmt.num(pb['max_h'], 0)} giờ. Tín hiệu theo giá đóng Chủ nhật vì thế có vào sáng thứ Hai giờ Việt Nam. "
          "Giờ chốt của dữ liệu cũ đã bị tính lại về sau (trung vị hàng năm), nên không dùng làm thời điểm công bố lịch sử; bot dùng quy tắc trễ cố định 1 ngày.", "",
          "## 4. Giá trị bất thường", ""]
    o = r["outliers"]
    L.append("Tuần giá đóng thay đổi hơn 5 độ lệch chuẩn (giữ nguyên, chỉ đánh dấu): " + (", ".join(f"{fmt.date(x['date'])} ({fmt.pct(x['change'], 0, sign=True)})" for x in o["price_weeks"]) or "không có") + ".")
    L.append("Số tuần chỉ số nhảy hơn 5 độ lệch chuẩn: " + ", ".join(f"{k} {v}" for k, v in o["feature_jumps"].items()) + ".")
    rg = r["regimes"]
    L += ["", "## 5. Chế độ lãi suất Fed (chỉ để chia nhóm khi báo cáo, không đưa vào mô hình)", "",
          "Theo thay đổi trần lãi suất Fed (FRED `DFEDTARU`) trong 26 tuần trước, chỉ dùng số liệu đến Chủ nhật đó: tăng, giữ hoặc giảm. Tính từ 2011.", "",
          "| Chế độ | Số tuần | Số đợt |", "|---|---|---|"]
    for k in ("tang", "giu", "giam"):
        L.append(f"| {REGIME_VI[k]} | {rg['weeks'].get(k, 0)} | {rg['episodes'].get(k, 0)} |")
    L.append(f"\nChế độ hiện tại: **{REGIME_VI.get(rg['current'], '—')}** (từ {fmt.date(rg['current_since']) if rg['current_since'] else '—'}). "
             + ("Chế độ này có dưới 3 đợt trong lịch sử, kết quả theo chế độ sẽ rất ít bằng chứng." if rg["episodes"].get(rg["current"], 0) < 3 else ""))
    L += ["", "## 6. Fear & Greed và chỉ báo thay thế có lịch sử dài", "",
          "Fear & Greed chỉ có từ 02/2018. Các chỉ báo thay thế tính được từ 2010: biến động thực 30 ngày (rv30), mức giảm từ đỉnh (dd_ath), độ lệch giá so với MA 20 tuần "
          "(dev_ma20w), RSI 14 tuần. Tương quan thứ hạng với Fear & Greed (phân vị 4 năm) trên các tuần cùng có số liệu:", "",
          "| Chỉ báo | Số tuần chung | Tương quan thứ hạng |", "|---|---|---|"]
    for k, v in r["fng_substitutes"].items():
        L.append(f"| {k} | {v['weeks']} | {fmt.dec(v['spearman'], 2) if v['spearman'] is not None else '—'} |")
    L += ["", "## 7. Trạng thái từng nguồn ở lần tải gần nhất", "", "| Nguồn | Kết quả | Đến ngày | Số dòng | Ghi chú |", "|---|---|---|---|---|"]
    for k, v in r["sources"].items():
        note = "; ".join(v["errors"])[:120] if v["errors"] else "; ".join(v["warnings"])[:120]
        L.append(f"| {k} | {'tốt' if v['ok'] else '**lỗi**'} | {fmt.date(v['last']) if v['last'] else '—'} | {v['rows'] or '—'} | {note} |")
    return "\n".join(L) + "\n"
