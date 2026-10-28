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

## Giai đoạn 1: Dữ liệu (xong 28/10/2026)

**Tóm tắt.** Thêm gói `bot/` (Python) với bộ tải dữ liệu cho từng nguồn, kho lưu theo thời điểm công bố, kiểm tra chất lượng và lệnh `python -m bot.cli fetch`. Đã tải lần đầu 11 chuỗi số liệu, có lịch sử từ 2010. Bản chụp thô không bao giờ ghi đè (`data/raw/<nguồn>/<ngày>.parquet`). Bản đầu chứa toàn bộ lịch sử, các bản sau chỉ giữ 90 ngày gần nhất, nên thư mục nhỏ (1,1 MB). Mỗi dòng có thời điểm công bố `available_at` = cuối kỳ + độ trễ của nguồn. Kiểm tra chất lượng chạy mỗi lần tải: trùng ngày, sai thứ tự, khoảng trống, biến động lớn hơn 5σ (chỉ đánh dấu), dữ liệu cũ hơn 3 ngày (lỗi, dẫn tới chế độ an toàn). Lịch sự kiện vĩ mô `config/events.yaml` dựng từ trang chính thức: 135 lần FOMC, 189 lần CPI từ 2011, lịch PCE sắp tới; đáo hạn quyền chọn tính theo quy tắc thứ Sáu cuối tháng. Thêm `bot/i18n/vi.yaml` và `bot/i18n/fmt.py` (định dạng Việt Nam) ngay từ đầu cho phần mới.

**Nguồn đã kiểm chứng (28/10/2026, từ máy ở Việt Nam).**
| Nguồn | Trường | Có từ | Kết quả |
|---|---|---|---|
| Coin Metrics community | PriceUSD, CapMrktCurUSD, CapMVRVCur, HashRate, IssTotUSD | 18/07/2010 | OK. `CapRealUSD` không có ở bản miễn phí, nên vốn hóa thực = vốn hóa / MVRV. |
| Alternative.me | Fear & Greed | 01/02/2018 | OK |
| Binance spot | nến ngày, khối lượng | 17/08/2017 | OK (có dự phòng data-api.binance.vision) |
| Binance USDⓈ-M | funding rate 8 giờ | 10/09/2019 | OK |
| Binance | khối lượng hợp đồng mở (chỉ 30 ngày) | ghi tiếp từ 28/10/2026 | OK, bắt đầu ghi mỗi ngày |
| Binance COIN-M | hợp đồng quý (basis) | 08/2020 | OK |
| DefiLlama | tổng cung stablecoin | 11/2017 | OK |
| FRED (CSV công khai, không cần khóa) | DTWEXBGS, DFII10, NASDAQCOM, M2SL | 1959–2006 | OK |
| Farside (dòng tiền ETF) | — | — | Không bật (tùy chọn, đọc bảng trên trang web dễ hỏng); ghi trong `features.disabled`. |

**File thay đổi.** `bot/` (config, cli, data/http, data/fetchers/*, data/pit_store, data/quality, data/update, data/check_sources, i18n), `config/bot.yaml`, `config/events.yaml`, `tools/update_events.py`, `data/raw/*`, `data/status.json`, `tests/test_data.py`.

**Kết quả kiểm tra.** `python -m pytest`: 13/13 đạt (7 bài mới cho dữ liệu, không gọi mạng).

**Câu hỏi còn mở.** Việc ghi khối lượng hợp đồng mở mỗi ngày đã chạy lần đầu trên máy này. Từ giai đoạn 9 sẽ do GitHub Actions chạy hằng ngày. Từ máy chủ GitHub ở Mỹ, Binance có thể chặn (HTTP 451); khi đó các chỉ số phái sinh tạm không dùng được (xem giai đoạn 9).
