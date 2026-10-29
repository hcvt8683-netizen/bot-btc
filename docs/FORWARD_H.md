# Phần H: kiểm định đi tới

Đăng ký trước: `config/candidates.yaml` mục `forward` (commit `13daebf`). Mã: `bot/models/forward.py`, lệnh `python -m bot.cli forward freeze | log | score`.

## 1. Cách làm

- **Đóng băng:** mô hình lồng nhau (Phần C) đóng băng: chọn bộ chỉ số, λ và trọng số MỘT lần tại ngày đóng băng; không học lại trong thời gian theo dõi.
- **Mã phiên bản:** sha256 của mã tính đầu ra (chuẩn hóa xuống dòng LF), các mục cấu hình model/sets/zones/multiplier/sell/rebuild, và trạng thái đóng băng (trọng số, lịch sử điểm để xếp hạng, khung tuần trước, ước lượng lợi thế từng khung, trạng thái cổng Phần I). Tên phiên bản = số thứ tự + 10 ký tự đầu của mã, ví dụ `v1-f7eb2b7151`.
- **Mỗi tuần một dòng** trong `forward_log.csv` (UTF-8 có BOM): `date`, `close`, `score`, `rank`, `zone`, `mult_rule`, `mult_used`, `model_version`, `rank_mvrv`, `zone_mvrv`, `rank_200w`, `zone_200w`, `sell_groups`, `sell_level`, `logged_at`, `late`.
  Ngoài mô hình, dòng ghi luôn thứ hạng và khung của hai quy tắc đơn giản (mốc so sánh) và mức bên bán.
- **Không sửa mô hình:** mã, cấu hình hoặc trạng thái đổi → không ghi tiếp; đóng băng lại thành phiên bản mới với nhật ký mới; nhật ký cũ giữ nguyên, chỉ thêm dòng, không sửa. Lệnh ghi tự kiểm tra mã trước mỗi lần ghi.
- **Ghi muộn:** dòng ghi sau giá đóng Chủ nhật kế tiếp → late = 1.
- **Chấm lại:** sau 26 và 52 tuần; chấm mọi dòng đã đủ kỳ hạn bằng giá đóng thứ Hai (như Phần B), cùng thước đo thống nhất; mốc = mọi tuần của nhật ký đã đủ kỳ hạn.
- **Vì sao chỉ nhật ký đi tới mới là kiểm định thật:** dữ liệu 2024–2026 (holdout) đã được con người nhìn thấy khi làm bot cũ. Chỉ những tuần ghi SAU khi đóng băng mới hoàn toàn ngoài mẫu.

Bài kiểm tra tự động (`tests/test_forward.py`): chỉ thêm dòng, không sửa dòng cũ; ghi lại cùng tuần không làm gì; đổi cấu hình thì dừng ghi và đóng băng lại tạo phiên bản mới với nhật ký mới; sửa tay `model.json` bị phát hiện; dòng không dùng dữ liệu sau Chủ nhật của nó; khi ghi không học lại mô hình. Đã cài thử 3 lỗi (sửa dòng cũ, nhìn trước 4 tuần, học lại mỗi tuần): test bắt được cả 3.

## 2. Chạy thử trên 2023 (không phải kiểm định)

Đóng băng tại 25/12/2022, ghi mỗi Chủ nhật đến 31/12/2023 như thể chạy vào mỗi thứ Hai, rồi chấm bằng dữ liệu đến 31/12/2023. Năm 2023 đã dùng ở Phần B–E, nên đây chỉ là chạy thử quy trình. File: `data/results/forward_dryrun/v1-f7eb2b7151/`.

- Phiên bản `v1-f7eb2b7151`, mã đầy đủ `f7eb2b71518398ac914a5d8e0e57a1d0d3a761060874444e92c985d26925fee6`.
- Mô hình đóng băng: bộ S3, λ = 3,0, giữ puell (trọng số 0,07); bỏ do sai dấu: mvrv. Tỷ lệ gốc 58%.
- Lịch sử điểm ngoài mẫu để xếp hạng: 97 tuần. Cổng Phần I: chua_kiem_dinh → hệ số dùng thực tế 1,0.

| Ngày | Giá đóng | Điểm | Thứ hạng | Khung | Hệ số (quy tắc / dùng) | Quy tắc MVRV | Quy tắc Giá/MA 200 tuần | Bên bán |
|---|---|---|---|---|---|---|---|---|
| 25/12/2022 | 16.825 $ | 0,605 | 13 | Không nên mua | 1,00 / 1,00 | 98 → Phải mua | 94 → Phải mua | 0 nhóm → Giữ |
| 22/01/2023 | 22.716 $ | 0,589 | 10 | Không nên mua | 1,00 / 1,00 | 79 → Phải mua | 86 → Phải mua | 0 nhóm → Giữ |
| 19/02/2023 | 24.367 $ | 0,581 | 9 | Không nên mua | 1,00 / 1,00 | 77 → Phải mua | 82 → Phải mua | 0 nhóm → Giữ |
| 19/03/2023 | 28.185 $ | 0,576 | 7 | Không nên mua | 1,00 / 1,00 | 70 → Cân nhắc mua | 75 → Phải mua | 0 nhóm → Giữ |
| 16/04/2023 | 30.313 $ | 0,580 | 12 | Không nên mua | 1,00 / 1,00 | 66 → Cân nhắc mua | 73 → Cân nhắc mua | 0 nhóm → Giữ |
| 14/05/2023 | 26.918 $ | 0,567 | 3 | Không nên mua | 1,00 / 1,00 | 74 → Cân nhắc mua | 77 → Cân nhắc mua | 0 nhóm → Giữ |
| 11/06/2023 | 25.907 $ | 0,571 | 5 | Không nên mua | 1,00 / 1,00 | 76 → Cân nhắc mua | 79 → Cân nhắc mua | 0 nhóm → Giữ |
| 09/07/2023 | 30.163 $ | 0,564 | 3 | Không nên mua | 1,00 / 1,00 | 63 → Cân nhắc mua | 69 → Cân nhắc mua | 0 nhóm → Giữ |
| 06/08/2023 | 29.048 $ | 0,567 | 5 | Không nên mua | 1,00 / 1,00 | 67 → Cân nhắc mua | 72 → Cân nhắc mua | 0 nhóm → Giữ |
| 03/09/2023 | 25.963 $ | 0,576 | 21 | Không nên mua | 1,00 / 1,00 | 77 → Cân nhắc mua | 81 → Phải mua | 0 nhóm → Giữ |
| 01/10/2023 | 27.950 $ | 0,579 | 24 | Không nên mua | 1,00 / 1,00 | 68 → Cân nhắc mua | 72 → Cân nhắc mua | 0 nhóm → Giữ |
| 29/10/2023 | 34.574 $ | 0,569 | 8 | Không nên mua | 1,00 / 1,00 | 34 → Không nên mua | 60 → Cân nhắc mua | 0 nhóm → Giữ |
| 26/11/2023 | 37.483 $ | 0,565 | 6 | Không nên mua | 1,00 / 1,00 | 27 → Không nên mua | 58 → Cân nhắc mua | 1 nhóm → Chốt lời một phần |
| 24/12/2023 | 43.098 $ | 0,558 | 1 | Không nên mua | 1,00 / 1,00 | 19 → Không nên mua | 55 → Không nên mua | 0 nhóm → Giữ |
| 31/12/2023 | 42.217 $ | 0,563 | 5 | Không nên mua | 1,00 / 1,00 | 21 → Không nên mua | 56 → Không nên mua | 0 nhóm → Giữ |

Bảng chỉ in mỗi 4 tuần một dòng; đủ 54 dòng trong file.

**Chấm lại:** 54 dòng; đủ kỳ hạn: 26 tuần: 27 dòng, 52 tuần: 1 dòng.

| Chiến lược | Kỳ hạn | Mốc (mọi tuần đủ kỳ hạn) | Khung | Số tuần | Số đợt | Tỷ lệ của khung | Chênh (KTC 95%) | Kết luận |
|---|---|---|---|---|---|---|---|---|
| Mô hình đóng băng | 26 tuần | 81% | Không nên mua | 27 | 1 | 81% | 0,0% (0,0% đến 0,0%) | ít đợt (< 3) |
| Mô hình đóng băng | 52 tuần | 100% | Không nên mua | 1 | 1 | 100% | 0,0% (0,0% đến 0,0%) | ít đợt (< 3) |
| Quy tắc MVRV | 26 tuần | 81% | Phải mua | 12 | 1 | 100% | +18,5% (0,0% đến +37,0%) | ít đợt (< 3) |
| Quy tắc MVRV | 26 tuần | 81% | Cân nhắc mua | 15 | 1 | 67% | -14,8% (-44,0% đến 0,0%) | ít đợt (< 3) |
| Quy tắc MVRV | 52 tuần | 100% | Phải mua | 1 | 1 | 100% | 0,0% (0,0% đến 0,0%) | ít đợt (< 3) |
| Quy tắc Giá/MA 200 tuần | 26 tuần | 81% | Phải mua | 14 | 1 | 86% | +4,2% (-7,4% đến +13,3%) | ít đợt (< 3) |
| Quy tắc Giá/MA 200 tuần | 26 tuần | 81% | Cân nhắc mua | 13 | 1 | 77% | -4,6% (-29,6% đến +6,2%) | ít đợt (< 3) |
| Quy tắc Giá/MA 200 tuần | 52 tuần | 100% | Phải mua | 1 | 1 | 100% | 0,0% (0,0% đến 0,0%) | ít đợt (< 3) |

## 3. Kế hoạch chạy thật

- **Đóng băng thật:** ngay sau lần chạy holdout duy nhất ở Phần I (đóng băng cần dữ liệu 2024–2026, làm sau để giữ khóa holdout). Lệnh `python -m bot.cli forward freeze` từ chối chạy khi chưa có kết quả Phần I.
- **Mỗi tuần:** `python -m bot.cli forward log` sau giá đóng Chủ nhật (tuần nào bị lỡ sẽ được ghi bù và đánh dấu ghi muộn). Tự động hóa trên GitHub Actions chỉ làm ở bước tích hợp cuối, khi bạn đồng ý.
- **Chấm:** `python -m bot.cli forward score`. Mỗi khung cần ít nhất 3 đợt mới kết luận. Trong chạy thử, sau 54 tuần ghi, khung nhiều đợt nhất mới có 1 đợt đủ kỳ 26 tuần. Trước khi đủ, kết luận đúng là "ít đợt".
- **Không sửa mô hình trong thời gian theo dõi.** Sửa mã hay cấu hình nghĩa là phiên bản mới và nhật ký mới, đếm lại từ đầu.
