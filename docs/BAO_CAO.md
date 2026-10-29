# Báo cáo bot BTC (bản xây lại), phân tích tại ngày 25/10/2026

Bot thống kê, không có trí tuệ AI. Mọi con số tính từ dữ liệu thật tải về, bằng kiểm chứng đi tới: tại mỗi tuần chỉ dùng dữ liệu đã có đến tuần đó. Báo cáo tạo lúc 06:41 29/10/2026 UTC bằng `python -m bot.cli final-report`, từ các file kết quả trong `data/results`. Cách làm từng phần và mọi thay đổi thiết kế: [REBUILD_LOG.md](REBUILD_LOG.md). Bảng chi tiết: [PHU_LUC.md](PHU_LUC.md).

Mỗi con số về khung đi kèm số tuần, số đợt độc lập, khoảng tin cậy bootstrap (95%) và mức chênh so với mốc "mua vào một tuần bất kỳ". Kết quả không có ý nghĩa thống kê ghi "chưa có lợi thế".

## Bối cảnh
- Giá đóng tuần (Chủ nhật 23:59 UTC) ngày 25/10/2026: **80.039 $**. Mọi tính toán dùng giá đóng tuần; giá trực tiếp chỉ để hiển thị trên trang.
- Dữ liệu (ngày cuối của từng nguồn lúc tải, 13:03 29/10/2026): Coin Metrics (giá, vốn hóa, MVRV, hash rate, phát hành) đến 28/10/2026; Fear & Greed (Alternative.me) đến 29/10/2026; Binance (giá và khối lượng ngày) đến 28/10/2026; DefiLlama (tổng cung stablecoin) đến 29/10/2026; FRED (chỉ số đô la Mỹ rộng) đến 23/10/2026; FRED (lợi suất thực 10 năm) đến 27/10/2026; FRED (Nasdaq Composite) đến 28/10/2026; FRED (cung tiền M2) đến 01/09/2026; Coin Metrics (giờ chốt số liệu, khối lượng giao ngay, nguồn cung) đến 28/10/2026; Bitstamp (giá ngày từ 2011, để đối chiếu) đến 28/10/2026; CoinGecko (giá 365 ngày gần nhất, để đối chiếu) đến 28/10/2026; FRED (trần lãi suất Fed) đến 28/10/2026.
- Mô hình đang theo dõi: phiên bản `v1-f46ea015fc`, đóng băng ngày 25/10/2026: bộ S1, còn Giá / MA 200 tuần (bỏ MVRV vì sai dấu).
- Mốc so sánh bắt buộc: mua đều; quy tắc đơn giản 1 chỉ số (phân vị MVRV, phân vị Giá / MA 200 tuần).
- Giai đoạn chấm: đi tới lồng nhau (học lại mỗi 13 tuần) có thứ hạng từ 13/02/2022; holdout 01/01/2024 → 25/10/2026 (147 tuần), chạy đúng một lần lúc 2026-10-29T05:32:09Z (mã `af7ccea`).

## Kết luận
- **Mua đều, hệ số 1,0.** Mô hình đạt 0/6 tiêu chí chấp nhận định trước (cần đạt cả 6): lợi thế giá vốn dương ở ≥ 75% số năm và trên holdout ✘; cận dưới khoảng tin cậy của lợi thế > 0 ✘; kiểm định hoán vị đã hiệu chỉnh < 0,05 ✘; khung đơn điệu, trọng số đúng dấu ✘; Brier tốt hơn tỷ lệ gốc ✘; thắng cả hai quy tắc đơn giản ✘.
- Thứ hạng tuần này (vị trí của điểm tuần này so với các tuần ngoài mẫu trước đó, **không phải xác suất có lãi**): mô hình 76 → Cân nhắc mua; quy tắc MVRV 65 → Cân nhắc mua; quy tắc Giá / MA 200 tuần 70 → Cân nhắc mua. Các khung chỉ để tham khảo: kiểm định cho thấy **chưa có lợi thế** (mục "Bộ tiêu chí").
- Bên bán: 0 nhóm bật → **Giữ**. Số tiêu chí bán đáng tin: 0.

## Khuyến nghị giải ngân tuần này
- Hệ số mua: **1,0** (mua đều). Vì sao: tiêu chí chấp nhận không đạt, nên không có cơ sở mua nhiều hay ít hơn mua đều. Hệ số theo khung (chưa qua cổng) tuần này: 1,00: khung Cân nhắc mua có 9 tuần, 1 đợt, chênh +38,3%, chỉ 1 đợt (cần ≥ 3).
- ⚑ Sự kiện đã xảy ra sau mốc chốt dữ liệu (giá đóng 25/10/2026), tín hiệu chưa tính phản ứng của thị trường: 01:00 29/10/2026 (giờ Việt Nam) Quyết định lãi suất FOMC. Nên chạy lại sau giá đóng tuần kế tiếp (01/11/2026).
- Sự kiện sắp tới: 19:30 29/10/2026 Chỉ số giá chi tiêu PCE; 15:00 30/10/2026 Đáo hạn quyền chọn BTC hằng tháng; 20:30 04/11/2026 Chỉ số giá chi tiêu PCE.
- Lịch sự kiện chưa đủ: Chỉ số giá tiêu dùng Mỹ (CPI) chỉ có tới 14/10/2026.
- Chế độ lãi suất Fed: **tăng** (từ 20/09/2026). Chỉ dùng để chia nhóm báo cáo. Cảnh báo: chế độ này có dưới 3 đợt trong giai đoạn đánh giá của Bot hiện tại (PA3), Mô hình lồng nhau, Quy tắc Giá/MA 200 tuần.
- Giải ngân một khoản tiền (ô trên trang web, 486 tuần bắt đầu từ 10/07/2016, khoảng 9 đợt độc lập): ROI trung vị cao nhất là giải ngân một lần (+56% sau 1 năm); đề xuất giải ngân một lần (10% xấu nhất -45%, xấu nhất -82%). Chi tiết: [PLAN.md](PLAN.md).

## Giá đề xuất mua và bán (kịch bản giá sau 4 tuần, tính tại 25/10/2026, giá 80.039 $)
Mọi chỉ số tính lại theo đường giá giả định. Fear & Greed đổi theo giá bằng mô hình học từ quá khứ (R² 0,71, 450 tuần), kèm khoảng 10–90%. Khoảng của quy tắc MVRV tính thêm theo thay đổi vốn hóa thực (-0,7% đến +4,9% trong 4 tuần). Đây là cách bot sẽ đọc, không phải dự báo; hệ số mua vẫn 1,0.
| Giá | So với hiện tại | Fear & Greed (10–90%) | Quy tắc Giá / MA 200 tuần | Quy tắc MVRV (khoảng) | Bên bán (số nhóm) |
|---|---|---|---|---|---|
| 56.027 $ | -30% | 21 (7–35) | 95 → Phải mua | 99 (99) → Phải mua | 0 → Giữ |
| 64.031 $ | -20% | 31 (17–45) | 93 → Phải mua | 97 (96–99) → Phải mua | 0 → Giữ |
| 72.035 $ | -10% | 41 (27–54) | 83 → Phải mua | 82 (80–89) → Phải mua | 0 → Giữ |
| 76.037 $ | -5% | 45 (31–58) | 75 → Cân nhắc mua | 76 (76–80) → Phải mua / Cân nhắc mua | 0 → Giữ |
| 80.039 $ | hiện tại | 49 (35–62) | 72 → Cân nhắc mua | 67 (65–76) → Cân nhắc mua | 0 → Giữ |
| 84.041 $ | +5% | 53 (38–66) | 67 → Cân nhắc mua | 59 (58–65) → Cân nhắc mua | 0 → Giữ |
| 88.043 $ | +10% | 56 (42–70) | 62 → Cân nhắc mua | 53 (53–59) → Cân nhắc mua / Không nên mua | 0 → Giữ |
| 96.047 $ | +20% | 63 (49–76) | 56 → Cân nhắc mua | 50 (47–52) → Không nên mua | 0 → Giữ |
| 104.051 $ | +30% | 69 (55–82) | 52 → Không nên mua | 37 (37–46) → Không nên mua | 0–1 → Giữ / Chốt lời một phần |
| 120.058 $ | +50% | 80 (66–93) | 36 → Không nên mua | 16 (13–23) → Không nên mua | 3 → Bán phần lớn |

## Xác suất thắng nếu mua tại ngày phân tích
**Bot không hiển thị xác suất có lãi.** Xác suất của mô hình tốt hơn tỷ lệ gốc (Brier thấp hơn) ở 1/6 lần đo, và chỉ 0/6 lần có khoảng tin cậy của mức cải thiện nằm hẳn trên 0; cần cả hai mới được hiển thị xác suất.
| Mô hình | Giai đoạn | Kỳ hạn | Số tuần | Brier mô hình | Brier tỷ lệ gốc | Mức cải thiện (KTC 95%) |
|---|---|---|---|---|---|---|
| Bot hiện tại (PA3) | đến 31/12/2023 | 1 tháng | 223 | 0,270 | 0,254 | -0,016 (-0,050 đến 0,017) |
| Bot hiện tại (PA3) | đến 31/12/2023 | 3 tháng | 205 | 0,321 | 0,270 | -0,050 (-0,115 đến 0,007) |
| Bot hiện tại (PA3) | đến 31/12/2023 | 6 tháng | 179 | 0,390 | 0,303 | -0,088 (-0,246 đến 0,057) |
| Bot hiện tại (PA3) | đến 31/12/2023 | 1 năm | 127 | 0,367 | 0,413 | 0,046 (-0,103 đến 0,204) |
| Lồng nhau | đến 31/12/2023 | 6 tháng | 104 | 0,364 | 0,329 | -0,035 (-0,114 đến 0,032) |
| Lồng nhau | holdout | 6 tháng | 95 | 0,193 | 0,189 | -0,004 (-0,035 đến 0,031) |

Thay vào đó: tỷ lệ giá cao hơn sau mỗi kỳ hạn khi ở **khung của tuần này**, trên toàn bộ giai đoạn ngoài mẫu đến hết holdout, so với mọi tuần:
| Chiến lược | Khung tuần này | Kỳ hạn | Số tuần | Số đợt | Giá cao hơn | Mốc | Chênh (KTC 95%) | Kết luận |
|---|---|---|---|---|---|---|---|---|
| Lồng nhau | Cân nhắc mua | 1 tháng | 15 | 2 | 73% | 54% | +19,1% (-17,8% đến +47,5%) | ít đợt (< 3), chưa kết luận |
| Lồng nhau | Cân nhắc mua | 3 tháng | 9 | 1 | 100% | 57% | +43,5% (+26,2% đến +61,3%) | ít đợt (< 3), chưa kết luận |
| Lồng nhau | Cân nhắc mua | 6 tháng | 9 | 1 | 100% | 70% | +29,7% (+8,4% đến +48,4%) | ít đợt (< 3), chưa kết luận |
| Lồng nhau | Cân nhắc mua | 1 năm | 9 | 1 | 100% | 62% | +37,8% (+5,6% đến +68,5%) | ít đợt (< 3), chưa kết luận |
| Quy tắc MVRV | Cân nhắc mua | 1 tháng | 125 | 18 | 51% | 57% | -5,8% (-17,2% đến +6,3%) | chưa có lợi thế |
| Quy tắc MVRV | Cân nhắc mua | 3 tháng | 119 | 17 | 43% | 57% | -13,9% (-29,7% đến +1,0%) | chưa có lợi thế |
| Quy tắc MVRV | Cân nhắc mua | 6 tháng | 114 | 17 | 49% | 62% | -12,6% (-37,7% đến +8,3%) | chưa có lợi thế |
| Quy tắc MVRV | Cân nhắc mua | 1 năm | 100 | 15 | 86% | 68% | +18,2% (-0,1% đến +33,7%) | chưa có lợi thế |
| Quy tắc Giá/MA 200 tuần | Cân nhắc mua | 1 tháng | 122 | 11 | 53% | 56% | -2,3% (-13,1% đến +8,9%) | chưa có lợi thế |
| Quy tắc Giá/MA 200 tuần | Cân nhắc mua | 3 tháng | 116 | 10 | 53% | 55% | -2,4% (-17,4% đến +13,1%) | chưa có lợi thế |
| Quy tắc Giá/MA 200 tuần | Cân nhắc mua | 6 tháng | 108 | 10 | 55% | 60% | -5,1% (-25,8% đến +12,1%) | chưa có lợi thế |
| Quy tắc Giá/MA 200 tuần | Cân nhắc mua | 1 năm | 91 | 9 | 59% | 65% | -5,9% (-31,5% đến +19,4%) | chưa có lợi thế |

## Bộ tiêu chí: tỷ lệ thắng thực tế theo từng khung mua
Khung theo thứ hạng ngoài mẫu (Phải mua từ 80, Cân nhắc mua từ 60, vùng trễ 5 điểm), giá vào và ra là giá đóng thứ Hai. Toàn bộ giai đoạn ngoài mẫu đến hết holdout.

**Lồng nhau** (từ 13/02/2022, 181 tuần có thứ hạng). Đơn điệu: 1 tháng không, 3 tháng không, 6 tháng không, 1 năm không.
| Kỳ hạn | Khung | Số tuần | Số đợt | Giá cao hơn | Mốc (mọi tuần) | Chênh (KTC 95%) | Wilson theo đợt | Kết luận |
|---|---|---|---|---|---|---|---|---|
| 1 tháng | Phải mua | 54 | 2 | 46% | 54% | -7,9% (-23,2% đến +6,3%) | 0%–66% | ít đợt (< 3), chưa kết luận |
| 1 tháng | Cân nhắc mua | 15 | 2 | 73% | 54% | +19,1% (-17,8% đến +47,5%) | 9%–91% | ít đợt (< 3), chưa kết luận |
| 1 tháng | Không nên mua | 108 | 3 | 56% | 54% | +1,3% (-6,3% đến +9,5%) | 21%–94% | chưa có lợi thế |
| 3 tháng | Phải mua | 51 | 2 | 29% | 57% | -27,1% (-58,2% đến -6,3%) | 9%–91% | ít đợt (< 3), chưa kết luận |
| 3 tháng | Cân nhắc mua | 9 | 1 | 100% | 57% | +43,5% (+26,2% đến +61,3%) | 21%–100% | ít đợt (< 3), chưa kết luận |
| 3 tháng | Không nên mua | 108 | 3 | 66% | 57% | +9,2% (-2,8% đến +24,0%) | 21%–94% | chưa có lợi thế |
| 6 tháng | Phải mua | 38 | 2 | 29% | 70% | -41,4% (-78,8% đến -5,9%) | 0%–66% | ít đợt (< 3), chưa kết luận |
| 6 tháng | Cân nhắc mua | 9 | 1 | 100% | 70% | +29,7% (+8,4% đến +48,4%) | 21%–100% | ít đợt (< 3), chưa kết luận |
| 6 tháng | Không nên mua | 108 | 3 | 82% | 70% | +12,1% (-1,6% đến +31,0%) | 21%–94% | chưa có lợi thế |
| 1 năm | Phải mua | 26 | 1 | 35% | 62% | -27,6% (-66,9% đến +16,8%) | 0%–79% | ít đợt (< 3), chưa kết luận |
| 1 năm | Cân nhắc mua | 9 | 1 | 100% | 62% | +37,8% (+5,6% đến +68,5%) | 21%–100% | ít đợt (< 3), chưa kết luận |
| 1 năm | Không nên mua | 108 | 3 | 66% | 62% | +3,5% (-7,2% đến +16,0%) | 44%–100% | chưa có lợi thế |

**Quy tắc MVRV** (từ 07/07/2013, 695 tuần có thứ hạng). Đơn điệu: 1 tháng không, 3 tháng không, 6 tháng không, 1 năm không.
| Kỳ hạn | Khung | Số tuần | Số đợt | Giá cao hơn | Mốc (mọi tuần) | Chênh (KTC 95%) | Wilson theo đợt | Kết luận |
|---|---|---|---|---|---|---|---|---|
| 1 tháng | Phải mua | 183 | 9 | 58% | 57% | +0,9% (-8,5% đến +10,8%) | 27%–81% | chưa có lợi thế |
| 1 tháng | Cân nhắc mua | 125 | 18 | 51% | 57% | -5,8% (-17,2% đến +6,3%) | 44%–84% | chưa có lợi thế |
| 1 tháng | Không nên mua | 383 | 10 | 58% | 57% | +1,5% (-3,9% đến +6,3%) | 24%–76% | chưa có lợi thế |
| 3 tháng | Phải mua | 180 | 9 | 54% | 57% | -2,3% (-18,7% đến +15,9%) | 35%–88% | chưa có lợi thế |
| 3 tháng | Cân nhắc mua | 119 | 17 | 43% | 57% | -13,9% (-29,7% đến +1,0%) | 22%–64% | chưa có lợi thế |
| 3 tháng | Không nên mua | 383 | 10 | 62% | 57% | +5,4% (-2,3% đến +13,3%) | 31%–83% | chưa có lợi thế |
| 6 tháng | Phải mua | 172 | 8 | 61% | 62% | -0,7% (-23,2% đến +25,9%) | 31%–86% | chưa có lợi thế |
| 6 tháng | Cân nhắc mua | 114 | 17 | 49% | 62% | -12,6% (-37,7% đến +8,3%) | 31%–74% | chưa có lợi thế |
| 6 tháng | Không nên mua | 383 | 10 | 66% | 62% | +4,1% (-6,2% đến +13,9%) | 40%–89% | chưa có lợi thế |
| 1 năm | Phải mua | 162 | 7 | 74% | 68% | +6,3% (-14,9% đến +30,9%) | 36%–92% | chưa có lợi thế |
| 1 năm | Cân nhắc mua | 100 | 15 | 86% | 68% | +18,2% (-0,1% đến +33,7%) | 48%–89% | chưa có lợi thế |
| 1 năm | Không nên mua | 381 | 10 | 60% | 68% | -7,4% (-19,2% đến +3,3%) | 60%–98% | chưa có lợi thế |

**Quy tắc Giá/MA 200 tuần** (từ 07/05/2017, 495 tuần có thứ hạng). Đơn điệu: 1 tháng không, 3 tháng không, 6 tháng không, 1 năm không.
| Kỳ hạn | Khung | Số tuần | Số đợt | Giá cao hơn | Mốc (mọi tuần) | Chênh (KTC 95%) | Wilson theo đợt | Kết luận |
|---|---|---|---|---|---|---|---|---|
| 1 tháng | Phải mua | 165 | 5 | 58% | 56% | +2,6% (-6,6% đến +11,8%) | 38%–96% | chưa có lợi thế |
| 1 tháng | Cân nhắc mua | 122 | 11 | 53% | 56% | -2,3% (-13,1% đến +8,9%) | 43%–90% | chưa có lợi thế |
| 1 tháng | Không nên mua | 204 | 5 | 55% | 56% | -0,7% (-8,8% đến +7,2%) | 38%–96% | chưa có lợi thế |
| 3 tháng | Phải mua | 162 | 5 | 56% | 55% | +1,2% (-12,5% đến +16,5%) | 12%–77% | chưa có lợi thế |
| 3 tháng | Cân nhắc mua | 116 | 10 | 53% | 55% | -2,4% (-17,4% đến +13,1%) | 31%–83% | chưa có lợi thế |
| 3 tháng | Không nên mua | 204 | 5 | 55% | 55% | +0,4% (-11,9% đến +11,9%) | 38%–96% | chưa có lợi thế |
| 6 tháng | Phải mua | 157 | 4 | 65% | 60% | +5,3% (-13,5% đến +21,5%) | 5%–70% | chưa có lợi thế |
| 6 tháng | Cân nhắc mua | 108 | 10 | 55% | 60% | -5,1% (-25,8% đến +12,1%) | 17%–69% | chưa có lợi thế |
| 6 tháng | Không nên mua | 204 | 5 | 58% | 60% | -1,4% (-17,2% đến +11,1%) | 23%–88% | chưa có lợi thế |
| 1 năm | Phải mua | 157 | 4 | 96% | 65% | +30,3% (+13,7% đến +46,4%) | 15%–85% | hơn mốc |
| 1 năm | Cân nhắc mua | 91 | 9 | 59% | 65% | -5,9% (-31,5% đến +19,4%) | 35%–88% | chưa có lợi thế |
| 1 năm | Không nên mua | 195 | 5 | 44% | 65% | -21,6% (-46,9% đến -6,3%) | 23%–88% | **kém mốc** |

**Bot hiện tại (PA3, khung 80/60 không vùng trễ)**, 179 tuần từ 02/08/2020 đến 31/12/2023 (Phần B, trước holdout).
| Kỳ hạn | Khung | Số tuần | Số đợt | Giá cao hơn | Mốc (mọi tuần) | Chênh (KTC 95%) | Wilson theo đợt | Kết luận |
|---|---|---|---|---|---|---|---|---|
| 1 tháng | Phải mua | 70 | 1 | 53% | 56% | -3,1% (-17,2% đến +10,6%) | 0%–79% | ít đợt (< 3), chưa kết luận |
| 1 tháng | Cân nhắc mua | 7 | 2 | 71% | 56% | +15,4% (-56,0% đến +48,6%) | 9%–91% | ít đợt (< 3), chưa kết luận |
| 1 tháng | Không nên mua | 98 | 2 | 57% | 56% | +1,1% (-8,9% đến +11,8%) | 34%–100% | ít đợt (< 3), chưa kết luận |
| 3 tháng | Phải mua | 69 | 1 | 61% | 56% | +4,8% (-21,6% đến +28,0%) | 0%–79% | ít đợt (< 3), chưa kết luận |
| 3 tháng | Cân nhắc mua | 3 | 2 | 33% | 56% | -22,7% (-60,8% đến +45,6%) | 9%–91% | ít đợt (< 3), chưa kết luận |
| 3 tháng | Không nên mua | 94 | 1 | 53% | 56% | -2,8% (-21,6% đến +13,2%) | 21%–100% | ít đợt (< 3), chưa kết luận |
| 6 tháng | Phải mua | 57 | 1 | 74% | 55% | +18,8% (-8,0% đến +45,7%) | 0%–79% | ít đợt (< 3), chưa kết luận |
| 6 tháng | Cân nhắc mua | 2 | 1 | 0% | 55% | -54,9% (-75,8% đến -23,1%) | 0%–79% | ít đợt (< 3), chưa kết luận |
| 6 tháng | Không nên mua | 94 | 1 | 45% | 55% | -10,2% (-36,5% đến +2,9%) | 21%–100% | ít đợt (< 3), chưa kết luận |
| 1 năm | Phải mua | 31 | 1 | 97% | 45% | +51,9% (+15,0% đến +76,5%) | 0%–79% | ít đợt (< 3), chưa kết luận |
| 1 năm | Cân nhắc mua | 2 | 1 | 0% | 45% | -44,9% (-78,0% đến -11,8%) | 0%–79% | ít đợt (< 3), chưa kết luận |
| 1 năm | Không nên mua | 94 | 1 | 29% | 45% | -16,2% (-35,4% đến 0,0%) | 21%–100% | ít đợt (< 3), chưa kết luận |

## Khung bán: giá có giảm thật không
Tiêu chí bật khi chỉ số thuộc 5% đắt nhất của 4 năm trước; đúng nếu giá 26 tuần sau thấp hơn. Chấm theo đợt; chu kỳ: 09/07/2016 → 10/05/2020; 11/05/2020 → 19/04/2024; 20/04/2024 → 25/10/2026. "Đáng tin" khi đúng hơn mốc ở cả hai chu kỳ gần nhất.
| Tiêu chí | Số đợt | Đúng / đã biết | Wilson theo đợt | Mốc (giá thấp hơn) | Chênh (KTC 95%) | Theo chu kỳ: đúng/đợt | Đáng tin? |
|---|---|---|---|---|---|---|---|
| MVRV | 4 | 0/4 | 0%–49% | 34% | +15,6% (-32,5% đến +51,8%) | 2016–2020: 0/3; 2020–2024: 0/1; 2024–2026: 0/0 | không |
| MVRV Z-Score | 7 | 3/7 | 16%–75% | 34% | +9,0% (-20,3% đến +58,5%) | 2016–2020: 0/3; 2020–2024: 1/2; 2024–2026: 0/0 | không |
| Pi Cycle (tỉ số MA 111/2×MA 350) | 1 | 1/1 | 21%–100% | 34% | +49,0% (+27,2% đến +70,8%) | 2016–2020: 1/1; 2020–2024: 0/0; 2024–2026: 0/0 | không |
| Mayer Multiple | 4 | 2/4 | 15%–85% | 34% | +52,3% (+15,0% đến +71,3%) | 2016–2020: 1/2; 2020–2024: 0/1; 2024–2026: 0/0 | không |
| Giá / MA 200 tuần | 2 | 0/2 | 0%–66% | 34% | -1,0% (-39,4% đến +61,7%) | 2016–2020: 0/2; 2020–2024: 0/0; 2024–2026: 0/0 | không |
| RSI 14 tuần | 9 | 3/9 | 12%–65% | 34% | -8,6% (-27,1% đến +11,8%) | 2016–2020: 1/3; 2020–2024: 1/3; 2024–2026: 1/2 | không |
| Puell Multiple | 3 | 2/3 | 21%–94% | 34% | +42,6% (+13,8% đến +75,0%) | 2016–2020: 0/1; 2020–2024: 1/1; 2024–2026: 0/0 | không |
| Fear & Greed | 4 | 1/4 | 5%–70% | 34% | -19,4% (-43,8% đến +14,3%) | 2016–2020: 0/0; 2020–2024: 1/3; 2024–2026: 0/1 | không |
| Độ lệch so với MA 20 tuần | 6 | 3/6 | 19%–81% | 34% | +45,6% (+19,5% đến +67,0%) | 2016–2020: 1/3; 2020–2024: 0/1; 2024–2026: 0/0 | không |
| ≥1 nhóm | 12 | 3/12 | 9%–53% | 34% | -4,6% (-20,3% đến +11,1%) | 2016–2020: 0/4; 2020–2024: 1/4; 2024–2026: 1/2 | không |
| ≥3 nhóm | 4 | 1/4 | 5%–70% | 34% | +34,1% (-7,6% đến +65,3%) | 2016–2020: 0/2; 2020–2024: 0/1; 2024–2026: 0/0 | không |

## So sánh các phương án (so với mua đều, cùng tiền nạp mỗi tuần)
Lợi thế giá vốn = tài sản cuối kỳ so với mua đều, tiền chưa dùng tính theo giá cuối. Khoảng tin cậy bằng bootstrap khối dừng (khối 26 tuần).
| Phương án | Giai đoạn | Số tuần | Hệ số | Lợi thế giá vốn (KTC 95%) | Tuần hệ số ≠ 1 | Kết luận |
|---|---|---|---|---|---|---|
| Bot hiện tại (PA3), hệ số theo khung 1,50 / 1,25 / 0,50 | 02/08/2020 → 31/12/2023 | 179 | theo khung | +2,5% (-35,6% đến +33,4%) | — | chưa có lợi thế |
| Lồng nhau | holdout | 147 | Phần D (sẽ dùng nếu đạt) | 0,0% (0,0% đến 0,0%) | 0% | chưa có lợi thế |
| Lồng nhau | holdout | 147 | so sánh 0,5 + thứ hạng | -0,3% (-11,3% đến +6,0%) | 82% | chưa có lợi thế |
| Quy tắc MVRV | holdout | 147 | Phần D (sẽ dùng nếu đạt) | 0,0% (0,0% đến 0,0%) | 0% | chưa có lợi thế |
| Quy tắc MVRV | holdout | 147 | so sánh 0,5 + thứ hạng | +0,8% (-12,8% đến +7,7%) | 100% | chưa có lợi thế |
| Quy tắc Giá/MA 200 tuần | holdout | 147 | Phần D (sẽ dùng nếu đạt) | 0,0% (0,0% đến 0,0%) | 0% | chưa có lợi thế |
| Quy tắc Giá/MA 200 tuần | holdout | 147 | so sánh 0,5 + thứ hạng | +2,7% (-5,5% đến +6,7%) | 99% | chưa có lợi thế |

Theo năm dương lịch trước holdout (hệ số so sánh): Lồng nhau: 2022 +1,2%, 2023 -3,5%; Quy tắc MVRV: 2013 -8,7%, 2014 +0,5%, 2015 0,0%, 2016 -5,6%, 2017 -38,7%, 2018 +2,0%, 2019 +1,9%, 2020 -3,4%, 2021 -2,0%, 2022 +0,2%, 2023 -0,3%; Quy tắc Giá/MA 200 tuần: 2017 -31,5%, 2018 +0,8%, 2019 0,0%, 2020 0,0%, 2021 +0,6%, 2022 0,0%, 2023 0,0%.

## Bộ chỉ số có tỷ lệ thắng cao nhất
8 bộ chỉ số đăng ký trước (mỗi bộ có lý do kinh tế, xem phụ lục) × 3 mức λ, cộng mô hình lồng nhau và 2 quy tắc. Kiểm định hoán vị: dịch vòng ≥ 52 tuần, 1000 lần, hiệu chỉnh max-statistic trên mọi cấu hình. Thống kê: IC 26 tuần và lợi thế giá vốn theo hệ số so sánh.
| Cấu hình | Đến 2023: tuần, IC 26 tuần, lợi thế (KTC), p hiệu chỉnh | Holdout: IC 26 tuần, lợi thế, p hiệu chỉnh |
|---|---|---|
| Lồng nhau | 59 tuần, IC -0,11, -8,6% (-16,3% đến +3,4%), p 1,000 | IC 0,17 (p 1,000), lợi thế -0,3% (p 1,000) |
| S1/λ0.3 | 191 tuần, IC -0,03, -4,0% (-22,3% đến +4,9%), p 1,000 | IC 0,30 (p 1,000), lợi thế +1,0% (p 0,762) |
| S1/λ1 | 191 tuần, IC -0,04, -4,1% (-22,3% đến +4,9%), p 1,000 | IC 0,30 (p 1,000), lợi thế +1,0% (p 0,762) |
| S1/λ3 | 191 tuần, IC -0,04, -4,1% (-22,5% đến +4,9%), p 1,000 | IC 0,30 (p 1,000), lợi thế +1,0% (p 0,762) |
| S2/λ0.3 | 172 tuần, IC -0,44, -1,3% (-5,0% đến +0,9%), p 1,000 | IC -0,41 (p 1,000), lợi thế -0,5% (p 1,000) |
| S2/λ1 | 172 tuần, IC -0,44, -1,3% (-5,1% đến +1,0%), p 1,000 | IC -0,41 (p 1,000), lợi thế -0,5% (p 1,000) |
| S2/λ3 | 172 tuần, IC -0,44, -1,4% (-5,2% đến +1,0%), p 1,000 | IC -0,41 (p 1,000), lợi thế -0,5% (p 1,000) |
| S3/λ0.3 | 114 tuần, IC -0,35, -6,1% (-12,1% đến +8,7%), p 1,000 | IC -0,38 (p 1,000), lợi thế -1,5% (p 1,000) |
| S3/λ1 | 114 tuần, IC -0,35, -6,1% (-12,1% đến +8,8%), p 1,000 | IC -0,38 (p 1,000), lợi thế -1,5% (p 1,000) |
| S3/λ3 | 114 tuần, IC -0,35, -6,2% (-12,1% đến +8,8%), p 1,000 | IC -0,39 (p 1,000), lợi thế -1,5% (p 1,000) |
| S4/λ0.3 | dưới 60 tuần ngoài mẫu | IC -0,54 (p 1,000), lợi thế 0,0% (p 1,000) |
| S4/λ1 | dưới 60 tuần ngoài mẫu | IC -0,54 (p 1,000), lợi thế 0,0% (p 1,000) |
| S4/λ3 | dưới 60 tuần ngoài mẫu | IC -0,54 (p 1,000), lợi thế 0,0% (p 1,000) |
| S5/λ0.3 | dưới 60 tuần ngoài mẫu | IC -0,27 (p 1,000), lợi thế -2,7% (p 1,000) |
| S5/λ1 | dưới 60 tuần ngoài mẫu | IC -0,27 (p 1,000), lợi thế -2,7% (p 1,000) |
| S5/λ3 | dưới 60 tuần ngoài mẫu | IC -0,27 (p 1,000), lợi thế -2,8% (p 1,000) |
| S6/λ0.3 | 191 tuần, IC -0,03, -4,0% (-22,3% đến +4,9%), p 1,000 | IC 0,30 (p 1,000), lợi thế +1,0% (p 0,762) |
| S6/λ1 | 191 tuần, IC -0,04, -4,1% (-22,3% đến +4,9%), p 1,000 | IC 0,30 (p 1,000), lợi thế +1,0% (p 0,762) |
| S6/λ3 | 191 tuần, IC -0,04, -4,1% (-22,5% đến +4,9%), p 1,000 | IC 0,30 (p 1,000), lợi thế +1,0% (p 0,762) |
| S7/λ0.3 | 166 tuần, IC -0,42, -0,7% (-10,1% đến +0,7%), p 1,000 | IC -0,43 (p 1,000), lợi thế -0,3% (p 1,000) |
| S7/λ1 | 166 tuần, IC -0,42, -0,7% (-10,1% đến +0,7%), p 1,000 | IC -0,43 (p 1,000), lợi thế -0,3% (p 1,000) |
| S7/λ3 | 166 tuần, IC -0,43, -0,7% (-10,1% đến +0,7%), p 1,000 | IC -0,43 (p 1,000), lợi thế -0,3% (p 1,000) |
| S8/λ0.3 | dưới 60 tuần ngoài mẫu | IC -0,27 (p 1,000), lợi thế -2,7% (p 1,000) |
| S8/λ1 | dưới 60 tuần ngoài mẫu | IC -0,27 (p 1,000), lợi thế -2,7% (p 1,000) |
| S8/λ3 | dưới 60 tuần ngoài mẫu | IC -0,27 (p 1,000), lợi thế -2,8% (p 1,000) |
| Quy tắc Giá/MA 200 tuần | 347 tuần, IC 0,28, -3,7% (-9,8% đến +1,3%), p 1,000 | IC 0,50 (p 0,904), lợi thế +2,7% (p 0,001) |
| Quy tắc MVRV | 547 tuần, IC -0,05, -6,1% (-25,9% đến +3,3%), p 1,000 | IC 0,15 (p 1,000), lợi thế +0,8% (p 1,000) |

Cấu hình có p hiệu chỉnh < 0,05 trên holdout: Quy tắc Giá/MA 200 tuần (chỉ ở một thống kê; khoảng tin cậy bootstrap của lợi thế vẫn chứa 0 và khung không đơn điệu, nên không qua tiêu chí). Vòng trong của mô hình lồng nhau chọn: S1/λ0.3 168 tuần, S2/λ0.3 13 tuần, S2/λ3 13 tuần, S3/λ0.3 13 tuần; 286/519 tuần không có cấu hình nào tốt hơn tỷ lệ gốc (mua đều).

## Bên bán: nên giữ hay chốt lời (ngày 25/10/2026)
- Mức hiện tại: **Giữ** (0 nhóm bật). Một hệ thống: 0 nhóm → Giữ, 1–2 → Chốt lời một phần, ≥ 3 → Bán phần lớn.
- Quy tắc bán X% một lần khi đợt tín hiệu bắt đầu, mua lại khi giá ≤ 80% giá bán hoặc sau 52 tuần, so với giữ nguyên:
| Quy tắc | Chu kỳ | Tài sản so với giữ nguyên | Số lần bán | Mua lại rẻ hơn / đã mua lại |
|---|---|---|---|---|
| Bán 10% khi ≥ 1 nhóm | 2016–2020 | -16,2% | 4 | 0 / 4 |
| Bán 10% khi ≥ 1 nhóm | 2020–2024 | -5,8% | 4 | 0 / 2 |
| Bán 10% khi ≥ 1 nhóm | 2024–2026 | +1,4% | 2 | 1 / 2 |
| Bán 20% khi ≥ 1 nhóm | 2016–2020 | -29,5% | 4 | 0 / 4 |
| Bán 20% khi ≥ 1 nhóm | 2020–2024 | -11,4% | 4 | 0 / 2 |
| Bán 20% khi ≥ 1 nhóm | 2024–2026 | +2,6% | 2 | 1 / 2 |
| Bán 30% khi ≥ 1 nhóm | 2016–2020 | -40,3% | 4 | 0 / 4 |
| Bán 30% khi ≥ 1 nhóm | 2020–2024 | -16,8% | 4 | 0 / 2 |
| Bán 30% khi ≥ 1 nhóm | 2024–2026 | +3,6% | 2 | 1 / 2 |
| Bán 10% khi ≥ 3 nhóm | 2016–2020 | +0,6% | 2 | 1 / 2 |
| Bán 10% khi ≥ 3 nhóm | 2020–2024 | -1,1% | 1 | 0 / 1 |
| Bán 10% khi ≥ 3 nhóm | 2024–2026 | 0,0% | 0 | 0 / 0 |
| Bán 20% khi ≥ 3 nhóm | 2016–2020 | +1,2% | 2 | 1 / 2 |
| Bán 20% khi ≥ 3 nhóm | 2020–2024 | -2,2% | 1 | 0 / 1 |
| Bán 20% khi ≥ 3 nhóm | 2024–2026 | 0,0% | 0 | 0 / 0 |
| Bán 30% khi ≥ 3 nhóm | 2016–2020 | +1,7% | 2 | 1 / 2 |
| Bán 30% khi ≥ 3 nhóm | 2020–2024 | -3,3% | 1 | 0 / 1 |
| Bán 30% khi ≥ 3 nhóm | 2024–2026 | 0,0% | 0 | 0 / 0 |

- Kết luận: bên bán **chưa có lợi thế đáng tin**; mức Giữ / Chốt lời một phần / Bán phần lớn chỉ để tham khảo, không khuyên tỷ lệ bán.

## Giá trị chỉ số tại ngày phân tích (25/10/2026)
| Chỉ số | Giá trị | Phân vị trong 4 năm trước | Thuộc 5% đắt nhất? |
|---|---|---|---|
| MVRV | 1,48 | 38% | không |
| MVRV Z-Score | 0,84 | 40% | không |
| Pi Cycle (tỉ số MA 111/2×MA 350) | 0,49 | 29% | không |
| Giá / MA 200 tuần | 1,19 | 34% | không |
| Mayer Multiple | 1,10 | 48% | không |
| RSI 14 tuần | 68 | 68% | không |
| Puell Multiple | 1,12 | 55% | không |
| Giảm từ đỉnh | -35,9% | 46% | không |
| Khối lượng tương đối | 0,70 | 26% | không |
| Fear & Greed | 54 | 54% | không |
| Biến động 30 ngày | 0,25 | 5% | không |
| Độ lệch so với MA 20 tuần | +11,4% | 58% | không |

## Khối lượng giao dịch
- Khối lượng giao dịch giao ngay tương đối (so với trung bình gần đây) tại 25/10/2026: 0,70, phân vị 4 năm 26%. Không dùng trong mô hình (không có trong bộ nào được đăng ký).

## Kiểm định đi tới
- Nhật ký `data/forward/v1-f46ea015fc/forward_log.csv`: 1 tuần từ 25/10/2026 đến 25/10/2026, 0 tuần ghi muộn. Đủ kỳ hạn để chấm: 26 tuần: 0, 52 tuần: 0.
- Đây là phép thử ngoài mẫu thật duy nhất (holdout đã có người xem khi làm bot cũ). Chấm lại sau 26 và 52 tuần; không sửa mô hình trong thời gian theo dõi.

## Câu hỏi gợi ý cho Claude
- Vì sao bot khuyên mua đều dù khung tuần này là "Cân nhắc mua"?
- Nếu giá giảm 20% trong 4 tuần tới, bot sẽ đọc thế nào và vì sao hệ số vẫn là 1,0?
- Giải ngân một lần và chia đều 26 tuần khác nhau thế nào về rủi ro?
- Khi nào nhật ký đi tới đủ dữ liệu để kết luận?

## Giới hạn: những gì báo cáo này không thể biết
- **Ít chu kỳ, ít đợt độc lập.** BTC mới qua khoảng 3–4 chu kỳ giảm một nửa. Hầu hết khung có dưới 10 đợt, nhiều ô chỉ 1–2 đợt; khoảng tin cậy rộng là đúng bản chất, không phải lỗi.
- **Holdout không hoàn toàn mù.** Dữ liệu từ 01/01/2024 đã được người xem khi làm bot cũ. Holdout có 147 tuần; với độ dịch ≥ 52 tuần, kiểm định hoán vị chỉ có vài chục độ dịch khác nhau, nên p-value thô.
- **Dữ liệu là bản mới nhất, không phải bản đúng như lúc công bố.** Độ trễ công bố được mô phỏng theo cấu hình, nhưng số liệu bị sửa lại về sau (nếu có) không được tái hiện. Coin Metrics bản cộng đồng không có vốn hóa thực trực tiếp; Fear & Greed chỉ có từ 02/2018; giá 2010–2013 lệch nhau giữa các sàn.
- **Mô hình hẹp.** Chỉ hồi quy logistic L2 trên 8 bộ chỉ số đăng ký trước. Ràng buộc dấu thường loại MVRV và Fear & Greed; vòng trong thường không chọn được mô hình nào.
- **Chi phí đơn giản.** Phí và trượt giá cố định mỗi lần mua; không tính thuế, chênh lệch tỷ giá, rủi ro sàn hay lưu ký.
- **Kịch bản giá** giữ nguyên nguồn cung, lượng phát hành và hash rate; sai nếu kịch bản vắt qua kỳ giảm một nửa phần thưởng.
- **Vĩ mô.** Chế độ Fed (hiện là tăng) chỉ để chia nhóm; lịch sự kiện nhập tay từ trang chính thức và có thể thiếu.
- **Kế hoạch giải ngân** dựa trên lợi nhuận quá khứ với khoảng 9 đợt độc lập; kết quả đổi khi đổi giai đoạn dữ liệu.
- **Không thể biết:** giá tương lai; chu kỳ 4 năm có còn lặp lại không; thay đổi cấu trúc (quỹ ETF, quy định, sự cố lớn); và liệu một quy tắc từng có vẻ tốt có còn tốt không.
- **Trang web** đã có ô kế hoạch giải ngân, nhưng các khung và tỷ lệ "nên mua / nên bán" trên trang vẫn là của bot cũ; chưa đưa kết luận bản xây lại lên các phần đó.

Công cụ tham khảo, không phải lời khuyên đầu tư.
