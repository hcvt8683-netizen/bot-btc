# -*- coding: utf-8 -*-
"""Rebuild config/events.yaml from the official calendars (Fed, BLS, BEA). Review the diff before committing.

Run: python tools/update_events.py
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from bot.data.fetchers import events  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "config" / "events.yaml"


def main() -> None:
    ev = events.fetch_all()
    lines = [
        "# Lịch sự kiện vĩ mô, giờ UTC (hiển thị đổi sang giờ Việt Nam).",
        f"# Tạo bằng tools/update_events.py ngày {dt.date.today():%d/%m/%Y} từ federalreserve.gov, bls.gov, bea.gov; sửa tay khi lịch đổi.",
        "# PCE chỉ có lịch sắp tới (BEA không có trang lưu trữ lịch phát hành dễ đọc), nên kiểm tra lịch sử chỉ dùng FOMC, CPI và đáo hạn quyền chọn.",
        "options_expiry: {rule: last_friday, time_utc: \"08:00\"}   # đáo hạn quyền chọn BTC hằng tháng (Deribit)",
        "window_hours: 48",
    ]
    for k, ten in (("fomc", "Quyết định lãi suất FOMC (14:00 giờ New York)"), ("cpi", "Chỉ số giá tiêu dùng CPI (8:30 giờ New York)"),
                   ("pce", "Chỉ số giá chi tiêu PCE (8:30 giờ New York)")):
        lines.append(f"{k}:   # {ten}, {len(ev[k])} lần")
        lines += [f"  - \"{t}\"" for t in ev[k]]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print({k: (len(v), v[0] if v else None, v[-1] if v else None) for k, v in ev.items()})


if __name__ == "__main__":
    main()
