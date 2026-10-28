# Kết quả nâng cấp "Best ROI for Invest" (giai đoạn 7)

Lần chạy duy nhất trên giai đoạn kiểm tra cuối (từ 01/01/2023), lúc 09:19 28/10/2026, ghi trong `experiments/final_runs.log`. Dữ liệu từ 04/01/2011 đến 27/10/2026. Không có gì được chỉnh sau khi xem kết quả này. Tổng số lần thử trong sổ (`experiments/registry.csv`): **135**.

Mô hình được chấm: lớp A, trung bình "độ rẻ" của Pi Cycle, Giá/MA 200 tuần, Hash Ribbon; bảng hệ số ≥ 0,8 → 2,0; 0,6–0,8 → 1,25; 0,2–0,6 → 1,0; < 0,2 → 0,5. Lớp B và C không giữ quy tắc nào. Bên bán chỉ là lời khuyên dạng chữ. Mốc so sánh: bot hiện tại (chế độ Tự động) dựng lại thành hệ số Phải mua 2,0, Cân nhắc mua 1,25, Không nên mua 0,25.

## Kết luận: mô hình mới KHÔNG ĐẠT tiêu chí chấp nhận

| # | Tiêu chí | Kết quả | Số liệu |
|---|---|---|---|
| 1 | Trung vị tỷ số tài sản (khung 2 năm) > 1,00 ở kiểm định và kiểm tra cuối, kịch bản xấu P10 ≥ 0,97 | **không đạt** | kiểm định 1,000 / 1,000; kiểm tra cuối 1,000 / 1,000 |
| 2 | Tỷ số tài sản > 1,00 ở ít nhất 3/4 chu kỳ halving trọn vẹn | **không đạt** | 1/4: 01/2011–11/2012 1,000, 11/2012–07/2016 1,000, 07/2016–05/2020 1,015, 05/2020–04/2024 1,000 |
| 3 | Sụt giảm lớn nhất không tệ hơn mua đều quá 5 điểm % | đạt | chênh lớn nhất 0,0 điểm % |
| 4 | Hơn ít nhất 95% số lần chạy với tín hiệu ngẫu nhiên | **không đạt** | kiểm định 50%, kiểm tra cuối 50% |
| 5 | Tiền mặt chờ trung bình ≤ 25% số tiền đã nạp | đạt | lớn nhất 0,3% |
| 6 | Mọi quy tắc đang dùng có ≥ 10 đợt độc lập | **không đạt** | hệ số 0,50: 3 đợt, hệ số 1,25: 19 đợt, hệ số 2,00: 9 đợt |
| 7 | Tốt hơn bot hiện tại ở tiêu chí 1 và 2 | đạt | bot hiện tại: kiểm định 0,974 / 0,967, kiểm tra cuối 0,940 / 0,898, 0/4 chu kỳ |
| 8 | Mọi bài kiểm tra đạt và phần khác biệt của báo cáo đã được duyệt | chờ duyệt | chờ bạn duyệt ở giai đoạn 9 |

## So sánh với mua đều (cùng tiền nạp mỗi tuần)

| Chiến lược | Giai đoạn | Tỷ số tài sản | Trung vị khung 2 năm | Kịch bản xấu (P10) | Lợi thế giá vốn | Tiền mặt chờ | Sụt giảm lớn nhất (chiến lược / mua đều) |
|---|---|---|---|---|---|---|---|
| Mô hình mới | Huấn luyện | 1,000 | 1,000 | 1,000 | 0,0% | 0,3% | -90% / -90% |
| Mô hình mới | Kiểm định | 1,000 | 1,000 | 1,000 | 0,0% | 0,0% | -76% / -76% |
| Mô hình mới | Kiểm tra cuối | 1,000 | 1,000 | 1,000 | 0,0% | 0,0% | -52% / -52% |
| Bot hiện tại | Huấn luyện | 1,000 | 1,000 | 1,000 | 0,0% | 0,0% | -90% / -90% |
| Bot hiện tại | Kiểm định | 0,988 | 0,974 | 0,967 | -1,6% | 5,3% | -76% / -76% |
| Bot hiện tại | Kiểm tra cuối | 0,967 | 0,940 | 0,898 | -3,1% | 8,1% | -50% / -52% |

| Chiến lược | 01/2011–11/2012 | 11/2012–07/2016 | 07/2016–05/2020 | 05/2020–04/2024 | 04/2024–10/2026 |
|---|---|---|---|---|---|
| Mô hình mới | 1,000 | 1,000 | 1,015 | 1,000 | 1,000 (đang chạy) |
| Bot hiện tại | 1,000 | 1,000 | 1,000 | 0,971 | 0,979 (đang chạy) |

## Độ bất định

| Chiến lược | Khoảng tin cậy 95% tỷ số tài sản (kiểm định / kiểm tra cuối) | Khoảng tin cậy 95% lợi thế giá vốn (kiểm định / kiểm tra cuối) | Hơn tín hiệu ngẫu nhiên (kiểm định / kiểm tra cuối) | Deflated Sharpe |
|---|---|---|---|---|
| Mô hình mới | 1,000–1,000 / 1,000–1,000 | 0,0% đến 0,0% / 0,0% đến 0,0% | 50% / 50% | không tính được (không khác mua đều) |
| Bot hiện tại | 0,819–1,051 / 0,859–1,045 | -15,4% đến 4,8% / -11,8% đến 5,4% | 62% / 87% | 0,000 |

## Vì sao không đạt

1. **Chỉ số chu kỳ không cho lợi thế vững so với mua đều** khi đo bằng tài sản cuối kỳ thay vì tỷ lệ thắng. Muốn mua gấp đôi lúc rẻ thì phải để dành tiền từ trước. Để dành trong lúc giá đang lên lại làm mất phần tăng. Trên giai đoạn huấn luyện, mọi bộ chỉ số với bảng hệ số mặc định đều kém mua đều. Bảng trung tính hơn chỉ đưa kết quả về sát mua đều.
2. **Quan hệ giữa "rẻ" và lợi suất sau đó không ổn định.** Trong hồi quy đi tới, hệ số của mọi chỉ số định giá đổi dấu giữa các lần học. Chu kỳ 2013 và 2017 tăng rất mạnh ngay khi chỉ số đã báo "đắt".
3. **Quá ít đợt độc lập.** Khung mua gấp đôi chỉ có 9 đợt, khung bán bớt 3 đợt từ 2011. Tiêu chí bán duy nhất đủ 10 đợt (RSI tuần ≥ 80) sai cả 11 lần.
4. **Lớp ngắn hạn và vĩ mô** (funding, basis, stablecoin, RSI, hoãn mua sát sự kiện, trần vĩ mô) không cải thiện kịch bản xấu, và chỉ có dữ liệu từ 2018–2020.

Điều đáng chú ý: **bot hiện tại cũng thua mua đều** ở cả kiểm định (0,988) và kiểm tra cuối (trung vị 0,940, kịch bản xấu 0,898). Lợi thế của nó không phân biệt được với may rủi (hơn 62% và 87% số lần chạy ngẫu nhiên). Mô hình mới "tốt hơn" bot hiện tại chỉ vì nó gần như mua đều.

## Quyết định (theo mục 5 và điểm dừng 2 của mục 11)

- **Không giao mô hình mới.** Logic bot hiện tại giữ nguyên trên trang web (tỷ lệ nên mua/bán, phương án, bên bán).
- Chỉ giao phần an toàn: chữ hiển thị tập trung ở `bot/i18n/vi.yaml`, định dạng số và ngày kiểu Việt Nam, chế độ an toàn, triển khai tự động.
- Phần mới "Khuyến nghị giải ngân tuần này" luôn cho **hệ số 1,0 (Chế độ an toàn: mua đều)**. Phần này nói rõ lý do và hiện bảng so sánh ở trên, để người dùng biết các khung của bot hiện tại chưa được chứng minh tốt hơn mua đều.
- Thất bại này là kết quả chấp nhận được. Một bản nâng cấp gây hiểu lầm thì không.
