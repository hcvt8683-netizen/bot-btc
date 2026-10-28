# Thử bỏ từng phần, lớp chu kỳ (lớp A)

Chỉ chọn bằng giai đoạn huấn luyện: khung 2 năm trượt mỗi 4 tuần, từ 07/2013 (khi đủ 104 tuần phân vị cho mọi chỉ số trừ Giá/MA 200 tuần) đến 12/2019. Giai đoạn kiểm định 2020–2022 chỉ để xem sau, không dùng để chọn. Quy tắc chọn: ưu tiên kịch bản xấu (P10) khi trung vị chênh không quá 0,01. Loại chiến lược trùng hệt mua đều (mọi khung bằng 1,000). Mỗi lần đánh giá là một lần thử trong `experiments/registry.csv`.

Mô hình 1 = trung bình "độ rẻ" (phân vị 208 tuần đã đổi chiều) của các chỉ số. Ba bảng hệ số được thử:

- **T0**: từ 0,80 → 2,00; từ 0,60 → 1,25; từ 0,40 → 0,75; từ 0,00 → 0,25
- **T1**: từ 0,80 → 2,00; từ 0,60 → 1,25; từ 0,20 → 1,00; từ 0,00 → 0,50
- **T2**: từ 0,80 → 1,75; từ 0,60 → 1,25; từ 0,40 → 1,00; từ 0,20 → 0,75; từ 0,00 → 0,25

## Bảng T0

| Chỉ số riêng | Huấn luyện: trung vị | Huấn luyện: P10 | Kiểm định: tỷ số | Kiểm định: trung vị | Kiểm định: P10 |
|---|---|---|---|---|---|
| mvrv | 0,942 | 0,761 | 0,954 | 0,904 | 0,872 |
| mvrv_z | 0,944 | 0,747 | 0,962 | 0,912 | 0,885 |
| pi_ratio | 0,915 | 0,803 | 0,983 | 0,962 | 0,943 |
| p_200wma | 0,968 | 0,738 | 1,008 | 1,015 | 0,971 |
| mayer | 0,921 | 0,769 | 0,928 | 0,893 | 0,864 |
| puell | 0,920 | 0,821 | 1,021 | 1,024 | 0,976 |
| dd_ath | 0,943 | 0,728 | 0,947 | 0,886 | 0,834 |
| hash_ribbon_buy | 0,960 | 0,879 | 1,010 | 1,026 | 0,980 |

1. Thêm hash_ribbon_buy: huấn luyện trung vị 0,960, P10 0,879.
2. Dừng: thêm mvrv không cải thiện trên giai đoạn huấn luyện.

Bộ của bảng T0: **hash_ribbon_buy**. Kiểm định: tỷ số 1,010, trung vị 1,026, P10 0,980. Chu kỳ halving: 01/2011–11/2012 0,855, 11/2012–07/2016 0,922, 07/2016–05/2020 0,918, 05/2020–12/2022 1,021.

## Bảng T1

| Chỉ số riêng | Huấn luyện: trung vị | Huấn luyện: P10 | Kiểm định: tỷ số | Kiểm định: trung vị | Kiểm định: P10 |
|---|---|---|---|---|---|
| mvrv | 0,993 | 0,897 | 1,015 | 1,031 | 0,981 |
| mvrv_z | 0,995 | 0,862 | 1,021 | 1,045 | 0,990 |
| pi_ratio | 1,000 | 0,956 | 1,013 | 1,027 | 1,006 |
| p_200wma | 0,999 | 0,874 | 1,012 | 1,026 | 1,006 |
| mayer | 0,998 | 0,913 | 1,004 | 1,008 | 1,005 |
| puell | 1,000 | 0,947 | 1,010 | 1,020 | 1,004 |
| dd_ath | 0,985 | 0,799 | 1,031 | 1,058 | 0,992 |
| hash_ribbon_buy | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 |

1. Thêm pi_ratio: huấn luyện trung vị 1,000, P10 0,956.
2. Thêm p_200wma: huấn luyện trung vị 1,000, P10 0,962.
3. Thêm hash_ribbon_buy: huấn luyện trung vị 1,000, P10 1,000.
4. Dừng: thêm mayer không cải thiện trên giai đoạn huấn luyện.

Bộ của bảng T1: **pi_ratio + p_200wma + hash_ribbon_buy**. Kiểm định: tỷ số 1,000, trung vị 1,000, P10 1,000. Chu kỳ halving: 01/2011–11/2012 1,000, 11/2012–07/2016 1,000, 07/2016–05/2020 1,015, 05/2020–12/2022 1,000.

## Bảng T2

| Chỉ số riêng | Huấn luyện: trung vị | Huấn luyện: P10 | Kiểm định: tỷ số | Kiểm định: trung vị | Kiểm định: P10 |
|---|---|---|---|---|---|
| mvrv | 0,970 | 0,823 | 0,993 | 0,989 | 0,946 |
| mvrv_z | 0,975 | 0,804 | 1,000 | 1,001 | 0,953 |
| pi_ratio | 0,995 | 0,894 | 1,023 | 1,049 | 1,005 |
| p_200wma | 0,983 | 0,791 | 1,023 | 1,049 | 0,999 |
| mayer | 0,964 | 0,847 | 0,986 | 0,979 | 0,972 |
| puell | 0,988 | 0,906 | 1,020 | 1,043 | 0,996 |
| dd_ath | 0,970 | 0,750 | 0,998 | 0,987 | 0,939 |
| hash_ribbon_buy | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 |

1. Thêm puell: huấn luyện trung vị 0,988, P10 0,906.
2. Thêm hash_ribbon_buy: huấn luyện trung vị 0,998, P10 0,981.
3. Dừng: thêm p_200wma không cải thiện trên giai đoạn huấn luyện.

Bộ của bảng T2: **puell + hash_ribbon_buy**. Kiểm định: tỷ số 1,006, trung vị 1,012, P10 1,009. Chu kỳ halving: 01/2011–11/2012 1,000, 11/2012–07/2016 0,991, 07/2016–05/2020 0,998, 05/2020–12/2022 1,008.

## Mô hình 2 và 3

- Mô hình 2 (ridge ràng buộc dấu, đi tới, học lại mỗi 13 tuần, cắt bỏ nhãn chồng): dấu trung bình của hệ số tự do qua các lần học: mvrv -0,32, mvrv_z -0,74, pi_ratio 0,42, p_200wma 0,89, mayer 0,00, puell 1,00, dd_ath -1,00. Chỉ số đổi dấu hoặc ngược chiều kinh tế bị bỏ, còn lại: puell. Kết quả: huấn luyện trung vị 1,000, kiểm định 1,013. Không hơn mô hình 1.
- Mô hình 3 (boosting đơn điệu, sklearn, cài đặt cố định): huấn luyện trung vị 1,000, P10 1,000, kiểm định 1,006. Không hơn mô hình 1, nên không dùng.

## Kết luận lớp A

Theo quy tắc chọn định trước, bảng **T1** với **pi_ratio + p_200wma + hash_ribbon_buy** thắng trên giai đoạn huấn luyện (trung vị 1,000, P10 1,000). Kiểm định: tỷ số 1,000, trung vị 1,000, P10 1,000, tiền mặt chờ TB 0%.

Đọc kết quả: không chỉ số chu kỳ nào, dùng riêng hay kết hợp, thắng mua đều một cách vững trên giai đoạn huấn luyện. Bảng mặc định T0 kém rõ (trung vị 0,92–0,97) vì hệ số trung bình dưới 1 làm tiền nằm chờ khi giá đi lên. Mua gấp đôi lúc rẻ chỉ làm được khi đã để dành từ trước. Bảng T1 và T2 gần như trung tính nên kết quả sát 1,000. Bộ T2 (Puell + Hash Ribbon) có kiểm định đẹp hơn (1,006), nhưng chọn nó sau khi đã xem kiểm định là thiên lệch chọn lựa, nên không đổi.

So với bot hiện tại (Tự động) ở kiểm định: tỷ số 0,988, trung vị 0,974, P10 0,967.
