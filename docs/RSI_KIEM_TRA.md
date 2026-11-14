# RSI 14 so với một ngày (giờ) bất kỳ

Đăng ký trước trong `config/candidates.yaml` mục `rsi_check`; chạy `python -m bot.cli rsi`. Phiên bản e3f0705b91.

- Số phép thử: 112 (dải × kỳ hạn, cả nến ngày và nến giờ), hiệu chỉnh Holm.
- Ô có lợi thế (p Holm < 0,05 và hơn tỷ lệ gốc ở cả hai nửa): **4**.
- Ô ít dữ liệu (dưới 30 lần độc lập): 37.
- Niềm tin 'dải càng sâu thắng càng cao': 0/56 cặp sâu hơn nông một cách chắc chắn sau Holm.

## Nến ngày Bitstamp (từ 2016)

| Dải | Kỳ hạn | Số lần | Đúng hướng | Tỷ lệ gốc | p Holm | Kết luận |
|---|---|---|---|---|---|---|
| qua_ban_sau | 1 | 22 | 55% | 52% | 1.00 | ít dữ liệu |
| qua_ban_sau | 2 | 13 | 54% | 54% | 1.00 | ít dữ liệu |
| qua_ban_sau | 3 | 11 | 45% | 54% | 1.00 | ít dữ liệu |
| qua_ban_sau | 4 | 9 | 44% | 54% | 1.00 | ít dữ liệu |
| qua_ban_sau | 5 | 8 | 62% | 54% | 1.00 | ít dữ liệu |
| qua_ban_sau | 6 | 8 | 62% | 54% | 1.00 | ít dữ liệu |
| qua_ban_sau | 7 | 7 | 43% | 54% | 1.00 | ít dữ liệu |
| qua_ban_sau | 14 | 6 | 67% | 56% | 1.00 | ít dữ liệu |
| qua_ban_sau | 21 | 6 | 50% | 56% | 1.00 | ít dữ liệu |
| qua_ban_sau | 28 | 6 | 50% | 57% | 1.00 | ít dữ liệu |
| qua_ban_sau | 30 | 6 | 67% | 57% | 1.00 | ít dữ liệu |
| qua_ban_sau | 60 | 6 | 50% | 59% | 1.00 | ít dữ liệu |
| qua_ban_sau | 90 | 6 | 67% | 60% | 1.00 | ít dữ liệu |
| qua_ban_sau | 120 | 6 | 67% | 60% | 1.00 | ít dữ liệu |
| qua_ban_sau | 150 | 5 | 80% | 61% | 1.00 | ít dữ liệu |
| qua_ban_sau | 180 | 4 | 75% | 64% | 1.00 | ít dữ liệu |
| qua_ban | 1 | 115 | 57% | 52% | 1.00 | không hơn |
| qua_ban | 2 | 70 | 63% | 54% | 1.00 | không hơn |
| qua_ban | 3 | 57 | 56% | 54% | 1.00 | không hơn |
| qua_ban | 4 | 49 | 59% | 54% | 1.00 | không hơn |
| qua_ban | 5 | 45 | 64% | 54% | 1.00 | không hơn |
| qua_ban | 6 | 40 | 68% | 54% | 1.00 | không hơn |
| qua_ban | 7 | 38 | 58% | 54% | 1.00 | không hơn |
| qua_ban | 14 | 29 | 48% | 56% | 1.00 | ít dữ liệu |
| qua_ban | 21 | 27 | 48% | 56% | 1.00 | ít dữ liệu |
| qua_ban | 28 | 26 | 50% | 57% | 1.00 | ít dữ liệu |
| qua_ban | 30 | 25 | 48% | 57% | 1.00 | ít dữ liệu |
| qua_ban | 60 | 22 | 59% | 59% | 1.00 | ít dữ liệu |
| qua_ban | 90 | 18 | 61% | 60% | 1.00 | ít dữ liệu |
| qua_ban | 120 | 18 | 67% | 60% | 1.00 | ít dữ liệu |
| qua_ban | 150 | 16 | 69% | 61% | 1.00 | ít dữ liệu |
| qua_ban | 180 | 13 | 69% | 64% | 1.00 | ít dữ liệu |
| qua_mua | 1 | 314 | 44% | 48% | 1.00 | không hơn |
| qua_mua | 2 | 197 | 37% | 46% | 1.00 | không hơn |
| qua_mua | 3 | 154 | 34% | 46% | 1.00 | không hơn |
| qua_mua | 4 | 130 | 36% | 46% | 1.00 | không hơn |
| qua_mua | 5 | 112 | 38% | 46% | 1.00 | không hơn |
| qua_mua | 6 | 101 | 43% | 46% | 1.00 | không hơn |
| qua_mua | 7 | 89 | 33% | 46% | 1.00 | không hơn |
| qua_mua | 14 | 63 | 30% | 44% | 1.00 | không hơn |
| qua_mua | 21 | 49 | 27% | 44% | 1.00 | không hơn |
| qua_mua | 28 | 43 | 28% | 43% | 1.00 | không hơn |
| qua_mua | 30 | 41 | 22% | 43% | 1.00 | không hơn |
| qua_mua | 60 | 32 | 34% | 41% | 1.00 | không hơn |
| qua_mua | 90 | 23 | 17% | 40% | 1.00 | ít dữ liệu |
| qua_mua | 120 | 20 | 30% | 40% | 1.00 | ít dữ liệu |
| qua_mua | 150 | 17 | 24% | 39% | 1.00 | ít dữ liệu |
| qua_mua | 180 | 15 | 33% | 36% | 1.00 | ít dữ liệu |
| qua_mua_sau | 1 | 165 | 45% | 48% | 1.00 | không hơn |
| qua_mua_sau | 2 | 97 | 38% | 46% | 1.00 | không hơn |
| qua_mua_sau | 3 | 70 | 41% | 46% | 1.00 | không hơn |
| qua_mua_sau | 4 | 60 | 35% | 46% | 1.00 | không hơn |
| qua_mua_sau | 5 | 54 | 46% | 46% | 1.00 | không hơn |
| qua_mua_sau | 6 | 47 | 36% | 46% | 1.00 | không hơn |
| qua_mua_sau | 7 | 46 | 35% | 46% | 1.00 | không hơn |
| qua_mua_sau | 14 | 34 | 29% | 44% | 1.00 | không hơn |
| qua_mua_sau | 21 | 27 | 30% | 44% | 1.00 | ít dữ liệu |
| qua_mua_sau | 28 | 24 | 25% | 43% | 1.00 | ít dữ liệu |
| qua_mua_sau | 30 | 24 | 25% | 43% | 1.00 | ít dữ liệu |
| qua_mua_sau | 60 | 19 | 21% | 41% | 1.00 | ít dữ liệu |
| qua_mua_sau | 90 | 13 | 8% | 40% | 1.00 | ít dữ liệu |
| qua_mua_sau | 120 | 13 | 23% | 40% | 1.00 | ít dữ liệu |
| qua_mua_sau | 150 | 10 | 10% | 39% | 1.00 | ít dữ liệu |
| qua_mua_sau | 180 | 10 | 0% | 36% | 1.00 | ít dữ liệu |

## Nến giờ vĩnh cửu (từ 07/2020)

| Dải | Kỳ hạn | Số lần | Đúng hướng | Tỷ lệ gốc | p Holm | Kết luận |
|---|---|---|---|---|---|---|
| qua_ban_sau | 1 | 302 | 60% | 51% | 0.08 | không hơn |
| qua_ban_sau | 2 | 200 | 59% | 51% | 1.00 | không hơn |
| qua_ban_sau | 3 | 169 | 59% | 51% | 1.00 | không hơn |
| qua_ban_sau | 4 | 148 | 60% | 51% | 1.00 | không hơn |
| qua_ban_sau | 6 | 129 | 57% | 51% | 1.00 | không hơn |
| qua_ban_sau | 8 | 117 | 58% | 51% | 1.00 | không hơn |
| qua_ban_sau | 12 | 107 | 54% | 51% | 1.00 | không hơn |
| qua_ban_sau | 24 | 94 | 48% | 52% | 1.00 | không hơn |
| qua_ban_sau | 48 | 90 | 49% | 52% | 1.00 | không hơn |
| qua_ban_sau | 72 | 86 | 56% | 53% | 1.00 | không hơn |
| qua_ban_sau | 120 | 79 | 51% | 53% | 1.00 | không hơn |
| qua_ban_sau | 168 | 73 | 49% | 53% | 1.00 | không hơn |
| qua_ban | 1 | 2322 | 56% | 51% | 0.00 | có lợi thế |
| qua_ban | 2 | 1465 | 55% | 51% | 0.06 | không hơn |
| qua_ban | 3 | 1155 | 55% | 51% | 0.26 | không hơn |
| qua_ban | 4 | 990 | 57% | 51% | 0.03 | có lợi thế |
| qua_ban | 6 | 801 | 54% | 51% | 1.00 | không hơn |
| qua_ban | 8 | 697 | 55% | 51% | 1.00 | không hơn |
| qua_ban | 12 | 594 | 51% | 51% | 1.00 | không hơn |
| qua_ban | 24 | 448 | 52% | 52% | 1.00 | không hơn |
| qua_ban | 48 | 362 | 53% | 52% | 1.00 | không hơn |
| qua_ban | 72 | 316 | 54% | 53% | 1.00 | không hơn |
| qua_ban | 120 | 248 | 50% | 53% | 1.00 | không hơn |
| qua_ban | 168 | 203 | 55% | 53% | 1.00 | không hơn |
| qua_mua | 1 | 2824 | 54% | 49% | 0.00 | có lợi thế |
| qua_mua | 2 | 1720 | 53% | 49% | 0.01 | có lợi thế |
| qua_mua | 3 | 1342 | 53% | 49% | 0.34 | không hơn |
| qua_mua | 4 | 1118 | 52% | 49% | 1.00 | không hơn |
| qua_mua | 6 | 914 | 51% | 49% | 1.00 | không hơn |
| qua_mua | 8 | 784 | 52% | 49% | 1.00 | không hơn |
| qua_mua | 12 | 643 | 50% | 49% | 1.00 | không hơn |
| qua_mua | 24 | 479 | 48% | 48% | 1.00 | không hơn |
| qua_mua | 48 | 393 | 50% | 48% | 1.00 | không hơn |
| qua_mua | 72 | 347 | 51% | 47% | 1.00 | không hơn |
| qua_mua | 120 | 255 | 52% | 47% | 1.00 | không hơn |
| qua_mua | 168 | 218 | 49% | 47% | 1.00 | không hơn |
| qua_mua_sau | 1 | 543 | 54% | 49% | 1.00 | không hơn |
| qua_mua_sau | 2 | 336 | 51% | 49% | 1.00 | không hơn |
| qua_mua_sau | 3 | 267 | 52% | 49% | 1.00 | không hơn |
| qua_mua_sau | 4 | 230 | 49% | 49% | 1.00 | không hơn |
| qua_mua_sau | 6 | 190 | 44% | 49% | 1.00 | không hơn |
| qua_mua_sau | 8 | 169 | 46% | 49% | 1.00 | không hơn |
| qua_mua_sau | 12 | 147 | 44% | 49% | 1.00 | không hơn |
| qua_mua_sau | 24 | 124 | 44% | 48% | 1.00 | không hơn |
| qua_mua_sau | 48 | 111 | 46% | 48% | 1.00 | không hơn |
| qua_mua_sau | 72 | 107 | 47% | 47% | 1.00 | không hơn |
| qua_mua_sau | 120 | 97 | 45% | 47% | 1.00 | không hơn |
| qua_mua_sau | 168 | 89 | 43% | 47% | 1.00 | không hơn |

Kết quả không có lợi thế chỉ ghi ở đây; trang chỉ hiện giá trị RSI kèm ghi chú trung thực, không đổi kết luận.
