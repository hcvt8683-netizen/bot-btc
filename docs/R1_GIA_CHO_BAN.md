# R1: khả năng chạm giá chờ bán có đúng tỷ lệ không? (03/11/2026)

Sinh bằng `python -m bot.cli exit-calib` (mục `exit_calib` của `config/candidates.yaml`, đăng ký trước). Dùng đúng hàm của `bot/models/exit_timing.py`, không sửa gì trong đó. Mỗi ngày gốc từ 01/01/2016: bot nói khả năng giá cao nhất k ngày tới chạm giá đóng × (1 + x) là bao nhiêu, và thực tế có chạm không. Khoảng tin cậy Wilson theo số lần độc lập (số ngày / k).

## Kết luận

**Không ô nào lệch có hệ thống** ở cả hai nửa giai đoạn: phần lệch thấy trong hồi cứu 24 thời điểm nằm trong dao động ngẫu nhiên hoặc chỉ ở một giai đoạn. Không đề xuất đổi phương pháp.

## Kỳ hạn 7 ngày (2016-01-01 → 2026-10-26, chia đôi ở 2021-05-30)

| Mức | Bot nói | Thực tế | Khoảng tin cậy | Nửa đầu (nói / thật) | Nửa sau (nói / thật) | Trên MA 200 (nói / thật) | Dưới MA 200 (nói / thật) |
|---|---|---|---|---|---|---|---|
| +1% | 85% | 87% | 84%–89% | 85% / 88% | 85% / 86% | 85% / 87% | 86% / 87% |
| +2% | 73% | 76% | 72%–79% | 75% / 78% | 72% / 74% | 72% / 76% | 75% / 75% |
| +3% | 63% | 66% | 61%–69% | 66% / 70% | 60% / 62% | 62% / 66% | 64% / 65% |
| +5% | 46% | 49% | 45%–53% | 52% / 55% | 41% / 42% | 46% / 50% | 47% / 48% |
| +8% | 31% | 31% | 27%–35% | 37% / 38% | 25% / 23% | 31% / 32% | 31% / 28% |

Theo năm, mức +3% (bot nói / thực tế, chênh lệch, số lần độc lập):

| Năm | Bot nói | Thực tế | Chênh | Lần độc lập |
|---|---|---|---|---|
| 2016 | 49% | 53% | +4 điểm | 52 |
| 2017 | 69% | 85% | +15 điểm | 52 |
| 2018 | 70% | 63% | −6 điểm | 52 |
| 2019 | 69% | 68% | −1 điểm | 52 |
| 2020 | 66% | 75% | +9 điểm | 52 |
| 2021 | 74% | 75% | +1 điểm | 52 |
| 2022 | 66% | 63% | −4 điểm | 52 |
| 2023 | 54% | 60% | +6 điểm | 52 |
| 2024 | 63% | 66% | +3 điểm | 52 |
| 2025 | 54% | 57% | +3 điểm | 52 |
| 2026 | 54% | 54% | −0 điểm | 43 |

## Kỳ hạn 30 ngày (2016-01-01 → 2026-10-03, chia đôi ở 2021-05-18)

| Mức | Bot nói | Thực tế | Khoảng tin cậy | Nửa đầu (nói / thật) | Nửa sau (nói / thật) | Trên MA 200 (nói / thật) | Dưới MA 200 (nói / thật) |
|---|---|---|---|---|---|---|---|
| +1% | 93% | 94% | 88%–97% | 92% / 95% | 94% / 94% | 93% / 94% | 94% / 94% |
| +2% | 88% | 90% | 84%–94% | 87% / 90% | 88% / 89% | 87% / 90% | 89% / 89% |
| +3% | 82% | 86% | 78%–91% | 82% / 86% | 83% / 85% | 82% / 87% | 84% / 84% |
| +5% | 72% | 77% | 69%–83% | 74% / 79% | 71% / 74% | 72% / 78% | 73% / 75% |
| +8% | 59% | 64% | 56%–72% | 64% / 69% | 55% / 60% | 59% / 66% | 60% / 62% |

Theo năm, mức +3% (bot nói / thực tế, chênh lệch, số lần độc lập):

| Năm | Bot nói | Thực tế | Chênh | Lần độc lập |
|---|---|---|---|---|
| 2016 | 70% | 85% | +15 điểm | 12 |
| 2017 | 84% | 96% | +12 điểm | 12 |
| 2018 | 85% | 72% | −13 điểm | 12 |
| 2019 | 85% | 86% | +1 điểm | 12 |
| 2020 | 84% | 92% | +8 điểm | 12 |
| 2021 | 87% | 89% | +2 điểm | 12 |
| 2022 | 84% | 85% | +1 điểm | 12 |
| 2023 | 79% | 88% | +9 điểm | 12 |
| 2024 | 86% | 90% | +4 điểm | 12 |
| 2025 | 81% | 80% | −1 điểm | 12 |
| 2026 | 82% | 79% | −3 điểm | 9 |

## Đọc thế nào

- "Bot nói" là trung bình khả năng bot đưa ra ở các ngày trong nhóm; "thực tế" là tỷ lệ ngày giá thật sự chạm mức đó.
- Một năm lệch không có nghĩa là phương pháp sai: mỗi năm chỉ có khoảng 50 lần độc lập ở 7 ngày và 12 lần ở 30 ngày.
- Năm tăng mạnh thường chạm mức bán nhiều hơn bot nói (bot không đoán hướng); năm giảm thì ngược lại.

Công cụ tham khảo, không phải lời khuyên đầu tư.
