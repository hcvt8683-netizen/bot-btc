# Tra cứu tại ngày t và Tình huống tương tự

Sinh tự động bằng `python -m bot.cli lookup` lúc 17:03 06/11/2026 UTC, giá đóng Coin Metrics đến 05/11/2026. Cách làm đăng ký trước trong `config/candidates.yaml` mục `lookup` và `analog` (06/11/2026), lưu git trước khi tính. Trong ngoặc là khoảng tin cậy Wilson 95% theo số lần độc lập.

## 1. Tình huống tương tự: sau đó giá lên nhiều hơn các ngày còn lại không

Mỗi ngày T từ 01/01/2014, xếp nhóm theo 5 đặc trưng (chỉ dùng giá đến T), đếm số lần giá sau h ngày cao hơn. So với các ngày còn lại, kiểm định hai tỷ lệ, Holm trên 72 phép thử, phải cùng dấu ở hai nửa giai đoạn.

Kết quả: 0 điều kiện sau đó lên nhiều hơn, 0 lên ít hơn, 32 như ngày bất kỳ, 40 ít dữ liệu.

| Đặc trưng | Nhóm | Kỳ hạn | Số ngày | Sau đó lên | Các ngày còn lại | Chênh | p Holm | Kết luận |
|---|---|---|---|---|---|---|---|---|
| Lợi suất 7 ngày | giảm mạnh (≤ −10%) | 7 ngày | 410 | 54% (42%–66%) | 53% | +1 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 7 ngày | giảm (−10% … −3%) | 7 ngày | 906 | 52% (43%–60%) | 53% | -1 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 7 ngày | đi ngang (−3% … +3%) | 7 ngày | 1731 | 53% (47%–59%) | 53% | +0 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 7 ngày | tăng (+3% … +10%) | 7 ngày | 991 | 48% (41%–57%) | 54% | -6 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 7 ngày | tăng mạnh (≥ +10%) | 7 ngày | 647 | 60% (50%–69%) | 52% | +8 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 30 ngày | giảm mạnh (≤ −20%) | 7 ngày | 414 | 56% (43%–68%) | 53% | +3 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 30 ngày | giảm (−20% … −7%) | 7 ngày | 885 | 44% (35%–52%) | 55% | -11 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 30 ngày | đi ngang (−7% … +7%) | 7 ngày | 1590 | 52% (46%–58%) | 53% | -1 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 30 ngày | tăng (+7% … +20%) | 7 ngày | 833 | 55% (46%–63%) | 53% | +2 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 30 ngày | tăng mạnh (≥ +20%) | 7 ngày | 963 | 60% (52%–68%) | 51% | +9 điểm | 1,000 | như ngày bất kỳ |
| MA 200 ngày | trên MA 200 ngày | 7 ngày | 2712 | 54% (49%–59%) | 51% | +3 điểm | 1,000 | như ngày bất kỳ |
| MA 200 ngày | dưới MA 200 ngày | 7 ngày | 1973 | 51% (46%–57%) | 54% | -3 điểm | 1,000 | như ngày bất kỳ |
| Giảm từ đỉnh | cách đỉnh < 20% | 7 ngày | 1118 | 55% (48%–63%) | 52% | +3 điểm | 1,000 | như ngày bất kỳ |
| Giảm từ đỉnh | cách đỉnh 20–50% | 7 ngày | 1491 | 50% (44%–57%) | 54% | -4 điểm | 1,000 | như ngày bất kỳ |
| Giảm từ đỉnh | cách đỉnh ≥ 50% | 7 ngày | 2076 | 54% (48%–59%) | 52% | +1 điểm | 1,000 | như ngày bất kỳ |
| Độ dao động 30 ngày | dao động thấp (1/3 dưới) | 7 ngày | 1988 | 53% (47%–59%) | 53% | +0 điểm | 1,000 | như ngày bất kỳ |
| Độ dao động 30 ngày | dao động vừa | 7 ngày | 1699 | 51% (45%–57%) | 54% | -3 điểm | 1,000 | như ngày bất kỳ |
| Độ dao động 30 ngày | dao động cao (1/3 trên) | 7 ngày | 998 | 56% (48%–64%) | 52% | +4 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 7 ngày | giảm mạnh (≤ −10%) | 30 ngày | 410 | 51% (27%–73%) | 56% | -5 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | giảm (−10% … −3%) | 30 ngày | 901 | 52% (36%–70%) | 56% | -4 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 7 ngày | đi ngang (−3% … +3%) | 30 ngày | 1714 | 56% (43%–68%) | 55% | +1 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 7 ngày | tăng (+3% … +10%) | 30 ngày | 990 | 54% (38%–70%) | 55% | -1 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 7 ngày | tăng mạnh (≥ +10%) | 30 ngày | 647 | 62% (43%–80%) | 54% | +8 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | giảm mạnh (≤ −20%) | 30 ngày | 414 | 54% (33%–79%) | 55% | -1 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | giảm (−20% … −7%) | 30 ngày | 885 | 53% (36%–70%) | 56% | -2 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 30 ngày | đi ngang (−7% … +7%) | 30 ngày | 1572 | 55% (42%–68%) | 55% | +0 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 30 ngày | tăng (+7% … +20%) | 30 ngày | 828 | 51% (33%–67%) | 56% | -4 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | tăng mạnh (≥ +20%) | 30 ngày | 963 | 60% (42%–74%) | 54% | +6 điểm | 1,000 | như ngày bất kỳ |
| MA 200 ngày | trên MA 200 ngày | 30 ngày | 2689 | 56% (45%–65%) | 54% | +2 điểm | 1,000 | như ngày bất kỳ |
| MA 200 ngày | dưới MA 200 ngày | 30 ngày | 1973 | 54% (43%–66%) | 56% | -2 điểm | 1,000 | như ngày bất kỳ |
| Giảm từ đỉnh | cách đỉnh < 20% | 30 ngày | 1118 | 57% (41%–71%) | 55% | +2 điểm | 1,000 | như ngày bất kỳ |
| Giảm từ đỉnh | cách đỉnh 20–50% | 30 ngày | 1468 | 52% (39%–66%) | 56% | -4 điểm | 1,000 | như ngày bất kỳ |
| Giảm từ đỉnh | cách đỉnh ≥ 50% | 30 ngày | 2076 | 56% (45%–68%) | 54% | +2 điểm | 1,000 | như ngày bất kỳ |
| Độ dao động 30 ngày | dao động thấp (1/3 dưới) | 30 ngày | 1973 | 54% (41%–65%) | 56% | -3 điểm | 1,000 | như ngày bất kỳ |
| Độ dao động 30 ngày | dao động vừa | 30 ngày | 1691 | 53% (41%–66%) | 56% | -3 điểm | 1,000 | như ngày bất kỳ |
| Độ dao động 30 ngày | dao động cao (1/3 trên) | 30 ngày | 998 | 62% (44%–75%) | 53% | +9 điểm | 1,000 | như ngày bất kỳ |
| Lợi suất 7 ngày | giảm mạnh (≤ −10%) | 90 ngày | 410 | 52% (23%–88%) | 57% | -6 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | giảm (−10% … −3%) | 90 ngày | 894 | 54% (24%–76%) | 58% | -4 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | đi ngang (−3% … +3%) | 90 ngày | 1682 | 58% (36%–77%) | 56% | +2 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | tăng (+3% … +10%) | 90 ngày | 980 | 58% (28%–79%) | 57% | +1 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | tăng mạnh (≥ +10%) | 90 ngày | 636 | 60% (25%–84%) | 56% | +4 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | giảm mạnh (≤ −20%) | 90 ngày | 414 | 53% (23%–88%) | 57% | -5 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | giảm (−20% … −7%) | 90 ngày | 885 | 56% (31%–83%) | 57% | -1 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | đi ngang (−7% … +7%) | 90 ngày | 1553 | 54% (31%–74%) | 58% | -4 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | tăng (+7% … +20%) | 90 ngày | 811 | 55% (27%–81%) | 57% | -3 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | tăng mạnh (≥ +20%) | 90 ngày | 939 | 66% (40%–89%) | 55% | +12 điểm | 1,000 | ít dữ liệu |
| MA 200 ngày | trên MA 200 ngày | 90 ngày | 2640 | 64% (44%–77%) | 48% | +16 điểm | 1,000 | ít dữ liệu |
| MA 200 ngày | dưới MA 200 ngày | 90 ngày | 1962 | 48% (27%–65%) | 64% | -16 điểm | 1,000 | ít dữ liệu |
| Giảm từ đỉnh | cách đỉnh < 20% | 90 ngày | 1118 | 59% (32%–81%) | 56% | +3 điểm | 1,000 | ít dữ liệu |
| Giảm từ đỉnh | cách đỉnh 20–50% | 90 ngày | 1408 | 54% (33%–77%) | 58% | -4 điểm | 1,000 | ít dữ liệu |
| Giảm từ đỉnh | cách đỉnh ≥ 50% | 90 ngày | 2076 | 58% (37%–74%) | 56% | +1 điểm | 1,000 | ít dữ liệu |
| Độ dao động 30 ngày | dao động thấp (1/3 dưới) | 90 ngày | 1955 | 60% (39%–77%) | 54% | +6 điểm | 1,000 | ít dữ liệu |
| Độ dao động 30 ngày | dao động vừa | 90 ngày | 1657 | 51% (29%–71%) | 60% | -9 điểm | 1,000 | ít dữ liệu |
| Độ dao động 30 ngày | dao động cao (1/3 trên) | 90 ngày | 990 | 59% (35%–85%) | 56% | +3 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | giảm mạnh (≤ −10%) | 365 ngày | 388 | 52% (21%–100%) | 69% | -17 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | giảm (−10% … −3%) | 365 ngày | 828 | 62% (9%–91%) | 68% | -7 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | đi ngang (−3% … +3%) | 365 ngày | 1559 | 71% (30%–95%) | 65% | +6 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | tăng (+3% … +10%) | 365 ngày | 916 | 73% (21%–94%) | 66% | +7 điểm | 1,000 | ít dữ liệu |
| Lợi suất 7 ngày | tăng mạnh (≥ +10%) | 365 ngày | 636 | 65% (9%–91%) | 67% | -2 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | giảm mạnh (≤ −20%) | 365 ngày | 368 | 49% (0%–79%) | 69% | -19 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | giảm (−20% … −7%) | 365 ngày | 826 | 63% (9%–91%) | 68% | -6 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | đi ngang (−7% … +7%) | 365 ngày | 1424 | 67% (30%–95%) | 67% | +0 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | tăng (+7% … +20%) | 365 ngày | 770 | 76% (34%–100%) | 65% | +11 điểm | 1,000 | ít dữ liệu |
| Lợi suất 30 ngày | tăng mạnh (≥ +20%) | 365 ngày | 939 | 70% (21%–94%) | 66% | +4 điểm | 1,000 | ít dữ liệu |
| MA 200 ngày | trên MA 200 ngày | 365 ngày | 2640 | 69% (36%–92%) | 65% | +4 điểm | 1,000 | ít dữ liệu |
| MA 200 ngày | dưới MA 200 ngày | 365 ngày | 1687 | 65% (23%–88%) | 69% | -4 điểm | 1,000 | ít dữ liệu |
| Giảm từ đỉnh | cách đỉnh < 20% | 365 ngày | 1110 | 53% (21%–94%) | 72% | -19 điểm | 1,000 | ít dữ liệu |
| Giảm từ đỉnh | cách đỉnh 20–50% | 365 ngày | 1156 | 49% (6%–79%) | 74% | -25 điểm | 1,000 | ít dữ liệu |
| Giảm từ đỉnh | cách đỉnh ≥ 50% | 365 ngày | 2061 | 85% (44%–97%) | 51% | +34 điểm | 1,000 | ít dữ liệu |
| Độ dao động 30 ngày | dao động thấp (1/3 dưới) | 365 ngày | 1824 | 74% (38%–96%) | 62% | +12 điểm | 1,000 | ít dữ liệu |
| Độ dao động 30 ngày | dao động vừa | 365 ngày | 1547 | 64% (30%–95%) | 69% | -5 điểm | 1,000 | ít dữ liệu |
| Độ dao động 30 ngày | dao động cao (1/3 trên) | 365 ngày | 956 | 59% (21%–94%) | 70% | -11 điểm | 1,000 | ít dữ liệu |

Dữ liệu giá từ 2014 đã được các kiểm định khác của dự án xem trước (xu hướng, price action), nên đây chưa phải kiểm định ngoài mẫu mới. Kiểm tra cuối: từ 06/11/2026, chạy một lần khi đủ 1 năm (từ 11/2027).

## 2. Kiểm chứng quá khứ của bảng tra cứu theo kỳ hạn

Mỗi h ngày một ngày gốc từ 01/01/2018, không chồng nhau, mỗi ngày gốc chỉ dùng dữ liệu đến ngày đó. Dải 8/10 lần đúng thì gần 80%, dải 5/10 lần gần 50%. Mua giữ: bot nói (tỷ lệ có lãi của 4 năm ngày mua trước đó) so với thực tế; sai số Brier càng thấp càng tốt, luôn nói 50% là 0,25.

| Kỳ hạn | Số ngày gốc | Trong dải 8/10 | Trong dải 5/10 | Mua giữ: bot nói | Thực tế có lãi | Brier | Brier nếu luôn nói 50% |
|---|---|---|---|---|---|---|---|
| 1 ngày | 3230 | 80% (79%–81%) | 49% (47%–50%) | 46% | 44% (43%–46%) | 0,247 | 0,250 |
| 7 ngày | 461 | 81% (77%–84%) | 49% (45%–54%) | 52% | 49% (44%–53%) | 0,252 | 0,250 |
| 30 ngày | 107 | 80% (72%–87%) | 50% (41%–60%) | 56% | 55% (46%–64%) | 0,252 | 0,250 |
| 90 ngày | 35 | 74% (58%–86%) | 46% (30%–62%) | 59% | 54% (38%–70%) | 0,258 | 0,250 |
| 180 ngày | 17 | 71% (47%–87%) | 41% (22%–64%) | 63% | 59% (36%–78%) | 0,254 | 0,250 |
| 365 ngày | 8 | 75% (41%–93%) | 50% (22%–78%) | 74% | 62% (31%–86%) | 0,257 | 0,250 |
| 730 ngày | 4 | 75% (30%–95%) | 25% (5%–70%) | 82% | 50% (15%–85%) | 0,425 | 0,250 |
| 1461 ngày | 2 | 0% (0%–66%) | 0% (0%–66%) | 100% | 100% (34%–100%) | 0,000 | 0,250 |

Kỳ hạn dài có ít ngày gốc không chồng nhau (ví dụ 4 năm chỉ vài lần), nên mọi con số ở đó rất không chắc.

## 3. Không phải lời khuyên

Không phần nào ở đây chọn được thời điểm mua: khuyến nghị tuần vẫn là mua đều. Bảng tra cứu cho biết lịch sử nói gì tại ngày t, để đặt kỳ vọng và cắt lỗ có kỷ luật.

Công cụ tham khảo, không phải lời khuyên đầu tư.
