# Phần G: vĩ mô và sự kiện

Đăng ký trước: `config/candidates.yaml` mục `macro` (commit `1548ac2`). Kết quả tính đến **31/12/2023** (holdout khóa).

- Chế độ Fed: trần lãi suất Fed (FRED DFEDTARU) thay đổi trong 26 tuần trước: > +0,1 điểm % = tăng, < −0,1 = giảm, còn lại = giữ; chỉ dùng số liệu đến Chủ nhật đó; chỉ để chia nhóm khi báo cáo, không đưa vào mô hình.
- Mốc so sánh: mọi tuần cùng chế độ, cùng chiến lược, cùng giai đoạn (đến 31/12/2023). Đếm đợt và bootstrap như mọi bảng khác; dưới 3 đợt thì "ít đợt", không kết luận.

## 1. Chế độ Fed hiện tại

- Số liệu Fed mới nhất: trần lãi suất 4,00% (ngày 25/10/2026). Chế độ tại Chủ nhật 25/10/2026: **tăng** (từ 20/09/2026).
- Số đợt mỗi chế độ từ 2011 đến nay (chỉ dùng chuỗi lãi suất): tăng 4, giữ 7, giảm 3.
- Tại 31/12/2023 (cuối giai đoạn đánh giá): tăng.

- Bot hiện tại (PA3): chế độ tăng có **1 đợt** trong giai đoạn đánh giá (02/08/2020 → 31/12/2023).
- Mô hình lồng nhau: chế độ tăng có **1 đợt** trong giai đoạn đánh giá (13/02/2022 → 31/12/2023).
- Quy tắc MVRV: chế độ tăng có **3 đợt** trong giai đoạn đánh giá (07/07/2013 → 31/12/2023).
- Quy tắc Giá/MA 200 tuần: chế độ tăng có **2 đợt** trong giai đoạn đánh giá (07/05/2017 → 31/12/2023).

> **Cảnh báo:** chế độ hiện tại (tăng) có dưới 3 đợt trong lịch sử đánh giá của Bot hiện tại (PA3), Mô hình lồng nhau, Quy tắc Giá/MA 200 tuần. Kết quả của các chiến lược này trong chế độ hiện tại không đủ để tin.

## 2. Kết quả các khung theo chế độ Fed (giá cao hơn sau 26 tuần)

Mỗi ô so khung với mọi tuần **cùng chế độ** của cùng chiến lược. Chênh = tỷ lệ của khung trừ mốc, khoảng tin cậy 95% bằng bootstrap khối.

### Bot hiện tại (PA3)

| Chế độ | Tuần (đợt chế độ) | Mốc cùng chế độ | Khung | Số tuần | Số đợt | Tỷ lệ của khung | Chênh (KTC 95%) | Kết luận |
|---|---|---|---|---|---|---|---|---|
| tăng | 94 (1) | 62% | Phải mua | 57 | 1 | 74% | +11,9% (0,0% đến +23,9%) | ít đợt (< 3) |
| tăng | 94 (1) | 62% | Cân nhắc mua | 2 | 1 | 0% | -61,8% (-76,5% đến -33,8%) | ít đợt (< 3) |
| tăng | 94 (1) | 62% | Không nên mua | 9 | 1 | 0% | -61,8% (-82,4% đến -35,3%) | ít đợt (< 3) |
| giữ | 78 (1) | 45% | Phải mua | 0 | 0 | — | — | không có tuần |
| giữ | 78 (1) | 45% | Cân nhắc mua | 0 | 0 | — | — | không có tuần |
| giữ | 78 (1) | 45% | Không nên mua | 78 | 1 | 45% | 0,0% (0,0% đến 0,0%) | ít đợt (< 3) |
| giảm | 7 (1) | 100% | Phải mua | 0 | 0 | — | — | không có tuần |
| giảm | 7 (1) | 100% | Cân nhắc mua | 0 | 0 | — | — | không có tuần |
| giảm | 7 (1) | 100% | Không nên mua | 7 | 1 | 100% | 0,0% (0,0% đến 0,0%) | ít đợt (< 3) |

### Mô hình lồng nhau

| Chế độ | Tuần (đợt chế độ) | Mốc cùng chế độ | Khung | Số tuần | Số đợt | Tỷ lệ của khung | Chênh (KTC 95%) | Kết luận |
|---|---|---|---|---|---|---|---|---|
| tăng | 54 (1) | 29% | Phải mua | 21 | 1 | 5% | -23,8% (-46,4% đến 0,0%) | ít đợt (< 3) |
| tăng | 54 (1) | 29% | Cân nhắc mua | 0 | 0 | — | — | không có tuần |
| tăng | 54 (1) | 29% | Không nên mua | 7 | 1 | 100% | +71,4% (+46,4% đến +92,9%) | ít đợt (< 3) |
| giữ | 5 (1) | 0% | Phải mua | 5 | 1 | 0% | 0,0% (0,0% đến 0,0%) | ít đợt (< 3) |
| giữ | 5 (1) | 0% | Cân nhắc mua | 0 | 0 | — | — | không có tuần |
| giữ | 5 (1) | 0% | Không nên mua | 0 | 0 | — | — | không có tuần |
| giảm | 0 | — | — | — | — | — | — | không có tuần nào |

### Quy tắc MVRV

| Chế độ | Tuần (đợt chế độ) | Mốc cùng chế độ | Khung | Số tuần | Số đợt | Tỷ lệ của khung | Chênh (KTC 95%) | Kết luận |
|---|---|---|---|---|---|---|---|---|
| tăng | 250 (3) | 65% | Phải mua | 68 | 2 | 81% | +16,2% (-14,2% đến +46,0%) | ít đợt (< 3) |
| tăng | 250 (3) | 65% | Cân nhắc mua | 46 | 5 | 26% | -38,6% (-64,5% đến -14,1%) | **kém mốc** |
| tăng | 250 (3) | 65% | Không nên mua | 110 | 5 | 71% | +6,2% (-20,3% đến +18,6%) | chưa có lợi thế |
| giữ | 238 (4) | 51% | Phải mua | 81 | 3 | 36% | -15,5% (-40,2% đến +25,3%) | chưa có lợi thế |
| giữ | 238 (4) | 51% | Cân nhắc mua | 19 | 5 | 58% | +6,6% (-35,8% đến +39,5%) | chưa có lợi thế |
| giữ | 238 (4) | 51% | Không nên mua | 138 | 5 | 59% | +8,2% (-7,0% đến +26,8%) | chưa có lợi thế |
| giảm | 59 (1) | 75% | Phải mua | 13 | 2 | 100% | +25,4% (0,0% đến +50,8%) | ít đợt (< 3) |
| giảm | 59 (1) | 75% | Cân nhắc mua | 18 | 5 | 78% | +3,2% (-9,3% đến +15,8%) | chưa có lợi thế |
| giảm | 59 (1) | 75% | Không nên mua | 28 | 5 | 61% | -13,9% (-29,4% đến 0,0%) | chưa có lợi thế |

### Quy tắc Giá/MA 200 tuần

| Chế độ | Tuần (đợt chế độ) | Mốc cùng chế độ | Khung | Số tuần | Số đợt | Tỷ lệ của khung | Chênh (KTC 95%) | Kết luận |
|---|---|---|---|---|---|---|---|---|
| tăng | 204 (2) | 56% | Phải mua | 101 | 2 | 58% | +2,8% (-18,8% đến +16,1%) | ít đợt (< 3) |
| tăng | 204 (2) | 56% | Cân nhắc mua | 32 | 5 | 31% | -24,4% (-57,3% đến +0,9%) | chưa có lợi thế |
| tăng | 204 (2) | 56% | Không nên mua | 45 | 1 | 67% | +11,0% (-36,8% đến +45,5%) | ít đợt (< 3) |
| giữ | 84 (2) | 42% | Phải mua | 1 | 1 | 0% | -41,7% (-65,5% đến -17,9%) | ít đợt (< 3) |
| giữ | 84 (2) | 42% | Cân nhắc mua | 30 | 4 | 43% | +1,7% (-14,3% đến +33,8%) | chưa có lợi thế |
| giữ | 84 (2) | 42% | Không nên mua | 53 | 3 | 42% | -0,2% (-10,5% đến +12,0%) | chưa có lợi thế |
| giảm | 59 (1) | 75% | Phải mua | 49 | 1 | 76% | +0,9% (-7,3% đến +5,1%) | ít đợt (< 3) |
| giảm | 59 (1) | 75% | Cân nhắc mua | 10 | 2 | 70% | -4,6% (-62,7% đến +22,0%) | ít đợt (< 3) |
| giảm | 59 (1) | 75% | Không nên mua | 0 | 0 | — | — | không có tuần |

Tổng cộng 25 ô có tuần ở kỳ 26 tuần: ít đợt (< 3) 15, **kém mốc** 1, chưa có lợi thế 9. Cả phụ lục có 4 chiến lược × 3 chế độ × 3 khung × 4 kỳ hạn; với chừng ấy phép so, vài ô "hơn mốc" hoặc "kém mốc" đứng riêng lẻ có thể chỉ do may rủi.

## 3. Sự kiện sau mốc chốt dữ liệu

- Mốc chốt dữ liệu: giá đóng Chủ nhật 25/10/2026 (23:59:59 UTC). Lúc tạo báo cáo: 29/10/2026 03:36 UTC. Chỉ liệt kê sự kiện sau mốc chốt, tới 05/11/2026 03:36 UTC; sự kiện trước mốc chốt không bao giờ được liệt kê.

**Đã xảy ra sau mốc chốt, trước lúc phát hành (gắn cờ):**

- ⚑ 29/10/2026 01:00 giờ Việt Nam: Quyết định lãi suất FOMC

> Tín hiệu tuần này **chưa tính** phản ứng của thị trường với các sự kiện trên. Nên chạy lại bot sau giá đóng tuần kế tiếp (Chủ nhật 01/11/2026).

**Sắp tới:**

- 29/10/2026 19:30 giờ Việt Nam: Chỉ số giá chi tiêu PCE
- 30/10/2026 15:00 giờ Việt Nam: Đáo hạn quyền chọn BTC hằng tháng
- 04/11/2026 20:30 giờ Việt Nam: Chỉ số giá chi tiêu PCE

> **Lịch chưa đủ:** Chỉ số giá tiêu dùng Mỹ (CPI) chỉ có tới 14/10/2026. Cần chạy `python tools/update_events.py` rồi duyệt khác biệt; trước đó, "không có sự kiện" của các loại này không đáng tin.

## 4. Kết luận Phần G

- Theo chế độ Fed, ở kỳ 26 tuần có 0 ô "hơn mốc" trên 25 ô. Không ô nào đủ để nói khung có lợi thế trong một chế độ riêng.
- Chế độ Fed chỉ dùng để chia nhóm báo cáo, không đưa vào mô hình hay hệ số giải ngân.
- Sự kiện: giờ chỉ liệt kê sau mốc chốt dữ liệu; sự kiện rơi vào khoảng giữa mốc chốt và lúc phát hành được gắn cờ kèm đề nghị chạy lại.
