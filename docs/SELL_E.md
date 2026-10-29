# Phần E: bên bán, một hệ thống

Dữ liệu từ 01/01/2012 đến **31/12/2023** (holdout khóa). Đăng ký trước: `config/candidates.yaml` mục `sell` (commit `d7a47ce`).

- Tiêu chí bật khi chỉ số thuộc **5% đắt nhất của 4 năm trước** (phân vị trượt, không ngưỡng tuyệt đối). Đếm theo **nhóm**: dinh gia onchain: mvrv, mvrv_z; xu huong gia: pi_ratio, mayer, p_200wma, rsi_14w; tho dao: puell; tam ly: fng, dev_ma20w.
- **Một hệ thống duy nhất**: 0 nhóm → Giữ; 1–2 nhóm → Chốt lời một phần; ≥ 3 nhóm → Bán phần lớn (thay cho khung "Nên bán" và bảng tiêu chí chốt lời riêng).
- Quy tắc thực thi: bán X% BTC đang giữ **một lần khi đợt tín hiệu bắt đầu** (quyết định ở giá đóng Chủ nhật, khớp ở giá đóng thứ Hai); mua lại toàn bộ khi giá ≤ 80% giá bán bình quân hoặc sau 52 tuần. Vẫn mua đều mỗi tuần; so với mua đều không bán.
- Chấm từng tiêu chí: giá 26 tuần sau thấp hơn lúc bật, theo **đợt** (Wilson), kèm bootstrap thống nhất của mức chênh so với mọi tuần.

## 1. Từng tiêu chí và tín hiệu theo nhóm

| Tiêu chí | Số đợt | Số tuần bật | Đợt đúng (giá thấp hơn sau 26 tuần) | Wilson theo đợt | Mốc (mọi tuần) | Chênh (bootstrap) | Theo chu kỳ: đúng/đợt | "Đáng tin" |
|---|---|---|---|---|---|---|---|---|
| mvrv | 4 | 20 | 0/4 (0%) | 0%–49% | 35% | +14,8% (-33,0% đến +51,5%) | 2012–2016: 0/0; 2016–2020: 0/3; 2020–2023: 0/1 | không |
| mvrv_z | 7 | 30 | 3/7 (43%) | 16%–75% | 35% | +8,2% (-22,0% đến +57,1%) | 2012–2016: 2/2; 2016–2020: 0/3; 2020–2023: 1/2 | không |
| pi_ratio | 1 | 6 | 1/1 (100%) | 21%–100% | 35% | +48,2% (+23,5% đến +71,8%) | 2012–2016: 0/0; 2016–2020: 1/1; 2020–2023: 0/0 | không |
| mayer | 4 | 15 | 2/4 (50%) | 15%–85% | 35% | +51,5% (+14,1% đến +71,3%) | 2012–2016: 1/1; 2016–2020: 1/2; 2020–2023: 0/1 | không |
| p_200wma | 2 | 24 | 0/2 (0%) | 0%–66% | 35% | -1,8% (-42,8% đến +58,0%) | 2012–2016: 0/0; 2016–2020: 0/2; 2020–2023: 0/0 | không |
| rsi_14w | 6 | 27 | 1/5 (20%) | 4%–62% | 35% | -10,2% (-33,1% đến +20,2%) | 2012–2016: 0/1; 2016–2020: 1/3; 2020–2023: 0/1 | không |
| puell | 3 | 13 | 2/3 (67%) | 21%–94% | 35% | +41,8% (+13,2% đến +76,1%) | 2012–2016: 1/1; 2016–2020: 0/1; 2020–2023: 1/1 | không |
| fng | 3 | 17 | 1/3 (33%) | 6%–79% | 35% | -17,5% (-44,5% đến +59,3%) | 2012–2016: 0/0; 2016–2020: 0/0; 2020–2023: 1/3 | không |
| dev_ma20w | 6 | 20 | 3/6 (50%) | 19%–81% | 35% | +44,8% (+17,7% đến +67,0%) | 2012–2016: 2/2; 2016–2020: 1/3; 2020–2023: 0/1 | không |
| ≥1 nhóm | 9 | 78 | 1/8 (12%) | 2%–47% | 35% | -4,5% (-22,9% đến +14,6%) | 2012–2016: 1/2; 2016–2020: 0/4; 2020–2023: 0/2 | không |
| ≥3 nhóm | 4 | 19 | 1/4 (25%) | 5%–70% | 35% | +33,3% (-6,6% đến +65,1%) | 2012–2016: 1/1; 2016–2020: 0/2; 2020–2023: 0/1 | không |

"Đáng tin" chỉ khi tiêu chí đúng nhiều hơn mốc ở **2 chu kỳ gần nhất, có chu kỳ 2021–2025**. Dữ liệu 2024–2025 nằm trong holdout, nên tiêu chí qua được 2 chu kỳ có sẵn chỉ ở trạng thái "chờ chấm ở Phần I".

## 2. Quy tắc bán so với giữ nguyên (cùng mua đều mỗi tuần)

| Kích hoạt | Bán mỗi lần | Giai đoạn | Tài sản so với giữ nguyên | Sụt giảm lớn nhất: có bán / giữ nguyên | Số lần bán | Đã mua lại: đúng / tổng | Còn mở cuối kỳ |
|---|---|---|---|---|---|---|---|
| ≥1 nhóm | 10% | 2012–2023 | -37,8% | -82% / -82% | 9 | 1 / 8 | 1 |
| ≥1 nhóm | 10% | 2012–2016 | -4,3% | -79% / -80% | 2 | 1 / 2 | 0 |
| ≥1 nhóm | 10% | 2016–2020 | -16,2% | -82% / -82% | 4 | 0 / 4 | 0 |
| ≥1 nhóm | 10% | 2020–2023 | -4,4% | -77% / -77% | 3 | 0 / 2 | 1 |
| ≥1 nhóm | 20% | 2012–2023 | -62,1% | -81% / -82% | 9 | 1 / 8 | 1 |
| ≥1 nhóm | 20% | 2012–2016 | -8,6% | -79% / -80% | 2 | 1 / 2 | 0 |
| ≥1 nhóm | 20% | 2016–2020 | -29,5% | -82% / -82% | 4 | 0 / 4 | 0 |
| ≥1 nhóm | 20% | 2020–2023 | -8,5% | -77% / -77% | 3 | 0 / 2 | 1 |
| ≥1 nhóm | 30% | 2012–2023 | -77,4% | -81% / -82% | 9 | 1 / 8 | 1 |
| ≥1 nhóm | 30% | 2012–2016 | -12,9% | -78% / -80% | 2 | 1 / 2 | 0 |
| ≥1 nhóm | 30% | 2016–2020 | -40,3% | -81% / -82% | 4 | 0 / 4 | 0 |
| ≥1 nhóm | 30% | 2020–2023 | -12,3% | -77% / -77% | 3 | 0 / 2 | 1 |
| ≥3 nhóm | 10% | 2012–2023 | +4,7% | -81% / -82% | 4 | 2 / 4 | 0 |
| ≥3 nhóm | 10% | 2012–2016 | +7,5% | -80% / -80% | 1 | 1 / 1 | 0 |
| ≥3 nhóm | 10% | 2016–2020 | +0,6% | -81% / -82% | 2 | 1 / 2 | 0 |
| ≥3 nhóm | 10% | 2020–2023 | -1,1% | -76% / -77% | 1 | 0 / 1 | 0 |
| ≥3 nhóm | 20% | 2012–2023 | +9,0% | -80% / -82% | 4 | 2 / 4 | 0 |
| ≥3 nhóm | 20% | 2012–2016 | +15,1% | -80% / -80% | 1 | 1 / 1 | 0 |
| ≥3 nhóm | 20% | 2016–2020 | +1,2% | -80% / -82% | 2 | 1 / 2 | 0 |
| ≥3 nhóm | 20% | 2020–2023 | -2,3% | -76% / -77% | 1 | 0 / 1 | 0 |
| ≥3 nhóm | 30% | 2012–2023 | +12,8% | -80% / -82% | 4 | 2 / 4 | 0 |
| ≥3 nhóm | 30% | 2012–2016 | +22,6% | -80% / -80% | 1 | 1 / 1 | 0 |
| ≥3 nhóm | 30% | 2016–2020 | +1,7% | -78% / -82% | 2 | 1 / 2 | 0 |
| ≥3 nhóm | 30% | 2020–2023 | -3,4% | -75% / -77% | 1 | 0 / 1 | 0 |

## 3. Kết luận Phần E

- Tuần cuối trước holdout (24/12/2023): 0 nhóm bật → **Giữ**.
- Bán 10% khi ≥1 nhóm: có lợi ở 0/3 chu kỳ; cả giai đoạn -37,8% với 9 lần bán (1/8 lần mua lại rẻ hơn giá bán).
- Bán 20% khi ≥1 nhóm: có lợi ở 0/3 chu kỳ; cả giai đoạn -62,1% với 9 lần bán (1/8 lần mua lại rẻ hơn giá bán).
- Bán 30% khi ≥1 nhóm: có lợi ở 0/3 chu kỳ; cả giai đoạn -77,4% với 9 lần bán (1/8 lần mua lại rẻ hơn giá bán).
- Bán 10% khi ≥3 nhóm: có lợi ở 2/3 chu kỳ; cả giai đoạn +4,7% với 4 lần bán (2/4 lần mua lại rẻ hơn giá bán).
- Bán 20% khi ≥3 nhóm: có lợi ở 2/3 chu kỳ; cả giai đoạn +9,0% với 4 lần bán (2/4 lần mua lại rẻ hơn giá bán).
- Bán 30% khi ≥3 nhóm: có lợi ở 2/3 chu kỳ; cả giai đoạn +12,8% với 4 lần bán (2/4 lần mua lại rẻ hơn giá bán).
- Tiêu chí qua được 2 chu kỳ gần nhất có dữ liệu: 0. Mọi kết luận bên bán dựa trên rất ít đợt (dưới 10), nên **chưa có lợi thế đáng tin**; bên bán chỉ hiển thị mức Giữ / Chốt lời một phần / Bán phần lớn để tham khảo, kèm số đợt.
