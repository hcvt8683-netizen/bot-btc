# Yếu điểm của bot và kế hoạch sửa (03/11/2026)

Viết sau khi chạy lại toàn bộ bot:
- `python -m pytest`: 203 bài qua, cộng 7 bài mới của `tests/test_forecast_regime.py`.
- Tải dữ liệu mới, chạy đủ 12 bước của quy trình Daily.
- Hồi cứu mở rộng (`docs/HOI_CUU_MO_RONG.md`): tại hàng trăm thời điểm từ 2016–2018, tính lại điều bot đã nói chỉ bằng dữ liệu có đến lúc đó, rồi so với điều đã xảy ra.

Mọi việc sửa vẫn theo quy tắc của `docs/KE_HOACH_CAI_TIEN.md`: đăng ký trước, không nhìn trước, không dò cho đẹp, không sửa file bị khóa.

## Cách chạy lại (mỗi khi muốn kiểm tra)

Quy trình Daily trên GitHub tải dữ liệu và lưu lên `main` mỗi ngày. Trên máy bạn chỉ cần lấy bản mới rồi chạy, không cần mạng:

```
git pull
python tools/hoi_cuu_mo_rong.py
python -m pytest
```

- Lệnh thứ hai ghi `docs/HOI_CUU_MO_RONG.md` (Mac / Linux: `make hoi-cuu`).
- Muốn xem lại phép so cách tính dải giá: `python -m bot.cli forecast-regime` (ghi `docs/FORECAST_REGIME.md`).
- Muốn đếm lại số lần Giải ngân / Chốt lời dần đổi lời: `python -m bot.cli plan-stable` (ghi `docs/PLAN_ON_DINH.md`, khoảng 30 giây).
- Không chạy `python -m bot.cli fetch` trên máy rồi đẩy `data/` lên git. Việc đó do Daily làm; đẩy cùng lúc dễ xung đột nhật ký.

## Yếu điểm, từ lớn đến nhỏ

| # | Yếu điểm | Mức | Trạng thái |
|---|---|---|---|
| 1 | Không thẻ nào đoán được hướng giá | rất lớn | chưa sửa được bằng cách dò; cần dữ liệu mới |
| 2 | Long/Short: kỳ vọng âm, có đòn bẩy | lớn | cần thêm chốt chặn rủi ro (T1) |
| 3 | Giải ngân đổi đề xuất ngược hẳn sau 1 ngày | lớn | **đã sửa 04/11/2026** (quy tắc "ngang nhau") |
| 4 | Dải giá hẹp quá lúc êm, rộng quá lúc mạnh | vừa | **đã sửa phần lớn hôm nay** |
| 5 | Cùng lỗi đó ở Giá chờ mua / bán, khoảng Xu hướng | vừa | cần đăng ký riêng |
| 6 | Kiểm chứng trực tiếp còn quá ngắn | vừa | chỉ chờ; lịch D1, D2 |
| 7 | Dữ liệu phái sinh trên GitHub chậm tới 1 tháng | nhỏ | cần nguồn khác hoặc chạy ở máy |
| 8 | Ảnh giao diện chỉ được so trên Windows | nhỏ | cần ảnh mốc Linux |
| 9 | Thư viện pandas không khóa phiên bản | nhỏ | **đã sửa hôm nay** |
| 10 | Dải giá neo giá đóng hôm trước | nhỏ | F1 cũ |

### 1. Không thẻ nào đoán được hướng giá (lớn nhất)

**Thấy gì:**
- Thẻ Xu hướng: khi bot nghiêng một phía, bao giờ cũng là nghiêng tăng. Nó đúng 58% (7 ngày), 63% (30 ngày), 62% (90 ngày), bằng đúng mốc "lúc nào cũng nói tăng" trên cùng các lần đó.
- Xác suất có lãi: mô hình 3 chỉ số rẻ có sai số Brier kém hơn tỷ lệ gốc ở 4, 13 và 26 tuần (0,263 / 0,300 / 0,245 so với 0,244 / 0,247 / 0,228). Thẻ đang hiện đúng tỷ lệ gốc.
- Phần I: 0/6 tiêu chí. Price action 0/48, hỗ trợ / kháng cự 0/102, mẫu nến 0/36.

**Vì sao quan trọng:** đây là câu hỏi người dùng muốn bot trả lời nhất ("mua lúc nào, long hay short"). Mọi tín hiệu hiện có đều tính từ cùng một chuỗi giá.

**Cách sửa:**
- Không dò thêm trên chuỗi giá: đã thử hơn 2.000 cấu hình, dò nữa chỉ ra kết quả may rủi.
- Chỉ dữ liệu mới mà giá chưa phản ánh hết mới có thể tạo lợi thế: dòng tiền quỹ ETF (C1), độ dao động kỳ vọng của quyền chọn (F3), funding và hợp đồng mở đủ 1 năm (C2, từ 11/2027).
- Trong lúc chờ: giữ mặc định Mua đều / Hold như hiện nay.

**Câu lệnh:** C1, C3 trong `docs/KE_HOACH_CAI_TIEN.md`; F3 trong `docs/DE_XUAT_NANG_CAP.md`.

### 2. Long/Short: kỳ vọng âm, người dùng có thể dùng đòn bẩy

**Thấy gì:** nếu mỗi tháng làm theo công thức bot chọn lúc đó, kết quả là 167 lệnh, thắng 43% (Wilson 36–51%), tổng −15,1R, trung bình −0,09R mỗi lệnh. 4 trên 6 năm âm (2022 −5,6R, 2023 −4,7R, 2025 −5,1R, 2026 −2,5R). Phía short chưa tháng nào có công thức.

**Vì sao quan trọng:** đây là chỗ duy nhất trên trang có thể làm mất tiền nhanh. Bot đã mặc định Hold và chưa tháng nào đạt 6/6. Nhưng thẻ vẫn hiện giá vào, cắt lỗ, chốt lời rất cụ thể, dễ được hiểu thành lời mời vào lệnh.

**Cách sửa:**
- T1: khối lượng lệnh theo % vốn chấp nhận mất. Mỗi lệnh mất tối đa 1R, nên người dùng thấy ngay 10 lệnh thua liên tiếp là bao nhiêu tiền.
- Dòng cảnh báo đỏ cố định khi R trung bình chấm đi tới < 0. Chỉ hiển thị lại số đã có, không tính số mới.

**Câu lệnh:**
```
Đọc docs/KE_HOACH_SUA_LOI.md mục 2 và docs/DANH_GIA_TONG_QUAN.md mục T1. Thêm vào thẻ Long/Short ô "% vốn chấp nhận mất mỗi lệnh" (mặc định 1%), tính khối lượng và đòn bẩy cần dùng từ khoảng cách cắt lỗ; hiện dòng cảnh báo đỏ lấy từ perp_trade.json khi R trung bình chấm đi tới âm. Không tính con số mới, không đổi kết luận Long/Short. Đăng ký cách hiển thị vào config/candidates.yaml trước, chữ trong vi.yaml, test giao diện ở 1280 và 390, build, pytest.
```

### 3. Giải ngân đổi đề xuất ngược hẳn sau 1 ngày

**Đã sửa 04/11/2026.** Bạn chọn cách "thiết thực, trung thực nhất".
- Đăng ký trước (`plan.stable`, `sell_plan.stable`, commit `1f0756b`): chỉ nêu "đề xuất" khi mọi cách khác đều kém cách tốt nhất đáng kể. Nếu không, trang nói các cách ngang nhau, chỉ ra cách lãi trung vị cao nhất và cách ít thiệt nhất khi gặp lúc xấu, rồi để bạn bấm chọn.
- Đếm lại từng tuần từ 02/01/2022, mỗi tuần chỉ dùng dữ liệu có đến tuần đó (`docs/PLAN_ON_DINH.md`):

| Thẻ | Cách cũ đổi đề xuất | Đảo hẳn (một lần ↔ 52 tuần) | Cách mới đổi lời |
|---|---|---|---|
| Giải ngân (253 tuần) | 27 lần | 11 lần | 0 lần: cả 253 tuần đều "ngang nhau" |
| Chốt lời dần (253 tuần) | 20 lần | 0 | 9 lần; từ 05/2025 luôn "chia 52 tuần" |

- Nghĩa là: từ 2022, lịch sử chưa bao giờ đủ để nói cách giải ngân nào hơn hẳn. Đề xuất cũ là một lựa chọn gần như ngẫu nhiên giữa các cách ngang nhau.
- Cùng đợt, sửa lỗi USD: gõ số tiền rồi bấm ngay nút USD thì lần bấm đầu bị mất, vì trang vẽ lại cả hàng nút đúng lúc bấm. Giờ nút giữ nguyên, có bài kiểm tra bấm chuột thật. Ô USD cũng nhận "$1000", "1000 USD", "1,000.50"; gợi ý và câu báo lỗi theo đúng đơn vị; báo khi số tiền quá nhỏ để chia; số tiền làm tròn không còn ",00" thừa.

**Trước khi sửa:**

**Thấy gì:**
- Ngày 02/11/2026, thẻ Giải ngân đề xuất **giải ngân một lần**. Ngày 03/11/2026 thì đề xuất **chia đều 52 tuần**. Đây là hai đầu ngược nhau.
- Chỉ thêm đúng một tuần bắt đầu vào dữ liệu (`git log -- data/recommendation.json`, mục `plan.recommended`: 1 → 52).
- Phép so chỉ có khoảng 9 đợt độc lập. Các phương án gần như ngang nhau, nên quy tắc "phân vị 10% cao nhất trong các phương án không kém đáng kể" nhảy qua lại.

**Vì sao quan trọng:** người có khoản tiền lớn làm theo đề xuất hôm qua sẽ đổ hết một lần. Hôm nay bot lại nói nên chia một năm. Điều này làm mất lòng tin, và đề xuất không có căn cứ chắc.

**Cách sửa (cần đăng ký trước vì đổi quy tắc):**
- Khi các phương án không khác nhau đáng kể, trang nói thẳng "các cách chia gần như ngang nhau trong lịch sử; chọn theo mức bạn chịu được nếu mua đúng đỉnh" và hiện cả bảng. Không nêu một phương án "đề xuất".
- Hoặc: chỉ đổi đề xuất khi phương án mới giữ vị trí đó ít nhất 4 tuần liên tiếp.
- Sửa cả Chốt lời dần (`sell_plan`), vì nó dùng cùng quy tắc.

**Câu lệnh:**
```
Đọc docs/KE_HOACH_SUA_LOI.md mục 3. Đề đăng ký trước (config/candidates.yaml, mục plan và sell_plan) một quy tắc ổn định cho đề xuất giải ngân / chốt lời dần: khi không phương án nào hơn hẳn thì không nêu "đề xuất" mà nói các cách gần ngang nhau, hoặc chỉ đổi khi giữ vị trí 4 tuần liên tiếp. Cho tôi chọn trước khi sửa. Sau đó sửa bot/models/deploy_plan.py và sell_plan.py, test, build, pytest.
```

### 4. Dải giá hẹp quá lúc êm, rộng quá lúc mạnh (đã sửa phần lớn hôm nay)

**Thấy gì:** cách cũ chia lợi suất cho độ dao động 30 ngày. Nó trúng 80% tính chung, nhưng lệch theo lúc dự báo (hồi cứu từ 2018, lần không chồng nhau):

| Kỳ hạn | Lúc êm (1/3) | Lúc giữa | Lúc mạnh (1/3) |
|---|---|---|---|
| 7 ngày, cách cũ | 73% | 87% | 90% |
| 7 ngày, cách mới | 77% | 84% | 84% |
| 30 ngày, cách cũ | 62% | 88% | 95% |
| 30 ngày, cách mới | 69% | 85% | 95% |

**Đã làm:**
- Đăng ký trước mục `forecast_regime` (commit `8fd2b9c`) trước khi tính số của hai cách mới.
- Chạy một lần. Cách **trộn đều phương sai 30 ngày và 365 ngày** đạt cả ba điều kiện ở giai đoạn xác nhận 2022 → nay:
  - điểm phân vị tốt hơn 1,4% (khoảng tin cậy 0,8% đến 2,0%);
  - dải 80% vẫn trúng 80,2%;
  - độ lệch tỷ lệ trúng giữa các nhóm giảm từ 8,5% xuống 4,5%.
- Dải 30 ngày còn hẹp hơn (trung vị 47,5% so với 53,8%). Chi tiết: `docs/FORECAST_REGIME.md`.
- `price_forecast.bands` dùng cách mới (`vol_long_days: 365`). Nhật ký dự báo sang phiên bản mới: kiểm chứng trực tiếp đếm lại từ hôm nay.

**Còn lại:**
- Dải 30 ngày lúc êm vẫn chỉ trúng khoảng 69%. Cách "theo nhóm độ dao động" sửa phần này tốt hơn, nhưng thua về điểm ở giai đoạn chọn. Quy tắc đã chốt nên không được chọn lại. Muốn thử phải đăng ký mới, với giai đoạn kiểm tra là dữ liệu sau ngày đăng ký.
- Những lần trượt xa nhất là các cú nhảy 5–10 lần độ dao động (11/2018, 03/2020, 11/2024, 08/2026). Không dải nào bắt được chúng. Luôn đặt cắt lỗ ngoài dải.

### 5. Cùng lỗi đó ở Giá chờ mua / bán, khoảng của Xu hướng, Kiểm tra điểm vào

**Thấy gì:** các công cụ này dùng cùng độ dao động 30 ngày.
- Khả năng chạm giá chờ mua đúng tỷ lệ tính chung: bot nói 51% thì chạm 52%.
- Từng năm lệch qua lại khá xa: −3% / 7 ngày năm 2019 nói 61%, chạm 77% (Wilson 64–86%); năm 2023 nói 52%, chạm 38% (26–52%). Giá chờ bán năm 2017: nói 69%, chạm 88%.
- R1 (`docs/R1_GIA_CHO_BAN.md`) kết luận không lệch có hệ thống ở hai nửa giai đoạn. So nhiều năm × nhiều mức thì vài ô lệch là có thể do may rủi. Vì vậy đây mới là **giả thuyết** (cùng nguyên nhân với mục 4), chưa phải lỗi đã chứng minh.

**Cách sửa:** đăng ký riêng một phép so giống `forecast_regime` cho `entry_timing` và `exit_timing` (trộn độ dao động 30 + 365 ngày), chấm bằng Brier của khả năng chạm. Chỉ đổi nếu thắng ở giai đoạn xác nhận. Khoảng của thẻ Xu hướng làm sau, vì Holm 80 phép so của nó đã chốt.

**Câu lệnh:**
```
Đọc docs/KE_HOACH_SUA_LOI.md mục 5 và docs/FORECAST_REGIME.md. Đăng ký trước (config/candidates.yaml, mục mới entry_regime) phép so khả năng chạm giá chờ mua và giá chờ bán: cách đang dùng (độ dao động 30 ngày) với cách trộn đều phương sai 30 và 365 ngày; thước đo Brier của các mức ±1, 2, 3, 5, 8% ở 1, 3, 7, 30 ngày; chọn trên 2016–2021, xác nhận 2022 → nay, chỉ đổi khi khoảng tin cậy của mức cải thiện nằm hẳn trên 0 và độ hiệu chỉnh theo nhóm độ dao động tốt hơn. Lưu git trước khi tính. Module mới, test rò rỉ có cài thử lỗi. Chỉ sửa entry_timing.py / exit_timing.py nếu đạt (phiên bản nhật ký mới).
```

### 6. Kiểm chứng trực tiếp còn quá ngắn

**Thấy gì:**
- Dải giá: 15 dự báo đã đến hạn, từ 5 ngày ghi, trúng 9/15 = 60% (Wilson 36–80%). Quá ít để kết luận đúng hay sai.
- Giá chờ mua / bán: mỗi bên 1 dự báo đến hạn.
- Nhật ký đi tới của khuyến nghị tuần: 2 tuần.
- Long/Short có cắt lỗ: 0 lệnh.

**Vì sao quan trọng:** hồi cứu dùng dữ liệu mà các kiểm định đã xem. Chỉ nhật ký ghi thật mỗi ngày mới chứng minh được bot đúng với tương lai.

**Cách sửa:** chỉ có chờ. Làm đúng lịch D1 (khoảng 30/11/2026), D2 (25/04/2027, 24/10/2027) và chấm 1 năm (11/2027) trong `docs/KE_HOACH_CAI_TIEN.md`. Dải giá vừa đổi phiên bản, nên D1 đếm theo phiên bản mới.

### 7. Dữ liệu phái sinh trên GitHub chậm

**Thấy gì:** máy chủ GitHub ở Mỹ bị Binance chặn (HTTP 451), nên funding lấy từ kho lưu trữ.
- Funding mới nhất là 31/10/2026, chậm tới khoảng 1 tháng ở file theo tháng.
- Nến giờ dừng lúc 09:00 ngày 02/11.
- Trong `perp_trade.json` ghi lúc Daily, tín hiệu "funding ngược" đang trống (`null`).
- Trên trang, lúc bấm Chạy thì trình duyệt tự lấy lại từ `fapi.binance.com`, nên ở Việt Nam vẫn có số mới.

**Cách sửa:** thêm nguồn funding công khai không chặn máy chủ Mỹ làm dự phòng (cần kiểm tra điều khoản). Hoặc ghi rõ trên thẻ "số lúc Daily chậm, bấm Chạy để lấy mới".

**Câu lệnh:**
```
Đọc docs/KE_HOACH_SUA_LOI.md mục 7. Tìm nguồn funding rate BTCUSDT vĩnh cửu công khai truy cập được từ máy chủ GitHub ở Mỹ (điều khoản, độ trễ, lịch sử). Báo tôi trước khi viết bộ tải. Không đổi tín hiệu hay kết luận Long/Short.
```

### 8. Ảnh giao diện chỉ được so trên Windows

**Thấy gì:** `tests/test_ui_snapshot.py` chỉ so ảnh với ảnh mốc cùng hệ điều hành. Git chỉ có `tests/snapshots/ui/win32/`. Trên GitHub (Linux) và trên Mac, bài kiểm tra tự tạo ảnh mốc mới rồi cho qua. Lỗi hình ảnh (vỡ khung, chồng chữ) không bị bắt ở đó. Chữ và kiểu dáng thì vẫn được so ở mọi nơi.

**Cách sửa:** cho CI tải ảnh mốc Linux lên dạng artifact. Bạn duyệt rồi lưu vào `tests/snapshots/ui/linux/`. Từ đó CI so thật.

**Câu lệnh:**
```
Đọc docs/KE_HOACH_SUA_LOI.md mục 8. Sửa .github/workflows/ci.yml để khi thiếu ảnh mốc Linux thì tải các ảnh vừa chụp lên dạng artifact và ghi cảnh báo vào tóm tắt (không im lặng cho qua). Sau khi tôi duyệt ảnh, lưu chúng vào tests/snapshots/ui/linux/.
```

### 9. Thư viện pandas không khóa phiên bản (đã sửa hôm nay)

**Thấy gì:** máy đang dùng pandas 3.1. pandas báo `DatetimeIndex.weekday` sẽ bị bỏ ở pandas 4. Dòng này nằm trong `bot/features/weekly_close.py`, file bị khóa của nhật ký đi tới. Khi pandas 4 ra, Daily sẽ hỏng, và muốn sửa thì phải đóng băng nhật ký lại từ đầu.

**Đã làm:** `requirements.txt` và `pyproject.toml` khóa `pandas>=2.2,<4`. Khi nào cần đóng băng nhật ký phiên bản mới (sau D2), sửa luôn dòng đó.

### 10. Dải giá neo giá đóng hôm trước

**Thấy gì:** thẻ Dự báo tính từ giá đóng ngày hôm trước, không theo giá lúc xem. Lệch nhỏ, vài trăm đô. **Cách sửa:** câu lệnh F1 trong `docs/DE_XUAT_NANG_CAP.md`.

## Thứ tự nên làm

1. ~~Mục 3 (Giải ngân ổn định)~~: đã xong 04/11/2026.
2. Mục 2 (T1 cho Long/Short).
3. Mục 5 (giá chờ mua / bán theo cách trộn độ dao động): cùng cách vừa thắng ở dải giá.
4. Mục 8, 7.
5. Mục 1: theo lịch dữ liệu mới (C1, F3, C2).

Công cụ tham khảo, không phải lời khuyên đầu tư.
