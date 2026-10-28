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

## Giai đoạn 2: Mô phỏng so với mua đều (xong 28/10/2026)

**Tóm tắt.** Bộ mô phỏng theo mục 2.1. Mỗi tuần nạp ngân sách B và mua `clip(m × B, 0, tiền mặt)` với hệ số m trong [0,25; 2]. Phần chưa tiêu vào quỹ dự trữ. Quỹ quá 12 × B thì buộc m ≥ 1. Phí 0,10% và trượt giá 0,05%. Mua đều (DCA) là mốc. Đã có đủ các thước đo của mục 2.2: tỷ số tài sản so với mua đều, lợi thế giá vốn, tiền mặt chờ, sụt giảm lớn nhất (theo lợi suất loại bỏ dòng tiền nạp), thời gian dưới đỉnh, Sortino, Calmar, khung trượt 104 tuần mỗi 4 tuần (trung vị và kịch bản xấu P10). Tỷ lệ thắng chỉ để tham khảo, luôn kèm số đợt và khoảng tin cậy.

**Quy ước thời điểm (không nhìn trước).** Quyết định lúc 01:00 UTC thứ Ba, chỉ dùng số liệu đã công bố lúc đó (Coin Metrics của Chủ nhật công bố sớm nhất 00:00 thứ Ba). Mua ở giá đóng cửa thứ Ba. Điểm của bot hiện tại tính cho Chủ nhật, nên chỉ được dùng từ thứ Ba.

**Dựng lại bot hiện tại.** Chạy chính mã JavaScript của bot (`tools/export_current_bot.js`) trên dữ liệu thật. Lấy điểm tỷ lệ nên mua từng tuần (đi tới, không nhìn trước), rồi đổi khung thành hệ số: Phải mua → 2,0, Cân nhắc mua → 1,25, Không nên mua → 0,25. Chế độ mặc định "Tự động: phương án tốt nhất" được chọn lại mỗi 4 tuần từ 01/2021, chỉ với dữ liệu có đến lúc đó. Bot đổi lựa chọn nhiều lần: tất cả chỉ số → PA6 [Khối lượng] (07/2022) → PA3 → PA6 [RSI + MVRV Z] → PA3. Trước khi có điểm, hệ số = 1 (mua đều).

**Bảng mốc đầu tiên** (dữ liệu đến 31/12/2022; giai đoạn kiểm tra cuối từ 01/01/2023 vẫn khóa):

| Chiến lược | Giai đoạn | Tỷ số tài sản so với mua đều | Trung vị khung 2 năm | Kịch bản xấu (10% tệ nhất) | Số khung | Lợi thế giá vốn | Tiền mặt chờ TB | Sụt giảm lớn nhất (bot / mua đều) |
|---|---|---|---|---|---|---|---|---|
| Bot hiện tại (Tự động: phương án tốt nhất, chọn lại mỗi 4 tuần) | Huấn luyện | 1,000 | 1,000 | 1,000 | 92 | 0,0% | 0% | -90% / -90% |
| Bot hiện tại (Tự động: phương án tốt nhất, chọn lại mỗi 4 tuần) | Kiểm định | 0,988 | 0,974 | 0,967 | 14 | -1,6% | 5% | -76% / -76% |
| PA3 cố định (Pi + MVRV + F&G) | Huấn luyện | 1,000 | 1,000 | 1,000 | 92 | 0,0% | 0% | -90% / -90% |
| PA3 cố định (Pi + MVRV + F&G) | Kiểm định | 0,943 | 0,882 | 0,856 | 14 | -5,7% | 10% | -74% / -76% |
| PA1 (Pi + MVRV) | Huấn luyện | 1,000 | 1,000 | 0,895 | 92 | +2,7% | 1% | -90% / -90% |
| PA1 (Pi + MVRV) | Kiểm định | 0,973 | 1,001 | 0,963 | 14 | -2,8% | 5% | -76% / -76% |
| PA2 (Pi + MVRV Z) | Huấn luyện | 1,000 | 1,000 | 0,897 | 92 | +2,7% | 2% | -90% / -90% |
| PA2 (Pi + MVRV Z) | Kiểm định | 0,962 | 1,001 | 0,946 | 14 | -4,1% | 8% | -76% / -76% |
| PA4 (Pi + Puell) | Huấn luyện | 0,999 | 0,989 | 0,775 | 92 | +2,7% | 2% | -90% / -90% |
| PA4 (Pi + Puell) | Kiểm định | 0,856 | 0,805 | 0,783 | 14 | -14,4% | 20% | -75% / -76% |
| PA5 (F&G + MVRV + MA200) | Huấn luyện | 1,000 | 1,000 | 1,000 | 92 | 0,0% | 0% | -90% / -90% |
| PA5 (F&G + MVRV + MA200) | Kiểm định | 0,957 | 0,910 | 0,884 | 14 | -4,3% | 9% | -74% / -76% |
| Tất cả chỉ số | Huấn luyện | 1,000 | 1,000 | 1,000 | 92 | 0,0% | 0% | -90% / -90% |
| Tất cả chỉ số | Kiểm định | 1,018 | 1,037 | 0,988 | 14 | +1,7% | 7% | -75% / -76% |

| Chiến lược | 01/2011–11/2012 | 11/2012–07/2016 | 07/2016–05/2020 | 05/2020–12/2022 |
|---|---|---|---|---|
| Bot hiện tại (Tự động: phương án tốt nhất, chọn lại mỗi 4 tuần) | 1,000 | 1,000 | 1,000 | 0,983 (chưa trọn) |
| PA3 cố định (Pi + MVRV + F&G) | 1,000 | 1,000 | 1,000 | 0,922 (chưa trọn) |
| PA1 (Pi + MVRV) | 1,000 | 0,987 | 0,986 | 1,001 (chưa trọn) |
| PA2 (Pi + MVRV Z) | 1,000 | 0,987 | 0,986 | 1,001 (chưa trọn) |
| PA4 (Pi + Puell) | 1,000 | 0,981 | 0,786 | 0,858 (chưa trọn) |
| PA5 (F&G + MVRV + MA200) | 1,000 | 1,000 | 1,000 | 0,941 (chưa trọn) |
| Tất cả chỉ số | 1,000 | 1,000 | 1,000 | 1,024 (chưa trọn) |

**Đọc kết quả.**
- Bot hiện tại ở chế độ mặc định **kém mua đều** trong giai đoạn kiểm định: tỷ số 0,988, trung vị khung 2 năm 0,974, kịch bản xấu 0,967.
- PA3 cố định (phương án đang đứng đầu, chọn bằng dữ liệu đến hôm nay) còn kém hơn: 0,943. PA4 kém nhất (0,856, chu kỳ 2016–2020 chỉ 0,786).
- Ở giai đoạn huấn luyện, phần lớn phương án chưa có điểm (cần Fear & Greed từ 2018), nên bằng đúng mua đều.
- Đây là mốc mà mô hình mới phải vượt (tiêu chí 7).

**File thay đổi.** `bot/backtest/` (engine, metrics, baselines, current_bot, benchmark), `bot/features/panel.py`, `bot/validation/splits.py` (chia giai đoạn, chu kỳ halving, khóa giai đoạn kiểm tra cuối), `tools/export_current_bot.js`, `bot/cli.py` (lệnh `backtest`), `tests/test_backtest.py`.

**Kết quả kiểm tra.** `python -m pytest`: 21/21 đạt (8 bài mới cho mô phỏng, thước đo, ghép điểm theo thời điểm, khóa giai đoạn kiểm tra cuối).

**Câu hỏi còn mở.** Không có.
