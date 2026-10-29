# Phần C: mô hình và chống khớp quá mức

Dữ liệu đến **31/12/2023**, holdout từ 01/01/2024 vẫn khóa. Mọi thiết lập lấy từ `config/candidates.yaml`, đã lưu git **trước** lần chạy đầu tiên (commit `da803d6`). Mọi cấu hình đã thử ghi trong `experiments/rebuild_configs.csv`.

## 1. Thiết lập đăng ký trước

- Hồi quy logistic L2. Nhãn: giá đóng thứ Hai sau 26 tuần cao hơn lúc mua. λ ∈ {0,3, 1,0, 3,0}.
- Đi tới lồng nhau: vòng ngoài học lại mỗi 13 tuần, cửa sổ mở rộng, chỉ để chấm điểm. Vòng trong chọn bộ chỉ số và λ theo log-loss trên 52 tuần có nhãn gần nhất (cắt bỏ 26 tuần để không chồng nhãn). Không cấu hình nào hơn tỷ lệ nền → không dùng mô hình (mua đều).
- Ràng buộc dấu bên mua: trọng số của "độ rẻ" phải ≥ 0; chỉ số học ra dấu ngược bị loại ở lần học đó và được ghi lại.
- Thứ hạng = vị trí của điểm hôm nay trong các điểm **ngoài mẫu** trước đó (cần 52 tuần). Để so sánh công bằng ở phần này, hệ số = 0,5 + thứ hạng.
- Mốc bắt buộc: mua đều; quy tắc 1 chỉ số (độ rẻ MVRV; độ rẻ Giá/MA 200 tuần).

| Bộ | Chỉ số | Lý do kinh tế |
|---|---|---|
| S1 | mvrv, p_200wma | Giá so với giá vốn on-chain cộng xu hướng 4 năm; các đáy chu kỳ trước nằm quanh MA 200 tuần và MVRV dưới 1. |
| S2 | mvrv, pi_ratio | Lõi của bot hiện tại (PA1): định giá on-chain cộng chu kỳ trung bình 111/350 ngày. |
| S3 | mvrv, puell | Định giá cộng áp lực thợ đào: doanh thu phát hành thấp (thợ đào đầu hàng) thường trùng vùng đáy. |
| S4 | mvrv, dev_ma20w | Định giá cộng tâm lý đo bằng giá so với MA 20 tuần (giống Fear & Greed 0,89, có lịch sử từ 2010). |
| S5 | mvrv, fng | Như S4 nhưng dùng Fear & Greed thật (chỉ có phân vị từ 02/2020, ít dữ liệu). |
| S6 | p_200wma, rsi_14w | Xu hướng dài hạn cộng bán quá đà trên khung tuần. |
| S7 | dd_ath, puell, dev_ma20w | Điều kiện đầu hàng: giá giảm sâu từ đỉnh, thợ đào căng thẳng, tâm lý sợ hãi. |
| S8 | pi_ratio, mvrv, fng | Bộ bot đang dùng (PA3), để so trực tiếp. |

## 2. Mô hình lồng nhau

- 372 tuần được chấm; **260 tuần vòng trong không tìm được cấu hình nào hơn tỷ lệ nền**, nên không dùng mô hình (mua đều).
- Cấu hình được chọn (số tuần): S1 λ0,3 (78), S2 λ3,0 (13), S3 λ0,3 (13), S2 λ0,3 (8).
- Ngoài mẫu từ 13/02/2022 (59 tuần có thứ hạng): tương quan thứ hạng với lợi suất 26 tuần -0,113; lợi thế giá vốn -8,6% (khoảng tin cậy -16,3% đến +3,4%).
- Xác suất: Brier 0,364 so với mốc 0,329, khoảng tin cậy của mức cải thiện -0,114 đến 0,032: **không hiển thị xác suất, chỉ thứ hạng**.

## 3. Mọi cấu hình, kiểm định hoán vị và hiệu chỉnh kiểm định bội

Hoán vị: dịch vòng chuỗi tín hiệu so với chuỗi lợi suất, độ lệch ngẫu nhiên ≥ 52 tuần, 1000 lần, dùng cùng các lần dịch cho mọi cấu hình. Hiệu chỉnh max-statistic trên **18 cấu hình chấm được** (Holm có trong file JSON). Chỉ khi p sau hiệu chỉnh nhỏ hơn 0,05 mới có ý nghĩa.

| Cấu hình | Từ | Số tuần | Tương quan với lợi suất 26 tuần | p (thô / hiệu chỉnh) | Lợi thế giá vốn | Khoảng tin cậy | p (thô / hiệu chỉnh) | Khung đơn điệu? |
|---|---|---|---|---|---|---|---|---|
| Lồng nhau (vòng trong chọn bộ và λ) | 13/02/2022 | 59 | -0,113 | — / 1,000 | -8,6% | -16,3% đến +3,4% | — / 1,000 | không |
| S1/λ0.3 | 03/05/2020 | 191 | -0,035 | 0,788 / 1,000 | -4,0% | -22,3% đến +4,9% | 0,420 / 1,000 | không |
| S1/λ1 | 03/05/2020 | 191 | -0,037 | 0,788 / 1,000 | -4,1% | -22,3% đến +4,9% | 0,420 / 1,000 | không |
| S1/λ3 | 03/05/2020 | 191 | -0,042 | 0,788 / 1,000 | -4,1% | -22,5% đến +4,9% | 0,438 / 1,000 | không |
| S2/λ0.3 | 13/09/2020 | 172 | -0,437 | 1,000 / 1,000 | -1,3% | -5,0% đến +0,9% | 1,000 / 1,000 | không |
| S2/λ1 | 13/09/2020 | 172 | -0,438 | 1,000 / 1,000 | -1,3% | -5,1% đến +1,0% | 1,000 / 1,000 | không |
| S2/λ3 | 13/09/2020 | 172 | -0,443 | 1,000 / 1,000 | -1,4% | -5,2% đến +1,0% | 1,000 / 1,000 | không |
| S3/λ0.3 | 24/10/2021 | 114 | -0,351 | 1,000 / 1,000 | -6,1% | -12,1% đến +8,7% | 1,000 / 1,000 | không |
| S3/λ1 | 24/10/2021 | 114 | -0,352 | 1,000 / 1,000 | -6,1% | -12,1% đến +8,8% | 1,000 / 1,000 | không |
| S3/λ3 | 24/10/2021 | 114 | -0,355 | 1,000 / 1,000 | -6,2% | -12,1% đến +8,8% | 1,000 / 1,000 | không |
| S6/λ0.3 | 03/05/2020 | 191 | -0,035 | 0,788 / 1,000 | -4,0% | -22,3% đến +4,9% | 0,420 / 1,000 | không |
| S6/λ1 | 03/05/2020 | 191 | -0,037 | 0,788 / 1,000 | -4,1% | -22,3% đến +4,9% | 0,420 / 1,000 | không |
| S6/λ3 | 03/05/2020 | 191 | -0,042 | 0,788 / 1,000 | -4,1% | -22,5% đến +4,9% | 0,438 / 1,000 | không |
| S7/λ0.3 | 29/01/2017 | 166 | -0,421 | 1,000 / 1,000 | -0,7% | -10,1% đến +0,7% | 0,829 / 1,000 | không |
| S7/λ1 | 29/01/2017 | 166 | -0,423 | 1,000 / 1,000 | -0,7% | -10,1% đến +0,7% | 0,829 / 1,000 | không |
| S7/λ3 | 29/01/2017 | 166 | -0,426 | 1,000 / 1,000 | -0,7% | -10,1% đến +0,7% | 0,829 / 1,000 | không |
| Quy tắc MVRV | 07/07/2013 | 547 | -0,051 | 0,627 / 1,000 | -6,1% | -25,9% đến +3,3% | 0,418 / 1,000 | không |
| Quy tắc Giá/MA 200 tuần | 07/05/2017 | 347 | 0,280 | 0,195 / 0,943 | -3,7% | -9,8% đến +1,3% | 0,700 / 1,000 | không |

Đã thử nhưng không đủ điểm ngoài mẫu để chấm (ràng buộc dấu loại hết chỉ số ở phần lớn các lần học, hoặc lịch sử quá ngắn): S4/λ0,3, S4/λ1,0, S4/λ3,0, S5/λ0,3, S5/λ1,0, S5/λ3,0, S8/λ0,3, S8/λ1,0, S8/λ3,0.

## 4. Ràng buộc dấu: chỉ số bị loại vì học ra dấu ngược

| Cấu hình | Số lần học có loại chỉ số | Chỉ số từng bị loại |
|---|---|---|
| S1/λ1 | 244 | mvrv |
| S2/λ1 | 221 | mvrv, pi_ratio |
| S3/λ1 | 167 | mvrv, puell |
| S4/λ1 | 34 | dev_ma20w |
| S5/λ1 | 75 | fng |
| S6/λ1 | 244 | rsi_14w |
| S7/λ1 | 219 | dd_ath, dev_ma20w, puell |
| S8/λ1 | 75 | fng, pi_ratio |

Mô hình rất hay học ra trọng số âm cho chỉ số "rẻ": rẻ hơn lại đi kèm xác suất có lãi sau 26 tuần thấp hơn. Fear & Greed bị loại ở **mọi** lần học, nên bộ có và không có Fear & Greed thực chất giống nhau (S5, S8 chỉ còn MVRV). Chỉ báo thay thế (độ lệch so với MA 20 tuần, S4) cũng bị loại.

## 5. Mô hình so với quy tắc đơn giản (cùng giai đoạn với mô hình lồng nhau)

| Cách | Từ | Số tuần | Tương quan với lợi suất 26 tuần | Lợi thế giá vốn (hệ số 0,5 + thứ hạng) |
|---|---|---|---|---|
| Lồng nhau (vòng trong chọn bộ và λ) | 13/02/2022 | 59 | -0,113 | -8,6% |
| Quy tắc MVRV | 13/02/2022 | 98 | 0,584 | -0,1% |
| Quy tắc Giá/MA 200 tuần | 13/02/2022 | 98 | 0,544 | 0,0% |

Mô hình lồng nhau **không thắng** hai quy tắc đơn giản, nên theo bản kế hoạch không được dùng.

## 6. Bỏ từng chu kỳ ra khỏi dữ liệu học (λ = 1)

Học trên các chu kỳ khác (cắt bỏ 26 tuần quanh chu kỳ bị bỏ), chấm trên chu kỳ bị bỏ. Đây không phải kiểm định đi tới, vì mô hình có thể học từ chu kỳ sau.

| Bộ | 2012-11-28 → 2016-07-08 | 2016-07-09 → 2020-05-10 | 2020-05-11 → 2023-12-31 |
|---|---|---|---|
| S1 | chưa đủ dữ liệu | p_200wma: tương quan -0,04, lợi thế -21,3% | p_200wma: tương quan 0,32, lợi thế +0,3% |
| S2 | mvrv+pi_ratio: tương quan -0,23, lợi thế -1,6% | mvrv: tương quan -0,16, lợi thế -17,2% | pi_ratio: tương quan 0,00, lợi thế +1,4% |
| S3 | puell: tương quan -0,42, lợi thế -5,8% | mvrv: tương quan -0,16, lợi thế -17,1% | mọi chỉ số bị loại |
| S4 | mvrv: tương quan -0,30, lợi thế -3,1% | mvrv: tương quan -0,16, lợi thế -16,3% | mọi chỉ số bị loại |
| S5 | chưa đủ dữ liệu | chưa đủ dữ liệu | chưa đủ dữ liệu |
| S6 | chưa đủ dữ liệu | p_200wma: tương quan -0,04, lợi thế -21,3% | p_200wma: tương quan 0,32, lợi thế +0,3% |
| S7 | puell: tương quan -0,42, lợi thế -5,8% | dd_ath: tương quan -0,30, lợi thế -24,3% | mọi chỉ số bị loại |
| S8 | chưa đủ dữ liệu | chưa đủ dữ liệu | chưa đủ dữ liệu |

## 7. Kiểm tra đơn điệu và gộp khung

Yêu cầu: Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua ở mọi kỳ hạn. Không đạt thì gộp Phải mua và Cân nhắc mua thành "Mua thêm"; vẫn không đạt thì bỏ khung.

- Lồng nhau (vòng trong chọn bộ và λ): khung gốc đơn điệu **không**; sau khi gộp **không**, nên bỏ khung, không gắn nhãn hành động.
- Quy tắc MVRV: khung gốc đơn điệu **không**; sau khi gộp **không**, nên bỏ khung, không gắn nhãn hành động.
- Quy tắc Giá/MA 200 tuần: khung gốc đơn điệu **không**; sau khi gộp **không**, nên bỏ khung, không gắn nhãn hành động.

## 8. Kết luận Phần C

- Không cấu hình nào, kể cả quy tắc đơn giản, có ý nghĩa thống kê sau hiệu chỉnh kiểm định bội (p hiệu chỉnh nhỏ nhất 0,943).
- Mô hình lồng nhau phần lớn thời gian **tự chọn không dùng mô hình**; khi có chọn thì kém mua đều và kém quy tắc đơn giản.
- Khung không đơn điệu ở bất kỳ cách nào, kể cả sau khi gộp.
- Kết luận đúng theo nguyên tắc: **chưa có lợi thế, nên mua đều (hệ số 1,0)**. Phần D vẫn dựng khung và hệ số theo quy tắc, nhưng với kết quả này hệ số sẽ là 1,0.
