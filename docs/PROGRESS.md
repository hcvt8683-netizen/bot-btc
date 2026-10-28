# Tiến độ nâng cấp "Best ROI for Invest"

Mỗi giai đoạn ghi: tóm tắt, file thay đổi, kết quả kiểm tra, bảng số liệu chính, câu hỏi còn mở. Khi bị gián đoạn, nói "Tiếp tục" để làm tiếp từ giai đoạn đầu tiên chưa xong.

## Giai đoạn 0: Kiểm toán (xong 28/10/2026)

**Tóm tắt.** Đã gắn thẻ `v1-before-upgrade` cho bản đang chạy (92d0762) và làm trên nhánh `upgrade/best-roi`. Đã đọc toàn bộ mã, ghi lại luồng dữ liệu, cách tính từng con số, rủi ro nhìn trước tương lai, thổi phồng số mẫu, cách chọn "bộ tốt nhất", giao diện hiện tại và 688 chuỗi chữ viết cứng. Cả 7 giả thuyết ở mục 0 đều đúng khi tính lại trên dữ liệu thật. Trang web hiện được tải lên bằng tay vào kho `hcvt8683-netizen/bot-btc`, chưa có triển khai tự động. Không đổi hành vi của bot.

**File thay đổi.** `docs/AUDIT.md`, `docs/AUDIT_STRINGS.md`, `docs/BTC_BOT_UPGRADE_SPEC.md` (chuyển từ thư mục gốc), `tools/list_strings.py`, `tests/snapshot_report.js`, `tests/test_ui_snapshot.py`, `tests/test_js.py`, `tests/conftest.py`, `tests/snapshots/*`, `tests/gen_data.js` (thêm `make`), `build.py` (thêm tham số đường dẫn ra), `pyproject.toml`, `Makefile`, `.gitignore`.

**Kết quả kiểm tra.** `python -m pytest`: 6/6 đạt (21 bài `test_engine.js`, ảnh chụp báo cáo và CSV, khối CSS, 3 ảnh chụp giao diện). Chạy lại lần hai cho kết quả giống hệt, nên ảnh chụp ổn định.

**Số liệu chính (dữ liệu thật đến 26/10/2026, mã hiện tại).**
| Phương án | Phải mua: số tuần / đợt | Thắng 1t / 6t / 1n | Mốc 1t / 6t / 1n | Nửa đầu / nửa sau (6t) |
|---|---|---|---|---|
| PA1 Pi + MVRV | 41 / 6 | 22% / 27% / 24% | 51% / 60% / 53% | 21% / 100% (3 tuần) |
| PA3 Pi + MVRV + F&G (hạng 1) | 80 / 5 | 54% / 81% / 97% | 51% / 60% / 53% | 81% / không có tín hiệu |
| PA4 Pi + Puell | 44 / 17 | 34% / 57% / 77% | 51% / 60% / 53% | 60% / 25% |
| Pi riêng | 66 / 2 | 56% / 84% / 95% | 51% / 60% / 53% | 79% / 100% |
| Tất cả 10 chỉ số | 37 / 4 | — / 59% / — | 51% / 60% / 53% | 59% / không có tín hiệu |

**Câu hỏi còn mở.** Không có. (Tài liệu nâng cấp nằm ở thư mục gốc, chưa lưu git; đã chuyển vào `docs/` như bạn ghi.)
