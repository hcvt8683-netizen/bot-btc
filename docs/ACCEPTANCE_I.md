# Phần I: tiêu chí chấp nhận và lần chạy holdout duy nhất

Đăng ký trước: `config/candidates.yaml` mục `acceptance` (commit `60ddb0a`), trước khi đọc bất kỳ số nào của holdout. Holdout: 01/01/2024 → 25/10/2026 (147 tuần). Chạy lúc 2026-10-29T05:32:09Z, mã `af7ccea`, ghi trong `experiments/final_runs.log`.

## Kết luận: **KHÔNG ĐẠT** → giữ mua đều (hệ số 1,0)

| # | Tiêu chí | Kết quả | Đạt? |
|---|---|---|---|
| 1 | Lợi thế giá vốn > 0 ở ≥ 75% số năm trước holdout và trên holdout | năm có lợi: 0/2 (2022: 0,0%, 2023: 0,0%); holdout 0,0% | ✘ |
| 2 | Cận dưới khoảng tin cậy của lợi thế trên holdout > 0 | 0,0%, KTC 95% 0,0% đến 0,0% | ✘ |
| 3 | p hoán vị đã hiệu chỉnh < 0,05 (IC 26 tuần và lợi thế giá vốn) | IC: 1,000 (thô 1,000); lợi thế: 1,000 (thô 1,000); 121 tuần có mô hình (cần ≥ 114), 27 cấu hình | ✘ |
| 4 | Khung đơn điệu ở mọi kỳ hạn, trọng số đúng dấu | đơn điệu: 4 tuần không, 13 tuần không, 26 tuần không, 52 tuần không; trọng số ≥ 0 nhờ ràng buộc dấu; 233/233 tuần có mô hình đã phải bỏ chỉ số sai dấu (fng, mvrv) | ✘ |
| 5 | Brier tốt hơn tỷ lệ gốc | Brier 0,193 so với 0,189 (95 tuần) | ✘ |
| 6 | Thắng cả hai quy tắc đơn giản 1 chỉ số | Lồng nhau: 0,0%; Quy tắc MVRV: 0,0%; Quy tắc Giá/MA 200 tuần: 0,0% | ✘ |

Mô hình lồng nhau: 519 tuần ngoài mẫu, 286 tuần không có mô hình (mua đều); trong holdout 26/147 tuần không có mô hình.

## Tham khảo (không quyết định): hệ số so sánh 0,5 + thứ hạng

Cùng tiêu chí 1, 2, 6 nhưng dùng hệ số so sánh của Phần C (tuần có thứ hạng luôn lệch khỏi 1,0), để biết riêng tín hiệu có giá trị không.

| Tiêu chí | Kết quả | Đạt? |
|---|---|---|
| 1 | năm có lợi 1/2; holdout -0,3% | ✘ |
| 2 | -0,3%, KTC 95% -11,3% đến +6,0% | ✘ |
| 6 | Lồng nhau: -0,3%; Quy tắc MVRV: +0,8%; Quy tắc Giá/MA 200 tuần: +2,7% | ✘ |

## Từng chiến lược trên holdout

| Chiến lược | Từ | Lợi thế giá vốn, hệ số Phần D (KTC 95%) | Tuần hệ số ≠ 1 | Lợi thế, hệ số so sánh (KTC 95%) | Đơn điệu cả giai đoạn | Đơn điệu riêng holdout |
|---|---|---|---|---|---|---|
| Lồng nhau | 13/02/2022 | 0,0% (0,0% đến 0,0%) | 0% | -0,3% (-11,3% đến +6,0%) | không | không |
| Quy tắc MVRV | 07/07/2013 | 0,0% (0,0% đến 0,0%) | 0% | +0,8% (-12,8% đến +7,7%) | không | không |
| Quy tắc Giá/MA 200 tuần | 07/05/2017 | 0,0% (0,0% đến 0,0%) | 0% | +2,7% (-5,5% đến +6,7%) | không | không |

## Khung trên holdout (giá cao hơn sau 26 tuần, so với mọi tuần holdout)

| Chiến lược | Mốc | Khung | Số tuần | Số đợt | Tỷ lệ | Chênh (KTC 95%) | Kết luận |
|---|---|---|---|---|---|---|---|
| Lồng nhau | 79% | Phải mua | 12 | 1 | 83% | +4,4% (-51,9% đến +22,3%) | ít đợt (< 3) |
| Lồng nhau | 79% | Cân nhắc mua | 9 | 1 | 100% | +21,1% (+3,2% đến +35,8%) | ít đợt (< 3) |
| Lồng nhau | 79% | Không nên mua | 74 | 2 | 76% | -3,3% (-9,7% đến +0,2%) | ít đợt (< 3) |
| Quy tắc MVRV | 62% | Phải mua | 10 | 1 | 80% | +18,0% (-30,9% đến +47,6%) | ít đợt (< 3) |
| Quy tắc MVRV | 62% | Cân nhắc mua | 14 | 2 | 14% | -47,7% (-76,0% đến +24,8%) | ít đợt (< 3) |
| Quy tắc MVRV | 62% | Không nên mua | 97 | 1 | 67% | +5,0% (-3,3% đến +14,5%) | ít đợt (< 3) |
| Quy tắc Giá/MA 200 tuần | 62% | Phải mua | 0 | 0 | — | — | không có tuần |
| Quy tắc Giá/MA 200 tuần | 62% | Cân nhắc mua | 19 | 2 | 63% | +1,2% (-36,3% đến +38,1%) | ít đợt (< 3) |
| Quy tắc Giá/MA 200 tuần | 62% | Không nên mua | 102 | 1 | 62% | -0,2% (-7,4% đến +4,8%) | ít đợt (< 3) |

## Bên bán: chấm lại với chu kỳ có holdout

Chu kỳ: 2016-07 → 2020-05; 2020-05 → 2024-04; 2024-04 → 2026-10. "Đáng tin" chỉ khi tiêu chí đúng nhiều hơn mốc ở CẢ hai chu kỳ gần nhất.

| Tiêu chí | Số đợt | Đúng / đã biết kết quả | Theo chu kỳ: đúng/đợt (mốc) | Đáng tin? |
|---|---|---|---|---|
| mvrv | 4 | 0/4 | 2016–2020: 0/3 (37%); 2020–2024: 0/1 (37%); 2024–2026: 0/0 (38%) | không |
| mvrv_z | 7 | 3/7 | 2016–2020: 0/3 (37%); 2020–2024: 1/2 (37%); 2024–2026: 0/0 (38%) | không |
| pi_ratio | 1 | 1/1 | 2016–2020: 1/1 (37%); 2020–2024: 0/0 (37%); 2024–2026: 0/0 (38%) | không |
| mayer | 4 | 2/4 | 2016–2020: 1/2 (37%); 2020–2024: 0/1 (37%); 2024–2026: 0/0 (38%) | không |
| p_200wma | 2 | 0/2 | 2016–2020: 0/2 (37%); 2020–2024: 0/0 (37%); 2024–2026: 0/0 (38%) | không |
| rsi_14w | 9 | 3/9 | 2016–2020: 1/3 (37%); 2020–2024: 1/3 (37%); 2024–2026: 1/2 (38%) | không |
| puell | 3 | 2/3 | 2016–2020: 0/1 (37%); 2020–2024: 1/1 (37%); 2024–2026: 0/0 (38%) | không |
| fng | 4 | 1/4 | 2016–2020: 0/0 (37%); 2020–2024: 1/3 (37%); 2024–2026: 0/1 (38%) | không |
| dev_ma20w | 6 | 3/6 | 2016–2020: 1/3 (37%); 2020–2024: 0/1 (37%); 2024–2026: 0/0 (38%) | không |
| ≥1 nhóm | 12 | 3/12 | 2016–2020: 0/4 (37%); 2020–2024: 1/4 (37%); 2024–2026: 1/2 (38%) | không |
| ≥3 nhóm | 4 | 1/4 | 2016–2020: 0/2 (37%); 2020–2024: 0/1 (37%); 2024–2026: 0/0 (38%) | không |

| Quy tắc | Giai đoạn | Tài sản so với giữ nguyên | Số lần bán | Mua lại rẻ hơn / đã mua lại |
|---|---|---|---|---|
| Bán 10% khi ≥1 nhóm | 2016–2020 | -16,2% | 4 | 0 / 4 |
| Bán 10% khi ≥1 nhóm | 2020–2024 | -5,8% | 4 | 0 / 2 |
| Bán 10% khi ≥1 nhóm | 2024–2026 | +1,4% | 2 | 1 / 2 |
| Bán 20% khi ≥1 nhóm | 2016–2020 | -29,5% | 4 | 0 / 4 |
| Bán 20% khi ≥1 nhóm | 2020–2024 | -11,4% | 4 | 0 / 2 |
| Bán 20% khi ≥1 nhóm | 2024–2026 | +2,6% | 2 | 1 / 2 |
| Bán 30% khi ≥1 nhóm | 2016–2020 | -40,3% | 4 | 0 / 4 |
| Bán 30% khi ≥1 nhóm | 2020–2024 | -16,8% | 4 | 0 / 2 |
| Bán 30% khi ≥1 nhóm | 2024–2026 | +3,6% | 2 | 1 / 2 |
| Bán 10% khi ≥3 nhóm | 2016–2020 | +0,6% | 2 | 1 / 2 |
| Bán 10% khi ≥3 nhóm | 2020–2024 | -1,1% | 1 | 0 / 1 |
| Bán 10% khi ≥3 nhóm | 2024–2026 | 0,0% | 0 | 0 / 0 |
| Bán 20% khi ≥3 nhóm | 2016–2020 | +1,2% | 2 | 1 / 2 |
| Bán 20% khi ≥3 nhóm | 2020–2024 | -2,2% | 1 | 0 / 1 |
| Bán 20% khi ≥3 nhóm | 2024–2026 | 0,0% | 0 | 0 / 0 |
| Bán 30% khi ≥3 nhóm | 2016–2020 | +1,7% | 2 | 1 / 2 |
| Bán 30% khi ≥3 nhóm | 2020–2024 | -3,3% | 1 | 0 / 1 |
| Bán 30% khi ≥3 nhóm | 2024–2026 | 0,0% | 0 | 0 / 0 |

Tiêu chí bên bán đáng tin: **0**. Tuần cuối (25/10/2026): 0 nhóm bật.
