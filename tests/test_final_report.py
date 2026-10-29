# -*- coding: utf-8 -*-
"""Final report: every section of the old report is present, the limits and appendix exist, no missing value leaks into
the text, and the calibration charts are valid SVG."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from bot.report import final_report

SECTIONS = ["## Bối cảnh", "## Kết luận", "## Khuyến nghị giải ngân tuần này", "## Giá đề xuất mua và bán", "## Xác suất thắng nếu mua tại ngày phân tích",
            "## Bộ tiêu chí: tỷ lệ thắng thực tế theo từng khung mua", "## Khung bán: giá có giảm thật không", "## So sánh các phương án",
            "## Bộ chỉ số có tỷ lệ thắng cao nhất", "## Bên bán: nên giữ hay chốt lời", "## Giá trị chỉ số tại ngày phân tích", "## Khối lượng giao dịch",
            "## Câu hỏi gợi ý cho Claude", "## Giới hạn"]
APPENDIX = ["## A. Danh sách mọi cấu hình đã thử", "## B. Kết quả kiểm định hoán vị", "## C. Biểu đồ hiệu chỉnh", "## D. Kết quả theo từng chu kỳ",
            "## E. Kết quả theo chế độ Fed"]


def test_report_has_the_old_structure_and_no_missing_values(tmp_path):
    r = final_report.build(tmp_path)
    main = (tmp_path / "BAO_CAO.md").read_text(encoding="utf-8")
    app = (tmp_path / "PHU_LUC.md").read_text(encoding="utf-8")
    pos = [main.index(s) for s in SECTIONS]
    assert pos == sorted(pos)  # same order as the old report, limits last
    assert all(s in app for s in APPENDIX)
    for text in (main, app):
        assert not re.search(r"\b(nan|NaN|None|inf)\b", text)
    assert "không phải lời khuyên đầu tư" in main and "chưa có lợi thế" in main
    assert r["charts"]
    for name in r["charts"]:
        ET.parse(tmp_path / "img" / f"{name}.svg")
        assert f"img/{name}.svg" in app
