# Báo cáo dữ liệu (Phần A)

Bảng tuần theo **giá đóng cửa Chủ nhật**: 18/07/2010 → 25/10/2026, 850 tuần, thiếu giá đóng tuần: 0 tuần. Giá trực tiếp chỉ để hiển thị, không vào bảng này.

## 1. Mỗi chỉ số có từ khi nào

Phân vị trượt 4 năm (208 tuần) chỉ dùng dữ liệu quá khứ và cần tối thiểu 104 tuần, nên luôn có sau giá trị gốc khoảng 2 năm.

| Chỉ số | Có giá trị gốc từ | Có phân vị từ | Số tuần có phân vị | Tuần bị thiếu sau khi bắt đầu |
|---|---|---|---|---|
| mvrv | 18/07/2010 | 08/07/2012 | 747 | 0 |
| mvrv_z | 22/08/2010 | 12/08/2012 | 742 | 0 |
| pi_ratio | 03/07/2011 | 23/06/2013 | 697 | 0 |
| p_200wma | 18/05/2014 | 08/05/2016 | 547 | 0 |
| mayer | 06/02/2011 | 27/01/2013 | 718 | 0 |
| rsi_14w | 24/10/2010 | 14/10/2012 | 731 | 2 |
| puell | 15/05/2011 | 05/05/2013 | 704 | 0 |
| dd_ath | 18/07/2010 | 08/07/2012 | 747 | 0 |
| vol_rel | 15/05/2011 | 02/06/2013 | 700 | 4 |
| fng | 04/02/2018 | 02/02/2020 | 352 | 1 |
| rv30 | 15/08/2010 | 05/08/2012 | 743 | 0 |
| dev_ma20w | 05/12/2010 | 25/11/2012 | 727 | 0 |

## 2. Đối chiếu giá giữa các nguồn (cùng ngày = cùng giá đóng cửa ngày)

Nguồn chính: Coin Metrics `PriceUSD` (từ 18/07/2010). Đã đo: dòng ngày d của Coin Metrics khớp giá đóng cửa ngày d của sàn (lệch 1 ngày thì sai lệch trung vị tăng lên khoảng 1,5%).

| Nguồn so với Coin Metrics | Đoạn chồng lấn | Số ngày | Lệch trung vị | Lệch 99% | Lệch lớn nhất | Số ngày lệch > 2% |
|---|---|---|---|---|---|---|
| bitstamp | 18/08/2011 → 28/10/2026 | 5.551 | 0,14% | 9,56% | 76,80% | 242 |
| binance_spot | 17/08/2017 → 28/10/2026 | 3.360 | 0,13% | 2,73% | 10,80% | 65 |
| coingecko | 29/10/2025 → 28/10/2026 | 365 | 0,07% | 0,75% | 3,49% | 1 |

Theo giai đoạn:

| Nguồn | Giai đoạn | Số ngày | Lệch trung vị | Lệch 99% | Số ngày lệch > 2% |
|---|---|---|---|---|---|
| bitstamp | 2010–2013 | 867 | 0,85% | 26,93% | 209 |
| bitstamp | 2014–2016 | 1.096 | 0,23% | 1,85% | 10 |
| bitstamp | 2017–2020 | 1.461 | 0,14% | 2,26% | 20 |
| bitstamp | 2021–nay | 2.127 | 0,08% | 0,87% | 3 |
| binance_spot | 2017–2020 | 1.233 | 0,24% | 3,91% | 62 |
| binance_spot | 2021–nay | 2.127 | 0,10% | 0,92% | 3 |
| coingecko | 2021–nay | 365 | 0,07% | 0,75% | 1 |

Ngày lệch nhiều nhất:

- bitstamp: 19/10/2011 (2,22 $ so với 3,92 $, +76,8%); 18/10/2011 (2,42 $ so với 3,92 $, +61,8%); 10/09/2011 (4,74 $ so với 7,40 $, +56,0%)
- binance_spot: 23/12/2017 (14.910,86 $ so với 13.300,00 $, -10,8%); 22/12/2017 (14.305,72 $ so với 13.326,61 $, -6,8%); 04/09/2017 (4.374,75 $ so với 4.100,11 $, -6,3%)
- coingecko: 22/02/2026 (67.550,02 $ so với 65.192,19 $, -3,5%); 21/03/2026 (69.707,29 $ so với 68.424,08 $, -1,8%); 05/02/2026 (63.494,69 $ so với 62.778,22 $, -1,1%)

## 3. Trường của Coin Metrics bản community

| Trường | Có không | Dùng cho |
|---|---|---|
| `PriceUSD` | có | giá đóng cửa ngày |
| `CapMrktCurUSD` | có | vốn hóa, MVRV Z |
| `CapMVRVCur` | có | MVRV |
| `CapRealUSD` | **không có** | vốn hóa thực (thiếu → tính bằng vốn hóa / MVRV) |
| `IssTotUSD` | có | Puell |
| `IssTotNtv` | có | kiểm tra Puell |
| `SplyCur` | có | nguồn cung |
| `HashRate` | có | Hash Ribbon |
| `RevUSD` | **không có** | doanh thu thợ đào (thiếu → dùng phát hành) |
| `AssetEODCompletionTime` | có | giờ chốt số liệu (chỉ đúng cho dữ liệu gần đây) |
| `volume_reported_spot_usd_1d` | có | khối lượng tương đối, lịch sử dài |

Độ trễ công bố của Coin Metrics (365 ngày gần nhất): số liệu ngày d có sau 00:00 UTC ngày d khoảng **27 giờ** (trung vị), 90% trong 28 giờ, chậm nhất 42 giờ. Tín hiệu theo giá đóng Chủ nhật vì thế có vào sáng thứ Hai giờ Việt Nam. Giờ chốt của dữ liệu cũ đã bị tính lại về sau (trung vị hàng năm), nên không dùng làm thời điểm công bố lịch sử; bot dùng quy tắc trễ cố định 1 ngày.

## 4. Giá trị bất thường

Tuần giá đóng thay đổi hơn 5 độ lệch chuẩn (giữ nguyên, chỉ đánh dấu): 01/05/2011 (+90%), 05/06/2011 (+97%), 14/04/2013 (-45%).
Số tuần chỉ số nhảy hơn 5 độ lệch chuẩn: mvrv 1, mvrv_z 4, pi_ratio 3, p_200wma 6, mayer 10, rsi_14w 0, puell 6, dd_ath 3, vol_rel 3, fng 0, rv30 6, dev_ma20w 11.

## 5. Chế độ lãi suất Fed (chỉ để chia nhóm khi báo cáo, không đưa vào mô hình)

Theo thay đổi trần lãi suất Fed (FRED `DFEDTARU`) trong 26 tuần trước, chỉ dùng số liệu đến Chủ nhật đó: tăng, giữ hoặc giảm. Tính từ 2011.

| Chế độ | Số tuần | Số đợt |
|---|---|---|
| tăng | 260 | 4 |
| giữ | 430 | 7 |
| giảm | 136 | 3 |

Chế độ hiện tại: **tăng** (từ 20/09/2026). 

## 6. Fear & Greed và chỉ báo thay thế có lịch sử dài

Fear & Greed chỉ có từ 02/2018. Các chỉ báo thay thế tính được từ 2010: biến động thực 30 ngày (rv30), mức giảm từ đỉnh (dd_ath), độ lệch giá so với MA 20 tuần (dev_ma20w), RSI 14 tuần. Tương quan thứ hạng với Fear & Greed (phân vị 4 năm) trên các tuần cùng có số liệu:

| Chỉ báo | Số tuần chung | Tương quan thứ hạng |
|---|---|---|
| rv30 | 352 | -0,18 |
| dd_ath | 352 | 0,55 |
| dev_ma20w | 352 | 0,89 |
| rsi_14w | 352 | 0,78 |

## 7. Trạng thái từng nguồn ở lần tải gần nhất

| Nguồn | Kết quả | Đến ngày | Số dòng | Ghi chú |
|---|---|---|---|---|
| coinmetrics | tốt | 28/10/2026 | 5947 | price: 28 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 12/03/2020; mcap: 28 biến động lớn hơn 5σ (giữ nguyê |
| fng | tốt | 29/10/2026 | 3189 | 2 khoảng trống (lớn nhất 4 ngày): 13/04/2018→17/04/2018, 25/10/2024→27/10/2024; fng: 7 biến động lớn hơn 5σ (giữ nguyên, |
| binance_spot | tốt | 28/10/2026 | 3360 | close: 5 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 08/02/2021; quote_volume: 2 biến động lớn hơn 5σ (giữ |
| binance_funding | tốt | 29/10/2026 | 7818 | funding_rate: 44 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 10/11/2022 |
| binance_oi | tốt | 29/10/2026 | 30 |  |
| binance_basis | tốt | 28/10/2026 | 2280 | fut_close: 4 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 09/11/2022 |
| stablecoins | tốt | 29/10/2026 | 3257 | stable_usd: 4 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 31/07/2018 |
| fred_DTWEXBGS | tốt | 23/10/2026 | 5217 | 2 khoảng trống (lớn nhất 7 ngày): 05/02/2010→12/02/2010, 21/01/2016→27/01/2016; usd_broad: 14 biến động lớn hơn 5σ (giữ  |
| fred_DFII10 | tốt | 27/10/2026 | 5959 | real_yield_10y: 10 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 10/11/2022 |
| fred_NASDAQCOM | tốt | 27/10/2026 | 14050 | 1 khoảng trống (lớn nhất 7 ngày): 10/09/2001→17/09/2001; nasdaq: 43 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần |
| fred_M2SL | tốt | 01/09/2026 | 813 | m2: 3 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 01/05/2020 |
| coinmetrics_ext | tốt | 28/10/2026 | 5947 | volume_spot_usd: có giá trị ≤ 0; volume_spot_usd: 11 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 14/11/201 |
| bitstamp | tốt | 28/10/2026 | 5551 | close: 22 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 12/03/2020 |
| coingecko | tốt | 28/10/2026 | 365 | price: 1 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 05/02/2026 |
| fred_DFEDTARU | tốt | 28/10/2026 | 6526 | fed_upper: 14 biến động lớn hơn 5σ (giữ nguyên, chỉ đánh dấu), gần nhất 03/11/2022 |
