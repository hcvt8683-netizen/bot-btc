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

## Giai đoạn 3: Bộ công cụ kiểm định (xong 28/10/2026)

**Tóm tắt.** Đủ các công cụ của mục 5:
- Chia giai đoạn huấn luyện 2011–2019, kiểm định 2020–2022, kiểm tra cuối từ 2023. Giai đoạn kiểm tra cuối bị khóa: mã phát triển không đọc được giá sau 31/12/2022. Chỉ cờ `--final` mới mở, và mỗi lần mở được ghi vào `experiments/final_runs.log`.
- Đi tới với cửa sổ mở rộng, học lại mỗi 13 tuần. Mẫu huấn luyện nào có nhãn chạm vào giai đoạn kiểm tra thì bị cắt bỏ (purge), cộng khoảng đệm (embargo) bằng kỳ nhãn.
- Bootstrap khối 26 tuần, 2.000 lần, cho khoảng tin cậy 95% của tỷ số tài sản và lợi thế giá vốn.
- Kiểm tra với tín hiệu ngẫu nhiên: xáo hệ số theo khối 26 tuần, 1.000 lần.
- Sổ ghi mọi lần thử `experiments/registry.csv` (thời gian, mã git, mã cấu hình, chỉ số, tham số, kết quả).
- Deflated Sharpe Ratio (Bailey & López de Prado) tính trên lợi suất vượt mua đều hằng tuần.
- Chu kỳ halving: chu kỳ bị cắt bởi khóa kiểm tra cuối được đánh dấu "chưa trọn".

**Áp dụng cho bot hiện tại (chế độ Tự động), giai đoạn kiểm định 2020–2022.**
| Thước đo | Kết quả | Ngưỡng chấp nhận |
|---|---|---|
| Tỷ số tài sản so với mua đều | 0,988 (khoảng tin cậy 95%: 0,819–1,051) | trung vị khung > 1,00 và P10 ≥ 0,97 |
| Lợi thế giá vốn | -1,6% (khoảng tin cậy 95%: -15,4% đến +4,8%) | — |
| Kiểm tra với tín hiệu ngẫu nhiên | hơn 62% số lần xáo | ≥ 95% |
| Sharpe của phần vượt mua đều (năm hóa) | -0,72 | — |
| Deflated Sharpe Ratio | 0,08 | — |

Bot hiện tại không đạt các tiêu chí mới. Lợi thế của nó không phân biệt được với may rủi.

**File thay đổi.** `bot/validation/` (walkforward, bootstrap, placebo, registry, dsr, evaluate), `bot/backtest/metrics.py` (lợi suất vượt mua đều, Sharpe), `bot/backtest/benchmark.py` (ghi sổ), `experiments/registry.csv` (7 lần thử: các phương án của bot hiện tại), `tests/test_validation.py`.

**Kết quả kiểm tra.** `python -m pytest`: 26/26 đạt.

**Câu hỏi còn mở.** Không có.

## Giai đoạn 4: Lõi lớp chu kỳ (lớp A) (xong 28/10/2026)

**Tóm tắt.** Dựng lại lõi trên dữ liệu từ 2011 với 10 chỉ số nhóm A (`bot/features/catalogue.py`): MVRV, MVRV Z, Pi, Giá/MA 200 tuần, Mayer, Puell, giảm từ đỉnh, NUPL, pha halving, Hash Ribbon. Chuẩn hóa thành phân vị theo thời điểm trong 208 tuần (trống trước 104 tuần), rồi đổi chiều thành "độ rẻ". Bảng chỉ số theo tuần lưu ở `data/features.parquet` kèm `available_at`. Thử theo đúng thứ tự mục 4.2: mô hình 1 (tổng hợp đều) → mô hình 2 (ridge ràng buộc dấu, đi tới, cắt bỏ nhãn chồng) → mô hình 3 (boosting đơn điệu). Chỉ chọn bằng giai đoạn huấn luyện. Chi tiết: `docs/ABLATION_A.md`.

**Phát hiện chính.**
- Các chỉ số định giá gần như đo cùng một thứ trong giai đoạn huấn luyện: MVRV tương quan 0,99 với MVRV Z, 1,00 với NUPL, 0,94 với giảm từ đỉnh, 0,91 với MA 200 tuần. Với quy tắc |ρ| > 0,8, tối đa giữ được 3 chỉ số.
- Với bảng hệ số mặc định của tài liệu (T0), mọi chỉ số riêng đều **kém mua đều** trên giai đoạn huấn luyện (trung vị khung 2 năm 0,92–0,97). Lý do: hệ số trung bình dưới 1 nên tiền nằm chờ khi giá lên, và mua gấp đôi lúc rẻ chỉ làm được khi đã để dành từ trước.
- Hồi quy đi tới: hệ số của mọi chỉ số định giá trên lợi suất 26/52 tuần **đổi dấu** giữa các lần học hoặc ngược chiều kinh tế ("rẻ" đi kèm lợi suất thấp hơn). Theo quy tắc mục 4.2 phải bỏ, nên mô hình 2 và 3 không hơn mô hình 1.
- Bộ thắng theo quy tắc định trước: bảng T1 (≥ 0,8 → 2,0; 0,6–0,8 → 1,25; 0,2–0,6 → 1,0; < 0,2 → 0,5) với Pi + Giá/MA 200 tuần + Hash Ribbon. Bộ này **gần như mua đều**.

| Chiến lược (dữ liệu đến 31/12/2022) | Huấn luyện: trung vị / P10 | Kiểm định: tỷ số | Kiểm định: trung vị / P10 | Chu kỳ halving có tỷ số > 1 |
|---|---|---|---|---|
| Lớp A chọn được (T1: Pi + MA200 tuần + Hash Ribbon) | 1,000 / 1,000 | 1,000 | 1,000 / 1,000 | 1/4 (2016–2020: 1,015) |
| Lớp A, bảng mặc định T0 (Hash Ribbon) | 0,960 / 0,879 | 1,010 | 1,026 / 0,980 | 1/4 |
| Lớp A, bảng T2 (Puell + Hash Ribbon) | 0,998 / 0,981 | 1,006 | 1,012 / 1,009 | 1/4 |
| Bot hiện tại (Tự động) | 1,000 / 1,000 (chưa có điểm) | 0,988 | 0,974 / 0,967 | 0/4 |

Số lần thử trong sổ đến hết giai đoạn này: 119.

**File thay đổi.** `bot/features/` (catalogue, normalize, build), `bot/models/core.py`, `bot/models/ablation_a.py`, `config/bot.yaml` (mục `model`), `docs/ABLATION_A.md`, `data/features.parquet`, `experiments/registry.csv`, `tests/test_features.py`.

**Kết quả kiểm tra.** `python -m pytest`: 31/31 đạt.

**Câu hỏi còn mở.** Lớp A không có lợi thế vững so với mua đều trên dữ liệu phát triển. Theo quy trình, vẫn làm tiếp lớp B/C, bên bán, rồi chạy một lần giai đoạn kiểm tra cuối để quyết định.

## Giai đoạn 5: Lớp ngắn hạn (B) và lớp vĩ mô (C) (xong 28/10/2026)

**Tóm tắt.** Thêm từng quy tắc một trên nền lớp A. Mọi chỉ số nhóm B dùng chung một mẫu cố định, không dò cho từng chỉ số: nhóm rẻ nhất 20% (phân vị 104 tuần) → × 1,25; nhóm đắt nhất 20% → × 0,75; sự kiện đầu hàng → × 1,25 trong 4 tuần. Dưới 10 đợt độc lập thì chỉ hiển thị. Dữ liệu nhóm B chỉ có từ 2018–2020, nên mỗi quy tắc được chấm trong khoảng có dữ liệu của nó với khung trượt 52 tuần (ghi rõ trong báo cáo). Lớp C: hoãn mua tới ngày sau sự kiện (FOMC, CPI, PCE, đáo hạn quyền chọn trong 48 giờ tới; mốc mua đều vẫn mua đúng giờ), và quy tắc trần 1,25 khi đô la và lợi suất thực cùng tăng nhanh mà Nasdaq dưới MA 200 ngày. Chi tiết: `docs/ABLATION_BC.md`.

**Kết quả.** Không quy tắc nào đạt điều kiện giữ (kịch bản xấu tốt hơn, trung vị giảm không quá 1%).
| Quy tắc | Số đợt | Trước → sau (trung vị / P10) | Kết luận |
|---|---|---|---|
| funding_7d | 25 | 1,000 / 1,000 → 1,003 / 0,993 | bỏ |
| basis_ann | 12 | 1,000 / 1,000 → 1,000 / 1,000 | bỏ |
| stable_supply_30d | 11 | 1,000 / 1,000 → 1,000 / 0,997 | bỏ |
| Fear & Greed (ngược đám đông / theo đà) | — | chỉ có năm 2019 trong giai đoạn huấn luyện, không chứng minh được ổn định | bỏ (mục 4.1) |
| rsi_14w / rsi_14d | 47 / 124 | → 0,995 / 0,944 và 0,997 / 0,960 | bỏ |
| capitulation | 9 | — | chỉ hiển thị (< 10 đợt) |
| oi_to_mcap, etf_flow_5d, vol_rel_20w | — | — | chỉ hiển thị (chưa đủ dữ liệu, chưa bật, hoặc chỉ là bối cảnh) |
| Hoãn mua sát sự kiện | 150 lần | 1,000 / 1,000 → 1,000 / 0,994 | bỏ |
| Trần vĩ mô 1,25 | 5 | 1,000 / 1,000 → 1,000 / 1,000 | bỏ (gần như không có tác dụng) |

Mô hình cuối vẫn chỉ là lớp A, giữ `layer_b: []` và `layer_c: []` trong `config/bot.yaml`. Số lần thử trong sổ: 132.

**File thay đổi.** `bot/models/overlays.py`, `bot/models/ablation_bc.py`, `bot/backtest/metrics.py` (so sánh khi bot mua ở giá khác mốc), `docs/ABLATION_BC.md`, `experiments/registry.csv`, `tests/test_overlays.py`.

**Kết quả kiểm tra.** `python -m pytest`: 35/35 đạt.

**Câu hỏi còn mở.** Không có.

## Giai đoạn 6: Bên bán (xong 28/10/2026)

**Tóm tắt.** Dựng lại 13 tiêu chí chốt lời của trang web trên lưới quyết định hằng tuần (dữ liệu 2011–2022). Đếm đợt độc lập như trang web (các tuần bật cách nhau dưới 8 tuần gộp một đợt). Tiêu chí dưới 10 đợt chỉ hiển thị. Quy tắc hành động: bán 10% khi nhóm định giá bật cùng nhóm xu hướng hoặc tâm lý; bán 30% khi từ 3 nhóm; không quá 50% trong 26 tuần; chỉ mua lại qua lớp mua. So với giữ nguyên theo từng chu kỳ halving. Chi tiết: `docs/SELL_SIDE.md`.

**Kết quả.**
- Chỉ **RSI 14 tuần ≥ 80** đủ 10 đợt (11 đợt). Cả 11 lần giá 26 tuần sau đều **cao hơn**, nên đây là tín hiệu đà tăng tiếp, không phải đỉnh.
- Các tiêu chí đang được trang web coi là "đáng tin" (Pi Cycle cắt lên, MVRV Z ≥ 7) chỉ có 4–5 đợt từ 2011.
- Không có tiêu chí định giá nào đủ đợt, nên quy tắc không bao giờ bán: 0 tuần bán, 0/4 chu kỳ cải thiện.
- **Kết luận: bên bán chỉ là lời khuyên dạng chữ** (`model.sell: advisory`). Logic bên bán hiện tại trên trang web giữ nguyên.

| Tiêu chí (ví dụ) | Số đợt | Giá thấp hơn sau 26 tuần |
|---|---|---|
| Pi Cycle cắt lên | 5 | 80% (5) |
| MVRV Z-Score ≥ 7 | 4 | 100% (4) |
| MVRV ≥ 3 | 7 | 0% (7) |
| RSI 14 tuần ≥ 80 | 11 | 0% (11) |
| Bot báo Nên bán | 1 | 0% (1) |

Số lần thử trong sổ: 133.

**File thay đổi.** `bot/models/sell.py`, `bot/models/sell_eval.py`, `bot/backtest/engine.py` (thêm bán), `bot/backtest/baselines.py` (ghép điểm bán theo thời điểm), `config/bot.yaml`, `docs/SELL_SIDE.md`, `experiments/registry.csv`, `tests/test_sell.py`.

**Kết quả kiểm tra.** `python -m pytest`: 38/38 đạt.

**Câu hỏi còn mở.** Không có.

## Giai đoạn 7: Giai đoạn kiểm tra cuối (xong 28/10/2026)

**Tóm tắt.** Chạy đúng một lần `python -m bot.cli final --final` (ghi trong `experiments/final_runs.log`) trên dữ liệu đến 27/10/2026, với mô hình đã chốt ở giai đoạn 4–6. Kết quả đầy đủ: `docs/RESULTS.md`; số liệu gốc: `data/results/final_summary.json`. Tổng số lần thử: 135.

**Kết luận: mô hình mới KHÔNG ĐẠT** (không đạt tiêu chí 1, 2, 4, 6; đạt 3, 5, 7; tiêu chí 8 chờ bạn duyệt).

| | Mô hình mới | Bot hiện tại |
|---|---|---|
| Kiểm định: trung vị / P10 | 1,000 / 1,000 | 0,974 / 0,967 |
| Kiểm tra cuối: trung vị / P10 | 1,000 / 1,000 | 0,940 / 0,898 |
| Chu kỳ trọn vẹn có tỷ số > 1 | 1/4 | 0/4 |
| Hơn tín hiệu ngẫu nhiên (kiểm tra cuối) | 50% | 87% |

**Quyết định (điểm dừng 2, bạn đã đồng ý làm tiếp).** Không giao mô hình mới; giữ logic bot hiện tại; chỉ giao phần an toàn (chữ tập trung ở `vi.yaml`, định dạng Việt Nam, chế độ an toàn, triển khai). Phần khuyến nghị mới luôn là hệ số 1,0 (mua đều), kèm lý do.

**File thay đổi.** `bot/validation/final.py`, `bot/cli.py` (lệnh `final`), `docs/RESULTS.md`, `data/results/final_summary.json`, `experiments/final_runs.log`, `experiments/registry.csv`.

**Kết quả kiểm tra.** `python -m pytest`: 38/38 đạt.

## Giai đoạn 8: Giao phần an toàn (xong 28/10/2026)

**Tóm tắt.** Theo điểm dừng 2, giữ logic bot hiện tại, chỉ giao phần an toàn.
- Xóa mã cũ không còn dùng trong `engine.js` (625 → 254 dòng; giao diện không gọi tới).
- **Chuyển toàn bộ 461 chuỗi chữ của trang web vào `bot/i18n/vi.yaml`**, đọc qua `tx()` (`src/i18n.js`). Trang chỉ còn khóa `{{web.page.…}}`. Chuyển bằng công cụ một lần (`tools/migrate_strings.py`). Sau khi chuyển, báo cáo .md, CSV, chữ trên trang, kiểu dáng và cả ảnh chụp giao diện **giống hệt từng byte và từng điểm ảnh** với trước.
- Phần mới **"Khuyến nghị giải ngân tuần này"**, ngay dưới hai đồng hồ:
  - hệ số 1,0 (Chế độ an toàn: mua đều), số tiền trên mỗi 100 $ ngân sách, lý do;
  - bảng so với mua đều (trung vị, kịch bản xấu, lợi thế giá vốn, sụt giảm, kiểm tra ngẫu nhiên);
  - mức bằng chứng (số đợt, cờ "Ít bằng chứng", khoảng tin cậy, số lần thử);
  - sự kiện vĩ mô 7 ngày tới theo giờ Việt Nam, và việc lệnh không bị hoãn;
  - độ mới của từng nguồn.
  
  Số liệu tính bởi `python -m bot.cli report` → `data/recommendation.json`, được `build.py` nhúng vào trang. Báo cáo .md có thêm phần này.
- Chế độ an toàn:
  - mô hình chưa đạt, hoặc dữ liệu bắt buộc thiếu/cũ hơn 3 ngày → hệ số 1,0 kèm lý do;
  - trang mở khi khuyến nghị đã cũ hơn 3 ngày → băng "⚠ Dữ liệu chưa cập nhật, đang hiển thị báo cáo gần nhất…";
  - chưa có khuyến nghị → "Chưa có dữ liệu khuyến nghị → mua đều".
- Đầu trang: "Cập nhật lúc HH:mm dd/mm/yyyy (giờ Việt Nam)". Tiêu đề tab "Báo cáo bot BTC", thêm mô tả trang (meta description).
- Dấu **⚠** cho bộ chỉ số có dưới 10 đợt độc lập ở khung Phải mua, hoặc kết quả 6 tháng của hai nửa lệch hơn 20 điểm %. Áp dụng ở bảng phương án, bảng bộ chỉ số khuyến cáo và báo cáo .md, kèm lý do và một câu chú thích.
- Định dạng: cột "Quy ra BTC" trong báo cáo .md đổi `1.246` → `1,246`. Các định dạng khác vốn đã đúng kiểu Việt Nam. Dấu âm trên trang giữ "−" như cũ.
- Quyền riêng tư: trang công khai chỉ ghi số tiền trên mỗi 100 $. Ngân sách cá nhân (nếu có) để ở `config/personal.yaml` (không lưu git) và chỉ in ra dòng lệnh.

**Khác biệt so với giao diện cũ (cần bạn duyệt, tiêu chí 8).** CSS và kiểu dáng của mọi thành phần **không đổi**: `theme.css` và `ui_styles_*.json` không đổi. Chữ thay đổi ở đúng các chỗ sau:
1. Phần mới "Khuyến nghị giải ngân tuần này" (trang web và báo cáo .md).
2. Dòng "Cập nhật lúc … (giờ Việt Nam)" ở đầu trang; tiêu đề tab "Bot mua bán BTC" → "Báo cáo bot BTC".
3. Dấu ⚠, dòng lý do dưới tên bộ chỉ số, và câu chú thích ⚠ ở cuối dòng dẫn của hai bảng xếp hạng.
4. Báo cáo .md: cột "Quy ra BTC" dùng dấu phẩy thập phân.

Ảnh chụp giao diện mới: `tests/snapshots/ui/win32/`.

**Ngoại lệ có chủ ý.** `chay_bot_xac_suat.py`, `Mo-Bot-BTC.command` (4–5 thông báo) và `HUONG_DAN_*.txt` giữ chữ tại chỗ, vì chúng phải chạy độc lập trong gói zip, không có `vi.yaml`. `build.py` chỉ in thông báo cho người phát triển. Các file tạo tài liệu nghiên cứu (`docs/*.md`) cũng giữ chữ trong mã.

**File thay đổi.** `src/i18n.js`, `src/vi.json`, `src/page.html`, `src/engine.js`, `src/analysis.js`, `src/ui.js`, `build.py`, `bot/i18n/vi.yaml`, `bot/report/vi_report.py`, `bot/cli.py` (lệnh `report`), `data/recommendation.json`, `tools/migrate_strings.py`, `tests/test_report.py`, `tests/fixtures/recommendation.json`, `tests/snapshot_report.js`, `tests/test_ui_snapshot.py`, `tests/snapshots/*`, `CLAUDE.md`.

**Kết quả kiểm tra.** `python -m pytest`: 42/42 đạt. Chạy với dữ liệu thật (giá 80.952 $): không lỗi JavaScript; điện thoại 390 px không cuộn ngang.

## Giai đoạn 9: Triển khai (đã chuẩn bị xong 28/10/2026, chờ "OK deploy")

**Tóm tắt.** Ba workflow GitHub Actions, mọi action chính thức ghim theo mã commit:
- `ci.yml`: kiểm tra mỗi lần đẩy mã và để lại bản trang tải về;
- `daily.yml`: chạy 01:00 UTC = 08:00 giờ Việt Nam; tải dữ liệu, kiểm tra chất lượng, khuyến nghị, dựng trang, kiểm tra, lưu dữ liệu, đăng Pages; không bao giờ chạy chồng nhau;
- `rollback.yml`: đăng lại một phiên bản cũ, mặc định `v1-before-upgrade`.

Thêm `python build.py --site`, `requirements.txt`, lệnh `features`. Bản chụp dữ liệu hằng ngày giảm còn 30 ngày cho nhẹ. Hướng dẫn đầy đủ, danh sách cài đặt GitHub cần đổi tay và cách quay lại bản cũ: `docs/DEPLOY.md`.

**Chưa đẩy lên GitHub, chưa gộp, chưa đăng gì** (đúng mục 11). Thẻ `v1-before-upgrade` khớp từng byte với trang đang chạy. Kho trên máy chưa nối với GitHub, nên bản dựng để duyệt được đóng gói trên máy: `dist/trang-web-ban-nang-cap.zip`. Đây là bản tương đương "artifact"; sau khi đẩy nhánh lên, CI cũng sẽ tạo bản này.

**Kiểm tra.** `python -m pytest`: 42/42 đạt. Trang dựng sẵn chạy với dữ liệu thật (giá 80.970 $): không lỗi JavaScript, điện thoại 390 px không cuộn ngang. 9/9 nguồn truy cập được từ máy ở Việt Nam. Kết quả từ máy chủ GitHub sẽ có sau lần chạy đầu.

**Cài đặt GitHub bạn cần đổi tay.** Pages → Source "GitHub Actions"; Actions → Workflow permissions "Read and write"; môi trường `github-pages` chỉ cho `main`; nên bật bắt buộc kiểm tra `test` trước khi gộp vào `main`; `FRED_API_KEY` không bắt buộc. Chi tiết ở mục 4 của `docs/DEPLOY.md`.

**Câu hỏi còn mở.** Chờ bạn duyệt khác biệt giao diện (tiêu chí 8) và nói **"OK deploy"**.

## Triển khai (xong 28/10/2026, sau khi bạn nói "OK deploy")

- Nối kho trên máy với `hcvt8683-netizen/bot-btc`. Gộp nâng cấp vào `main` (giữ lịch sử và `index.html` cũ của GitHub để quay lại được). Đẩy `main`, thẻ `v1-before-upgrade` và nhánh `upgrade/best-roi`. Bạn tự đăng nhập GitHub bằng mã thiết bị.
- CI trên máy chủ GitHub đạt hết. Bạn đổi Pages sang "GitHub Actions" và bật quyền ghi cho workflow.
- `Daily` giờ chạy cả khi có mã mới trên `main` (trừ khi chỉ sửa tài liệu). Lần chạy đầu thành công: lưu dữ liệu, dựng trang, đăng lên https://hcvt8683-netizen.github.io/bot-btc/ (tiêu đề "Báo cáo bot BTC", có phần khuyến nghị).
- Từ máy chủ GitHub ở Mỹ, Binance chặn hợp đồng tương lai (HTTP 451): funding, khối lượng hợp đồng mở, hợp đồng quý. Ba nguồn này không dùng trong khuyến nghị. Trên trang, thông báo lỗi giờ là tiếng Việt dễ hiểu. Khối lượng hợp đồng mở không ghi tiếp được từ máy chủ GitHub; muốn ghi thì cần chạy trên máy ở Việt Nam (self-hosted runner, xem `docs/DEPLOY.md`).
- Kết quả kiểm tra từng nguồn được lưu mỗi ngày ở `data/endpoint_check.json`.
