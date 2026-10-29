# Phần B: đo lại bot hiện tại bằng thước đo thống nhất

Dữ liệu đến **31/12/2023** (holdout từ 01/01/2024 vẫn khóa). Tín hiệu ở giá đóng Chủ nhật; mua và chấm ở **giá đóng thứ Hai**. Mốc so sánh luôn là **mọi tuần trong cùng giai đoạn** của chính bảng đó. Khoảng tin cậy 95%: bootstrap khối dừng, độ dài khối trung bình bằng kỳ hạn, 2.000 lần, tính cho **mức chênh so với mốc**. Đối chiếu: Wilson theo đợt (mỗi đợt một quan sát, lấy tuần đầu). Đợt = các tuần cùng khung, cách nhau ≤ 4 tuần gộp một đợt. Khoảng tin cậy của mức chênh chứa 0 → "chưa có lợi thế"; dưới 3 đợt → "ít đợt, chưa kết luận" (bootstrap theo tuần không đo được bất định khi chỉ có 1–2 đợt).

## PA3 cố định (Pi + MVRV + Fear & Greed, bộ bot đang dùng)

Từ 02/08/2020, 179 tuần có điểm.

### Giữ 1 tháng (mốc: 56% thắng, 175 tuần; lãi trung vị +3%)

| Khung | Số tuần | Số đợt | Thắng | Chênh so với mốc | Khoảng tin cậy của mức chênh | Wilson theo đợt | Lãi trung vị (tứ phân vị) | Sụt giảm trung vị trong kỳ | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Phải mua | 70 | 1 | 53% | -3% | -17% đến +11% | 0%–79% (1 đợt) | +1% (-6% đến +9%) | -4% | ít đợt (< 3), chưa kết luận |
| Cân nhắc mua | 7 | 2 | 71% | +15% | -56% đến +49% | 9%–91% (2 đợt) | +14% (-11% đến +22%) | 0% | ít đợt (< 3), chưa kết luận |
| Không nên mua | 98 | 2 | 57% | +1% | -9% đến +12% | 34%–100% (2 đợt) | +3% (-11% đến +20%) | -5% | ít đợt (< 3), chưa kết luận |

Các khung có xếp đúng thứ tự (Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua)? **không**.

### Giữ 3 tháng (mốc: 56% thắng, 166 tuần; lãi trung vị +6%)

| Khung | Số tuần | Số đợt | Thắng | Chênh so với mốc | Khoảng tin cậy của mức chênh | Wilson theo đợt | Lãi trung vị (tứ phân vị) | Sụt giảm trung vị trong kỳ | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Phải mua | 69 | 1 | 61% | +5% | -22% đến +28% | 0%–79% (1 đợt) | +7% (-7% đến +24%) | -7% | ít đợt (< 3), chưa kết luận |
| Cân nhắc mua | 3 | 2 | 33% | -23% | -61% đến +46% | 9%–91% (2 đợt) | -27% (-32% đến +17%) | -31% | ít đợt (< 3), chưa kết luận |
| Không nên mua | 94 | 1 | 53% | -3% | -22% đến +13% | 21%–100% (1 đợt) | +5% (-30% đến +68%) | -14% | ít đợt (< 3), chưa kết luận |

Các khung có xếp đúng thứ tự (Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua)? **không**.

### Giữ 6 tháng (mốc: 55% thắng, 153 tuần; lãi trung vị +8%)

| Khung | Số tuần | Số đợt | Thắng | Chênh so với mốc | Khoảng tin cậy của mức chênh | Wilson theo đợt | Lãi trung vị (tứ phân vị) | Sụt giảm trung vị trong kỳ | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Phải mua | 57 | 1 | 74% | +19% | -8% đến +46% | 0%–79% (1 đợt) | +28% (-1% đến +44%) | -10% | ít đợt (< 3), chưa kết luận |
| Cân nhắc mua | 2 | 1 | 0% | -55% | -76% đến -23% | 0%–79% (1 đợt) | -46% (-46% đến -46%) | -48% | ít đợt (< 3), chưa kết luận |
| Không nên mua | 94 | 1 | 45% | -10% | -37% đến +3% | 21%–100% (1 đợt) | -5% (-42% đến +47%) | -30% | ít đợt (< 3), chưa kết luận |

Các khung có xếp đúng thứ tự (Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua)? **không**.

### Giữ 1 năm (mốc: 45% thắng, 127 tuần; lãi trung vị -13%)

| Khung | Số tuần | Số đợt | Thắng | Chênh so với mốc | Khoảng tin cậy của mức chênh | Wilson theo đợt | Lãi trung vị (tứ phân vị) | Sụt giảm trung vị trong kỳ | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Phải mua | 31 | 1 | 97% | +52% | +15% đến +77% | 0%–79% (1 đợt) | +44% (+29% đến +95%) | -21% | ít đợt (< 3), chưa kết luận |
| Cân nhắc mua | 2 | 1 | 0% | -45% | -78% đến -12% | 0%–79% (1 đợt) | -13% (-15% đến -10%) | -48% | ít đợt (< 3), chưa kết luận |
| Không nên mua | 94 | 1 | 29% | -16% | -35% đến 0% | 21%–100% (1 đợt) | -31% (-48% đến +18%) | -46% | ít đợt (< 3), chưa kết luận |

Các khung có xếp đúng thứ tự (Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua)? **không**.

**Lợi thế giá vốn khi dùng khung làm hệ số** (Phải mua × 1,5; Cân nhắc mua × 1,25; Không nên mua × 0,5), cùng tiền nạp mỗi tuần, có quỹ dự trữ, không vay, tiền dư cuối kỳ tính theo giá cuối: **+2,5%** (khoảng tin cậy -35,6% đến +33,4%, 179 tuần) → chưa có lợi thế. Chỉ tính phần đã giải ngân: +6,2%; tiền dư cuối kỳ 8,0% tổng nạp.
Theo từng năm: 2021: -5,4%, 2022: +10,0%, 2023: -0,4%.

## Chế độ Tự động (chọn lại phương án mỗi 4 tuần)

Từ 06/12/2020, 161 tuần có điểm.

### Giữ 1 tháng (mốc: 54% thắng, 157 tuần; lãi trung vị +1%)

| Khung | Số tuần | Số đợt | Thắng | Chênh so với mốc | Khoảng tin cậy của mức chênh | Wilson theo đợt | Lãi trung vị (tứ phân vị) | Sụt giảm trung vị trong kỳ | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Phải mua | 63 | 6 | 41% | -12% | -29% đến +2% | 10%–70% (6 đợt) | -2% (-11% đến +7%) | -5% | chưa có lợi thế |
| Cân nhắc mua | 26 | 3 | 58% | +4% | -21% đến +31% | 21%–94% (3 đợt) | +4% (-16% đến +13%) | -4% | chưa có lợi thế |
| Không nên mua | 68 | 6 | 63% | +10% | -4% đến +23% | 19%–81% (6 đợt) | +4% (-6% đến +20%) | -2% | chưa có lợi thế |

Các khung có xếp đúng thứ tự (Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua)? **không**.

### Giữ 3 tháng (mốc: 51% thắng, 148 tuần; lãi trung vị 0%)

| Khung | Số tuần | Số đợt | Thắng | Chênh so với mốc | Khoảng tin cậy của mức chênh | Wilson theo đợt | Lãi trung vị (tứ phân vị) | Sụt giảm trung vị trong kỳ | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Phải mua | 62 | 6 | 56% | +6% | -15% đến +18% | 3%–56% (6 đợt) | +2% (-13% đến +18%) | -13% | chưa có lợi thế |
| Cân nhắc mua | 22 | 3 | 9% | -42% | -54% đến +26% | 21%–94% (3 đợt) | -24% (-37% đến -5%) | -27% | chưa có lợi thế |
| Không nên mua | 64 | 5 | 59% | +9% | -9% đến +28% | 23%–88% (5 đợt) | +11% (-19% đến +53%) | -10% | chưa có lợi thế |

Các khung có xếp đúng thứ tự (Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua)? **không**.

### Giữ 6 tháng (mốc: 49% thắng, 135 tuần; lãi trung vị -2%)

| Khung | Số tuần | Số đợt | Thắng | Chênh so với mốc | Khoảng tin cậy của mức chênh | Wilson theo đợt | Lãi trung vị (tứ phân vị) | Sụt giảm trung vị trong kỳ | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Phải mua | 50 | 6 | 58% | +9% | -17% đến +18% | 10%–70% (6 đợt) | +14% (-37% đến +37%) | -16% | chưa có lợi thế |
| Cân nhắc mua | 21 | 2 | 5% | -44% | -58% đến +30% | 9%–91% (2 đợt) | -46% (-52% đến -20%) | -50% | ít đợt (< 3), chưa kết luận |
| Không nên mua | 64 | 5 | 56% | +7% | -8% đến +27% | 38%–96% (5 đợt) | +7% (-7% đến +42%) | -21% | chưa có lợi thế |

Các khung có xếp đúng thứ tự (Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua)? **không**.

### Giữ 1 năm (mốc: 36% thắng, 109 tuần; lãi trung vị -25%)

| Khung | Số tuần | Số đợt | Thắng | Chênh so với mốc | Khoảng tin cậy của mức chênh | Wilson theo đợt | Lãi trung vị (tứ phân vị) | Sụt giảm trung vị trong kỳ | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Phải mua | 24 | 6 | 42% | +6% | -10% đến +46% | 19%–81% (6 đợt) | -18% (-65% đến +29%) | -54% | chưa có lợi thế |
| Cân nhắc mua | 21 | 2 | 29% | -7% | -27% đến +54% | 9%–91% (2 đợt) | -28% (-41% đến +30%) | -59% | ít đợt (< 3), chưa kết luận |
| Không nên mua | 64 | 5 | 36% | 0% | -9% đến +21% | 38%–96% (5 đợt) | -25% (-41% đến +28%) | -39% | chưa có lợi thế |

Các khung có xếp đúng thứ tự (Phải mua ≥ Cân nhắc mua ≥ mốc ≥ Không nên mua)? **không**.

**Lợi thế giá vốn khi dùng khung làm hệ số** (Phải mua × 1,5; Cân nhắc mua × 1,25; Không nên mua × 0,5), cùng tiền nạp mỗi tuần, có quỹ dự trữ, không vay, tiền dư cuối kỳ tính theo giá cuối: **+2,8%** (khoảng tin cậy -20,7% đến +10,3%, 161 tuần) → chưa có lợi thế. Chỉ tính phần đã giải ngân: +3,6%; tiền dư cuối kỳ 2,5% tổng nạp.
Theo từng năm: 2021: -6,3%, 2022: +0,2%, 2023: -0,4%.

## Xác suất của mô hình hiện tại có đáng tin không (PA3)

Brier score: càng thấp càng tốt. Mốc là tỷ lệ thắng nền trong cửa sổ huấn luyện tại từng thời điểm. Chỉ hiển thị xác suất khi khoảng tin cậy của (Brier mốc − Brier mô hình) nằm hẳn trên 0; nếu không, chỉ hiển thị thứ hạng.

| Kỳ hạn | Số tuần | Brier mô hình | Brier mốc | Điểm kỹ năng | Khoảng tin cậy của mức cải thiện | Hiển thị xác suất? |
|---|---|---|---|---|---|---|
| 1 tháng | 223 | 0,270 | 0,254 | -0,063 | -0,050 đến 0,017 | **không, chỉ thứ hạng** |
| 3 tháng | 205 | 0,321 | 0,270 | -0,186 | -0,115 đến 0,007 | **không, chỉ thứ hạng** |
| 6 tháng | 179 | 0,390 | 0,303 | -0,289 | -0,246 đến 0,057 | **không, chỉ thứ hạng** |
| 1 năm | 127 | 0,367 | 0,413 | 0,112 | -0,103 đến 0,204 | **không, chỉ thứ hạng** |

Biểu đồ độ tin cậy (dạng bảng) của mô hình 6 tháng, theo nhóm thập phân vị của xác suất dự báo:

| Nhóm | Xác suất dự báo TB | Tỷ lệ thắng thực tế | Số tuần |
|---|---|---|---|
| 1 | 1% | 56% | 18 |
| 2 | 6% | 89% | 18 |
| 3 | 13% | 89% | 18 |
| 4 | 22% | 72% | 18 |
| 5 | 31% | 71% | 17 |
| 6 | 49% | 17% | 18 |
| 7 | 59% | 6% | 18 |
| 8 | 77% | 78% | 18 |
| 9 | 82% | 83% | 18 |
| 10 | 85% | 78% | 18 |
