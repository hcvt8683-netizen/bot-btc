# RSI ghép với price action (mục `pa_rsi`)

Đăng ký trước trong `config/candidates.yaml` mục `pa_rsi`; chạy `python -m bot.cli pa-rsi`. Phiên bản e8535ad978.
Giai đoạn nghiên cứu 2016-01-01 → 2026-11-01, nến ngày Bitstamp, cách chấm giống hệt mục `price_action`.

## Kết luận

- 144 cặp (12 tín hiệu price action × 3 cách ghép RSI × 4 kỳ hạn), Holm trên 144 cặp.
- Hơn một ngày bất kỳ: **0**; kém: 0; chưa có lợi thế: 77; ít đợt (không kết luận): 67.
- Làm tăng lợi ích (hơn ngày bất kỳ, hơn price action một mình và hơn RSI một mình ở cả hai nửa): **0**.
- Theo quy tắc đã đăng ký và lời người dùng: **không dùng** cách ghép nào, thẻ Xu hướng giữ nguyên.

## Từng cặp

| Tín hiệu | Cách ghép RSI | Kỳ hạn | Số ngày | Đợt | Đúng | Ngày bất kỳ | PA một mình | RSI một mình | p Holm | Nhãn |
|---|---|---|---|---|---|---|---|---|---|---|
| bo_giam | nghiêng đảo chiều (50) | 1 | 102 | 91 | 48% | 48% | 46% | 47% | 1.00 | chưa có lợi thế |
| bo_giam | nghiêng đảo chiều (50) | 3 | 102 | 82 | 51% | 45% | 49% | 44% | 1.00 | chưa có lợi thế |
| bo_giam | nghiêng đảo chiều (50) | 7 | 102 | 71 | 52% | 46% | 52% | 44% | 1.00 | chưa có lợi thế |
| bo_giam | nghiêng đảo chiều (50) | 30 | 101 | 45 | 48% | 42% | 50% | 42% | 1.00 | chưa có lợi thế |
| bo_giam | nghiêng xu hướng (50) | 1 | 123 | 87 | 44% | 48% | 46% | 49% | 1.00 | chưa có lợi thế |
| bo_giam | nghiêng xu hướng (50) | 3 | 121 | 67 | 48% | 45% | 49% | 47% | 1.00 | chưa có lợi thế |
| bo_giam | nghiêng xu hướng (50) | 7 | 119 | 54 | 52% | 46% | 52% | 48% | 1.00 | chưa có lợi thế |
| bo_giam | nghiêng xu hướng (50) | 30 | 116 | 25 | 52% | 42% | 50% | 43% | 1.00 | ít đợt |
| bo_giam | quá bán/mua 30–70 | 1 | 10 | 10 | 60% | 48% | 46% | 44% | 1.00 | ít đợt |
| bo_giam | quá bán/mua 30–70 | 3 | 10 | 9 | 60% | 45% | 49% | 38% | 1.00 | ít đợt |
| bo_giam | quá bán/mua 30–70 | 7 | 10 | 8 | 30% | 46% | 52% | 37% | 1.00 | ít đợt |
| bo_giam | quá bán/mua 30–70 | 30 | 10 | 8 | 30% | 42% | 50% | 27% | 1.00 | ít đợt |
| bo_tang | nghiêng đảo chiều (50) | 1 | 202 | 153 | 50% | 52% | 49% | 51% | 1.00 | chưa có lợi thế |
| bo_tang | nghiêng đảo chiều (50) | 3 | 202 | 120 | 53% | 55% | 50% | 53% | 1.00 | chưa có lợi thế |
| bo_tang | nghiêng đảo chiều (50) | 7 | 202 | 89 | 55% | 54% | 53% | 52% | 1.00 | chưa có lợi thế |
| bo_tang | nghiêng đảo chiều (50) | 30 | 200 | 44 | 59% | 58% | 55% | 57% | 1.00 | chưa có lợi thế |
| bo_tang | nghiêng xu hướng (50) | 1 | 146 | 112 | 47% | 52% | 49% | 53% | 1.00 | chưa có lợi thế |
| bo_tang | nghiêng xu hướng (50) | 3 | 146 | 83 | 45% | 55% | 50% | 56% | 1.00 | chưa có lợi thế |
| bo_tang | nghiêng xu hướng (50) | 7 | 146 | 65 | 50% | 54% | 53% | 56% | 1.00 | chưa có lợi thế |
| bo_tang | nghiêng xu hướng (50) | 30 | 142 | 39 | 49% | 58% | 55% | 58% | 1.00 | chưa có lợi thế |
| bo_tang | quá bán/mua 30–70 | 1 | 7 | 7 | 86% | 52% | 49% | 57% | 1.00 | ít đợt |
| bo_tang | quá bán/mua 30–70 | 3 | 7 | 6 | 86% | 55% | 50% | 60% | 1.00 | ít đợt |
| bo_tang | quá bán/mua 30–70 | 7 | 7 | 6 | 86% | 54% | 53% | 59% | 1.00 | ít đợt |
| bo_tang | quá bán/mua 30–70 | 30 | 7 | 6 | 71% | 58% | 55% | 65% | 1.00 | ít đợt |
| cau_truc_giam | nghiêng đảo chiều (50) | 1 | 162 | 65 | 49% | 48% | 49% | 47% | 1.00 | chưa có lợi thế |
| cau_truc_giam | nghiêng đảo chiều (50) | 3 | 162 | 52 | 48% | 45% | 46% | 44% | 1.00 | chưa có lợi thế |
| cau_truc_giam | nghiêng đảo chiều (50) | 7 | 162 | 43 | 48% | 46% | 44% | 44% | 1.00 | chưa có lợi thế |
| cau_truc_giam | nghiêng đảo chiều (50) | 30 | 159 | 37 | 38% | 42% | 35% | 42% | 1.00 | chưa có lợi thế |
| cau_truc_giam | nghiêng xu hướng (50) | 1 | 585 | 79 | 48% | 48% | 49% | 49% | 1.00 | chưa có lợi thế |
| cau_truc_giam | nghiêng xu hướng (50) | 3 | 583 | 61 | 45% | 45% | 46% | 47% | 1.00 | chưa có lợi thế |
| cau_truc_giam | nghiêng xu hướng (50) | 7 | 579 | 51 | 44% | 46% | 44% | 48% | 1.00 | chưa có lợi thế |
| cau_truc_giam | nghiêng xu hướng (50) | 30 | 569 | 31 | 34% | 42% | 35% | 43% | 1.00 | chưa có lợi thế |
| cau_truc_giam | quá bán/mua 30–70 | 1 | 0 | 0 | — | 48% | 49% | 44% | 1.00 | ít đợt |
| cau_truc_giam | quá bán/mua 30–70 | 3 | 0 | 0 | — | 45% | 46% | 38% | 1.00 | ít đợt |
| cau_truc_giam | quá bán/mua 30–70 | 7 | 0 | 0 | — | 46% | 44% | 37% | 1.00 | ít đợt |
| cau_truc_giam | quá bán/mua 30–70 | 30 | 0 | 0 | — | 42% | 35% | 27% | 1.00 | ít đợt |
| cau_truc_tang | nghiêng đảo chiều (50) | 1 | 320 | 96 | 49% | 52% | 53% | 51% | 1.00 | chưa có lợi thế |
| cau_truc_tang | nghiêng đảo chiều (50) | 3 | 320 | 77 | 49% | 55% | 56% | 53% | 1.00 | chưa có lợi thế |
| cau_truc_tang | nghiêng đảo chiều (50) | 7 | 320 | 66 | 47% | 54% | 55% | 52% | 1.00 | chưa có lợi thế |
| cau_truc_tang | nghiêng đảo chiều (50) | 30 | 320 | 44 | 53% | 58% | 58% | 57% | 1.00 | chưa có lợi thế |
| cau_truc_tang | nghiêng xu hướng (50) | 1 | 1045 | 96 | 54% | 52% | 53% | 53% | 1.00 | chưa có lợi thế |
| cau_truc_tang | nghiêng xu hướng (50) | 3 | 1045 | 71 | 58% | 55% | 56% | 56% | 1.00 | chưa có lợi thế |
| cau_truc_tang | nghiêng xu hướng (50) | 7 | 1045 | 63 | 57% | 54% | 55% | 56% | 1.00 | chưa có lợi thế |
| cau_truc_tang | nghiêng xu hướng (50) | 30 | 1041 | 37 | 60% | 58% | 58% | 58% | 1.00 | chưa có lợi thế |
| cau_truc_tang | quá bán/mua 30–70 | 1 | 0 | 0 | — | 52% | 53% | 57% | 1.00 | ít đợt |
| cau_truc_tang | quá bán/mua 30–70 | 3 | 0 | 0 | — | 55% | 56% | 60% | 1.00 | ít đợt |
| cau_truc_tang | quá bán/mua 30–70 | 7 | 0 | 0 | — | 54% | 55% | 59% | 1.00 | ít đợt |
| cau_truc_tang | quá bán/mua 30–70 | 30 | 0 | 0 | — | 58% | 58% | 65% | 1.00 | ít đợt |
| ho_tro | nghiêng đảo chiều (50) | 1 | 300 | 229 | 55% | 52% | 52% | 51% | 1.00 | chưa có lợi thế |
| ho_tro | nghiêng đảo chiều (50) | 3 | 299 | 167 | 57% | 55% | 54% | 53% | 1.00 | chưa có lợi thế |
| ho_tro | nghiêng đảo chiều (50) | 7 | 299 | 114 | 59% | 54% | 56% | 52% | 1.00 | chưa có lợi thế |
| ho_tro | nghiêng đảo chiều (50) | 30 | 298 | 40 | 60% | 58% | 57% | 57% | 1.00 | chưa có lợi thế |
| ho_tro | nghiêng xu hướng (50) | 1 | 180 | 140 | 48% | 52% | 52% | 53% | 1.00 | chưa có lợi thế |
| ho_tro | nghiêng xu hướng (50) | 3 | 180 | 112 | 50% | 55% | 54% | 56% | 1.00 | chưa có lợi thế |
| ho_tro | nghiêng xu hướng (50) | 7 | 180 | 83 | 49% | 54% | 56% | 56% | 1.00 | chưa có lợi thế |
| ho_tro | nghiêng xu hướng (50) | 30 | 175 | 40 | 53% | 58% | 57% | 58% | 1.00 | chưa có lợi thế |
| ho_tro | quá bán/mua 30–70 | 1 | 16 | 15 | 69% | 52% | 52% | 57% | 1.00 | ít đợt |
| ho_tro | quá bán/mua 30–70 | 3 | 16 | 14 | 69% | 55% | 54% | 60% | 1.00 | ít đợt |
| ho_tro | quá bán/mua 30–70 | 7 | 16 | 13 | 88% | 54% | 56% | 59% | 0.71 | ít đợt |
| ho_tro | quá bán/mua 30–70 | 30 | 16 | 10 | 75% | 58% | 57% | 65% | 1.00 | ít đợt |
| inside_bar_ho_tro | nghiêng đảo chiều (50) | 1 | 256 | 229 | 54% | 52% | 54% | 51% | 1.00 | chưa có lợi thế |
| inside_bar_ho_tro | nghiêng đảo chiều (50) | 3 | 255 | 161 | 53% | 55% | 53% | 53% | 1.00 | chưa có lợi thế |
| inside_bar_ho_tro | nghiêng đảo chiều (50) | 7 | 255 | 101 | 54% | 54% | 55% | 52% | 1.00 | chưa có lợi thế |
| inside_bar_ho_tro | nghiêng đảo chiều (50) | 30 | 252 | 37 | 59% | 58% | 58% | 57% | 1.00 | chưa có lợi thế |
| inside_bar_ho_tro | nghiêng xu hướng (50) | 1 | 142 | 127 | 54% | 52% | 54% | 53% | 1.00 | chưa có lợi thế |
| inside_bar_ho_tro | nghiêng xu hướng (50) | 3 | 142 | 96 | 53% | 55% | 53% | 56% | 1.00 | chưa có lợi thế |
| inside_bar_ho_tro | nghiêng xu hướng (50) | 7 | 142 | 66 | 56% | 54% | 55% | 56% | 1.00 | chưa có lợi thế |
| inside_bar_ho_tro | nghiêng xu hướng (50) | 30 | 138 | 35 | 58% | 58% | 58% | 58% | 1.00 | chưa có lợi thế |
| inside_bar_ho_tro | quá bán/mua 30–70 | 1 | 8 | 8 | 75% | 52% | 54% | 57% | 1.00 | ít đợt |
| inside_bar_ho_tro | quá bán/mua 30–70 | 3 | 8 | 6 | 62% | 55% | 53% | 60% | 1.00 | ít đợt |
| inside_bar_ho_tro | quá bán/mua 30–70 | 7 | 8 | 5 | 50% | 54% | 55% | 59% | 1.00 | ít đợt |
| inside_bar_ho_tro | quá bán/mua 30–70 | 30 | 8 | 5 | 75% | 58% | 58% | 65% | 1.00 | ít đợt |
| inside_bar_khang_cu | nghiêng đảo chiều (50) | 1 | 204 | 185 | 40% | 48% | 43% | 47% | 1.00 | chưa có lợi thế |
| inside_bar_khang_cu | nghiêng đảo chiều (50) | 3 | 204 | 139 | 47% | 45% | 48% | 44% | 1.00 | chưa có lợi thế |
| inside_bar_khang_cu | nghiêng đảo chiều (50) | 7 | 204 | 91 | 44% | 46% | 47% | 44% | 1.00 | chưa có lợi thế |
| inside_bar_khang_cu | nghiêng đảo chiều (50) | 30 | 200 | 39 | 40% | 42% | 44% | 42% | 1.00 | chưa có lợi thế |
| inside_bar_khang_cu | nghiêng xu hướng (50) | 1 | 157 | 142 | 46% | 48% | 43% | 49% | 1.00 | chưa có lợi thế |
| inside_bar_khang_cu | nghiêng xu hướng (50) | 3 | 156 | 102 | 50% | 45% | 48% | 47% | 1.00 | chưa có lợi thế |
| inside_bar_khang_cu | nghiêng xu hướng (50) | 7 | 156 | 69 | 50% | 46% | 47% | 48% | 1.00 | chưa có lợi thế |
| inside_bar_khang_cu | nghiêng xu hướng (50) | 30 | 154 | 32 | 50% | 42% | 44% | 43% | 1.00 | chưa có lợi thế |
| inside_bar_khang_cu | quá bán/mua 30–70 | 1 | 20 | 19 | 40% | 48% | 43% | 44% | 1.00 | ít đợt |
| inside_bar_khang_cu | quá bán/mua 30–70 | 3 | 20 | 18 | 40% | 45% | 48% | 38% | 1.00 | ít đợt |
| inside_bar_khang_cu | quá bán/mua 30–70 | 7 | 20 | 15 | 20% | 46% | 47% | 37% | 1.00 | ít đợt |
| inside_bar_khang_cu | quá bán/mua 30–70 | 30 | 20 | 14 | 25% | 42% | 44% | 27% | 1.00 | ít đợt |
| khang_cu | nghiêng đảo chiều (50) | 1 | 296 | 230 | 47% | 48% | 49% | 47% | 1.00 | chưa có lợi thế |
| khang_cu | nghiêng đảo chiều (50) | 3 | 296 | 184 | 41% | 45% | 45% | 44% | 1.00 | chưa có lợi thế |
| khang_cu | nghiêng đảo chiều (50) | 7 | 296 | 123 | 49% | 46% | 53% | 44% | 1.00 | chưa có lợi thế |
| khang_cu | nghiêng đảo chiều (50) | 30 | 294 | 42 | 48% | 42% | 52% | 42% | 1.00 | chưa có lợi thế |
| khang_cu | nghiêng xu hướng (50) | 1 | 165 | 122 | 53% | 48% | 49% | 49% | 1.00 | chưa có lợi thế |
| khang_cu | nghiêng xu hướng (50) | 3 | 164 | 89 | 54% | 45% | 45% | 47% | 1.00 | chưa có lợi thế |
| khang_cu | nghiêng xu hướng (50) | 7 | 162 | 64 | 59% | 46% | 53% | 48% | 1.00 | chưa có lợi thế |
| khang_cu | nghiêng xu hướng (50) | 30 | 162 | 30 | 60% | 42% | 52% | 43% | 1.00 | chưa có lợi thế |
| khang_cu | quá bán/mua 30–70 | 1 | 38 | 34 | 47% | 48% | 49% | 44% | 1.00 | chưa có lợi thế |
| khang_cu | quá bán/mua 30–70 | 3 | 38 | 29 | 39% | 45% | 45% | 38% | 1.00 | ít đợt |
| khang_cu | quá bán/mua 30–70 | 7 | 38 | 25 | 37% | 46% | 53% | 37% | 1.00 | ít đợt |
| khang_cu | quá bán/mua 30–70 | 30 | 38 | 18 | 32% | 42% | 52% | 27% | 1.00 | ít đợt |
| pha_vo_gia_duoi | nghiêng đảo chiều (50) | 1 | 35 | 35 | 46% | 52% | 42% | 51% | 1.00 | chưa có lợi thế |
| pha_vo_gia_duoi | nghiêng đảo chiều (50) | 3 | 35 | 33 | 46% | 55% | 47% | 53% | 1.00 | chưa có lợi thế |
| pha_vo_gia_duoi | nghiêng đảo chiều (50) | 7 | 35 | 30 | 51% | 54% | 57% | 52% | 1.00 | chưa có lợi thế |
| pha_vo_gia_duoi | nghiêng đảo chiều (50) | 30 | 34 | 22 | 41% | 58% | 40% | 57% | 1.00 | ít đợt |
| pha_vo_gia_duoi | nghiêng xu hướng (50) | 1 | 18 | 18 | 33% | 52% | 42% | 53% | 1.00 | ít đợt |
| pha_vo_gia_duoi | nghiêng xu hướng (50) | 3 | 18 | 16 | 50% | 55% | 47% | 56% | 1.00 | ít đợt |
| pha_vo_gia_duoi | nghiêng xu hướng (50) | 7 | 18 | 16 | 67% | 54% | 57% | 56% | 1.00 | ít đợt |
| pha_vo_gia_duoi | nghiêng xu hướng (50) | 30 | 18 | 14 | 39% | 58% | 40% | 58% | 1.00 | ít đợt |
| pha_vo_gia_duoi | quá bán/mua 30–70 | 1 | 6 | 6 | 67% | 52% | 42% | 57% | 1.00 | ít đợt |
| pha_vo_gia_duoi | quá bán/mua 30–70 | 3 | 6 | 6 | 67% | 55% | 47% | 60% | 1.00 | ít đợt |
| pha_vo_gia_duoi | quá bán/mua 30–70 | 7 | 6 | 6 | 67% | 54% | 57% | 59% | 1.00 | ít đợt |
| pha_vo_gia_duoi | quá bán/mua 30–70 | 30 | 6 | 6 | 50% | 58% | 40% | 65% | 1.00 | ít đợt |
| pha_vo_gia_tren | nghiêng đảo chiều (50) | 1 | 26 | 25 | 23% | 48% | 28% | 47% | 1.00 | ít đợt |
| pha_vo_gia_tren | nghiêng đảo chiều (50) | 3 | 26 | 23 | 46% | 45% | 40% | 44% | 1.00 | ít đợt |
| pha_vo_gia_tren | nghiêng đảo chiều (50) | 7 | 26 | 21 | 46% | 46% | 45% | 44% | 1.00 | ít đợt |
| pha_vo_gia_tren | nghiêng đảo chiều (50) | 30 | 26 | 18 | 50% | 42% | 42% | 42% | 1.00 | ít đợt |
| pha_vo_gia_tren | nghiêng xu hướng (50) | 1 | 14 | 13 | 36% | 48% | 28% | 49% | 1.00 | ít đợt |
| pha_vo_gia_tren | nghiêng xu hướng (50) | 3 | 14 | 13 | 29% | 45% | 40% | 47% | 1.00 | ít đợt |
| pha_vo_gia_tren | nghiêng xu hướng (50) | 7 | 14 | 11 | 43% | 46% | 45% | 48% | 1.00 | ít đợt |
| pha_vo_gia_tren | nghiêng xu hướng (50) | 30 | 14 | 11 | 29% | 42% | 42% | 43% | 1.00 | ít đợt |
| pha_vo_gia_tren | quá bán/mua 30–70 | 1 | 6 | 5 | 0% | 48% | 28% | 44% | 0.14 | ít đợt |
| pha_vo_gia_tren | quá bán/mua 30–70 | 3 | 6 | 5 | 50% | 45% | 40% | 38% | 1.00 | ít đợt |
| pha_vo_gia_tren | quá bán/mua 30–70 | 7 | 6 | 5 | 50% | 46% | 45% | 37% | 1.00 | ít đợt |
| pha_vo_gia_tren | quá bán/mua 30–70 | 30 | 6 | 5 | 33% | 42% | 42% | 27% | 1.00 | ít đợt |
| pin_bar_ho_tro | nghiêng đảo chiều (50) | 1 | 64 | 63 | 47% | 52% | 44% | 51% | 1.00 | chưa có lợi thế |
| pin_bar_ho_tro | nghiêng đảo chiều (50) | 3 | 64 | 58 | 48% | 55% | 45% | 53% | 1.00 | chưa có lợi thế |
| pin_bar_ho_tro | nghiêng đảo chiều (50) | 7 | 64 | 49 | 61% | 54% | 55% | 52% | 1.00 | chưa có lợi thế |
| pin_bar_ho_tro | nghiêng đảo chiều (50) | 30 | 62 | 33 | 63% | 58% | 57% | 57% | 1.00 | chưa có lợi thế |
| pin_bar_ho_tro | nghiêng xu hướng (50) | 1 | 42 | 41 | 40% | 52% | 44% | 53% | 1.00 | chưa có lợi thế |
| pin_bar_ho_tro | nghiêng xu hướng (50) | 3 | 42 | 38 | 40% | 55% | 45% | 56% | 1.00 | chưa có lợi thế |
| pin_bar_ho_tro | nghiêng xu hướng (50) | 7 | 42 | 34 | 45% | 54% | 55% | 56% | 1.00 | chưa có lợi thế |
| pin_bar_ho_tro | nghiêng xu hướng (50) | 30 | 42 | 27 | 48% | 58% | 57% | 58% | 1.00 | ít đợt |
| pin_bar_ho_tro | quá bán/mua 30–70 | 1 | 7 | 6 | 71% | 52% | 44% | 57% | 1.00 | ít đợt |
| pin_bar_ho_tro | quá bán/mua 30–70 | 3 | 7 | 5 | 86% | 55% | 45% | 60% | 1.00 | ít đợt |
| pin_bar_ho_tro | quá bán/mua 30–70 | 7 | 7 | 5 | 71% | 54% | 55% | 59% | 1.00 | ít đợt |
| pin_bar_ho_tro | quá bán/mua 30–70 | 30 | 7 | 5 | 71% | 58% | 57% | 65% | 1.00 | ít đợt |
| pin_bar_khang_cu | nghiêng đảo chiều (50) | 1 | 35 | 34 | 49% | 48% | 48% | 47% | 1.00 | chưa có lợi thế |
| pin_bar_khang_cu | nghiêng đảo chiều (50) | 3 | 35 | 32 | 43% | 45% | 45% | 44% | 1.00 | chưa có lợi thế |
| pin_bar_khang_cu | nghiêng đảo chiều (50) | 7 | 35 | 32 | 51% | 46% | 48% | 44% | 1.00 | chưa có lợi thế |
| pin_bar_khang_cu | nghiêng đảo chiều (50) | 30 | 35 | 25 | 57% | 42% | 49% | 42% | 1.00 | ít đợt |
| pin_bar_khang_cu | nghiêng xu hướng (50) | 1 | 21 | 20 | 48% | 48% | 48% | 49% | 1.00 | ít đợt |
| pin_bar_khang_cu | nghiêng xu hướng (50) | 3 | 21 | 19 | 48% | 45% | 45% | 47% | 1.00 | ít đợt |
| pin_bar_khang_cu | nghiêng xu hướng (50) | 7 | 21 | 18 | 43% | 46% | 48% | 48% | 1.00 | ít đợt |
| pin_bar_khang_cu | nghiêng xu hướng (50) | 30 | 20 | 14 | 35% | 42% | 49% | 43% | 1.00 | ít đợt |
| pin_bar_khang_cu | quá bán/mua 30–70 | 1 | 0 | 0 | — | 48% | 48% | 44% | 1.00 | ít đợt |
| pin_bar_khang_cu | quá bán/mua 30–70 | 3 | 0 | 0 | — | 45% | 45% | 38% | 1.00 | ít đợt |
| pin_bar_khang_cu | quá bán/mua 30–70 | 7 | 0 | 0 | — | 46% | 48% | 37% | 1.00 | ít đợt |
| pin_bar_khang_cu | quá bán/mua 30–70 | 30 | 0 | 0 | — | 42% | 49% | 27% | 1.00 | ít đợt |

Công cụ tham khảo, không phải lời khuyên đầu tư.
