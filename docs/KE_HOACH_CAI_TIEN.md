# Kế hoạch cải tiến bot BTC (dùng cho các phiên sau)

Viết ngày 29/10/2026, sau khi bot đạt 0/6 tiêu chí chấp nhận (`docs/ACCEPTANCE_I.md`). Kết luận hiện tại: **mua đều**. Khuyết điểm gốc: tín hiệu không chọn được thời điểm tốt hơn mua đều. Phần đáng tin: dải giá dự báo trúng đúng tỷ lệ, quy trình kiểm định trung thực.

## Cách dùng file này

1. Mở Claude Code trong thư mục dự án (`D:\Claude_bot_bit`).
2. Chọn **một** bước chưa làm bên dưới, sao chép nguyên khối "Câu lệnh" và dán vào phiên mới. Mỗi bước một phiên.
3. Khi phiên xong, kiểm tra mục "Xong khi", rồi nhờ Claude đánh dấu `[x]` và ghi ngày vào bảng tiến độ ở cuối file.
4. Nếu Claude muốn sửa một trong các file bị khóa (mục "Quy tắc"), dừng lại hỏi rõ lý do trước khi đồng ý.

## Quy tắc không được vi phạm

- **Đăng ký trước:** mọi lựa chọn (chỉ số, ngưỡng, kỳ hạn, quy tắc so sánh) ghi vào `config/candidates.yaml` và lưu git **trước** khi tính bất kỳ con số nào. Đổi sau khi xem kết quả phải ghi vào `docs/REBUILD_LOG.md`.
- **Không nhìn trước:** tại mỗi tuần chỉ dùng dữ liệu đã có đến tuần đó. Mỗi tính năng mới phải có test rò rỉ, và phải thử cài lỗi nhìn trước để chắc test bắt được.
- **Giai đoạn kiểm tra cuối cũ (01/01/2024 → 25/10/2026) đã dùng hết.** Nghiên cứu mới dùng **giai đoạn kiểm tra cuối mới bắt đầu từ ngày đăng ký**. Chỉ chạy nó một lần, khi đã đủ dữ liệu (ít nhất 1 năm).
- **Nhật ký đi tới đang chạy (`data/forward/`).** Không sửa các file trong danh sách `CODE` của `bot/models/forward.py` (`weekly_close.py`, `wf_logit.py`, `zones.py`, `sell_system.py`, `scenarios.py`, `forward.py`) và các mục `model`, `sets`, `zones`, `multiplier`, `sell` (`config/candidates.yaml`), `rebuild` (`config/bot.yaml`). Sửa thì nhật ký dừng, phải đóng băng phiên bản mới và đếm lại từ đầu. Code mới viết thành **module mới**.
- **Nhật ký dự báo (`data/forecast/`).** Sửa `bot/models/price_forecast.py` hoặc mục `forecast` sẽ tạo phiên bản mới; số liệu kiểm chứng trực tiếp đếm lại theo phiên bản.
- **Mọi con số hiển thị phải tính từ dữ liệu**, không gõ tay. Kết quả không có ý nghĩa thống kê ghi "chưa có lợi thế".
- **Trước khi đưa lên web:** `python build.py`, `python -m pytest` (tất cả phải qua), duyệt khác biệt ảnh chụp rồi mới cập nhật, sau đó đẩy lên `main` và xem GitHub chạy xong.

## Lịch theo dõi (không cần làm gì, chỉ xem lại)

| Ngày | Việc |
|---|---|
| từ 30/10/2026 | Dự báo dải giá đầu tiên đến hạn; trang tự hiện bảng kiểm chứng trực tiếp |
| khoảng 30/11/2026 | Xem tỷ lệ dải 80% trúng sau 1 tháng (bước D1) |
| 25/04/2027 | Nhật ký đi tới đủ 26 tuần: chấm lần đầu (bước D2) |
| 24/10/2027 | Nhật ký đi tới đủ 52 tuần: chấm lần hai (bước D2) |

---

## Nhóm A: việc nhanh (vài giờ mỗi bước)

### A1. Cập nhật lịch sự kiện vĩ mô
- **Vì sao:** lịch CPI chỉ có tới 14/10/2026, trang đang cảnh báo "lịch chưa đủ".
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước A1. Chạy python tools/update_events.py để cập nhật config/events.yaml từ trang chính thức (Fed, BLS, BEA), cho tôi xem khác biệt trước khi lưu. Sau đó chạy lại báo cáo tuần, python build.py, python -m pytest, rồi đẩy lên web và kiểm tra trang không còn cảnh báo lịch thiếu.
```
- **Xong khi:** `config/events.yaml` có CPI các tháng tới; trang không còn dòng "Lịch Chỉ số giá tiêu dùng Mỹ (CPI) chỉ có tới…".

### A2. Gỡ hoặc tính lại phần phân tích cũ trên trang
- **Vì sao:** đồng hồ "Tỷ lệ nên mua", bảng "xác suất thắng" với khoảng tin cậy theo tuần chồng lấn, mục "Bộ chỉ số tìm lại" vẫn hiện và dễ gây hiểu nhầm (khuyết điểm nặng thứ hai).
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước A2. Phần phân tích cũ trong trình duyệt (src/engine.js, src/analysis.js, src/ui.js: đồng hồ tỷ lệ nên mua/bán, giá đề xuất, xác suất thắng, bộ tiêu chí, bộ chỉ số, so sánh phương án) đang dùng khoảng tin cậy theo tuần chồng lấn và chọn bộ chỉ số trên chính dữ liệu chấm. Đề xuất cho tôi hai phương án: (1) gỡ hẳn khỏi trang và báo cáo, (2) tính lại theo thước đo thống nhất (đợt độc lập, bootstrap khối, mốc cùng giai đoạn). Nêu ưu nhược điểm rồi chờ tôi chọn. Không sửa các file bị khóa của nhật ký đi tới.
```
- **Xong khi:** trang chỉ còn con số đã kiểm định, hoặc phần cũ được tính lại và có test; ảnh chụp giao diện đã duyệt.

### A3. Thông báo qua Telegram hoặc email
- **Vì sao:** không phải mở trang mỗi ngày vẫn biết khi có sự kiện ⚑, khi giá ra khỏi dải 80%, hoặc khi nhật ký có kết quả mới.
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước A3. Thêm vào quy trình Daily trên GitHub một bước gửi thông báo Telegram ngắn bằng tiếng Việt khi: có sự kiện gắn cờ sau mốc chốt dữ liệu, giá đóng ngày nằm ngoài dải 80% của dự báo đã đến hạn, hoặc mức bên bán đổi. Token bot Telegram và chat id lấy từ GitHub Secrets (tôi sẽ tự thêm, đừng hỏi tôi token). Có test cho phần soạn nội dung, không gửi thật khi chạy test.
```
- **Xong khi:** có thông báo thử thành công; không lộ token trong mã hay nhật ký.

---

## Nhóm B: đổi sang câu hỏi có cơ may thành công (mỗi bước 1 phiên dài)

Ý tưởng chung: bot đo **độ dao động** tốt (dải giá trúng đúng tỷ lệ), nên dùng nó cho **quản trị rủi ro** thay vì đoán thời điểm. Mỗi bước phải đăng ký trước, so với mua đều, và vẫn phải đạt đủ 6 tiêu chí của Phần I trên giai đoạn kiểm tra cuối mới thì mới được bật trên trang.

### B1. Mua theo độ dao động
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước B1 và docs/REBUILD_LOG.md. Nghiên cứu quy tắc "mua theo độ dao động": giữ tổng tiền như mua đều, nhưng số tiền mỗi tuần tỷ lệ nghịch với độ dao động dự báo (dùng cùng cách đo của bot/models/price_forecast.py), có giới hạn 0,5–1,5 lần. Mục tiêu chính: giảm mức sụt lớn nhất và độ biến động của tài sản mà không thua mua đều về lợi thế giá vốn. Làm theo đúng quy trình: đăng ký trước trong config/candidates.yaml (mục mới), lưu git, viết module mới (không sửa file bị khóa), test rò rỉ có thử cài lỗi, kiểm định đi tới trên dữ liệu đến 25/10/2026 với đợt độc lập và bootstrap, rồi đặt giai đoạn kiểm tra cuối mới từ hôm nay. Dừng lại tóm tắt kết quả trước khi đưa gì lên web.
```
- **Xong khi:** có báo cáo `docs/` riêng, kết luận rõ "hơn / chưa có lợi thế / kém" so với mua đều, kèm số tuần, số đợt, khoảng tin cậy.

### B2. Tái cân bằng tỷ trọng thay cho đoán đỉnh (bên bán)
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước B2. Nghiên cứu quy tắc bán theo tỷ trọng: người dùng đặt tỷ trọng BTC mục tiêu trong tài sản; khi BTC vượt 1,5 lần mục tiêu thì bán phần vượt, khi xuống dưới 0,5 lần thì mua bù (thử các ngưỡng đăng ký trước, không dò). So với giữ nguyên và với hệ thống bán hiện tại (Phần E) trên từng chu kỳ, theo đợt. Đúng quy trình đăng ký trước, module mới, test rò rỉ. Nếu có lợi, đề xuất cách hiện trên trang (ô nhập tỷ trọng mục tiêu) nhưng chờ tôi đồng ý.
```
- **Xong khi:** biết rõ quy tắc này có giảm rủi ro hay không ở mỗi chu kỳ, và tốn bao nhiêu lợi nhuận.

### B3. Mua thêm khi giá chạm đáy dải 80%
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước B3. Nghiên cứu: khi giá đóng ngày xuống dưới q10 của dải dự báo 7 ngày đã ghi trước đó, mua thêm một phần cố định từ quỹ dự phòng; so với mua đều cùng tổng tiền. Đăng ký trước, kiểm định đi tới, đợt độc lập, bootstrap, 6 tiêu chí. Nói thẳng nếu không có lợi thế.
```
- **Xong khi:** có kết luận, kèm cảnh báo rõ nếu chỉ có vài đợt.

---

## Nhóm C: dữ liệu mới (cách duy nhất có thể tạo lợi thế thật, cần thời gian)

Dữ liệu mới phải là thứ thị trường chưa phản ánh hết. Mỗi nguồn mới: kiểm tra chất lượng, lưu theo thời điểm công bố, ghi độ trễ trong `config/bot.yaml`. Giai đoạn kiểm tra cuối luôn là **dữ liệu sau ngày đăng ký**.

### C1. Dòng tiền quỹ ETF BTC giao ngay
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước C1. Tìm nguồn công khai, miễn phí, có lịch sử từ 01/2024 cho dòng tiền ròng hằng ngày của các quỹ ETF BTC giao ngay ở Mỹ. Báo tôi nguồn, giấy phép sử dụng và độ trễ công bố trước khi viết bộ tải. Sau đó thêm bộ tải vào bot/data/fetchers theo đúng mẫu hiện có (lưu theo thời điểm công bố, kiểm tra chất lượng, test). Chưa đưa vào mô hình.
```
- **Xong khi:** có bộ tải chạy hằng ngày; dữ liệu nằm trong `data/raw/`.

### C2. Phái sinh: funding rate, hợp đồng mở, chênh lệch giá tương lai
- **Ghi chú:** đã ghi mỗi ngày từ 28/10/2026 (`binance_funding`, `binance_oi`). Chỉ nghiên cứu khi có ít nhất 1 năm dữ liệu (từ khoảng 11/2027).
- **Câu lệnh (dùng từ 11/2027):**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước C2. Dữ liệu funding rate và hợp đồng mở đã ghi từ 28/10/2026. Đăng ký trước một bộ nhỏ (tối đa 4 cấu hình, mỗi cấu hình có lý do kinh tế) dùng các dữ liệu này cùng chỉ số cũ, chạy lại quy trình Phần C–I với giai đoạn kiểm tra cuối mới (dữ liệu sau ngày đăng ký). Không sửa file bị khóa; dùng module mới.
```

### C3. Vĩ mô đã tải nhưng chưa dùng
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước C3. Các chuỗi FRED đã tải (chỉ số đô la rộng, lợi suất thực 10 năm, Nasdaq, cung tiền M2) và tổng cung stablecoin chưa được dùng làm đặc trưng. Đăng ký trước tối đa 4 bộ chỉ số có thêm 1 biến vĩ mô (mỗi bộ có lý do), xử lý độ trễ công bố đúng, rồi chạy lại quy trình Phần C (đi tới lồng nhau, ràng buộc dấu, hoán vị có hiệu chỉnh) trên dữ liệu đến 25/10/2026. Giai đoạn kiểm tra cuối mới từ ngày đăng ký. Báo kết quả trung thực.
```

### C4. On-chain sâu (cần bạn quyết định chi phí)
- Dòng tiền vào/ra sàn, nguồn cung của người giữ lâu năm, vốn hóa thực chính xác: thường cần nguồn trả phí (Glassnode, CryptoQuant). **Bạn quyết định có mua không** trước khi mở phiên.
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước C4. So sánh giúp tôi các nguồn dữ liệu on-chain (miễn phí và trả phí): chỉ số có, lịch sử, độ trễ, giá, điều khoản. Đừng đăng ký hay nhập khóa nào; chỉ báo cáo để tôi quyết định.
```

---

## Nhóm D: kiểm tra định kỳ (chỉ đọc, không sửa mô hình)

### D1. Kiểm tra dự báo dải giá hằng tháng
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước D1. Chấm nhật ký data/forecast/forecast_log.csv: bao nhiêu dự báo đã đến hạn, tỷ lệ giá thật nằm trong dải 80% và 50% theo từng kỳ hạn, kèm khoảng tin cậy Wilson theo số lần độc lập, so với kỳ vọng 80% / 50%. Chỉ báo cáo, không sửa phương pháp. Nếu lệch nhiều, nói rõ có ý nghĩa thống kê hay chưa.
```

### D2. Chấm nhật ký đi tới (25/04/2027 và 24/10/2027)
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước D2. Chạy python -m bot.cli forward score và báo cáo kết quả nhật ký đi tới (phiên bản trong data/forward/current.txt): số tuần, số dòng đủ kỳ hạn 26 và 52 tuần, tỷ lệ thắng từng khung so với mốc theo đợt, khoảng tin cậy, kết luận. Không sửa mô hình. Ghi kết quả vào docs/REBUILD_LOG.md.
```

### D3. Kiểm tra sức khỏe hằng tháng
- **Câu lệnh:**
```
Đọc docs/KE_HOACH_CAI_TIEN.md bước D3. Kiểm tra: quy trình Daily trên GitHub có chạy thành công 30 ngày qua không, nguồn dữ liệu nào lỗi hoặc cũ, nhật ký đi tới và nhật ký dự báo có ghi đều không (dòng ghi muộn?), python -m pytest có qua không. Báo cáo ngắn, đề xuất sửa nếu có lỗi, chờ tôi đồng ý mới sửa.
```

---

## Không nên làm (dù kết quả trông đẹp hơn)

- Dò tham số hay ngưỡng cho đến khi kết quả đẹp.
- Thêm chỉ số rồi chọn bộ tốt nhất trên chính dữ liệu dùng để chấm.
- Chạy lại hay xem lại giai đoạn kiểm tra cuối nhiều lần.
- Sửa các file bị khóa của nhật ký đi tới "cho tiện".
- Bật hệ số mua khác 1,0 khi chưa đạt đủ 6 tiêu chí.

## Bảng tiến độ

| Bước | Trạng thái | Ngày | Ghi chú |
|---|---|---|---|
| A1 Lịch sự kiện | [ ] | | |
| A2 Phần phân tích cũ | [ ] | | |
| A3 Thông báo | [ ] | | |
| B1 Mua theo độ dao động | [ ] | | |
| B2 Tái cân bằng tỷ trọng | [ ] | | |
| B3 Mua thêm ở đáy dải | [ ] | | |
| C1 Dòng tiền ETF | [ ] | | |
| C2 Phái sinh (từ 11/2027) | [ ] | | |
| C3 Vĩ mô | [ ] | | |
| C4 On-chain (bạn quyết định) | [ ] | | |
| D1 Dải giá hằng tháng | [ ] | | lần đầu khoảng 30/11/2026 |
| D2 Nhật ký đi tới | [ ] | | 25/04/2027, 24/10/2027 |
| D3 Sức khỏe hằng tháng | [ ] | | |

Thứ tự khuyên dùng: A1 → A2 → B1 → B2; D1, D2, D3 làm theo lịch; nhóm C khi có thời gian, và C2 chỉ từ 11/2027.
