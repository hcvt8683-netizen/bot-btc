"""docs/MODEL_C.md (Vietnamese) from data/results/part_c.json."""
from __future__ import annotations

import json

import numpy as np

from bot.config import DATA, ROOT
from bot.i18n import fmt
from bot.models.part_c import spec


def _num(x, d=3):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else fmt.dec(x, d)


def _pct(x):
    return "—" if x is None else fmt.pct(x, 1, sign=True)


def markdown(o: dict) -> str:
    sp = spec()
    md = sp["model"]
    L = ["# Phần C: mô hình và chống khớp quá mức", "",
         f"Dữ liệu đến **{fmt.date(o['eval_end'])}**, holdout từ 01/01/2024 vẫn khóa. Mọi thiết lập lấy từ `config/candidates.yaml`, đã lưu git **trước** "
         "lần chạy đầu tiên (commit `da803d6`). Mọi cấu hình đã thử ghi trong `experiments/rebuild_configs.csv`.", "",
         "## 1. Thiết lập đăng ký trước", "",
         f"- Hồi quy logistic L2. Nhãn: giá đóng thứ Hai sau {md['target_weeks']} tuần cao hơn lúc mua. λ ∈ {{{', '.join(fmt.dec(x, 1) for x in md['lambdas'])}}}.",
         f"- Đi tới lồng nhau: vòng ngoài học lại mỗi {md['refit_weeks']} tuần, cửa sổ mở rộng, chỉ để chấm điểm. Vòng trong chọn bộ chỉ số và λ theo log-loss "
         f"trên {md['inner_valid_weeks']} tuần có nhãn gần nhất (cắt bỏ {md['target_weeks']} tuần để không chồng nhãn). Không cấu hình nào hơn tỷ lệ nền → không dùng mô hình (mua đều).",
         "- Ràng buộc dấu bên mua: trọng số của \"độ rẻ\" phải ≥ 0; chỉ số học ra dấu ngược bị loại ở lần học đó và được ghi lại.",
         "- Thứ hạng = vị trí của điểm hôm nay trong các điểm **ngoài mẫu** trước đó (cần 52 tuần). Để so sánh công bằng ở phần này, hệ số = 0,5 + thứ hạng.",
         "- Mốc bắt buộc: mua đều; quy tắc 1 chỉ số (độ rẻ MVRV; độ rẻ Giá/MA 200 tuần).", "",
         "| Bộ | Chỉ số | Lý do kinh tế |", "|---|---|---|"]
    for k, v in sp["sets"].items():
        L.append(f"| {k} | {', '.join(v['features'])} | {v['why']} |")
    main = next(r for r in o["results"] if r["name"].startswith("Lồng nhau"))
    L += ["", "## 2. Mô hình lồng nhau", "",
          f"- {o['nested_weeks']} tuần được chấm; **{o['no_model_weeks']} tuần vòng trong không tìm được cấu hình nào hơn tỷ lệ nền**, nên không dùng mô hình (mua đều).",
          "- Cấu hình được chọn (số tuần): " + ", ".join(f"{x['config']} λ{fmt.dec(x['lam'], 1)} ({x['weeks']})" for x in o["selected"]) + ".",
          f"- Ngoài mẫu từ {fmt.date(main['from'])} ({main['weeks']} tuần có thứ hạng): tương quan thứ hạng với lợi suất 26 tuần {_num(main['ic26'])}; "
          f"lợi thế giá vốn {_pct(main['cost_basis'])} (khoảng tin cậy {_pct(main['cost_ci'][0])} đến {_pct(main['cost_ci'][1])})."]
    c = o.get("calibration")
    if c:
        L.append(f"- Xác suất: Brier {_num(c['brier'])} so với mốc {_num(c['brier_base'])}, khoảng tin cậy của mức cải thiện {_num(c['gain_ci'][0])} đến "
                 f"{_num(c['gain_ci'][1])}: " + ("hiển thị xác suất." if c["show_probability"] else "**không hiển thị xác suất, chỉ thứ hạng**."))
    L += ["", "## 3. Mọi cấu hình, kiểm định hoán vị và hiệu chỉnh kiểm định bội", "",
          f"Hoán vị: dịch vòng chuỗi tín hiệu so với chuỗi lợi suất, độ lệch ngẫu nhiên ≥ 52 tuần, {sp['tests']['permutation_n']} lần, dùng cùng các lần dịch cho mọi cấu hình. "
          f"Hiệu chỉnh max-statistic trên **{o['n_strategies']} cấu hình chấm được** (Holm có trong file JSON). Chỉ khi p sau hiệu chỉnh nhỏ hơn 0,05 mới có ý nghĩa.", "",
          "| Cấu hình | Từ | Số tuần | Tương quan với lợi suất 26 tuần | p (thô / hiệu chỉnh) | Lợi thế giá vốn | Khoảng tin cậy | p (thô / hiệu chỉnh) | Khung đơn điệu? |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in o["results"]:
        pi, pc = o["permutation"]["ic26"][r["name"]], o["permutation"]["cost_basis"][r["name"]]
        L.append(f"| {r['name']} | {fmt.date(r['from'])} | {r['weeks']} | {_num(r['ic26'])} | {_num(pi['p_raw'])} / {_num(pi['p_maxstat'])} | "
                 f"{_pct(r['cost_basis'])} | {_pct(r['cost_ci'][0])} đến {_pct(r['cost_ci'][1])} | {_num(pc['p_raw'])} / {_num(pc['p_maxstat'])} | "
                 f"{'có' if all(r['monotone'].values()) else 'không'} |")
    L += ["", "Đã thử nhưng không đủ điểm ngoài mẫu để chấm (ràng buộc dấu loại hết chỉ số ở phần lớn các lần học, hoặc lịch sử quá ngắn): "
          + ", ".join(f"{k}/λ{fmt.dec(lam, 1)}" for k in ("S4", "S5", "S8") for lam in md["lambdas"]) + ".", "",
          "## 4. Ràng buộc dấu: chỉ số bị loại vì học ra dấu ngược", "",
          "| Cấu hình | Số lần học có loại chỉ số | Chỉ số từng bị loại |", "|---|---|---|"]
    for k, v in o["sign_drops"].items():
        if k.endswith("λ1"):
            L.append(f"| {k} | {v['refits_with_drop']} | {', '.join(v['dropped']) or '—'} |")
    L += ["", "Mô hình rất hay học ra trọng số âm cho chỉ số \"rẻ\": rẻ hơn lại đi kèm xác suất có lãi sau 26 tuần thấp hơn. Fear & Greed bị loại ở **mọi** lần học, "
          "nên bộ có và không có Fear & Greed thực chất giống nhau (S5, S8 chỉ còn MVRV). Chỉ báo thay thế (độ lệch so với MA 20 tuần, S4) cũng bị loại.", "",
          "## 5. Mô hình so với quy tắc đơn giản (cùng giai đoạn với mô hình lồng nhau)", "",
          "| Cách | Từ | Số tuần | Tương quan với lợi suất 26 tuần | Lợi thế giá vốn (hệ số 0,5 + thứ hạng) |", "|---|---|---|---|---|"]
    for x in o["common"]:
        L.append(f"| {x['name']} | {fmt.date(x['from'])} | {x['weeks']} | {_num(x['ic26'])} | {_pct(x['cost_basis'])} |")
    L += ["", "Mô hình lồng nhau **không thắng** hai quy tắc đơn giản, nên theo bản kế hoạch không được dùng.", "",
          "## 6. Bỏ từng chu kỳ ra khỏi dữ liệu học (λ = 1)", "",
          "Học trên các chu kỳ khác (cắt bỏ 26 tuần quanh chu kỳ bị bỏ), chấm trên chu kỳ bị bỏ. Đây không phải kiểm định đi tới, vì mô hình có thể học từ chu kỳ sau.", "",
          "| Bộ | " + " | ".join(x.replace("/", " → ") for x in sp["tests"]["loco_cycles"]) + " |", "|---|" + "---|" * len(sp["tests"]["loco_cycles"])]
    for s, cyc in o["loco"].items():
        cells = []
        for x in sp["tests"]["loco_cycles"]:
            v = cyc.get(x)
            if v is None:
                cells.append("chưa đủ dữ liệu")
            elif not v.get("kept"):
                cells.append("mọi chỉ số bị loại")
            else:
                cells.append(f"{'+'.join(v['kept'])}: tương quan {_num(v.get('ic26'), 2)}, lợi thế {_pct(v.get('cost_basis'))}")
        L.append(f"| {s} | " + " | ".join(cells) + " |")
    L += ["", "## 7. Kiểm tra đơn điệu và gộp khung", "",
          "Yêu cầu: Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua ở mọi kỳ hạn. Không đạt thì gộp Phải mua và Cân nhắc mua thành \"Mua thêm\"; vẫn không đạt thì bỏ khung.", ""]
    for r in o["results"]:
        if r["name"].startswith(("Lồng nhau", "Quy tắc")):
            mg = r.get("merged")
            ok2 = bool(mg) and all(mg["monotone"].values())
            L.append(f"- {r['name']}: khung gốc đơn điệu **{'có' if all(r['monotone'].values()) else 'không'}**; sau khi gộp **{'có' if ok2 else 'không'}**"
                     + ("." if ok2 else ", nên bỏ khung, không gắn nhãn hành động."))
    pmin = min(o["permutation"][s][r["name"]]["p_maxstat"] for s in ("ic26", "cost_basis") for r in o["results"])
    L += ["", "## 8. Kết luận Phần C", "",
          f"- Không cấu hình nào, kể cả quy tắc đơn giản, có ý nghĩa thống kê sau hiệu chỉnh kiểm định bội (p hiệu chỉnh nhỏ nhất {_num(pmin)}).",
          "- Mô hình lồng nhau phần lớn thời gian **tự chọn không dùng mô hình**; khi có chọn thì kém mua đều và kém quy tắc đơn giản.",
          "- Khung không đơn điệu ở bất kỳ cách nào, kể cả sau khi gộp.",
          "- Kết luận đúng theo nguyên tắc: **chưa có lợi thế, nên mua đều (hệ số 1,0)**. Phần D vẫn dựng khung và hệ số theo quy tắc, nhưng với kết quả này hệ số sẽ là 1,0.", ""]
    return "\n".join(L)


def write() -> None:
    o = json.loads((DATA / "results" / "part_c.json").read_text(encoding="utf-8"))
    (ROOT / "docs" / "MODEL_C.md").write_text(markdown(o), encoding="utf-8", newline="\n")
