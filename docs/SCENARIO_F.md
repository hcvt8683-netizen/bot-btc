# Phần F: kịch bản giá động

Ngày phân tích: **31/12/2023**, Chủ nhật cuối trước holdout (Phần D, E dừng ở 24/12/2023 vì cần giá thứ Hai để chấm; kịch bản chỉ cần giá Chủ nhật). Giá đóng 42.217 $, Fear & Greed 67, MVRV 1,92.

- Quy tắc Giá/MA 200 tuần: thứ hạng 56 → Không nên mua. Quy tắc MVRV: thứ hạng 21 → Không nên mua. Bên bán: 0 nhóm → Giữ.
- Đăng ký trước: `config/candidates.yaml` mục `scenarios` (commit `f44bab8`). Giá đi tới mức giả định sau k tuần theo đường đều trên thang log.
- Chỉ số tính từ giá (MVRV, MVRV Z, Pi, Mayer, MA 200 tuần, MA 20 tuần, RSI, biến động 30 ngày, giảm từ đỉnh, Puell) tính lại đúng từ đường giá giả định.
- Giữ nguyên ở trường hợp giữa: vốn hóa thực, nguồn cung, số BTC phát hành mỗi ngày, hash rate giữ ở giá trị cuối (thay đổi rất chậm trong ≤ 4 tuần).
- Fear & Greed **không còn bị giữ nguyên**: dự báo theo mô hình phản ứng học chỉ từ dữ liệu đến ngày phân tích, kèm khoảng 10–90%.
- Khoảng dao động của quy tắc MVRV và nhóm định giá bên bán còn tính theo thay đổi vốn hóa thực trong k tuần (10–90% của 4 năm trước; thêm sau lần chạy đầu, ghi trong nhật ký).
- Thứ hạng là vị trí của điểm tuần đó trong các tuần trước, **không phải xác suất có lãi**. Khung dùng vùng trễ 5 điểm tính tiếp từ khung hiện tại.

## 1. Fear & Greed phản ứng với giá thế nào

Mô hình: thay đổi F&G sau k tuần = a + b × lợi suất log k tuần + c × (F&G hiện tại − 50).

| Kỳ | Số tuần học | b (theo giá) | c (kéo về 50) | R² | Khoảng 10–90% phần dư | Kiểm ngoài mẫu 2022–2023 (học đến 2021): độ phủ khoảng | Sai số TB: mô hình / giữ nguyên F&G |
|---|---|---|---|---|---|---|---|
| 1 tuần | 306 | 92,8 | -0,21 | 0,56 | -10,6 đến 10,0 điểm | 98% (104 tuần) | 4,3 / 5,9 điểm |
| 2 tuần | 305 | 83,2 | -0,33 | 0,65 | -11,6 đến 11,4 điểm | 98% (103 tuần) | 4,7 / 7,8 điểm |
| 4 tuần | 303 | 72,5 | -0,53 | 0,73 | -13,8 đến 12,5 điểm | 100% (101 tuần) | 5,9 / 10,6 điểm |

Đọc: kỳ 4 tuần, giá giảm 10% kéo F&G xuống khoảng 8 điểm, cộng phần kéo về 50 (53% khoảng cách tới 50). Mô hình sai ít hơn hẳn cách giữ nguyên F&G.
Độ phủ ngoài mẫu cao hơn mức 80% kỳ vọng: khoảng hơi rộng, tức thận trọng hơn cần thiết ở giai đoạn 2022–2023.

Thay đổi vốn hóa thực trong k tuần (10–90%, 208 tuần trước ngày phân tích): 1 tuần: -0,5% đến +2,6%; 2 tuần: -1,0% đến +5,3%; 4 tuần: -2,1% đến +11,9%.

## Nếu giá đi tới mức này sau 1 tuần

| Giá | So với hiện tại | F&G dự báo (10–90%) | Quy tắc Giá/MA 200 tuần: thứ hạng → khung | Quy tắc MVRV: thứ hạng (khoảng) → khung | Bên bán: số nhóm (khoảng) → mức | Cách cũ, giữ F&G: số nhóm |
|---|---|---|---|---|---|---|
| 29.552 $ | -30% | 29 (18–39) | 73 → Cân nhắc mua | 72 (72–73) → Cân nhắc mua | 0 (0) → Giữ | 0 |
| 33.774 $ | -20% | 41 (31–51) | 63 → Cân nhắc mua | 56 (55–59) → Không nên mua | 0 (0) → Giữ | 0 |
| 37.995 $ | -10% | 52 (42–62) | 59 → Không nên mua | 33 (33–39) → Không nên mua | 0 (0) → Giữ | 0 |
| 40.106 $ | -5% | 57 (47–67) | 57 → Không nên mua | 26 (26–30) → Không nên mua | 0 (0) → Giữ | 0 |
| 42.217 $ | không đổi | 62 (51–72) | 56 → Không nên mua | 21 (20–25) → Không nên mua | 0 (0) → Giữ | 0 |
| 44.328 $ | +5% | 66 (56–76) | 54 → Không nên mua | 17 (17–19) → Không nên mua | 0 (0) → Giữ | 0 |
| 46.439 $ | +10% | 71 (60–81) | 52 → Không nên mua | 16 (16) → Không nên mua | 0 (0) → Giữ | 0 |
| 50.661 $ | +20% | 79 (68–89) | 48 → Không nên mua | 13 (13–14) → Không nên mua | 1 (1–2) → Chốt lời một phần | 1 |
| 54.882 $ | +30% | 86 (76–96) | 45 → Không nên mua | 9 (9–11) → Không nên mua | 2 (1–2) → Chốt lời một phần | 1 |
| 63.326 $ | +50% | 99 (89–100) | 34 → Không nên mua | 6 (6) → Không nên mua | 2 (2) → Chốt lời một phần | 2 |

## Nếu giá đi tới mức này sau 2 tuần

| Giá | So với hiện tại | F&G dự báo (10–90%) | Quy tắc Giá/MA 200 tuần: thứ hạng → khung | Quy tắc MVRV: thứ hạng (khoảng) → khung | Bên bán: số nhóm (khoảng) → mức | Cách cũ, giữ F&G: số nhóm |
|---|---|---|---|---|---|---|
| 29.552 $ | -30% | 29 (18–41) | 73 → Cân nhắc mua | 72 (72–78) → Cân nhắc mua | 0 (0) → Giữ | 0 |
| 33.774 $ | -20% | 40 (29–52) | 64 → Cân nhắc mua | 56 (55–64) → Cân nhắc mua / Không nên mua | 0 (0) → Giữ | 0 |
| 37.995 $ | -10% | 50 (38–61) | 59 → Không nên mua | 34 (33–44) → Không nên mua | 0 (0) → Giữ | 0 |
| 40.106 $ | -5% | 55 (43–66) | 57 → Không nên mua | 26 (26–34) → Không nên mua | 0 (0) → Giữ | 0 |
| 42.217 $ | không đổi | 59 (47–70) | 56 → Không nên mua | 22 (20–27) → Không nên mua | 0 (0) → Giữ | 0 |
| 44.328 $ | +5% | 63 (51–74) | 54 → Không nên mua | 17 (17–23) → Không nên mua | 0 (0) → Giữ | 0 |
| 46.439 $ | +10% | 67 (55–78) | 52 → Không nên mua | 16 (16–18) → Không nên mua | 0 (0) → Giữ | 0 |
| 50.661 $ | +20% | 74 (62–85) | 48 → Không nên mua | 13 (13–16) → Không nên mua | 1 (1) → Chốt lời một phần | 1 |
| 54.882 $ | +30% | 81 (69–92) | 45 → Không nên mua | 9 (9–11) → Không nên mua | 1 (1–2) → Chốt lời một phần | 1 |
| 63.326 $ | +50% | 93 (81–100) | 34 → Không nên mua | 6 (5–7) → Không nên mua | 2 (2) → Chốt lời một phần | 2 |

## Nếu giá đi tới mức này sau 4 tuần

| Giá | So với hiện tại | F&G dự báo (10–90%) | Quy tắc Giá/MA 200 tuần: thứ hạng → khung | Quy tắc MVRV: thứ hạng (khoảng) → khung | Bên bán: số nhóm (khoảng) → mức | Cách cũ, giữ F&G: số nhóm |
|---|---|---|---|---|---|---|
| 29.552 $ | -30% | 28 (14–40) | 75 → Cân nhắc mua | 72 (72–82) → Phải mua / Cân nhắc mua | 0 (0) → Giữ | 0 |
| 33.774 $ | -20% | 38 (24–50) | 64 → Cân nhắc mua | 56 (53–72) → Cân nhắc mua / Không nên mua | 0 (0) → Giữ | 0 |
| 37.995 $ | -10% | 46 (32–59) | 59 → Không nên mua | 36 (32–56) → Không nên mua | 0 (0) → Giữ | 0 |
| 40.106 $ | -5% | 50 (36–63) | 57 → Không nên mua | 28 (27–46) → Không nên mua | 0 (0) → Giữ | 0 |
| 42.217 $ | không đổi | 54 (40–66) | 56 → Không nên mua | 22 (19–37) → Không nên mua | 0 (0) → Giữ | 0 |
| 44.328 $ | +5% | 57 (43–70) | 54 → Không nên mua | 17 (16–30) → Không nên mua | 0 (0) → Giữ | 0 |
| 46.439 $ | +10% | 61 (47–73) | 52 → Không nên mua | 16 (16–25) → Không nên mua | 0 (0) → Giữ | 0 |
| 50.661 $ | +20% | 67 (53–79) | 49 → Không nên mua | 13 (12–16) → Không nên mua | 1 (1) → Chốt lời một phần | 1 |
| 54.882 $ | +30% | 73 (59–85) | 47 → Không nên mua | 9 (8–15) → Không nên mua | 1 (1) → Chốt lời một phần | 1 |
| 63.326 $ | +50% | 83 (69–96) | 34 → Không nên mua | 6 (5–8) → Không nên mua | 1 (1–2) → Chốt lời một phần | 1 |

## Kết luận Phần F

- Sau 4 tuần, mức giá đầu tiên (đi từ trên xuống) làm quy tắc chạm khung mua: Giá/MA 200 tuần ở giá giảm 20% (vào Cân nhắc mua); MVRV ở giá giảm 20% (vào Cân nhắc mua / Không nên mua). Giá đi ngang hoặc tăng: cả hai ở Không nên mua.
- Bên bán bắt đầu có nhóm bật (Chốt lời một phần) khi giá tăng từ 20% (tính cả khoảng); tiêu chí bật ở trường hợp giữa: rsi_14w.
- So với cách cũ (giữ nguyên F&G): số nhóm bên bán ở trường hợp giữa khác ở 1/30 kịch bản: 1 tuần +30%: 1 → 2 nhóm.
- Kiểm tra tự động: cho kịch bản đi đúng đường giá thật thì mọi chỉ số trùng bảng thật; kịch bản không đọc dữ liệu sau ngày phân tích.
- Kịch bản chỉ mô tả bot **sẽ đọc thế nào** nếu giá đi tới mức đó, không dự báo giá. Theo Phần C–D, hệ số giải ngân vẫn là 1,0 (mua đều) ở mọi mức giá.
- Giới hạn: nguồn cung và số BTC phát hành giữ nguyên, nên kịch bản vắt qua kỳ giảm một nửa phần thưởng (dự kiến 04/2024) sẽ sai Puell; khoảng F&G dựa trên dữ liệu từ 02/2018 (khoảng 300 tuần); khoảng vốn hóa thực không phụ thuộc hướng giá (4 năm trước có đợt tăng mạnh 2020–2021), nên phía trên của khoảng MVRV khi giá giảm có thể rộng quá.
