# Phần I: DIỄN TẬP (holdout giả, dữ liệu đã xem)

Đăng ký trước: `config/candidates.yaml` mục `acceptance` (commit `60ddb0a`), trước khi đọc bất kỳ số nào của holdout. Holdout: 01/01/2022 → 24/12/2023 (104 tuần). Chạy lúc 2026-10-29T04:03:41Z.

## Kết luận: **KHÔNG ĐẠT** → giữ mua đều (hệ số 1,0)

| # | Tiêu chí | Kết quả | Đạt? |
|---|---|---|---|
| 1 | Lợi thế giá vốn > 0 ở ≥ 75% số năm trước holdout và trên holdout | năm có lợi: 0/0 (không có năm đủ tuần); holdout 0,0% | ✘ |
| 2 | Cận dưới khoảng tin cậy của lợi thế trên holdout > 0 | 0,0%, KTC 95% 0,0% đến 0,0% | ✘ |
| 3 | p hoán vị đã hiệu chỉnh < 0,05 (IC 26 tuần và lợi thế giá vốn) | IC: không tính được; lợi thế: không tính được; 59 tuần có mô hình (cần ≥ 114), 18 cấu hình | ✘ |
| 4 | Khung đơn điệu ở mọi kỳ hạn, trọng số đúng dấu | đơn điệu: 4 tuần không, 13 tuần không, 26 tuần không, 52 tuần không; trọng số ≥ 0 nhờ ràng buộc dấu; 112/112 tuần có mô hình đã phải bỏ chỉ số sai dấu (mvrv) | ✘ |
| 5 | Brier tốt hơn tỷ lệ gốc | Brier 0,416 so với 0,320 (58 tuần) | ✘ |
| 6 | Thắng cả hai quy tắc đơn giản 1 chỉ số | Lồng nhau: 0,0%; Quy tắc MVRV: 0,0%; Quy tắc Giá/MA 200 tuần: 0,0% | ✘ |

Mô hình lồng nhau: 372 tuần ngoài mẫu, 260 tuần không có mô hình (mua đều); trong holdout 39/104 tuần không có mô hình.

## Tham khảo (không quyết định): hệ số so sánh 0,5 + thứ hạng

Cùng tiêu chí 1, 2, 6 nhưng dùng hệ số so sánh của Phần C (tuần có thứ hạng luôn lệch khỏi 1,0), để biết riêng tín hiệu có giá trị không.

| Tiêu chí | Kết quả | Đạt? |
|---|---|---|
| 1 | năm có lợi 0/0; holdout -5,2% | ✘ |
| 2 | -5,2%, KTC 95% -7,7% đến +2,1% | ✘ |
| 6 | Lồng nhau: -5,2%; Quy tắc MVRV: 0,0%; Quy tắc Giá/MA 200 tuần: 0,0% | ✘ |

## Từng chiến lược trên holdout

| Chiến lược | Từ | Lợi thế giá vốn, hệ số Phần D (KTC 95%) | Tuần hệ số ≠ 1 | Lợi thế, hệ số so sánh (KTC 95%) | Đơn điệu cả giai đoạn | Đơn điệu riêng holdout |
|---|---|---|---|---|---|---|
| Lồng nhau | 13/02/2022 | 0,0% (0,0% đến 0,0%) | 0% | -5,2% (-7,7% đến +2,1%) | không | không |
| Quy tắc MVRV | 07/07/2013 | 0,0% (0,0% đến 0,0%) | 0% | 0,0% (-0,2% đến +1,1%) | không | không |
| Quy tắc Giá/MA 200 tuần | 07/05/2017 | 0,0% (0,0% đến 0,0%) | 0% | 0,0% (0,0% đến 0,0%) | không | không |

## Khung trên holdout (giá cao hơn sau 26 tuần, so với mọi tuần holdout)

| Chiến lược | Mốc | Khung | Số tuần | Số đợt | Tỷ lệ | Chênh (KTC 95%) | Kết luận |
|---|---|---|---|---|---|---|---|
| Lồng nhau | 50% | Phải mua | 26 | 1 | 4% | -46,2% (-78,8% đến -15,0%) | ít đợt (< 3) |
| Lồng nhau | 50% | Cân nhắc mua | 0 | 0 | — | — | không có tuần |
| Lồng nhau | 50% | Không nên mua | 26 | 1 | 96% | +46,2% (+15,0% đến +73,1%) | ít đợt (< 3) |
| Quy tắc MVRV | 53% | Phải mua | 44 | 1 | 70% | +17,9% (-4,3% đến +42,3%) | ít đợt (< 3) |
| Quy tắc MVRV | 53% | Cân nhắc mua | 25 | 3 | 40% | -12,6% (-63,3% đến +13,5%) | chưa có lợi thế |
| Quy tắc MVRV | 53% | Không nên mua | 9 | 2 | 0% | -52,6% (-78,2% đến -20,5%) | ít đợt (< 3) |
| Quy tắc Giá/MA 200 tuần | 53% | Phải mua | 47 | 1 | 66% | +13,4% (-7,1% đến +31,5%) | ít đợt (< 3) |
| Quy tắc Giá/MA 200 tuần | 53% | Cân nhắc mua | 31 | 2 | 32% | -20,3% (-61,9% đến +4,5%) | ít đợt (< 3) |
| Quy tắc Giá/MA 200 tuần | 53% | Không nên mua | 0 | 0 | — | — | không có tuần |

## Bên bán: chấm lại với chu kỳ có holdout

Chu kỳ: 2016-07 → 2020-05; 2020-05 → 2023-12. "Đáng tin" chỉ khi tiêu chí đúng nhiều hơn mốc ở CẢ hai chu kỳ gần nhất.

| Tiêu chí | Số đợt | Đúng / đã biết kết quả | Theo chu kỳ: đúng/đợt (mốc) | Đáng tin? |
|---|---|---|---|---|
| mvrv | 4 | 0/4 | 2016–2020: 0/3 (37%); 2020–2023: 0/1 (42%) | không |
| mvrv_z | 7 | 3/7 | 2016–2020: 0/3 (37%); 2020–2023: 1/2 (42%) | không |
| pi_ratio | 1 | 1/1 | 2016–2020: 1/1 (37%); 2020–2023: 0/0 (42%) | không |
| mayer | 4 | 2/4 | 2016–2020: 1/2 (37%); 2020–2023: 0/1 (42%) | không |
| p_200wma | 2 | 0/2 | 2016–2020: 0/2 (37%); 2020–2023: 0/0 (42%) | không |
| rsi_14w | 6 | 1/5 | 2016–2020: 1/3 (37%); 2020–2023: 0/1 (42%) | không |
| puell | 3 | 2/3 | 2016–2020: 0/1 (37%); 2020–2023: 1/1 (42%) | không |
| fng | 3 | 1/3 | 2016–2020: 0/0 (37%); 2020–2023: 1/3 (42%) | không |
| dev_ma20w | 6 | 3/6 | 2016–2020: 1/3 (37%); 2020–2023: 0/1 (42%) | không |
| ≥1 nhóm | 9 | 1/8 | 2016–2020: 0/4 (37%); 2020–2023: 0/2 (42%) | không |
| ≥3 nhóm | 4 | 1/4 | 2016–2020: 0/2 (37%); 2020–2023: 0/1 (42%) | không |

| Quy tắc | Giai đoạn | Tài sản so với giữ nguyên | Số lần bán | Mua lại rẻ hơn / đã mua lại |
|---|---|---|---|---|
| Bán 10% khi ≥1 nhóm | 2016–2020 | -16,2% | 4 | 0 / 4 |
| Bán 10% khi ≥1 nhóm | 2020–2023 | -4,4% | 3 | 0 / 2 |
| Bán 20% khi ≥1 nhóm | 2016–2020 | -29,5% | 4 | 0 / 4 |
| Bán 20% khi ≥1 nhóm | 2020–2023 | -8,5% | 3 | 0 / 2 |
| Bán 30% khi ≥1 nhóm | 2016–2020 | -40,3% | 4 | 0 / 4 |
| Bán 30% khi ≥1 nhóm | 2020–2023 | -12,3% | 3 | 0 / 2 |
| Bán 10% khi ≥3 nhóm | 2016–2020 | +0,6% | 2 | 1 / 2 |
| Bán 10% khi ≥3 nhóm | 2020–2023 | -1,1% | 1 | 0 / 1 |
| Bán 20% khi ≥3 nhóm | 2016–2020 | +1,2% | 2 | 1 / 2 |
| Bán 20% khi ≥3 nhóm | 2020–2023 | -2,3% | 1 | 0 / 1 |
| Bán 30% khi ≥3 nhóm | 2016–2020 | +1,7% | 2 | 1 / 2 |
| Bán 30% khi ≥3 nhóm | 2020–2023 | -3,4% | 1 | 0 / 1 |

Tiêu chí bên bán đáng tin: **0**. Tuần cuối (24/12/2023): 0 nhóm bật.
