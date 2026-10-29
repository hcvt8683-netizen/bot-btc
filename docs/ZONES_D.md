# Phần D: khung mua và hệ số giải ngân

Dữ liệu đến **31/12/2023** (holdout khóa). Tham số đăng ký trước trong `config/candidates.yaml` (commit `c7eeb48`).

- **Tỷ lệ nên mua là THỨ HẠNG của điểm tuần này trong các điểm ngoài mẫu trước đó, không phải xác suất có lãi.**
- Khung: Phải mua từ 80, Cân nhắc mua từ 60 (thang thứ hạng 0–100). **Vùng trễ 5 điểm**: vào khung khi vượt ngưỡng, chỉ ra khi lùi quá ngưỡng 5 điểm. Tính trên giá đóng tuần.
- Hệ số trong khoảng 0,5–1,5: lệch khỏi 1,0 theo **cận** khoảng tin cậy của lợi thế khung (tỷ lệ thắng 26 tuần trừ mốc cùng giai đoạn): m = 1 + 2,0 × cận dưới (khung mua) hoặc cận trên (Không nên mua). Cận chứa 0, hoặc dưới 3 đợt → 1,0. Lợi thế ước lượng lại mỗi 13 tuần, chỉ bằng các tuần đã biết kết quả.
- **Cổng Phần I**: chỉ dùng hệ số khác 1,0 khi đạt tất cả tiêu chí Phần I; chưa đạt → 1,0 kèm lý do.

## Mô hình lồng nhau

Từ 13/02/2022, 59 tuần có thứ hạng ngoài mẫu. Số lần đổi khung: **không vùng trễ 3 lần, có vùng trễ 1 lần**.

| Kỳ hạn | Mốc (thắng) | Phải mua | Cân nhắc mua | Không nên mua | Đơn điệu? |
|---|---|---|---|---|---|
| 1 tháng | 47% | 35% (-13%; -37% đến +6%; 26 tuần, 1 đợt) ít đợt | không có | 59% (+11%; -7% đến +34%; 29 tuần, 1 đợt) ít đợt | không |
| 3 tháng | 26% | 4% (-22%; -50% đến +1%; 26 tuần, 1 đợt) ít đợt | không có | 55% (+29%; -4% đến +78%; 20 tuần, 1 đợt) ít đợt | không |
| 6 tháng | 24% | 4% (-20%; -40% đến 0%; 26 tuần, 1 đợt) ít đợt | không có | 100% (+76%; +55% đến +94%; 7 tuần, 1 đợt) ít đợt | không |
| 1 năm | 57% | 57% (0%; 0% đến 0%; 7 tuần, 1 đợt) ít đợt | không có | không có | có |

- Hệ số theo quy tắc (chưa qua cổng): khác 1,0 ở **0%** số tuần, trung bình 1,000; các giá trị: 1,00 (59 tuần).
- Nếu dùng hệ số đó (chưa qua cổng): lợi thế giá vốn 0,0% (khoảng tin cậy 0,0% đến 0,0%).
- Tuần cuối trước holdout (24/12/2023): thứ hạng 4, khung Không nên mua, hệ số theo quy tắc 1,00, **hệ số dùng 1,0** (chưa chạy kiểm định Phần I).

## Quy tắc MVRV

Từ 07/07/2013, 547 tuần có thứ hạng ngoài mẫu. Số lần đổi khung: **không vùng trễ 51 lần, có vùng trễ 41 lần**.

| Kỳ hạn | Mốc (thắng) | Phải mua | Cân nhắc mua | Không nên mua | Đơn điệu? |
|---|---|---|---|---|---|
| 1 tháng | 58% | 56% (-2%; -12% đến +9%; 162 tuần, 7 đợt) chưa có lợi thế | 53% (-5%; -18% đến +9%; 100 tuần, 15 đợt) chưa có lợi thế | 60% (+3%; -4% đến +9%; 281 tuần, 10 đợt) chưa có lợi thế | không |
| 3 tháng | 57% | 53% (-4%; -20% đến +14%; 162 tuần, 7 đợt) chưa có lợi thế | 46% (-11%; -29% đến +6%; 96 tuần, 15 đợt) chưa có lợi thế | 63% (+6%; -4% đến +16%; 276 tuần, 9 đợt) chưa có lợi thế | không |
| 6 tháng | 60% | 60% (0%; -23% đến +28%; 162 tuần, 7 đợt) chưa có lợi thế | 45% (-15%; -37% đến +10%; 83 tuần, 15 đợt) chưa có lợi thế | 64% (+4%; -9% đến +16%; 276 tuần, 9 đợt) chưa có lợi thế | không |
| 1 năm | 68% | 72% (+4%; -17% đến +30%; 151 tuần, 7 đợt) chưa có lợi thế | 79% (+11%; -16% đến +26%; 68 tuần, 14 đợt) chưa có lợi thế | 63% (-5%; -20% đến +8%; 276 tuần, 9 đợt) chưa có lợi thế | không |

- Hệ số theo quy tắc (chưa qua cổng): khác 1,0 ở **0%** số tuần, trung bình 1,000; các giá trị: 1,00 (547 tuần).
- Nếu dùng hệ số đó (chưa qua cổng): lợi thế giá vốn 0,0% (khoảng tin cậy 0,0% đến 0,0%).
- Tuần cuối trước holdout (24/12/2023): thứ hạng 19, khung Không nên mua, hệ số theo quy tắc 1,00, **hệ số dùng 1,0** (chưa chạy kiểm định Phần I).

## Quy tắc Giá/MA 200 tuần

Từ 07/05/2017, 347 tuần có thứ hạng ngoài mẫu. Số lần đổi khung: **không vùng trễ 30 lần, có vùng trễ 24 lần**.

| Kỳ hạn | Mốc (thắng) | Phải mua | Cân nhắc mua | Không nên mua | Đơn điệu? |
|---|---|---|---|---|---|
| 1 tháng | 56% | 57% (+1%; -8% đến +10%; 157 tuần, 4 đợt) chưa có lợi thế | 53% (-3%; -17% đến +11%; 88 tuần, 8 đợt) chưa có lợi thế | 57% (+1%; -13% đến +14%; 98 tuần, 4 đợt) chưa có lợi thế | không |
| 3 tháng | 54% | 55% (+1%; -12% đến +14%; 157 tuần, 4 đợt) chưa có lợi thế | 49% (-5%; -24% đến +13%; 79 tuần, 7 đợt) chưa có lợi thế | 57% (+3%; -16% đến +23%; 98 tuần, 4 đợt) chưa có lợi thế | không |
| 6 tháng | 55% | 64% (+8%; -7% đến +22%; 151 tuần, 3 đợt) chưa có lợi thế | 42% (-14%; -40% đến +9%; 72 tuần, 7 đợt) chưa có lợi thế | 53% (-2%; -26% đến +16%; 98 tuần, 4 đợt) chưa có lợi thế | không |
| 1 năm | 64% | 95% (+31%; +12% đến +48%; 138 tuần, 3 đợt) hơn mốc | 37% (-27%; -57% đến +1%; 59 tuần, 6 đợt) chưa có lợi thế | 38% (-27%; -56% đến -6%; 98 tuần, 4 đợt) kém mốc | không |

- Hệ số theo quy tắc (chưa qua cổng): khác 1,0 ở **0%** số tuần, trung bình 1,000; các giá trị: 1,00 (347 tuần).
- Nếu dùng hệ số đó (chưa qua cổng): lợi thế giá vốn 0,0% (khoảng tin cậy 0,0% đến 0,0%).
- Tuần cuối trước holdout (24/12/2023): thứ hạng 55, khung Không nên mua, hệ số theo quy tắc 1,00, **hệ số dùng 1,0** (chưa chạy kiểm định Phần I).

## Kết luận Phần D

- Vùng trễ làm khung bớt nhảy qua lại (xem số lần đổi khung ở trên), sửa lỗi nhãn đổi liên tục khi giá sát ngưỡng.
- Hệ số tính theo cận khoảng tin cậy nên tự co về 1,0 khi chưa chắc chắn. Với dữ liệu đến 2023, phần lớn các tuần hệ số theo quy tắc là 1,0.
- Cổng Phần I chưa mở, nên **hệ số dùng thực tế là 1,0 (mua đều)**. Phần I sẽ chấm đủ 6 tiêu chí một lần.
