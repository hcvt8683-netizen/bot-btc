"""Part H runner: a dry run of the forward log on 2023 (freeze 22/12/2022 → log every Sunday of 2023 → score), on data
already used in Parts B–E, to show the procedure works. Writes data/results/forward_dryrun/ and docs/FORWARD_H.md.
The real freeze happens after the single Part I holdout run (python -m bot.cli forward freeze)."""
from __future__ import annotations

import json
import shutil

import pandas as pd

from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.i18n import fmt
from bot.models import forward as fw, part_c, zones as zn

DRY = DATA / "results" / "forward_dryrun"
ZONE_VI = {"phai": "Phải mua", "cannhac": "Cân nhắc mua", "khong": "Không nên mua", "": "—"}
LEVEL_VI = {"giu": "Giữ", "chot": "Chốt lời một phần", "ban": "Bán phần lớn"}
VERDICT = {"chua_co_loi_the": "chưa có lợi thế", "hon_moc": "hơn mốc", "kem_moc": "**kém mốc**", "it_dot": "ít đợt (< 3)"}


def run(write: bool = True) -> dict:
    sp = part_c.spec()
    fc = sp["forward"]
    rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
    start, end = pd.Timestamp(str(fc["dry_run"]["freeze"])), pd.Timestamp(str(fc["dry_run"]["log_until"]))
    if DRY.exists():
        shutil.rmtree(DRY)  # regenerated artifact
    vid, _ = fw.freeze(DRY, start, part_c.table, mode="chay_thu", now=start + pd.Timedelta(days=1))
    for d in pd.date_range(start, end, freq="W-SUN"):
        fw.log_week(DRY, d, part_c.table, now=d + pd.Timedelta(days=1))  # as if run every Monday
    vdir = DRY / vid
    sc = fw.score(vdir, part_c.table(end), fc["score_horizons"], rb["bootstrap_n"], rb["seed"], rb["episode_gap_weeks"])
    m = json.loads((vdir / "model.json").read_text(encoding="utf-8"))
    out = {"version": vid, "hash": m["hash"], "state": {k: v for k, v in m["state"].items() if k != "score_history"},
           "history_n": len(m["state"]["score_history"]), "score": sc, "log": fw.read_log(vdir).to_dict("records")}
    if write:
        (vdir / "score.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (ROOT / "docs" / "FORWARD_H.md").write_text(markdown(out), encoding="utf-8", newline="\n")
    return out


def markdown(o: dict) -> str:
    fc = part_c.spec()["forward"]
    st, sc = o["state"], o["score"]
    num = lambda x, d=0: "—" if x in ("", None) else fmt.num(float(x), d)  # noqa: E731
    sp = lambda x: "—" if x is None else fmt.pct(x, 1, sign=True)  # noqa: E731
    fit = st["fit"]
    L = ["# Phần H: kiểm định đi tới", "",
         "Đăng ký trước: `config/candidates.yaml` mục `forward` (commit `13daebf`). Mã: `bot/models/forward.py`, lệnh `python -m bot.cli forward freeze | log | score`.", "",
         "## 1. Cách làm", "",
         f"- **Đóng băng:** {fc['model']}.",
         f"- **Mã phiên bản:** {fc['hash']}. Tên phiên bản = số thứ tự + 10 ký tự đầu của mã, ví dụ `{o['version']}`.",
         f"- **Mỗi tuần một dòng** trong `forward_log.csv` (UTF-8 có BOM): " + ", ".join(f"`{c}`" for c in fc["columns"]) + ".",
         "  Ngoài mô hình, dòng ghi luôn thứ hạng và khung của hai quy tắc đơn giản (mốc so sánh) và mức bên bán.",
         f"- **Không sửa mô hình:** {fc['version_rule']}. Lệnh ghi tự kiểm tra mã trước mỗi lần ghi.",
         f"- **Ghi muộn:** {fc['late_rule']}.",
         f"- **Chấm lại:** sau {' và '.join(map(str, fc['score_horizons']))} tuần; {fc['score_rule']}.",
         "- **Vì sao chỉ nhật ký đi tới mới là kiểm định thật:** dữ liệu 2024–2026 (holdout) đã được con người nhìn thấy khi làm bot cũ. "
         "Chỉ những tuần ghi SAU khi đóng băng mới hoàn toàn ngoài mẫu.", "",
         "Bài kiểm tra tự động (`tests/test_forward.py`): chỉ thêm dòng, không sửa dòng cũ; ghi lại cùng tuần không làm gì; đổi cấu hình thì dừng ghi và "
         "đóng băng lại tạo phiên bản mới với nhật ký mới; sửa tay `model.json` bị phát hiện; dòng không dùng dữ liệu sau Chủ nhật của nó; "
         "khi ghi không học lại mô hình. Đã cài thử 3 lỗi (sửa dòng cũ, nhìn trước 4 tuần, học lại mỗi tuần): test bắt được cả 3.", "",
         f"## 2. Chạy thử trên 2023 (không phải kiểm định)", "",
         f"Đóng băng tại {fmt.date(st['asof'])}, ghi mỗi Chủ nhật đến {fmt.date(fc['dry_run']['log_until'])} như thể chạy vào mỗi thứ Hai, rồi chấm bằng dữ liệu đến "
         f"{fmt.date(fc['dry_run']['log_until'])}. Năm 2023 đã dùng ở Phần B–E, nên đây chỉ là chạy thử quy trình. File: `data/results/forward_dryrun/{o['version']}/`.", "",
         f"- Phiên bản `{o['version']}`, mã đầy đủ `{o['hash']}`.",
         ("- Mô hình đóng băng: **không có mô hình** (vòng trong không thấy cấu hình nào tốt hơn tỷ lệ gốc), nên điểm để trống, hệ số 1,0." if not fit else
          f"- Mô hình đóng băng: bộ {st['set']}, λ = {fmt.dec(fit['lam'], 1)}, giữ " + ", ".join(f"{f} (trọng số {fmt.dec(c, 2)})" for f, c in zip(fit["features"], fit["coef"]))
          + (f"; bỏ do sai dấu: {', '.join(fit['dropped'])}" if fit["dropped"] else "") + f". Tỷ lệ gốc {fmt.pct(st['p0'])}."),
         f"- Lịch sử điểm ngoài mẫu để xếp hạng: {o['history_n']} tuần. Cổng Phần I: {st['gate']} → hệ số dùng thực tế 1,0.", "",
         "| Ngày | Giá đóng | Điểm | Thứ hạng | Khung | Hệ số (quy tắc / dùng) | Quy tắc MVRV | Quy tắc Giá/MA 200 tuần | Bên bán |",
         "|---|---|---|---|---|---|---|---|---|"]
    rows = o["log"]
    for r in rows[::4] + ([rows[-1]] if (len(rows) - 1) % 4 else []):
        L.append(f"| {fmt.date(r['date'])} | {fmt.usd(float(r['close']))} | {num(r['score'], 3)} | {num(r['rank'])} | {ZONE_VI[r['zone']]} | "
                 f"{num(r['mult_rule'], 2)} / {num(r['mult_used'], 2)} | {num(r['rank_mvrv'])} → {ZONE_VI[r['zone_mvrv']]} | "
                 f"{num(r['rank_200w'])} → {ZONE_VI[r['zone_200w']]} | {r['sell_groups']} nhóm → {LEVEL_VI[r['sell_level']]} |")
    L += ["", f"Bảng chỉ in mỗi 4 tuần một dòng; đủ {len(rows)} dòng trong file.", "",
          f"**Chấm lại:** {sc['rows']} dòng; đủ kỳ hạn: " + ", ".join(f"{h} tuần: {n} dòng" for h, n in sc["matured"].items()) + ".", "",
          "| Chiến lược | Kỳ hạn | Mốc (mọi tuần đủ kỳ hạn) | Khung | Số tuần | Số đợt | Tỷ lệ của khung | Chênh (KTC 95%) | Kết luận |",
          "|---|---|---|---|---|---|---|---|---|"]
    names = {"model": "Mô hình đóng băng", "mvrv": "Quy tắc MVRV", "200w": "Quy tắc Giá/MA 200 tuần"}
    for k, tab in sc["zones"].items():
        for h in fc["score_horizons"]:
            base = tab["baseline"][h] if "baseline" in tab else None
            shown = False
            for z in zn.ORDER:
                c = tab["zones"].get(z, {}).get(h, {})
                if not c.get("weeks"):
                    continue
                shown = True
                ci = c.get("ci") or [None, None]
                L.append(f"| {names[k]} | {h} tuần | {fmt.pct(base['win']) if base and base.get('win') is not None else '—'} | {ZONE_VI[z]} | {c['weeks']} | {c['episodes']} | "
                         f"{fmt.pct(c['win'])} | {sp(c['diff'])} ({sp(ci[0])} đến {sp(ci[1])}) | {VERDICT.get(c.get('verdict'), c.get('verdict'))} |")
            if not shown:
                L.append(f"| {names[k]} | {h} tuần | — | — | 0 | 0 | — | — | chưa có dòng đủ kỳ hạn |")
    h0 = fc["score_horizons"][0]
    max_eps = max((c.get(h0, {}).get("episodes", 0) for tab in sc["zones"].values() for c in tab["zones"].values()), default=0)
    L += ["", "## 3. Kế hoạch chạy thật", "",
          f"- **Đóng băng thật:** {fc['real_freeze']}. Lệnh `python -m bot.cli forward freeze` từ chối chạy khi chưa có kết quả Phần I.",
          "- **Mỗi tuần:** `python -m bot.cli forward log` sau giá đóng Chủ nhật (tuần nào bị lỡ sẽ được ghi bù và đánh dấu ghi muộn). "
          "Tự động hóa trên GitHub Actions chỉ làm ở bước tích hợp cuối, khi bạn đồng ý.",
          "- **Chấm:** `python -m bot.cli forward score`. Mỗi khung cần ít nhất 3 đợt mới kết luận. Trong chạy thử, sau "
          f"{len(rows)} tuần ghi, khung nhiều đợt nhất mới có {max_eps} đợt đủ kỳ 26 tuần. Trước khi đủ, kết luận đúng là \"ít đợt\".",
          "- **Không sửa mô hình trong thời gian theo dõi.** Sửa mã hay cấu hình nghĩa là phiên bản mới và nhật ký mới, đếm lại từ đầu.", ""]
    return "\n".join(L)
