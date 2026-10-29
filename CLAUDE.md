# Bot mua bán BTC – hướng dẫn cho Claude Code

Bot chạy trên máy người dùng (Windows và Mac), giao diện tiếng Việt, giúp quyết định mua thêm hoặc chốt lời BTC bằng thống kê lịch sử. Người dùng không phải lập trình viên: luôn giải thích bằng tiếng Việt đơn giản, mỗi thay đổi nhỏ và kiểm tra được.

## Cấu trúc
- `src/engine.js` (đối tượng `BOT`): tải và ghép dữ liệu, tính 10 chỉ số (Fear & Greed, MVRV, MVRV Z-Score, Giá/MA 200 tuần, Mayer, RSI 14 tuần, Pi Cycle, Puell, Giảm từ đỉnh, Khối lượng tương đối), hồi quy logistic, khối lượng giao dịch.
- `src/analysis.js` (đối tượng `B3`): phân tích theo tuần tại một ngày bất kỳ (`analyze`), tìm bộ chỉ số (`search`), so sánh phương án PA1–PA6 (`compareOptions`), bên bán (`sellSide`), báo cáo và CSV.
- `src/ui.js`: toàn bộ giao diện (bên mua, bên bán, biểu đồ canvas, Claude API, xuất file).
- `src/page.html`: khung trang và CSS; có 4 chỗ đánh dấu `/*I18N*/`, `/*CORE*/`, `/*B3*/`, `/*UI*/`; chữ trong trang viết dạng `{{web.page.khoa}}`.
- `src/i18n.js` (`I18N.tx`, `I18N.vnTime`): đọc chữ từ `bot/i18n/vi.yaml`. Mọi chữ người dùng thấy nằm trong `vi.yaml`, mã chỉ dùng `tx('web.ui.khoa', ...)`. `python build.py` sinh `src/vi.json` cho bài kiểm tra node.
- `bot/models/price_forecast.py`: dải giá theo ngày (1–7 và 30 ngày, mục `forecast` của `config/candidates.yaml`), nhật ký `data/forecast/forecast_log.csv` (chỉ thêm dòng, Daily ghi mỗi ngày bằng `python -m bot.cli forecast`); giao diện `#fc-sec`. Không phải dự báo hướng giá.
- `bot/models/deploy_plan.py`: kế hoạch giải ngân một khoản tiền (phương án và quy tắc ở `config/candidates.yaml` mục `plan`), ghi vào `data/recommendation.json` (`plan`); giao diện ở `#plan-sec` (bên mua), lịch tính trên trình duyệt, không lưu số tiền.
- `bot/` (Python): dữ liệu theo thời điểm công bố, mô phỏng so với mua đều, kiểm định, mô hình, khuyến nghị tuần (`data/recommendation.json`). Kết quả nghiên cứu: `docs/RESULTS.md` (mô hình mới chưa đạt, khuyến nghị luôn là mua đều).
- `build.py`: ghép thành `bot-xac-suat.html` (một file, chạy bằng cách mở trực tiếp hoặc qua `chay_bot_xac_suat.py`). `python build.py --zip` tạo `dist/BotBTC-Windows.zip` và `dist/BotBTC-Mac.zip`.
- `chay_bot_xac_suat.py`: máy chủ cục bộ cổng 8789, chuyển tiếp yêu cầu dữ liệu (tránh CORS), lưu bản sao vào `du_lieu_tam/` để dùng khi mất mạng.
- `Mo-Bot-BTC.bat` (Windows), `Mo-Bot-BTC.command` (Mac): file bấm đúp để chạy.

## Lệnh
- Ghép: `python build.py`
- Kiểm tra tất cả (không cần mạng): `python -m pytest` (gồm `node tests/test_engine.js`, ảnh chụp báo cáo, CSV, chữ, kiểu dáng và ảnh giao diện)
- Dữ liệu và khuyến nghị: `python -m bot.cli fetch`, `python -m bot.cli report`; mốc so sánh: `python -m bot.cli backtest`
- Giai đoạn kiểm tra cuối (2023 trở đi) bị khóa; chỉ `python -m bot.cli final --final` mở và được ghi vào `experiments/final_runs.log`. Không chỉnh gì theo kết quả này.
- Cập nhật ảnh chụp chỉ sau khi đã duyệt khác biệt: `UPDATE_SNAPSHOTS=1 python -m pytest` và `node tests/snapshot_report.js --update`
- Báo cáo tổng bản xây lại: `python -m bot.cli final-report` (sinh `docs/BAO_CAO.md`, `docs/PHU_LUC.md`, `docs/img/`), chạy lại sau khi kết quả đổi.
- Nhật ký đi tới (`data/forward/`, quy trình Daily tự ghi): không sửa các file trong `CODE` của `bot/models/forward.py` hay các mục `model`, `sets`, `zones`, `multiplier`, `sell` (`config/candidates.yaml`) và `rebuild` (`config/bot.yaml`); sửa thì lệnh ghi dừng, phải `python -m bot.cli forward freeze` thành phiên bản mới.
- Kiểm tra tính toán (không cần mạng): `node tests/test_engine.js`
- Kiểm tra giao diện (cần Playwright): `python tests/test_browser.py`
- Chạy với dữ liệu thật: `python chay_bot_xac_suat.py` rồi mở http://127.0.0.1:8789
- Sau mỗi thay đổi: ghép lại, chạy cả hai bài kiểm tra, rồi chạy với dữ liệu thật và đọc lại các con số.

## Nguồn dữ liệu (tải trực tiếp, không bịa số)
- Coin Metrics community API: giá, vốn hóa, MVRV, phát hành (Puell), từ 2010.
- Alternative.me: Fear & Greed, từ 02/2018.
- Binance: giá trực tiếp, nến ngày và khối lượng BTC/USDT từ 08/2017; dự phòng CoinGecko.

## Nguyên tắc phương pháp (bắt buộc giữ)
1. Không nhìn trước tương lai: tại mỗi thời điểm chỉ dùng dữ liệu và kết quả đã biết tại thời điểm đó. `tests/test_engine.js` có bài kiểm tra điều này; không được làm nó sai.
2. Mọi con số hiển thị phải tính từ dữ liệu tải về; không đặt tay con số kết quả.
3. Luôn so với mốc "mua/bán vào một tuần bất kỳ", kèm số lần, số đợt độc lập và khoảng tin cậy Wilson.
4. Ngưỡng khung cố định, không dò cho đẹp: mua 60/80, bán 70/85; bên bán 1 nhóm → chốt một phần, 3 nhóm → bán phần lớn.
5. Đếm đồng thuận theo nhóm chỉ số, không theo từng chỉ số (MVRV và MVRV Z cùng nhóm; Pi, Mayer, MA 200 tuần, RSI cùng nhóm xu hướng giá).
6. Khi ít dữ liệu hoặc kết quả nửa sau kém nửa đầu, phải nói rõ trên giao diện.
7. Luôn có câu: công cụ tham khảo, không phải lời khuyên đầu tư.

## Lỗi đã gặp, đừng lặp lại
- Canvas: đọc chiều cao gốc qua `baseH(cv)`; không đọc `getAttribute('height')` sau khi đã gán `cv.height = H * dpr` (biểu đồ phình to khi trình duyệt phóng khác 100%). Thử ở `device_scale_factor` 1,25 và 2.
- `Mo-Bot-BTC.bat` phải là ASCII, xuống dòng CRLF; HUONG_DAN cho Windows lưu UTF-8 có BOM.
- Trên Windows không bật `allow_reuse_address` cho máy chủ (cho phép hai máy chủ chiếm một cổng).
- CSV xuất ra có BOM UTF-8, dấu phẩy ngăn cột, dấu chấm thập phân.
- Gọi Claude API từ trình duyệt cần tiêu đề `anthropic-dangerous-direct-browser-access: true`; khóa chỉ lưu trong trình duyệt nếu người dùng chọn ghi nhớ.

## Văn phong giao diện
Tiếng Việt có dấu, câu ngắn, nói con số nghĩa là gì; dùng "Phải mua / Cân nhắc mua / Không nên mua", "Nên bán / Cân nhắc bán / Không nên bán", "Giữ / Chốt lời một phần / Bán phần lớn".
