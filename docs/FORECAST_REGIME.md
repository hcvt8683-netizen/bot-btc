# Dải giá theo nhóm độ dao động

Đăng ký trước: `config/candidates.yaml` mục `forecast_regime` (commit `8fd2b9c`). Dữ liệu giá Coin Metrics từ 18/07/2010 đến 02/11/2026. Mã: `bot/models/forecast_regime.py`; chạy lại: `python -m bot.cli forecast-regime`.

- **Vì sao:** độ dao động quay về mức trung bình: sau giai đoạn êm giá thường biến động mạnh lên, sau giai đoạn mạnh thường dịu lại. Chia cho độ dao động 30 ngày một mình làm dải hẹp quá lúc êm, rộng quá lúc mạnh.
- **Thước đo:** như forecast_search: điểm phân vị trên log giá, 5 phân vị × 8 kỳ hạn, chia cho cách đang dùng rồi lấy trung bình (dưới 1 là tốt hơn); thêm độ lệch phủ theo nhóm: trung bình qua 8 kỳ hạn của trung bình qua 3 nhóm độ dao động (nhóm tính như theo_nhom) của |tỷ lệ trúng dải 80% − 80%|.
- **Quy tắc:** chọn trong tron / theo_nhom cách có điểm thấp nhất ở giai đoạn chọn. Chỉ thay cách đang dùng nếu ở giai đoạn xác nhận: (a) khoảng tin cậy 95% của chênh lệch điểm (bootstrap khối 30 ngày, 2000 lần, seed của rebuild) nằm hẳn dưới 0; (b) dải 80% phủ 75–85% (trung bình 8 kỳ hạn); (c) độ lệch phủ theo nhóm nhỏ hơn cách đang dùng. Không đạt đủ cả ba thì giữ nguyên và ghi kết quả.

## Kết luận: **đổi sang trộn ngắn + dài hạn**

- Tốt hơn ở giai đoạn chọn (01/01/2014 → 31/12/2021): **trộn ngắn + dài hạn**, điểm 0,9788 (cách đang dùng = 1,0000; cách còn lại 0,9975).
- Giai đoạn xác nhận (01/01/2022 → nay, 1737 ngày): chênh điểm -1,4%, khoảng tin cậy 95% -2,0% đến -0,8% → (a) đạt.
- Dải 80% phủ 80,2% (cần 75–85%) → (b) đạt.
- Độ lệch phủ theo nhóm 4,5% so với 8,5% của cách đang dùng → (c) đạt.
- Đạt cả ba: đổi `price_forecast.bands`, nhật ký dự báo sang phiên bản mới.

## Tỷ lệ trúng dải 8/10 lần theo nhóm độ dao động lúc dự báo

| Kỳ hạn | Giai đoạn | Cách tính | Số ngày | Trúng chung | 1/3 êm nhất | giữa | 1/3 mạnh nhất | Độ lệch theo nhóm | Độ rộng dải 80% (trung vị) |
|---|---|---|---|---|---|---|---|---|---|
| 1 ngày | 2014–2021 | đang dùng | 2922 | 79,6% | 75,1% | 80,4% | 84,2% | 3,2% | 8,4% |
| 1 ngày | 2014–2021 | trộn ngắn + dài hạn | 2922 | 78,5% | 80,9% | 79,1% | 74,5% | 2,4% | 8,0% |
| 1 ngày | 2014–2021 | theo nhóm độ dao động | 2922 | 79,0% | 78,5% | 80,2% | 77,6% | 1,4% | 8,1% |
| 1 ngày | 2022–nay | đang dùng | 1766 | 80,2% | 76,9% | 82,7% | 89,6% | 5,1% | 5,5% |
| 1 ngày | 2022–nay | trộn ngắn + dài hạn | 1766 | 79,7% | 80,1% | 78,9% | 79,6% | 0,6% | 5,5% |
| 1 ngày | 2022–nay | theo nhóm độ dao động | 1766 | 80,2% | 79,2% | 81,0% | 82,6% | 1,4% | 5,8% |
| 7 ngày | 2014–2021 | đang dùng | 2922 | 81,9% | 73,6% | 82,5% | 91,7% | 6,8% | 30,6% |
| 7 ngày | 2014–2021 | trộn ngắn + dài hạn | 2922 | 80,1% | 78,6% | 81,0% | 80,7% | 1,1% | 27,0% |
| 7 ngày | 2014–2021 | theo nhóm độ dao động | 2922 | 79,4% | 80,7% | 80,7% | 75,5% | 2,0% | 29,5% |
| 7 ngày | 2022–nay | đang dùng | 1760 | 80,4% | 72,2% | 89,3% | 95,7% | 10,9% | 17,6% |
| 7 ngày | 2022–nay | trộn ngắn + dài hạn | 1760 | 80,5% | 75,7% | 84,4% | 92,2% | 6,9% | 17,2% |
| 7 ngày | 2022–nay | theo nhóm độ dao động | 1760 | 82,9% | 81,1% | 84,6% | 87,0% | 4,2% | 19,0% |
| 30 ngày | 2014–2021 | đang dùng | 2922 | 81,7% | 66,8% | 85,3% | 95,2% | 11,2% | 101,1% |
| 30 ngày | 2014–2021 | trộn ngắn + dài hạn | 2922 | 79,2% | 72,2% | 79,8% | 87,1% | 5,0% | 78,6% |
| 30 ngày | 2014–2021 | theo nhóm độ dao động | 2922 | 75,6% | 75,3% | 80,2% | 69,0% | 5,3% | 85,1% |
| 30 ngày | 2022–nay | đang dùng | 1737 | 80,5% | 70,9% | 94,4% | 90,9% | 11,5% | 53,8% |
| 30 ngày | 2022–nay | trộn ngắn + dài hạn | 1737 | 80,5% | 72,8% | 90,9% | 90,4% | 9,5% | 47,5% |
| 30 ngày | 2022–nay | theo nhóm độ dao động | 1737 | 85,1% | 84,1% | 87,8% | 83,5% | 5,1% | 56,4% |

## Tóm tắt 8 kỳ hạn

| Cách tính | Điểm 2014–2021 | Trúng 80% / 50% | Lệch theo nhóm | Điểm 2022–nay | Trúng 80% / 50% | Lệch theo nhóm |
|---|---|---|---|---|---|---|
| đang dùng | 1,0000 | 81,1% / 49,4% | 6,0% | 1,0000 | 80,2% / 50,8% | 8,5% |
| trộn ngắn + dài hạn | 0,9788 | 79,5% / 47,2% | 1,6% | 0,9860 | 80,2% / 50,1% | 4,5% |
| theo nhóm độ dao động | 0,9975 | 79,0% / 47,9% | 2,1% | 0,9939 | 82,0% / 51,8% | 3,1% |

Điểm dưới 1 là tốt hơn cách đang dùng. Độ lệch theo nhóm = trung bình |tỷ lệ trúng − 80%| của 3 nhóm; 0 là đúng tỷ lệ ở mọi lúc.

Công cụ tham khảo, không phải lời khuyên đầu tư.
