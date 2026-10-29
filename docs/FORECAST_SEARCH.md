# Dự báo dải giá: so 32 cách tính

Đăng ký trước: `config/candidates.yaml` mục `forecast_search` (commit `c3b4f52`). Dữ liệu giá Coin Metrics từ 18/07/2010 đến 28/10/2026. Mã: `bot/models/forecast_search.py`; mọi cấu hình: `experiments/forecast_configs.csv`.

- **Vì sao không chọn theo tỷ lệ trúng:** tỷ lệ trúng một mình không đủ: dải càng rộng càng trúng. Thước đo chính là điểm phân vị (pinball loss), thưởng cho dải vừa đúng tỷ lệ vừa hẹp.
- **Thước đo:** điểm phân vị trung bình trên log giá, 5 phân vị × 8 kỳ hạn; mỗi kỳ hạn chia cho điểm của cách đang dùng trong cùng giai đoạn rồi lấy trung bình (dưới 1 là tốt hơn).
- **Quy tắc:** chọn cấu hình có điểm thấp nhất ở giai đoạn chọn. Chỉ thay cách đang dùng nếu ở giai đoạn xác nhận nó vẫn có điểm thấp hơn với khoảng tin cậy 95% của chênh lệch (bootstrap khối 30 ngày, 2000 lần) nằm hẳn dưới 0, và dải 80% phủ 75–85%. Không thì giữ nguyên ("phủ 75–85%" tính trung bình qua 8 kỳ hạn, chốt trước khi chạy).

## Kết luận: **giữ nguyên cách đang dùng (std30/1461/empirical)**

- Tốt nhất ở giai đoạn chọn (01/01/2014 → 31/12/2021): **chuẩn/ewma94**, điểm 0,9791 (cách đang dùng = 1,0000).
- Ở giai đoạn xác nhận (01/01/2022 → nay, 1732 ngày): chênh -0,1% so với cách đang dùng, khoảng tin cậy 95% -1,1% đến +0,8%; dải 80% phủ 81,3%.
- Khoảng tin cậy chứa 0: không đủ bằng chứng cách mới tốt hơn, nên giữ nguyên. Chọn lại theo kết quả giai đoạn xác nhận sẽ là chọn may rủi, nên không làm.

## Cách đang dùng theo từng kỳ hạn

| Kỳ hạn | Giai đoạn | Số ngày | Trúng dải 80% | Trúng dải 50% | Độ rộng dải 80% (trung vị) | Sai số của giữa (trung vị) | Đoán đúng hướng |
|---|---|---|---|---|---|---|---|
| 1 ngày | 2014–2021 | 2922 | 79,6% | 48,8% | 8,4% | 1,6% | 53,5% |
| 2 ngày | 2014–2021 | 2922 | 80,8% | 48,9% | 12,7% | 2,5% | 54,4% |
| 3 ngày | 2014–2021 | 2922 | 81,3% | 48,6% | 16,5% | 3,3% | 54,6% |
| 4 ngày | 2014–2021 | 2922 | 81,2% | 49,3% | 20,4% | 3,9% | 54,1% |
| 5 ngày | 2014–2021 | 2922 | 81,0% | 49,8% | 23,6% | 4,5% | 54,4% |
| 6 ngày | 2014–2021 | 2922 | 81,4% | 49,9% | 27,3% | 5,0% | 54,0% |
| 7 ngày | 2014–2021 | 2922 | 81,9% | 49,6% | 30,6% | 5,5% | 54,2% |
| 30 ngày | 2014–2021 | 2922 | 81,7% | 50,6% | 101,1% | 14,9% | 55,6% |
| 1 ngày | 2022–nay | 1761 | 80,3% | 49,4% | 5,5% | 1,2% | 50,1% |
| 2 ngày | 2022–nay | 1760 | 79,8% | 49,9% | 8,2% | 1,8% | 51,4% |
| 3 ngày | 2022–nay | 1759 | 80,0% | 50,1% | 10,2% | 2,3% | 52,0% |
| 4 ngày | 2022–nay | 1758 | 80,8% | 50,8% | 12,6% | 2,7% | 51,1% |
| 5 ngày | 2022–nay | 1757 | 79,8% | 51,2% | 14,5% | 3,0% | 51,6% |
| 6 ngày | 2022–nay | 1756 | 80,5% | 50,2% | 15,9% | 3,3% | 51,8% |
| 7 ngày | 2022–nay | 1755 | 80,5% | 50,5% | 17,7% | 3,5% | 51,1% |
| 30 ngày | 2022–nay | 1732 | 80,5% | 54,8% | 53,8% | 8,5% | 54,5% |

"Đoán đúng hướng" (giữa cao hơn giá gốc thì coi là đoán tăng) chỉ quanh 50–55%: dải giá không biết giá sẽ lên hay xuống; nó chỉ cho biết giá có thể đi xa đến đâu.

## Cả 32 cách (điểm dưới 1 là tốt hơn cách đang dùng)

| Cách tính | Độ dao động | Lịch sử | Trung tâm | Phân phối | Điểm 2014–2021 | Trúng 80% / 50% | Điểm 2022–nay | Trúng 80% / 50% | Độ rộng 80%, 7 ngày |
|---|---|---|---|---|---|---|---|---|---|
| chuẩn/ewma94 **(tốt nhất giai đoạn chọn)** | ewma94 | — | zero | chuẩn | 0,9791 | 80,0% / 56,3% | 0,9988 | 81,3% / 57,8% | 17,6% |
| ewma97/all/zero | ewma97 | all | zero | thực nghiệm | 0,9797 | 80,7% / 47,7% | 0,9889 | 80,6% / 49,5% | 17,7% |
| ewma97/1461/zero | ewma97 | 1461 | zero | thực nghiệm | 0,9799 | 80,2% / 48,8% | 0,9868 | 80,4% / 50,8% | 17,0% |
| ewma94/1461/zero | ewma94 | 1461 | zero | thực nghiệm | 0,9807 | 80,7% / 49,3% | 0,9936 | 80,5% / 50,9% | 17,1% |
| ewma94/all/zero | ewma94 | all | zero | thực nghiệm | 0,9815 | 81,3% / 48,5% | 0,9972 | 81,1% / 50,5% | 18,8% |
| ewma94/730/zero | ewma94 | 730 | zero | thực nghiệm | 0,9818 | 79,6% / 49,3% | 1,0001 | 80,2% / 51,2% | 17,2% |
| ewma97/730/zero | ewma97 | 730 | zero | thực nghiệm | 0,9829 | 79,2% / 48,8% | 0,9937 | 80,0% / 51,4% | 16,8% |
| ewma97/1461/empirical | ewma97 | 1461 | empirical | thực nghiệm | 0,9858 | 79,9% / 47,9% | 0,9883 | 80,4% / 50,4% | 17,0% |
| chuẩn/std30 | std30 | — | zero | chuẩn | 0,9861 | 78,8% / 55,3% | 1,0023 | 80,7% / 57,4% | 17,2% |
| ewma94/1461/empirical | ewma94 | 1461 | empirical | thực nghiệm | 0,9864 | 80,4% / 48,8% | 0,9950 | 80,3% / 50,5% | 17,1% |
| ewma97/all/empirical | ewma97 | all | empirical | thực nghiệm | 0,9887 | 79,9% / 46,5% | 0,9971 | 79,8% / 48,9% | 17,7% |
| ewma94/all/empirical | ewma94 | all | empirical | thực nghiệm | 0,9904 | 80,7% / 47,7% | 1,0056 | 80,3% / 49,8% | 18,8% |
| std60/1461/zero | std60 | 1461 | zero | thực nghiệm | 0,9918 | 81,1% / 49,6% | 0,9883 | 80,7% / 50,8% | 17,6% |
| std30/1461/zero | std30 | 1461 | zero | thực nghiệm | 0,9930 | 81,6% / 50,0% | 0,9984 | 80,5% / 50,8% | 17,7% |
| std30/730/zero | std30 | 730 | zero | thực nghiệm | 0,9932 | 80,6% / 49,7% | 1,0053 | 80,2% / 51,2% | 17,3% |
| std60/all/zero | std60 | all | zero | thực nghiệm | 0,9934 | 82,8% / 49,2% | 0,9928 | 81,9% / 50,9% | 18,6% |
| std60/730/zero | std60 | 730 | zero | thực nghiệm | 0,9944 | 79,6% / 49,3% | 0,9952 | 80,3% / 51,4% | 16,6% |
| none/730/zero | none | 730 | zero | thực nghiệm | 0,9949 | 79,6% / 50,1% | 0,9936 | 83,6% / 55,3% | 18,5% |
| none/1461/zero | none | 1461 | zero | thực nghiệm | 0,9952 | 82,6% / 52,0% | 0,9929 | 87,5% / 58,4% | 23,7% |
| std30/all/zero | std30 | all | zero | thực nghiệm | 0,9966 | 82,7% / 49,8% | 1,0049 | 82,2% / 51,2% | 19,5% |
| none/1461/empirical | none | 1461 | empirical | thực nghiệm | 0,9984 | 82,6% / 51,3% | 0,9947 | 87,5% / 58,0% | 23,7% |
| ewma94/730/empirical | ewma94 | 730 | empirical | thực nghiệm | 0,9989 | 78,7% / 48,4% | 1,0123 | 79,5% / 50,6% | 17,2% |
| std60/1461/empirical | std60 | 1461 | empirical | thực nghiệm | 0,9994 | 80,7% / 48,7% | 0,9898 | 80,7% / 50,6% | 17,6% |
| ewma97/730/empirical | ewma97 | 730 | empirical | thực nghiệm | 0,9997 | 78,4% / 47,7% | 1,0062 | 79,7% / 50,9% | 16,8% |
| std30/1461/empirical **(đang dùng)** | std30 | 1461 | empirical | thực nghiệm | 1,0000 | 81,1% / 49,4% | 1,0000 | 80,3% / 50,9% | 17,7% |
| none/all/zero | none | all | zero | thực nghiệm | 1,0001 | 87,2% / 55,4% | 1,0407 | 93,1% / 65,3% | 31,0% |
| none/730/empirical | none | 730 | empirical | thực nghiệm | 1,0053 | 79,3% / 49,1% | 1,0079 | 83,2% / 54,7% | 18,5% |
| std60/all/empirical | std60 | all | empirical | thực nghiệm | 1,0056 | 81,5% / 48,2% | 1,0021 | 81,2% / 50,2% | 18,6% |
| none/all/empirical | none | all | empirical | thực nghiệm | 1,0064 | 86,7% / 54,4% | 1,0506 | 92,7% / 64,1% | 31,0% |
| std30/all/empirical | std30 | all | empirical | thực nghiệm | 1,0070 | 81,7% / 48,9% | 1,0138 | 81,5% / 51,0% | 19,5% |
| std30/730/empirical | std30 | 730 | empirical | thực nghiệm | 1,0122 | 79,6% / 48,9% | 1,0180 | 79,5% / 50,9% | 17,3% |
| std60/730/empirical | std60 | 730 | empirical | thực nghiệm | 1,0141 | 78,7% / 48,1% | 1,0079 | 79,8% / 50,9% | 16,6% |

Ghi chú: `none` = không chuẩn hóa theo độ dao động; `std30`, `std60` = độ lệch chuẩn 30, 60 ngày; `ewma94`, `ewma97` = trung bình trượt mũ (λ 0,94, 0,97); lịch sử 730 / 1461 ngày hoặc `all` (từ 2010); `zero` = không giả định xu hướng. Cách không chuẩn hóa với toàn bộ lịch sử có dải quá rộng (trúng hơn 90% ở 2022–nay).

Công cụ tham khảo, không phải lời khuyên đầu tư.
