# Rà soát toàn bộ bot và đề xuất nâng cấp (02/11/2026)

Rà soát sau khi làm lại thẻ Long/Short: mở trang web thật (Bên mua, Bên bán, Long/Short), chạy `python -m pytest` (146 bài, qua hết), `node tests/test_engine.js` (qua), `tests/test_browser.py` (xem L6), đọc từng thẻ với dữ liệu thật ngày 02/11/2026.

**Nói thẳng về "xác suất cao nhất có thể":** bot không thể hứa tỷ lệ thắng cao. Điều làm được là mỗi con số xác suất trên trang **đúng tỷ lệ** (bot nói 60% thì trong thực tế khoảng 60% lần xảy ra) và dải giá **hẹp nhất mà vẫn trúng đúng tỷ lệ**. Các đề xuất dưới đây nhắm vào hai điều đó, cộng với sửa lỗi và làm trang dễ dùng hơn. Mọi nghiên cứu mới vẫn theo quy tắc ở `docs/KE_HOACH_CAI_TIEN.md` (đăng ký trước, không nhìn trước, không dò cho đẹp).

Cách dùng: giống `KE_HOACH_CAI_TIEN.md`, mỗi mục một phiên, sao chép khối "Câu lệnh".

---

## Ưu tiên 1: lỗi đã thấy, sửa ngay (mỗi mục dưới 1 giờ)

### L1. Thẻ Giải ngân: câu thừa khi chưa nhập số tiền
- **Thấy gì:** chưa nhập số tiền mà ô kết quả đã hiện "Đây cũng là cách có ROI trung vị cao nhất." (khóa `web.plan.sum_best_same`) đứng một mình, thiếu câu đề xuất phía trước.
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục L1. Trong src/ui.js (kế hoạch giải ngân, #plan-sec), câu web.plan.sum_best_same / sum_best_diff chỉ được hiện khi đã có đề xuất (đã nhập số tiền). Sửa, thêm kiểm tra vào tests/test_ui_snapshot.py hoặc bài kiểm tra giao diện phù hợp, chạy python build.py và python -m pytest.
```

### L2. Chế độ Bên bán còn chữ và công cụ của bên mua
- **Thấy gì:** ở Bên bán, thẻ "Giải ngân" vẫn là công cụ đưa tiền vào BTC; dòng sự kiện vĩ mô ghi "quy tắc hoãn **mua** sát ngày sự kiện".
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục L2. Ở chế độ Bên bán: (1) dòng web.kn.no_delay phải có bản cho bên bán (không nói "hoãn mua"); (2) thẻ Giải ngân hoặc ẩn đi, hoặc ghi rõ "công cụ cho bên mua" — đề xuất cho tôi chọn trước khi sửa. Không đổi số liệu nào. Chạy build, pytest, xem ảnh chụp khác biệt rồi mới cập nhật.
```

### L3. Bộ kiểm tra ghi đè file kết quả thật
- **Thấy gì:** chạy `python -m pytest` làm đổi `data/results/calib.json` (2.800 dòng), dễ lỡ tay commit số liệu do bài kiểm tra tạo ra.
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục L3. Tìm bài kiểm tra nào ghi vào data/results/calib.json khi chạy python -m pytest, sửa để nó ghi vào thư mục tạm (tmp_path), không đổi phương pháp hay số liệu. Kiểm tra: chạy pytest xong thì git status không có file data/ nào bị đổi.
```

### L4. Lịch CPI hết hạn (đã có ở bước A1)
- **Thấy gì:** trang cảnh báo "Lịch CPI chỉ có tới 14/10/2026". Dùng đúng câu lệnh bước A1 trong `KE_HOACH_CAI_TIEN.md`.

### L5. Kiểm chứng trực tiếp dải giá dễ gây hiểu nhầm
- **Thấy gì:** thẻ Dự báo ghi "Đã đến hạn 10 dự báo: 6 lần (60%) trong khoảng 80%". 10 dự báo này đến từ chỉ 4 ngày gốc và chồng thời gian lên nhau, nên 60% chưa nói được gì; trang không có khoảng tin cậy Wilson hay số lần độc lập (trái nguyên tắc 3 và 6 của dự án).
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục L5. Phần "Kiểm chứng trực tiếp" của dải giá (#fc-sec, src/ui.js; số liệu từ nhật ký data/forecast/forecast_log.csv): tách theo kỳ hạn, đếm số lần độc lập (không chồng thời gian), thêm khoảng tin cậy Wilson, và ghi rõ "chưa đủ để kết luận" khi ít hơn 30 lần độc lập. Không sửa bot/models/price_forecast.py (sửa sẽ đổi phiên bản nhật ký). Có test, build, pytest.
```

### L6. `tests/test_browser.py` bị kẹt, không nằm trong pytest
- **Thấy gì:** bài kiểm tra trình duyệt chạy riêng chờ 150 giây ở thẻ "Phân tích cũ" (`#old-body` không hiện) rồi dừng. Đã chạy lại trên bản trang trước khi làm lại Long/Short (commit `43790e3`): kẹt y hệt, nên lỗi có từ trước. Bài này không chạy trong `python -m pytest` nên lỗi không ai thấy.
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục L6. tests/test_browser.py dừng ở wait_for_selector('#old-body:not([hidden])'). Tìm vì sao (có thể bài kiểm tra chặn các nguồn dữ liệu mới, hoặc thiếu window.BOT_NO_WS = true), sửa bài kiểm tra cho khớp trang hiện tại, rồi đưa nó vào python -m pytest (có đánh dấu chạy chậm nếu cần). Không sửa số liệu của trang.
```

---

## Ưu tiên 2: thiếu sót về dự báo giá

### F1. Dải giá neo giá đóng hôm trước, không neo giá lúc xem
- **Thấy gì:** thẻ Dự báo tính dải từ "giá đóng ngày 01/11: 78.135 $" trong khi giá lúc xem đã khác (77.9xx $), và không tính phần ngày đã trôi qua. Công cụ Giá chờ mua thì đã dùng giá lúc tra. Hai thẻ có thể lệch nhau vài trăm đô.
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục F1. Đề xuất cách hiển thị dải giá 1–7 và 30 ngày theo giá trực tiếp (giữ nguyên phân vị đã tính, chỉ đổi giá mốc như mục entry.touch.live), kèm ghi chú. Không sửa bot/models/price_forecast.py và nhật ký. Đăng ký cách hiển thị vào config/candidates.yaml trước, rồi làm, có test.
```

### F2. Chưa có dự báo theo giờ cho Long/Short (xác suất chạm một mức giá trong N giờ)
- **Vì sao:** Long/Short cần biết "giá có chạm cắt lỗ / chốt lời tôi tự đặt trong 4 giờ không". Hiện chỉ có thống kê của các công thức có sẵn. Cách đo đã đúng tỷ lệ ở thẻ Giá chờ mua (từ giá thấp nhất ngày) có thể làm lại trên nến giờ hợp đồng vĩnh cửu (có từ 2020), cho cả hai chiều.
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục F2. Nghiên cứu "xác suất chạm giá trong 1–24 giờ" trên nến giờ BTCUSDT vĩnh cửu (bot/models/perp_signal.hourly), cùng cách của bot/models/entry_timing.py (chia độ dao động, phân vị của 365 ngày trước, chỉ những lần đã biết kết quả), cho cả giá cao nhất và thấp nhất. Đăng ký trước trong config/candidates.yaml, module mới, test rò rỉ có cài thử lỗi, kiểm chứng đi tới (độ phủ dải 80%, Brier so với cách không chỉnh độ dao động). Nếu đạt, thêm ô "giá cắt lỗ / chốt lời của tôi" vào thẻ Long/Short hiện xác suất chạm trong thời gian giữ đã chọn. Dừng lại báo kết quả trước khi đưa lên web.
```

### F3. Độ dao động kỳ vọng từ thị trường quyền chọn (dữ liệu mới)
- **Vì sao:** dải giá hiện chỉ dùng dao động 30 ngày đã qua. Chỉ số dao động kỳ vọng của quyền chọn BTC (Deribit DVOL, công khai, miễn phí) phản ánh điều thị trường đang lo trước sự kiện; có thể làm dải hẹp hơn mà vẫn đúng tỷ lệ. Phải thử trung thực bằng điểm phân vị như `docs/FORECAST_SEARCH.md`.
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục F3. Tìm nguồn công khai lịch sử chỉ số DVOL của Deribit (độ dài lịch sử, độ trễ, điều khoản), báo tôi trước khi viết bộ tải. Sau đó thêm bộ tải theo mẫu bot/data/fetchers (lưu theo thời điểm công bố, test). Chưa đưa vào mô hình; việc so với dải hiện tại làm ở phiên sau, có đăng ký trước.
```

### F4. Dải giá ngày có sự kiện vĩ mô
- **Vì sao:** ngày công bố CPI, họp Fed thường biến động mạnh hơn; dải hiện không đổi theo lịch sự kiện. Cần làm L4 (lịch CPI) trước.
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục F4. Kiểm tra (đăng ký trước, chỉ đo, chưa đổi dải): biến động thật của các ngày có sự kiện trong config/events.yaml có lớn hơn ngày thường không, theo đợt độc lập, khoảng tin cậy, hai nửa giai đoạn. Báo kết quả; nếu có ý nghĩa, đề xuất cách nới dải ngày sự kiện để tôi duyệt.
```

---

## Ưu tiên 3: công cụ nên thêm

### T1. Máy tính khối lượng lệnh theo rủi ro (Long/Short)
- **Vì sao:** quản lý vốn quan trọng hơn chọn điểm vào. Người dùng nhập tổng vốn và % chấp nhận mất mỗi lệnh (ví dụ 1%); bot tính ký quỹ và đòn bẩy để nếu chạm cắt lỗ thì mất đúng số đó, và báo nếu thanh lý đến trước cắt lỗ. Chỉ là phép tính, không cần kiểm định.
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục T1. Thêm vào thẻ Long/Short (src/ls.js, #lt-sec) ô "Tổng vốn" và "Chấp nhận mất mỗi lệnh (%)": tính khối lượng vị thế, ký quỹ theo đòn bẩy, số tiền mất khi chạm cắt lỗ (gồm phí), cảnh báo khi thanh lý đến trước cắt lỗ. Chữ trong bot/i18n/vi.yaml, có test giao diện ở 1280 và 390, không lưu số tiền ngoài trình duyệt.
```

### T2. Thông báo qua Telegram (bước A3, thêm phần Long/Short)
- **Vì sao:** không phải mở trang mỗi giờ. Báo khi một phía Long/Short đạt từ 5/6 tiêu chí, khi tín hiệu công thức của tháng bật, khi giá ra khỏi dải 80%. Dùng câu lệnh A3 trong `KE_HOACH_CAI_TIEN.md`, thêm các điều kiện này.

### T3. Kế hoạch bán dần cho Bên bán (đối xứng Giải ngân)
- **Vì sao:** Bên bán chưa có công cụ "bán một lượng BTC trong N tuần" như Giải ngân của bên mua; liên quan bước B2.
- **Câu lệnh:**
```
Đọc docs/DE_XUAT_NANG_CAP.md mục T3. Nghiên cứu (đăng ký trước, như mục plan) các cách bán một lượng BTC: bán một lần, chia đều 4/13/26/52 tuần; so trên giá thật, đợt độc lập, Wilson; module mới (không sửa deploy_plan.py). Nếu có cách nên dùng, đề xuất giao diện cho chế độ Bên bán để tôi duyệt.
```

### T4. Dữ liệu mới — cách duy nhất có thể tạo lợi thế thật
- Dòng tiền ETF (C1), phái sinh khi đủ 1 năm (C2, từ 11/2027), vĩ mô (C3): làm theo `KE_HOACH_CAI_TIEN.md`. Riêng Long/Short: nhật ký `data/perp_trade/` từ 03/11/2026 là kiểm tra sạch; chấm lần đầu khoảng 11/2027.

---

## Ưu tiên 4: giao diện dễ dùng hơn

### U1. Long/Short tự lấy giá khi mở
- Hiện phải bấm "Chạy" mới có trạng thái lúc này; trước đó trang dùng số của lần cập nhật gần nhất (có thể chậm 1 ngày vì máy chủ GitHub phải lấy nến giờ từ kho lưu trữ). Đề xuất: tự tải khi mở chế độ Long/Short và mỗi giờ khi trang đang mở.

### U2. Gộp hoặc gỡ "Phân tích cũ" (bước A2)
- Thẻ Phân tích cũ vẫn ghi "Tỷ lệ nên mua 69% → Cân nhắc mua", thẻ Kiểm định ghi "thứ hạng 78 → Cân nhắc mua", trong khi khuyến nghị chính là "Mua đều". Ba câu khác nhau dễ làm người dùng rối. Làm bước A2 (khuyên chọn phương án gỡ hẳn).

### U3. Chú giải cho các khái niệm khó
- R, t, khoảng tin cậy Wilson, "chấm đi tới", "đợt độc lập": thêm dấu (?) bấm vào hiện một câu giải thích, dùng chung cho mọi thẻ.

---

## Bảng theo dõi

| Mục | Ưu tiên | Trạng thái | Ghi chú |
|---|---|---|---|
| L1 Câu thừa ở Giải ngân | 1 | [ ] | |
| L2 Chữ bên mua ở Bên bán | 1 | [ ] | cần bạn chọn cách xử lý thẻ Giải ngân |
| L3 Test ghi đè số liệu | 1 | [ ] | |
| L4 Lịch CPI (A1) | 1 | [ ] | |
| L5 Kiểm chứng dải giá trực tiếp | 1 | [ ] | |
| L6 test_browser.py kẹt | 1 | [ ] | |
| F1 Dải giá theo giá trực tiếp | 2 | [ ] | |
| F2 Xác suất chạm giá theo giờ | 2 | [ ] | phiên dài |
| F3 Dao động kỳ vọng (DVOL) | 2 | [ ] | dữ liệu mới |
| F4 Dải giá ngày sự kiện | 2 | [ ] | sau L4 |
| T1 Khối lượng lệnh theo rủi ro | 3 | [ ] | |
| T2 Telegram (A3) | 3 | [ ] | |
| T3 Bán dần | 3 | [ ] | |
| U1 Long/Short tự lấy giá | 4 | [ ] | |
| U2 Gỡ Phân tích cũ (A2) | 4 | [ ] | |
| U3 Chú giải | 4 | [ ] | |

Thứ tự khuyên dùng: L1 → L3 → L5 → L6 → L4 → T1 → U1 → F1 → F2; sau đó theo lịch của `KE_HOACH_CAI_TIEN.md`.
