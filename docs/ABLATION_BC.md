# Thử bỏ từng phần, lớp ngắn hạn (B) và lớp vĩ mô (C)

Nền: lớp A đã chọn ở giai đoạn 4. Dữ liệu nhóm B chỉ có từ 2018–2020, nên mỗi quy tắc được chấm **trong khoảng có dữ liệu của nó**, đến 31/12/2022, với khung trượt 52 tuần (khung 104 tuần sẽ còn quá ít). Khoảng này gồm cả giai đoạn kiểm định, nên với lớp B/C chỉ giai đoạn kiểm tra cuối mới là kiểm tra thật ngoài mẫu. Mẫu quy tắc cố định cho mọi chỉ số (không dò): phân vị 104 tuần; nhóm rẻ nhất 20% → hệ số × 1,25; nhóm đắt nhất 20% → × 0,75. Sự kiện đầu hàng (giảm > 10% trong tuần, khối lượng > 2 lần TB 20 tuần) → × 1,25 trong 4 tuần. Giữ quy tắc khi kịch bản xấu (P10) tốt hơn và trung vị không giảm quá 1%. Dưới 10 đợt độc lập → chỉ hiển thị.

## Fear & Greed: ngược đám đông hay theo đà (chỉ dùng giai đoạn huấn luyện)

- fng: năm có tín hiệu trong giai đoạn huấn luyện 2019; tác động lên tỷ số tài sản theo năm: 0,004 → không ổn định.
- fng_momentum: năm có tín hiệu trong giai đoạn huấn luyện 2019; tác động lên tỷ số tài sản theo năm: 0,001 → không ổn định.

Không cách hiểu nào được chứng minh ổn định: Fear & Greed có từ 02/2018 và cần 52 tuần lịch sử phân vị, nên giai đoạn huấn luyện chỉ còn năm 2019 (cần ít nhất 2 năm cùng chiều). Theo mục 4.1, bỏ chỉ số này.

## Lớp B

| Quy tắc | Kết luận | Số đợt | Tỷ lệ tuần bật | Chấm từ | Trước: trung vị / P10 | Sau: trung vị / P10 |
|---|---|---|---|---|---|---|
| funding_7d | bỏ | 25 | 8% | 15/09/2020 | 1,000 / 1,000 | 1,003 / 0,993 |
| basis_ann | bỏ | 12 | 6% | 03/08/2021 | 1,000 / 1,000 | 1,000 / 1,000 |
| stable_supply_30d | bỏ | 11 | 13% | 01/01/2019 | 1,000 / 1,000 | 1,000 / 0,997 |
| fng | bỏ: không ổn định trên giai đoạn huấn luyện | — | — | — | — | — |
| fng_momentum | bỏ: không ổn định trên giai đoạn huấn luyện | — | — | — | — | — |
| rsi_14w | bỏ | 47 | 40% | 03/01/2012 | 1,000 / 1,000 | 0,995 / 0,944 |
| rsi_14d | bỏ | 124 | 38% | 03/01/2012 | 1,000 / 1,000 | 0,997 / 0,960 |
| capitulation | chỉ hiển thị: 9 đợt (< 10) | 9 | — | — | — | — |
| oi_to_mcap | chỉ hiển thị: Binance chỉ giữ 30 ngày; đang ghi tiếp từ 28/10/2026, chưa đủ để kiểm định | — | — | — | — | — |
| etf_flow_5d | chỉ hiển thị: nguồn tùy chọn, chưa bật | — | — | — | — | — |
| vol_rel_20w | chỉ hiển thị: chỉ là bối cảnh (khối lượng cao ở cả đỉnh lẫn đáy) | — | — | — | — | — |

## Lớp C (chấm từ 07/2013 đến 31/12/2022, khung 52 tuần)

| Quy tắc | Kết luận | Số lần / đợt | Tỷ lệ tuần bật | Trước: trung vị / P10 | Sau: trung vị / P10 |
|---|---|---|---|---|---|
| event_window | bỏ | 150 | 24% | 1,000 / 1,000 | 1,000 / 0,994 |
| macro_cap | bỏ | 5 | 4% | 1,000 / 1,000 | 1,000 / 1,000 |

Quy tắc lớp B được giữ: không có. Lớp C được giữ: không có.
