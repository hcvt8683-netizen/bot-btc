# Hồi cứu cắt ngang các phần của trang (02/11/2026)

Tại 24 thời điểm (01/11/2024 → 01/10/2026, ngày 1 hằng tháng), tính lại điều mỗi phần của trang đã nói **chỉ bằng dữ liệu có đến lúc đó** (cùng hàm mà trang dùng), rồi so với điều đã xảy ra. Các thời điểm cách nhau 1 tháng nên kỳ hạn đến 30 ngày không chồng nhau; 90 ngày và 13 tuần thì chồng nhau, khoảng tin cậy thực tế rộng hơn số ghi. 24 thời điểm là ít: đây là kiểm tra sức khỏe, không phải kiểm định (kiểm định dài hạn nằm trong từng thẻ).

Tạo bằng `python tools/hoi_cuu.py`.

## Tóm tắt

| Phần | Kiểm tra | Kết quả | Đánh giá |
|---|---|---|---|
| Dự báo dải giá | Trúng khoảng 8/10 lần, 7 và 30 ngày | 7 ngày: 19/24 = 79% (Wilson 95%: 60%–91%); 30 ngày: 19/24 = 79% (Wilson 95%: 60%–91%) | đúng tỷ lệ khi khoảng tin cậy chứa 80% |
| Giá chờ mua / bán | Khả năng chạm ±3% trong 7 ngày | mua: nói 53%, chạm 12/24 = 50% (Wilson 95%: 31%–69%); bán: nói 55%, chạm 19/24 = 79% (Wilson 95%: 60%–91%) | đúng khi tỷ lệ chạm gần mức bot nói |
| Xác suất có lãi | 4 và 13 tuần | 4 tuần: nói 53%, có lãi 14/24 = 58% (Wilson 95%: 39%–76%); 13 tuần: nói 57%, có lãi 10/22 = 45% (Wilson 95%: 27%–65%) | tỷ lệ gốc, không đoán thời điểm |
| Long/Short | Tháng đạt 6/6 | 0 tháng; long theo công thức mọi tháng: 59 lệnh, tổng −8,1R | không đề xuất là đúng khi tổng R âm |
| Xu hướng | Đúng hướng khi nghiêng 1 phía, 30 ngày | 1/3 = 33% (Wilson 95%: 6%–79%) | tỷ lệ gốc, không phải tín hiệu |

## 1. Dải giá 7 ngày và 30 ngày (thẻ Dự báo)

| Ngày gốc | Giá | Dải 7 ngày (8/10 lần) | Giá thật sau 7 ngày | Trúng | Dải 30 ngày | Giá thật sau 30 ngày | Trúng |
|---|---|---|---|---|---|---|---|
| 01/11/2024 | 69.484 $ | 65.412 $ – 75.064 $ | 76.507 $ | **không** | 59.277 $ – 83.928 $ | 97.470 $ | **không** |
| 01/12/2024 | 97.470 $ | 88.447 $ – 110.717 $ | 100.799 $ | có | 75.490 $ – 135.526 $ | 93.390 $ | có |
| 01/01/2025 | 94.456 $ | 87.880 $ – 102.845 $ | 95.039 $ | có | 78.471 $ – 118.034 $ | 102.263 $ | có |
| 01/02/2025 | 100.610 $ | 93.680 $ – 109.540 $ | 96.603 $ | có | 83.594 $ – 125.585 $ | 86.316 $ | có |
| 01/03/2025 | 85.844 $ | 80.174 $ – 92.769 $ | 86.171 $ | có | 72.173 $ – 105.524 $ | 82.461 $ | có |
| 01/04/2025 | 85.227 $ | 76.963 $ – 95.453 $ | 76.351 $ | **không** | 65.940 $ – 115.385 $ | 96.412 $ | có |
| 01/05/2025 | 96.412 $ | 87.853 $ – 107.226 $ | 103.070 $ | có | 76.544 $ – 128.105 $ | 104.709 $ | có |
| 01/06/2025 | 105.750 $ | 100.391 $ – 112.773 $ | 105.728 $ | có | 92.552 $ – 125.483 $ | 105.566 $ | có |
| 01/07/2025 | 105.566 $ | 100.425 $ – 112.361 $ | 108.957 $ | có | 92.826 $ – 124.512 $ | 115.848 $ | có |
| 01/08/2025 | 113.282 $ | 108.871 $ – 119.012 $ | 116.741 $ | có | 102.266 $ – 128.183 $ | 108.316 $ | có |
| 01/09/2025 | 108.992 $ | 102.915 $ – 116.672 $ | 112.112 $ | có | 94.579 $ – 129.362 $ | 118.393 $ | có |
| 01/10/2025 | 118.393 $ | 113.421 $ – 124.571 $ | 123.390 $ | có | 106.251 $ – 134.357 $ | 109.554 $ | có |
| 01/11/2025 | 110.005 $ | 102.871 $ – 118.868 $ | 102.335 $ | **không** | 93.766 $ – 132.587 $ | 86.505 $ | **không** |
| 01/12/2025 | 86.505 $ | 79.935 $ – 94.709 $ | 90.673 $ | có | 71.567 $ – 107.613 $ | 87.517 $ | có |
| 01/01/2026 | 88.684 $ | 84.662 $ – 93.731 $ | 91.097 $ | có | 79.122 $ – 101.337 $ | 78.702 $ | **không** |
| 01/02/2026 | 76.911 $ | 71.442 $ – 83.755 $ | 70.523 $ | **không** | 64.517 $ – 94.449 $ | 68.431 $ | có |
| 01/03/2026 | 65.734 $ | 57.449 $ – 76.173 $ | 66.203 $ | có | 46.607 $ – 94.643 $ | 68.215 $ | có |
| 01/04/2026 | 68.117 $ | 62.946 $ – 74.262 $ | 71.085 $ | có | 55.686 $ – 84.337 $ | 78.133 $ | có |
| 01/05/2026 | 78.133 $ | 73.291 $ – 84.091 $ | 80.180 $ | có | 66.943 $ – 93.366 $ | 73.600 $ | có |
| 01/06/2026 | 71.329 $ | 68.246 $ – 75.086 $ | 63.110 $ | **không** | 64.755 $ – 80.780 $ | 60.066 $ | **không** |
| 01/07/2026 | 60.066 $ | 55.803 $ – 65.367 $ | 62.214 $ | có | 50.292 $ – 73.731 $ | 62.875 $ | có |
| 01/08/2026 | 62.752 $ | 59.677 $ – 66.463 $ | 64.907 $ | có | 55.512 $ – 72.290 $ | 78.534 $ | **không** |
| 01/09/2026 | 77.408 $ | 72.291 $ – 84.224 $ | 78.446 $ | có | 65.081 $ – 96.296 $ | 84.777 $ | có |
| 01/10/2026 | 84.777 $ | 79.471 $ – 91.951 $ | 81.732 $ | có | 71.915 $ – 108.295 $ | 77.401 $ | có |

Trúng khoảng 8/10 lần: 7 ngày 19/24 = 79% (Wilson 95%: 60%–91%); 30 ngày 19/24 = 79% (Wilson 95%: 60%–91%). Mục tiêu khoảng 80%.

## 2. Khả năng chạm giá chờ mua −3% và giá chờ bán +3% trong 7 ngày (thẻ Giá & ngày mua / bán)

| Ngày gốc | Bot nói chạm −3% | Thật | Bot nói chạm +3% | Thật |
|---|---|---|---|---|
| 01/11/2024 | 51% | chạm | 52% | chạm |
| 01/12/2024 | 68% | chạm | 69% | chạm |
| 01/01/2025 | 58% | không chạm | 59% | chạm |
| 01/02/2025 | 57% | chạm | 59% | không chạm |
| 01/03/2025 | 55% | chạm | 54% | chạm |
| 01/04/2025 | 70% | chạm | 69% | chạm |
| 01/05/2025 | 66% | chạm | 65% | chạm |
| 01/06/2025 | 50% | chạm | 50% | không chạm |
| 01/07/2025 | 45% | không chạm | 46% | chạm |
| 01/08/2025 | 34% | không chạm | 36% | chạm |
| 01/09/2025 | 51% | không chạm | 51% | chạm |
| 01/10/2025 | 38% | không chạm | 39% | chạm |
| 01/11/2025 | 55% | chạm | 57% | không chạm |
| 01/12/2025 | 59% | không chạm | 61% | chạm |
| 01/01/2026 | 39% | không chạm | 41% | chạm |
| 01/02/2026 | 56% | chạm | 59% | chạm |
| 01/03/2026 | 75% | không chạm | 77% | chạm |
| 01/04/2026 | 60% | chạm | 61% | chạm |
| 01/05/2026 | 50% | không chạm | 52% | chạm |
| 01/06/2026 | 36% | chạm | 38% | không chạm |
| 01/07/2026 | 56% | không chạm | 60% | chạm |
| 01/08/2026 | 40% | không chạm | 43% | chạm |
| 01/09/2026 | 55% | không chạm | 60% | chạm |
| 01/10/2026 | 54% | chạm | 58% | không chạm |

Giá chờ mua −3%: bot nói trung bình 53%, thực tế chạm 12/24 = 50% (Wilson 95%: 31%–69%); sai số Brier 0,230.
Giá chờ bán +3%: bot nói trung bình 55%, thực tế chạm 19/24 = 79% (Wilson 95%: 60%–91%); sai số Brier 0,225.

## 3. Xác suất có lãi sau 4 và 13 tuần (thẻ Dự báo, Xác suất có lãi)

| Tuần (Chủ nhật trước ngày gốc) | Bot nói có lãi 4 tuần | Thật | Bot nói có lãi 13 tuần | Thật |
|---|---|---|---|---|
| 27/10/2024 | 55% | có lãi | 59% | có lãi |
| 24/11/2024 | 55% | có lãi | 59% | lỗ |
| 29/12/2024 | 55% | có lãi | 59% | lỗ |
| 26/01/2025 | 54% | lỗ | 59% | lỗ |
| 23/02/2025 | 53% | lỗ | 59% | có lãi |
| 30/03/2025 | 50% | có lãi | 56% | có lãi |
| 27/04/2025 | 50% | có lãi | 54% | có lãi |
| 25/05/2025 | 52% | lỗ | 54% | có lãi |
| 29/06/2025 | 54% | có lãi | 57% | có lãi |
| 27/07/2025 | 55% | lỗ | 59% | lỗ |
| 31/08/2025 | 53% | có lãi | 60% | lỗ |
| 28/09/2025 | 53% | lỗ | 60% | lỗ |
| 26/10/2025 | 53% | lỗ | 59% | lỗ |
| 30/11/2025 | 51% | có lãi | 56% | lỗ |
| 28/12/2025 | 52% | có lãi | 55% | lỗ |
| 25/01/2026 | 54% | lỗ | 55% | lỗ |
| 22/02/2026 | 53% | có lãi | 55% | có lãi |
| 29/03/2026 | 52% | có lãi | 55% | lỗ |
| 26/04/2026 | 53% | lỗ | 54% | lỗ |
| 31/05/2026 | 55% | lỗ | 55% | có lãi |
| 28/06/2026 | 54% | có lãi | 56% | có lãi |
| 26/07/2026 | 54% | có lãi | 56% | có lãi |
| 30/08/2026 | 54% | có lãi | 56% | — |
| 27/09/2026 | 56% | lỗ | 58% | — |
- 4 tuần: bot nói trung bình 53%, thực tế có lãi 14/24 = 58% (Wilson 95%: 39%–76%); Brier 0,249 (nói 50% mọi lần thì Brier 0,250).
- 13 tuần: bot nói trung bình 57%, thực tế có lãi 10/22 = 45% (Wilson 95%: 27%–65%); Brier 0,267 (nói 50% mọi lần thì Brier 0,250).

## 4. Long/Short: bot đề xuất gì mỗi tháng và lệnh thật ra sao

| Tháng | Phía | Công thức của tháng | Tiêu chí đạt lúc đó | Đề xuất vào lệnh? | Lệnh trong tháng | Thắng | Tổng R |
|---|---|---|---|---|---|---|---|
| 11/2024 | long | funding_nguoc · long · cho · 1.5 · 2 · 72 | 3/6 | không | 0 | 0 | — |
| 11/2024 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 12/2024 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 3 | 2 | −0,5R |
| 12/2024 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 01/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 4 | 1 | −1,3R |
| 01/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 02/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 1 | 0 | −1,0R |
| 02/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 03/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 4 | 1 | −2,0R |
| 03/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 04/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 4 | 3 | +0,9R |
| 04/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 05/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 4 | 3 | +1,3R |
| 05/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 06/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 5 | 3 | −1,2R |
| 06/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 07/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 4 | 2 | +1,9R |
| 07/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 08/2025 | long | xu_huong · long · ngay · 2 · 3 · 168 | 4/6 | không | 3 | 1 | −2,0R |
| 08/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 09/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 4 | 3 | +1,5R |
| 09/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 10/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 3 | 0 | −2,2R |
| 10/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 11/2025 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 1 | 0 | −1,0R |
| 11/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 12/2025 | long | pha_vo · long · ngay · 2 · 1.5 · 72 | 3/6 | không | 0 | 0 | — |
| 12/2025 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 01/2026 | long | pha_vo · long · ngay · 2 · 1.5 · 72 | 4/6 | không | 2 | 1 | +0,2R |
| 01/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 02/2026 | long | pha_vo · long · ngay · 2 · 1.5 · 72 | 3/6 | không | 0 | 0 | — |
| 02/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 03/2026 | long | pha_vo · long · ngay · 2 · 1.5 · 72 | 4/6 | không | 2 | 0 | −1,5R |
| 03/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 04/2026 | long | pha_vo · long · ngay · 2 · 1.5 · 72 | 4/6 | không | 4 | 1 | −0,7R |
| 04/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 05/2026 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 3 | 2 | −0,0R |
| 05/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 06/2026 | long | pha_vo · long · cho · 2 · 2 · 72 | 3/6 | không | 0 | 0 | — |
| 06/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 07/2026 | long | pha_vo · long · cho · 2 · 2 · 72 | 3/6 | không | 0 | 0 | — |
| 07/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 08/2026 | long | pha_vo · long · cho · 2 · 2 · 72 | 4/6 | không | 1 | 1 | +0,0R |
| 08/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 09/2026 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 5 | 3 | +1,6R |
| 09/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |
| 10/2026 | long | xu_huong · long · ngay · 2 · 2 · 168 | 4/6 | không | 2 | 0 | −2,1R |
| 10/2026 | short | đứng ngoài | 1/6 | không | 0 | 0 | — |

Tháng đạt đủ 6/6 (bot sẽ nói Nên long / Nên short): 0. Nếu đã vào lệnh theo công thức long của mọi tháng (bất chấp tiêu chí): 59 lệnh, thắng 27/59 = 46% (Wilson 95%: 34%–58%), tổng −8,1R. Tức là tiêu chí đã chặn đúng những tháng lẽ ra thua.

## 5. Xu hướng: hướng và khoảng giá sau 7, 30, 90 ngày (thẻ Xu hướng)

| Ngày gốc | 7 ngày: bot nói | thật | 30 ngày: bot nói | thật | 90 ngày: bot nói | thật |
|---|---|---|---|---|---|---|
| 01/11/2024 | không rõ (52%) | +10,1% | không rõ (54%) | +40,3% | nghiêng tăng (56%) | +51,1% |
| 01/12/2024 | không rõ (52%) | +3,4% | không rõ (54%) | −4,2% | nghiêng tăng (56%) | −11,9% |
| 01/01/2025 | không rõ (52%) | +0,6% | không rõ (54%) | +8,3% | nghiêng tăng (56%) | −9,8% |
| 01/02/2025 | không rõ (52%) | −4,0% | không rõ (53%) | −14,2% | nghiêng tăng (56%) | −3,7% |
| 01/03/2025 | không rõ (51%) | +0,4% | không rõ (52%) | −3,9% | nghiêng tăng (57%) | +21,1% |
| 01/04/2025 | không rõ (51%) | −10,4% | không rõ (51%) | +13,1% | nghiêng tăng (57%) | +25,7% |
| 01/05/2025 | không rõ (51%) | +6,9% | không rõ (52%) | +8,6% | nghiêng tăng (57%) | +22,1% |
| 01/06/2025 | không rõ (52%) | −0,0% | không rõ (54%) | −0,2% | nghiêng tăng (57%) | +2,8% |
| 01/07/2025 | không rõ (52%) | +3,2% | không rõ (54%) | +9,7% | nghiêng tăng (57%) | +8,3% |
| 01/08/2025 | không rõ (52%) | +3,1% | không rõ (54%) | −4,4% | nghiêng tăng (57%) | −4,6% |
| 01/09/2025 | không rõ (52%) | +2,9% | không rõ (54%) | +8,6% | nghiêng tăng (57%) | −16,9% |
| 01/10/2025 | không rõ (52%) | +4,2% | không rõ (53%) | −7,5% | nghiêng tăng (58%) | −25,3% |
| 01/11/2025 | không rõ (51%) | −7,0% | không rõ (53%) | −21,4% | nghiêng tăng (58%) | −23,6% |
| 01/12/2025 | không rõ (51%) | +4,8% | không rõ (53%) | +1,2% | nghiêng tăng (58%) | −24,0% |
| 01/01/2026 | không rõ (51%) | +2,7% | không rõ (53%) | −11,3% | nghiêng tăng (58%) | −23,2% |
| 01/02/2026 | không rõ (51%) | −8,3% | không rõ (53%) | −11,0% | nghiêng tăng (57%) | +2,3% |
| 01/03/2026 | không rõ (51%) | +0,7% | không rõ (52%) | +3,8% | nghiêng tăng (57%) | +12,2% |
| 01/04/2026 | không rõ (51%) | +4,4% | không rõ (53%) | +14,7% | nghiêng tăng (57%) | −14,1% |
| 01/05/2026 | không rõ (52%) | +2,6% | không rõ (54%) | −5,8% | nghiêng tăng (57%) | −17,0% |
| 01/06/2026 | không rõ (52%) | −11,5% | nghiêng tăng (56%) | −15,8% | nghiêng tăng (59%) | +8,9% |
| 01/07/2026 | không rõ (52%) | +3,6% | không rõ (55%) | +4,7% | nghiêng tăng (59%) | +39,3% |
| 01/08/2026 | không rõ (53%) | +3,4% | không rõ (55%) | +25,1% | nghiêng tăng (58%) | +22,9% |
| 01/09/2026 | không rõ (53%) | +1,3% | nghiêng tăng (57%) | +9,5% | nghiêng tăng (59%) | — |
| 01/10/2026 | không rõ (53%) | −3,6% | nghiêng tăng (58%) | −8,7% | nghiêng tăng (61%) | — |

- 7 ngày: khi bot nghiêng một phía, đúng chưa có kết quả; Brier 0,243 (nói 50% mọi lần thì 0,250); giá thật nằm trong khoảng 8/10 lần 19/24 = 79% (Wilson 95%: 60%–91%).
- 30 ngày: khi bot nghiêng một phía, đúng 1/3 = 33% (Wilson 95%: 6%–79%); Brier 0,254 (nói 50% mọi lần thì 0,250); giá thật nằm trong khoảng 8/10 lần 19/24 = 79% (Wilson 95%: 60%–91%).
- 90 ngày: khi bot nghiêng một phía, đúng 11/22 = 50% (Wilson 95%: 31%–69%); Brier 0,255 (nói 50% mọi lần thì 0,250); giá thật nằm trong khoảng 8/10 lần 17/22 = 77% (Wilson 95%: 57%–90%).

Công cụ tham khảo, không phải lời khuyên đầu tư.
