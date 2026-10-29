# Bot mua bán BTC

Bot thống kê giúp quyết định mua thêm hay chốt lời BTC, giao diện tiếng Việt. Chạy trên máy (Windows, Mac) hoặc xem trên web:
https://hcvt8683-netizen.github.io/bot-btc/

**Kết luận hiện tại:** sau khi xây lại quy trình kiểm định, mô hình không đạt tiêu chí chấp nhận định trước, nên khuyến nghị là **mua đều** (hệ số 1,0). Các khung "Phải mua / Cân nhắc mua" chỉ để tham khảo. Số liệu đầy đủ: [docs/BAO_CAO.md](docs/BAO_CAO.md), phụ lục: [docs/PHU_LUC.md](docs/PHU_LUC.md).

Công cụ tham khảo, không phải lời khuyên đầu tư.

## Dùng bot

- Windows: bấm đúp `Mo-Bot-BTC.bat`. Mac: bấm đúp `Mo-Bot-BTC.command`. Hướng dẫn chi tiết: `HUONG_DAN_WINDOWS.txt`, `HUONG_DAN_MAC.txt`.
- Hoặc: `python chay_bot_xac_suat.py` rồi mở http://127.0.0.1:8789 (máy chủ cục bộ chuyển tiếp yêu cầu dữ liệu và lưu bản sao để dùng khi mất mạng).
- Trên trang: chọn Bên mua / Bên bán, ngày phân tích, bộ chỉ số; ô "Kế hoạch giải ngân một khoản tiền" lập lịch mua theo số tiền bạn nhập.

## Cấu trúc mã

| Phần | Thư mục | Nội dung |
|---|---|---|
| Dữ liệu | `bot/data/` | Tải từng nguồn (`fetchers/`: Coin Metrics, Alternative.me, Binance, FRED, Bitstamp, CoinGecko…), lưu theo thời điểm công bố (`pit_store.py`), kiểm tra chất lượng, đối chiếu giữa các nguồn (`crosscheck.py`), danh mục nguồn có dấu thời gian (`manifest.py`). |
| Đặc trưng | `bot/features/` | `weekly_close.py`: bảng tuần theo giá đóng Chủ nhật 23:59 UTC, phân vị trượt 4 năm, chế độ lãi suất Fed. |
| Mô hình | `bot/models/` | Hồi quy logistic L2 đi tới lồng nhau có ràng buộc dấu (`wf_logit.py`), khung có vùng trễ và hệ số giải ngân (`zones.py`), bên bán một hệ thống (`sell_system.py`), kịch bản giá (`scenarios.py`), nhật ký đi tới (`forward.py`), kế hoạch giải ngân (`deploy_plan.py`); các bước kiểm định `part_c.py` … `part_i.py`. |
| Kiểm định | `bot/backtest/` | Thước đo thống nhất (`measure.py`: đợt, bootstrap khối, Wilson, đơn điệu, hiệu chỉnh), mô phỏng so với mua đều (`engine.py`, `metrics.py`), bot hiện tại chạy lại bằng node (`current_bot.py`). |
| Báo cáo | `bot/report/` | Khuyến nghị tuần cho web (`vi_report.py`), báo cáo dữ liệu (`data_report.py`), sự kiện sau mốc chốt dữ liệu (`events.py`), báo cáo tổng và phụ lục (`final_report.py`). |
| Web | `src/`, `build.py` | `engine.js`, `analysis.js`, `ui.js`, `page.html`, chữ trong `bot/i18n/vi.yaml`; `python build.py` ghép thành `bot-xac-suat.html`. |

## Cấu hình

- `config/bot.yaml`: nguồn dữ liệu và độ trễ công bố, chi phí (phí, trượt giá), mục `rebuild` (giá đóng tuần, giá khớp thứ Hai, holdout từ 01/01/2024, kỳ hạn, số lần bootstrap, hạt giống ngẫu nhiên).
- `config/candidates.yaml`: mọi lựa chọn **đăng ký trước khi chạy**: 8 bộ chỉ số kèm lý do kinh tế, λ, khung, hệ số, bên bán, kịch bản giá, vĩ mô, nhật ký đi tới, 6 tiêu chí chấp nhận, kế hoạch giải ngân. Mỗi lần đổi sau khi xem kết quả được ghi trong `docs/REBUILD_LOG.md`.
- `config/events.yaml`: lịch FOMC, CPI, PCE (cập nhật bằng `python tools/update_events.py`).

## Lệnh

| Việc | Lệnh |
|---|---|
| Tải dữ liệu, kiểm tra chất lượng | `python -m bot.cli fetch` |
| Báo cáo dữ liệu (Phần A) | `python -m bot.cli data-report` |
| Khuyến nghị tuần cho web | `python -m bot.cli report` |
| Ghép trang | `python build.py` (thêm `--zip` để tạo gói Windows và Mac) |
| Báo cáo tổng, phụ lục, biểu đồ hiệu chỉnh | `python -m bot.cli final-report` |
| Nhật ký đi tới | `python -m bot.cli forward log`, `python -m bot.cli forward score` |
| Kiểm tra tất cả (không cần mạng) | `python -m pytest` |

Lần chạy holdout duy nhất (`python -m bot.cli acceptance --final`) đã chạy ngày 29/10/2026 và được ghi trong `experiments/final_runs.log`; lệnh từ chối chạy lần hai.

## Kiểm tra

`python -m pytest` chạy mọi bài kiểm tra, gồm:

- **Rò rỉ thông tin (không nhìn trước):** `tests/test_leak.py` (đặc trưng, phân vị), `tests/test_leak_model.py` (mô hình đi tới, purge, hệ số), `tests/test_sell_system.py`, `tests/test_scenarios.py`, `tests/test_forward.py`, `tests/test_plan.py`. Các bài cho mô hình đi tới, hệ số giải ngân, bên bán, sự kiện và nhật ký đi tới đã được thử bằng cách cài lỗi vào mã: bài kiểm tra bắt được (ghi trong `docs/REBUILD_LOG.md`).
- Thước đo, khung, sự kiện, tiêu chí chấp nhận: `tests/test_measure.py`, `tests/test_zones.py`, `tests/test_events.py`, `tests/test_part_i.py`, `tests/test_part_c.py`.
- Tính toán phía trình duyệt: `node tests/test_engine.js`; ảnh chụp báo cáo, CSV, chữ và giao diện: `tests/test_ui_snapshot.py`, `tests/test_report.py`.

## Nguyên tắc

1. Không nhìn trước: tại tuần t chỉ dùng dữ liệu đến hết t; mẫu học kết thúc tại t − h (purge theo kỳ hạn).
2. Mọi tính toán mô hình dùng giá đóng tuần; giá trực tiếp chỉ để hiển thị.
3. Mọi con số tính từ dữ liệu tải về, không gõ tay; mỗi kết quả kèm số tuần, số đợt độc lập, khoảng tin cậy bootstrap và mức chênh so với mốc.
4. Lựa chọn được đăng ký trước; mọi cấu hình đã thử được ghi lại (`experiments/`) để hiệu chỉnh kiểm định bội.
5. **Nhật ký đi tới đang chạy** (`data/forward/`): không sửa các file tính đầu ra (`bot/models/forward.py`, danh sách `CODE`) hay các mục `model`, `sets`, `zones`, `multiplier`, `sell` (`config/candidates.yaml`) và `rebuild` (`config/bot.yaml`). Sửa nghĩa là phiên bản mới với nhật ký mới (`python -m bot.cli forward freeze`).

## Tự động trên GitHub

- `.github/workflows/daily.yml`: mỗi ngày 01:00 UTC và mỗi lần có mã mới trên `main`: tải dữ liệu, khuyến nghị tuần, ghi nhật ký đi tới, ghép trang, chạy kiểm tra, lưu dữ liệu, đăng trang.
- `.github/workflows/ci.yml`: kiểm tra mỗi lần đẩy mã. `rollback.yml`: đăng lại bản cũ khi cần. Chi tiết: `docs/DEPLOY.md`.

## Tài liệu

- [docs/BAO_CAO.md](docs/BAO_CAO.md): báo cáo tổng; [docs/PHU_LUC.md](docs/PHU_LUC.md): phụ lục (cấu hình, hoán vị, hiệu chỉnh, chu kỳ, chế độ Fed).
- [docs/REBUILD_LOG.md](docs/REBUILD_LOG.md): nhật ký xây lại, Phần A–I và mọi thay đổi thiết kế.
- Từng phần: `DATA_REPORT.md` (A), `MEASURE_B.md` (B), `MODEL_C.md` (C), `ZONES_D.md` (D), `SELL_E.md` (E), `SCENARIO_F.md` (F), `MACRO_G.md` (G), `FORWARD_H.md` (H), `ACCEPTANCE_I.md` (I), `PLAN.md` (kế hoạch giải ngân).
