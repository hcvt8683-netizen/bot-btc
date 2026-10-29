# Nhật ký xây lại kiểm định và mô hình (Phần A → I)

Làm trên nhánh `rebuild/kiem-dinh`, chưa đưa lên trang web. Mỗi phần: làm xong → tóm tắt → chờ xác nhận. Mọi thay đổi thiết kế sau khi đã xem kết quả đều được ghi ở đây.

## Phần A: Dữ liệu (xong 29/10/2026, chờ xác nhận)

**Đã làm**
- Cập nhật dữ liệu đến 28–29/10/2026. Funding, khối lượng hợp đồng mở và hợp đồng quý của Binance tải từ máy ở Việt Nam, vì máy chủ GitHub bị chặn.
- **Bài kiểm tra rò rỉ viết trước tiên** (`tests/test_leak.py`): xóa, xáo trộn hoặc nhân 3,7 mọi dữ liệu sau một tuần t thì bảng tuần đến t phải giữ nguyên từng giá trị. Kết quả đạt. Đã thử cài cố ý hai kiểu nhìn trước (xếp hạng trên toàn bộ dữ liệu; dùng giá trị tuần sau) và bài kiểm tra đều báo sai, nên nó bắt được rò rỉ thật.
- Nguồn mới:
  - Bitstamp: giá ngày từ 18/08/2011.
  - CoinGecko: chỉ 365 ngày; bản miễn phí không cho lịch sử dài hơn.
  - FRED `DFEDTARU`: trần lãi suất Fed.
  - Coin Metrics thêm `AssetEODCompletionTime` (giờ chốt số liệu), `volume_reported_spot_usd_1d` (khối lượng giao ngay từ 2011), `SplyCur`, `IssTotNtv`.
- **Bảng tuần theo giá đóng Chủ nhật** (`bot/features/weekly_close.py`), từ 18/07/2010, 850 tuần, không thiếu tuần nào. Mọi chỉ số chuẩn hóa bằng phân vị trượt 4 năm (208 tuần, cần ít nhất 104 tuần), chỉ dùng dữ liệu quá khứ, không dùng ngưỡng tuyệt đối.
- Chỉ báo thay thế Fear & Greed có lịch sử từ 2010: biến động thực 30 ngày, mức giảm từ đỉnh, độ lệch giá so với MA 20 tuần, RSI 14 tuần. Khối lượng tương đối giờ có từ 2011 nhờ khối lượng của Coin Metrics, thay cho Binance (từ 2017).
- Chế độ Fed (tăng / giữ / giảm theo thay đổi trần lãi suất trong 26 tuần trước). Chỉ dùng để chia nhóm khi báo cáo, không đưa vào mô hình.
- Báo cáo chất lượng dữ liệu: `docs/DATA_REPORT.md` và `data/results/data_quality.json`. Bản kê dữ liệu kèm mã băm SHA-256 của từng file, giờ tải, mã git, mã cấu hình và hạt giống ngẫu nhiên: `data/manifest.json`. Lệnh: `python -m bot.cli data-report`.

**Kết quả chính**
| Mục | Kết quả |
|---|---|
| Dòng ngày d của Coin Metrics | là **giá đóng cửa ngày d**: lệch trung vị 0,13% so với Binance, 0,14% so với Bitstamp, 0,07% so với CoinGecko; lệch 1 ngày thì sai khoảng 1,5% |
| Đối chiếu Bitstamp theo giai đoạn | 2010–2013 lệch trung vị 0,85%, có ngày tới 77% (thời Mt.Gox, các sàn rất lệch nhau); 2014–2016: 0,23%; 2017–2020: 0,14%; 2021–nay: 0,08% |
| Đối chiếu Binance | 2017–2020: 0,24% (lớn nhất −10,8% ngày 23/12/2017); 2021–nay: 0,10% |
| Coin Metrics community | có MVRV, vốn hóa, phát hành, hash rate; **không có** vốn hóa thực (`CapRealUSD`, đã tự tính bằng vốn hóa / MVRV) và doanh thu thợ đào (`RevUSD`, Puell dùng phát hành) |
| Độ trễ công bố Coin Metrics | trung vị 27 giờ sau 00:00 ngày d (90% trong 28 giờ, chậm nhất 42 giờ), tức có vào sáng thứ Hai giờ Việt Nam. Giờ chốt của dữ liệu cũ đã bị tính lại về sau, nên không dùng làm thời điểm công bố lịch sử |
| Có phân vị từ | MVRV, giảm từ đỉnh 07/2012; Mayer 01/2013; Pi, Puell 06/2013; MA 200 tuần 05/2016; Fear & Greed 02/2020 |
| Thay thế Fear & Greed (tương quan thứ hạng, 352 tuần chung) | độ lệch so với MA 20 tuần **0,89**; RSI 14 tuần 0,78; giảm từ đỉnh 0,55; biến động 30 ngày −0,18 |
| Chế độ Fed từ 2011 | tăng 260 tuần / 4 đợt; giữ 430 / 7; giảm 136 / 3. Hiện tại: **tăng** (Fed nâng trần lên 4,00% ngày 17/09/2026) |
| Tuần bất thường (> 5σ, giữ nguyên, chỉ đánh dấu) | 01/05/2011 (+90%), 05/06/2011 (+97%), 14/04/2013 (−45%) |

**Thay đổi thiết kế so với bản trước (ghi theo yêu cầu)**
- Lưới tuần đổi từ "quyết định thứ Ba, mua giá đóng thứ Ba" sang **giá đóng Chủ nhật**, đúng nguyên tắc mới. Thay đổi quyết định trước khi chạy bất kỳ kiểm định nào của bản mới.
- Giá Coin Metrics là nguồn giá duy nhất cho mô hình. Bitstamp, Binance, CoinGecko chỉ dùng đối chiếu: Coin Metrics là giá tổng hợp, còn các sàn lệch nhau nhiều trước 2014.

**Câu hỏi cần bạn quyết trước Phần B**
1. Tín hiệu tính ở giá đóng Chủ nhật, nhưng số liệu chỉ có vào sáng thứ Hai. Khi chấm điểm, mua theo giá nào?
   - (a) giá đóng Chủ nhật, đúng chữ trong bản kế hoạch, hơi lạc quan khoảng 1 ngày;
   - (b) giá đóng thứ Hai, thận trọng hơn; tôi đề xuất cách này.
2. Holdout mới bắt đầu từ 01/01/2024, theo bản kế hoạch. Như bản kế hoạch đã nói, giai đoạn này con người đã từng xem (giai đoạn 7 trước dùng 2023 trở đi). Nên chỉ nhật ký đi tới (Phần H) mới là kiểm định ngoài mẫu thật.
