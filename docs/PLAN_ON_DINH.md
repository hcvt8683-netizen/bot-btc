# Đề xuất Giải ngân / Chốt lời dần có ổn định không

Đăng ký trước: `config/candidates.yaml` mục `plan.stable` và `sell_plan.stable` (commit `1f0756b`, 04/11/2026, trước khi tính số nào). Mã: `bot/models/plan_stable.py`, chạy lại bằng `python -m bot.cli plan-stable`.

- Mỗi tuần từ 02/01/2022: tính lại bảng so các cách chia chỉ với dữ liệu có đến tuần đó (như báo cáo chạy thứ Ba sau tuần đó).
- Cách cũ (đến 03/11/2026): đề xuất cách có 10% xấu nhất ít thiệt nhất trong các cách không kém cách tốt nhất đáng kể.
- Cách mới: chỉ đề xuất khi mọi cách khác đều kém cách tốt nhất đáng kể; nếu không, trang nói các cách gần như ngang nhau.
- Chỉ để báo cáo: quy tắc không đổi theo kết quả này.

| Thẻ | Số tuần | Cách cũ: số lần đổi đề xuất | Cách cũ: đảo hẳn (một lần ↔ 52 tuần) | Cách mới: số lần đổi lời | Cách mới: đảo hẳn | Nhóm ngang nhau đổi thành viên | Số tuần nói "ngang nhau" |
|---|---|---|---|---|---|---|---|
| Giải ngân | 253 | 27 | 11 | 0 | 0 | 38 | 253 |
| Chốt lời dần | 253 | 20 | 0 | 9 | 0 | 25 | 165 |

## Giải ngân: lời của trang theo thời gian

| Từ tuần | Đến tuần | Cách cũ nói | Cách mới nói |
|---|---|---|---|
| 02/01/2022 | 21/08/2022 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 28/08/2022 | 28/08/2022 | đề xuất chia 52 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 04/09/2022 | 18/09/2022 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 25/09/2022 | 23/10/2022 | đề xuất chia 52 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 30/10/2022 | 13/11/2022 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 20/11/2022 | 20/11/2022 | đề xuất chia 52 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 27/11/2022 | 18/05/2025 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 25/05/2025 | 25/05/2025 | đề xuất chia 4 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 01/06/2025 | 01/06/2025 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 08/06/2025 | 08/06/2025 | đề xuất chia 4 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 15/06/2025 | 22/06/2025 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 29/06/2025 | 06/07/2025 | đề xuất chia 4 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 13/07/2025 | 13/07/2025 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 20/07/2025 | 20/07/2025 | đề xuất chia 4 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 27/07/2025 | 27/07/2025 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 03/08/2025 | 24/08/2025 | đề xuất chia 4 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 31/08/2025 | 14/09/2025 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 21/09/2025 | 05/10/2025 | đề xuất chia 4 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 12/10/2025 | 12/10/2025 | đề xuất chia 52 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 19/10/2025 | 19/10/2025 | đề xuất một lần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 26/10/2025 | 02/11/2025 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 09/11/2025 | 09/11/2025 | đề xuất một lần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần |
| 16/11/2025 | 16/11/2025 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 23/11/2025 | 23/11/2025 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 30/11/2025 | 30/11/2025 | đề xuất một lần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần |
| 07/12/2025 | 04/01/2026 | đề xuất chia 4 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 11/01/2026 | 11/01/2026 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 18/01/2026 | 18/01/2026 | đề xuất chia 52 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 25/01/2026 | 01/02/2026 | đề xuất một lần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần |
| 08/02/2026 | 08/02/2026 | đề xuất một lần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 15/02/2026 | 01/03/2026 | đề xuất chia 4 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần |
| 08/03/2026 | 28/06/2026 | đề xuất một lần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần |
| 05/07/2026 | 05/07/2026 | đề xuất một lần | ngang nhau: một lần, chia 26 tuần |
| 12/07/2026 | 09/08/2026 | đề xuất một lần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần |
| 16/08/2026 | 16/08/2026 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 23/08/2026 | 13/09/2026 | đề xuất một lần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần |
| 20/09/2026 | 27/09/2026 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 04/10/2026 | 25/10/2026 | đề xuất một lần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần |
| 01/11/2026 | 01/11/2026 | đề xuất chia 52 tuần | ngang nhau: một lần, chia 13 tuần, chia 26 tuần, chia 52 tuần |

## Chốt lời dần: lời của trang theo thời gian

| Từ tuần | Đến tuần | Cách cũ nói | Cách mới nói |
|---|---|---|---|
| 02/01/2022 | 26/06/2022 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 03/07/2022 | 03/07/2022 | đề xuất chia 52 tuần | ngang nhau: chia 26 tuần, chia 52 tuần |
| 10/07/2022 | 10/07/2022 | đề xuất chia 52 tuần | đề xuất chia 52 tuần |
| 17/07/2022 | 17/07/2022 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 24/07/2022 | 31/07/2022 | đề xuất chia 52 tuần | ngang nhau: chia 26 tuần, chia 52 tuần |
| 07/08/2022 | 08/01/2023 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 15/01/2023 | 05/03/2023 | đề xuất chia 4 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 12/03/2023 | 19/05/2024 | đề xuất bán một lần | ngang nhau: bán một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 26/05/2024 | 26/05/2024 | đề xuất bán một lần | ngang nhau: bán một lần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 02/06/2024 | 09/06/2024 | đề xuất bán một lần | ngang nhau: bán một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 16/06/2024 | 30/06/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 07/07/2024 | 07/07/2024 | đề xuất chia 4 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 14/07/2024 | 14/07/2024 | đề xuất bán một lần | ngang nhau: bán một lần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 21/07/2024 | 21/07/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 28/07/2024 | 28/07/2024 | đề xuất chia 4 tuần | ngang nhau: chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 04/08/2024 | 04/08/2024 | đề xuất bán một lần | ngang nhau: bán một lần, chia 4 tuần, chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 11/08/2024 | 29/09/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 06/10/2024 | 06/10/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 52 tuần |
| 13/10/2024 | 17/11/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 24/11/2024 | 24/11/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 52 tuần |
| 01/12/2024 | 01/12/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 08/12/2024 | 08/12/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 52 tuần |
| 15/12/2024 | 22/12/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 29/12/2024 | 29/12/2024 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 52 tuần |
| 05/01/2025 | 12/01/2025 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 19/01/2025 | 19/01/2025 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 52 tuần |
| 26/01/2025 | 02/02/2025 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 26 tuần, chia 52 tuần |
| 09/02/2025 | 09/02/2025 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 52 tuần |
| 16/02/2025 | 09/03/2025 | đề xuất chia 52 tuần | đề xuất chia 52 tuần |
| 16/03/2025 | 16/03/2025 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 52 tuần |
| 23/03/2025 | 23/03/2025 | đề xuất chia 52 tuần | đề xuất chia 52 tuần |
| 30/03/2025 | 30/03/2025 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 52 tuần |
| 06/04/2025 | 20/04/2025 | đề xuất chia 52 tuần | đề xuất chia 52 tuần |
| 27/04/2025 | 27/04/2025 | đề xuất chia 13 tuần | ngang nhau: chia 13 tuần, chia 52 tuần |
| 04/05/2025 | 01/11/2026 | đề xuất chia 52 tuần | đề xuất chia 52 tuần |

Công cụ tham khảo, không phải lời khuyên đầu tư.
