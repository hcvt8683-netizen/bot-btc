# Đánh giá tổng quan các thẻ và kế hoạch cập nhật (03/11/2026)

Viết sau khi có đủ 5 chế độ (Bên mua, Bên bán, Long/Short, Xu hướng, Price action). Bằng chứng lấy từ các kiểm định đã đăng ký trước (`docs/REBUILD_LOG.md`), hồi cứu cắt ngang 24 thời điểm (`docs/HOI_CUU.md`) và nhật ký đi tới. Không có con số nào ở đây được tính mới.

**Câu ngắn nhất:** phần đáng tin của bot là **đo độ dao động** (giá có thể đi xa tới đâu, khả năng chạm một mức giá). Phần **đoán hướng** (tăng hay giảm, long hay short) ở mọi thẻ đều chưa thắng "một ngày bất kỳ". Không thẻ nào đúng hướng 99%; bot nói thẳng điều đó và để Hold / Mua đều làm mặc định.

## 1. Thẻ nào đáng tin cậy nhất

| Hạng | Thẻ / công cụ | Trả lời câu hỏi | Bằng chứng | Dùng để |
|---|---|---|---|---|
| ★★★★★ | **Dự báo dải giá** 1–7 và 30 ngày (thẻ Dự báo) | Giá sau k ngày thường nằm trong khoảng nào | Khoảng 8/10 lần trúng 80–81% từ 2018 (hàng nghìn lần, Wilson 79–82% ở 1 ngày); hồi cứu 24 thời điểm 19/24. Từ 03/11/2026 trộn độ dao động 1 năm: đúng tỷ lệ hơn lúc êm / lúc mạnh (`docs/FORECAST_REGIME.md`); 30 ngày lúc êm vẫn chỉ khoảng 69% | Đặt cắt lỗ ngoài dải, biết rủi ro |
| ★★★★★ | **Khoảng 9/10 lần** (thẻ Xu hướng) | Như trên, rộng hơn | Trúng 89–93% khi kiểm chứng, cả trên giá Bitstamp | Như trên, khi cần chắc hơn |
| ★★★★½ | **Giá chờ mua** (khả năng chạm) | Đặt lệnh chờ thấp hơn x% thì bao nhiêu % khớp | Đúng tỷ lệ từ 2016 (−2%/7 ngày: nói 71%, thật 72%; −5%: 42% / 43%); hồi cứu 12/24 khi nói 53% | Chọn giá đặt lệnh chờ mua |
| ★★★★ | **Giá chờ bán** (khả năng chạm) | Đặt lệnh chờ bán cao hơn x% | Dài hạn hơi thận trọng (+2%: nói 73%, thật 76%); **2024–2026 đánh giá thấp rõ** (nói 55%, thật 79%) → mục R1 | Chọn giá chốt lời, cộng thêm biên an toàn |
| ★★★ | **Xác suất có lãi** 1, 3, 6, 12 tháng; **Xu hướng** (P tăng); **khuyến nghị tuần "Mua đều"** | Mua lúc này thì sau h tháng có lãi bao nhiêu % | Đúng tỷ lệ nhưng chỉ là **tỷ lệ gốc**: 0/6 tiêu chí; 0/80 mô hình xu hướng; học máy, mẫu nến không thắng | Biết "giữ lâu thì lợi hơn"; không chọn được ngày mua |
| ★★★ | **Hỗ trợ / kháng cự**: khoảng cách, khả năng chạm | Mức gần nhất ở đâu, có tới được không | Đếm trực tiếp từ lịch sử (mô tả, có Wilson) | Biết mức giá đáng chú ý |
| ★★ | **Long/Short** (giá vào, cắt lỗ, chốt lời, thanh lý, 6 tiêu chí) | Có nên long / short lúc này | Chấm đi tới 167 lệnh, thắng 43%, −0,09R mỗi lệnh; chưa tháng nào đạt 6/6; short chưa từng có công thức | **Công cụ kỷ luật**: cắt lỗ ở đâu, đòn bẩy tối đa |
| ★★ | **Price action** (tiêu chí, bật lại / xuyên qua, Kiểm tra điểm vào, Hold) | Chạm hỗ trợ có bật lên không | 0/48 tiêu chí hơn một ngày bất kỳ; 0/102 khung: mức thật không bật tốt hơn mức giả | Đọc thị trường, đặt cắt lỗ có lý do; mặc định Hold |
| ★★ | **Giải ngân / Chốt lời dần** | Chia tiền vào / ra trong bao lâu | So trên giá thật nhưng chỉ khoảng 9 đợt độc lập (cửa sổ 1 năm chồng nhau) | Giảm rủi ro mua / bán đúng đỉnh / đáy; con số kỳ vọng rất rộng |
| ★ | **Phân tích cũ** | Tỷ lệ nên mua / bán | Chọn bộ chỉ số trên chính dữ liệu chấm, khoảng tin cậy quá hẹp; đang nói "Cân nhắc mua" trái với "Mua đều" | **Không dùng để quyết định** → gỡ (A2) |
| — | **Hỏi Claude** | Diễn giải, hỏi đáp | Không phải số đã kiểm định | Hỏi cho hiểu, không để quyết định |

## 2. Các thẻ độc lập hay chồng lên nhau

Các thẻ **riêng rẽ về giao diện** nhưng **không độc lập về thông tin**. Có ba nhóm:

1. **Nhóm đo độ dao động** — Dự báo dải giá, Giá chờ mua / bán, khoảng của Xu hướng, phần "khả năng chạm" của Kiểm tra điểm vào và của Hỗ trợ / kháng cự. Gần như cùng một phép đo (lợi suất chia độ dao động gần đây, phân vị của mấy năm trước). Số của chúng **phải** gần nhau: đó là kiểm tra chéo (lệch nhau là có lỗi), không phải ba lần xác nhận. Ví dụ: tâm và khoảng 1–7 ngày của Xu hướng (tỷ lệ gốc) trùng với thẻ Dự báo vì cùng cách tính.
2. **Nhóm đoán hướng** — tín hiệu tuần (MVRV, MA 200 tuần…), 5 mô hình xu hướng, học máy, 12 mẫu nến, Long/Short (6 tín hiệu trên nến giờ), price action (10 tiêu chí, hỗ trợ / kháng cự). Đặc trưng khác nhau nhưng đều tính từ **cùng một chuỗi giá**, nên tương quan với nhau qua xu hướng vừa qua. Vì **không cái nào có lợi thế**, đếm "nhiều thẻ cùng nói tăng" không tạo ra lợi thế; trang cố ý không cộng chúng lại.
3. **Nhóm kế hoạch tiền** — Giải ngân, Chốt lời dần, tiền và đòn bẩy của Long/Short. Không đoán hướng; kết quả phụ thuộc xu hướng BTC 2016–2026.

**Dữ liệu dùng chung (rủi ro cùng lỗi):** Coin Metrics (giá ngày, MVRV) cho bên mua / bán / xu hướng; Bitstamp ngày cho giá chờ và price action; Binance nến giờ cho Long/Short và khung giờ của Hỗ trợ / kháng cự. Một nguồn lỗi làm nhiều thẻ sai cùng lúc; thẻ "Độ mới của dữ liệu" là nơi xem.

**Thông tin độc lập thật** chỉ có thể đến từ dữ liệu mới mà giá chưa phản ánh hết: dòng tiền quỹ ETF (C1), funding / hợp đồng mở đủ dài (C2, từ 11/2027), độ dao động kỳ vọng của quyền chọn (F3), on-chain sâu (C4).

## 3. Dùng các thẻ thế nào cho đúng

1. **Tích lũy dài hạn:** làm theo khuyến nghị tuần (Mua đều). Có khoản tiền lớn thì dùng Giải ngân để chia đợt.
2. **Đặt lệnh chờ:** thẻ Giá & ngày mua / bán (khả năng chạm đáng tin). Với lệnh bán, cộng thêm biên vì bot đang thận trọng (R1).
3. **Biết rủi ro trước khi vào lệnh:** Dự báo dải giá hoặc khoảng 9/10 lần; đặt cắt lỗ ngoài khoảng thường gặp.
4. **Giao dịch ngắn hạn:** mặc định **Hold**. Nếu vẫn vào: dùng Long/Short hoặc Kiểm tra điểm vào để đặt cắt lỗ, xem đòn bẩy tối đa, không dùng đòn bẩy cao.
5. **Không** dùng Phân tích cũ hay câu trả lời của Claude làm căn cứ chính.

## 4. Kế hoạch cập nhật

Mỗi mục một phiên, sao chép khối "Câu lệnh". Mọi nghiên cứu theo quy tắc của `docs/KE_HOACH_CAI_TIEN.md` (đăng ký trước, không nhìn trước, không dò cho đẹp). Đã xong từ `docs/DE_XUAT_NANG_CAP.md`: L1–L6, T3 (Chốt lời dần), lịch CPI.

### Đợt 1 — gọn và an toàn (1–2 phiên)

**S1. Thẻ "Tóm tắt quyết định" ở đầu trang** — một trang, mỗi công cụ một dòng: đang nói gì, độ tin cậy (theo bảng mục 1), bấm để mở thẻ. Người dùng không phải đi qua 5 chế độ để biết bot nói gì.
```
Đọc docs/DANH_GIA_TONG_QUAN.md mục S1. Thêm một chế độ hoặc khối "Tóm tắt quyết định" ở đầu trang: mỗi công cụ một dòng (Khuyến nghị tuần, Dải giá 7 ngày, Giá chờ mua / bán, Xác suất có lãi, Xu hướng, Long/Short, Price action), ghi điều nó đang nói lúc này và huy hiệu độ tin cậy lấy đúng theo bảng mục 1 của file này (chữ trong vi.yaml, không tự chấm lại). Chỉ đọc số các thẻ đã tính, không tính con số mới. Có test giao diện ở 1280 và 390, build, pytest, đẩy GitHub.
```

**A2 / U2. Gỡ Phân tích cũ** — dùng câu lệnh A2 trong `docs/KE_HOACH_CAI_TIEN.md`, chọn phương án gỡ hẳn.

**R1. Hiệu chỉnh khả năng chạm của giá chờ bán** — câu lệnh R1 trong `docs/DE_XUAT_NANG_CAP.md`.

**L7. Đưa `tests/test_browser.py` vào kiểm tra tự động** — câu lệnh L7 trong `docs/DE_XUAT_NANG_CAP.md`.

### Đợt 2 — chính xác hơn ở phần đáng tin (2–3 phiên)

- **F2. Khả năng chạm giá trong 1–24 giờ** (ưu tiên cao nhất của đợt): cho Long/Short và Price action biết xác suất chạm cắt lỗ / chốt lời **bạn tự đặt** trong số giờ bạn chọn, cùng cách đo đã đúng tỷ lệ ở Giá chờ mua. Câu lệnh F2 trong `docs/DE_XUAT_NANG_CAP.md`.
- **F1. Dải giá theo giá lúc xem** — câu lệnh F1.
- **F4. Nới dải giá ngày có sự kiện vĩ mô** (lịch CPI đã có tới 12/2027) — câu lệnh F4.
- **T1. Khối lượng lệnh theo % vốn chấp nhận mất** — câu lệnh T1.

### Đợt 3 — dữ liệu mới, cách duy nhất có thể tạo lợi thế thật (cần thời gian)

- **F3.** Độ dao động kỳ vọng của quyền chọn (Deribit DVOL): câu lệnh F3.
- **C1.** Dòng tiền quỹ ETF; **C3.** vĩ mô đã tải: câu lệnh trong `docs/KE_HOACH_CAI_TIEN.md`.
- **C2.** Phái sinh (funding, hợp đồng mở): chỉ từ 11/2027.

### Đợt 4 — kiểm chứng đi tới (theo lịch, chỉ đọc, không sửa mô hình)

| Khi nào | Việc | Câu lệnh |
|---|---|---|
| khoảng 30/11/2026 | Dải giá: tỷ lệ trúng trực tiếp sau 1 tháng | D1 trong `KE_HOACH_CAI_TIEN.md` |
| hằng tháng | Sức khỏe: Daily, nguồn dữ liệu, nhật ký | D3 |
| 25/04/2027, 24/10/2027 | Nhật ký đi tới của khuyến nghị tuần | D2 |
| 11/2027 | Nhật ký Long/Short (`data/perp/`, `data/perp_trade/`), Xu hướng (`data/trend/`): chấm lần đầu sau 1 năm | xem mục dưới |
| từ 12/2027 | Price action: giai đoạn kiểm tra cuối mới, chạy một lần | `python -m bot.cli price-action --final` |

Câu lệnh chấm 11/2027:
```
Đọc docs/DANH_GIA_TONG_QUAN.md đợt 4. Chấm các nhật ký đi tới đã đủ 1 năm: data/perp/perp_log.csv, data/perp_trade/select_log.csv, data/trend/trend_log.csv, data/forecast/forecast_log.csv. Mỗi nhật ký: số dòng đã đến hạn, tỷ lệ trúng / thắng so với mốc đã đăng ký, khoảng tin cậy theo lần độc lập, kết luận. Chỉ báo cáo, không sửa mô hình. Ghi vào docs/REBUILD_LOG.md và cập nhật bảng mục 1 của docs/DANH_GIA_TONG_QUAN.md nếu bằng chứng đổi.
```

### Đợt 5 — tiện ích

- **T2.** Thông báo Telegram (gồm khi Long/Short có phía đạt từ 5/6, khi giá vào vùng hỗ trợ / kháng cự đang theo dõi).
- **U1.** Long/Short tự lấy giá khi mở (Price action và Xu hướng đã tự lấy).
- **U3.** Chú giải bấm (?) cho R, t, Wilson, ATR, "chấm đi tới", "mức giả".

## Bảng theo dõi

| Mục | Đợt | Trạng thái | Ghi chú |
|---|---|---|---|
| S1 Tóm tắt quyết định | 1 | [x] 03/11/2026 | bảng ở đầu Tổng quan, 8 dòng, nút Mở |
| A2 Gỡ Phân tích cũ | 1 | [x] 03/11/2026 | gỡ thẻ; báo cáo tải về và gửi Claude bỏ phần chưa kiểm định |
| R1 Giá chờ bán | 1 | [x] 03/11/2026 | không lệch có hệ thống (docs/R1_GIA_CHO_BAN.md) |
| L7 test_browser vào CI | 1 | [x] 03/11/2026 | chạy trong CI (22 giây); chưa bật trong Daily, chờ duyệt |
| F2 Chạm giá theo giờ | 2 | [ ] | ưu tiên của đợt |
| F1 Dải giá theo giá lúc xem | 2 | [ ] | |
| F4 Dải giá ngày sự kiện | 2 | [ ] | |
| T1 Khối lượng lệnh theo rủi ro | 2 | [ ] | |
| F3 DVOL | 3 | [ ] | |
| C1 ETF, C3 vĩ mô | 3 | [ ] | |
| C2 Phái sinh | 3 | [ ] | từ 11/2027 |
| Chấm nhật ký 1 năm | 4 | [ ] | 11/2027 |
| T2, U1, U3 | 5 | [ ] | |

Công cụ tham khảo, không phải lời khuyên đầu tư.
