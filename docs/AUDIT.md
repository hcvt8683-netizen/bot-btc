# Kiểm toán bot BTC (Giai đoạn 0)

Ngày kiểm toán: 28/10/2026. Nhánh `upgrade/best-roi`, bản gốc được gắn thẻ `v1-before-upgrade` (commit 92d0762).
Giai đoạn này không đổi hành vi của bot. Các con số kiểm chứng bên dưới được tính lại từ dữ liệu thật đã lưu trong `du_lieu_tam/` (dữ liệu đến 26/10/2026), bằng chính mã hiện tại.

## 1. Bản đồ mã nguồn

| File | Vai trò |
|---|---|
| `src/engine.js` (đối tượng `BOT`) | Ghép dữ liệu (`buildSeries`), tính 10 chỉ số (`computeRaw`), chuẩn hóa phân vị (`pctAt`, `featAt`), hồi quy logistic L2 (`fitLogit`, `predLogit`), Wilson, nghiên cứu khối lượng (`volumeStudy`). |
| `src/analysis.js` (đối tượng `B3`) | Logic giao diện đang dùng: `analyze` (tỷ lệ nên mua/bán theo tuần), `search` (tìm bộ chỉ số), `compareOptions` (PA1–PA6), `sellSide` (bên bán), `priceLevels` (giá đề xuất), `report` (.md), CSV. |
| `src/ui.js` | Toàn bộ giao diện: tải dữ liệu, chọn bộ chỉ số, vẽ bảng và biểu đồ canvas, xuất file, gọi Claude API. |
| `src/page.html` | Khung trang và toàn bộ CSS (giao diện), 3 chỗ đánh dấu `/*CORE*/ /*B3*/ /*UI*/`. |
| `build.py` | Ghép thành một file `bot-xac-suat.html`; `--zip` đóng gói cho Windows và Mac. |
| `chay_bot_xac_suat.py` | Máy chủ cục bộ cổng 8789 (chỉ 127.0.0.1), chuyển tiếp yêu cầu tới 5 nguồn được phép, lưu bản sao vào `du_lieu_tam/` để dùng khi mất mạng. |
| `Mo-Bot-BTC.bat`, `Mo-Bot-BTC.command`, `HUONG_DAN_*.txt` | Mở bot bằng bấm đúp và hướng dẫn cho người dùng. |
| `tests/test_engine.js` | 21 bài kiểm tra tính toán, có bài kiểm tra không nhìn trước tương lai tại 19/06/2022. |
| `tests/test_browser.py` | Kịch bản thử giao diện bằng tay (Playwright), không phải bài kiểm tra tự động. |

**Mã không còn dùng:** trong `engine.js`, các hàm `BOT.analyze`, `walkForward`, `metrics`, `greedy`, `simulate`, `recommend`, `buildLog`, `buildReport`, `exportJSON` cùng các hằng `LEVELS`, `HOLD`, `FRAMES`, `ERAS`, `MULT`, `SELL` là của phiên bản cũ. Giao diện và `analysis.js` không gọi tới (đã kiểm tra bằng tìm kiếm). Khoảng 120/161 chuỗi tiếng Việt trong `engine.js` nằm ở phần mã chết này.

## 2. Luồng dữ liệu

1. Trình duyệt tải trực tiếp: Coin Metrics community (`PriceUSD, CapMrktCurUSD, CapMVRVCur, IssTotUSD` từ 18/07/2010), Alternative.me Fear & Greed (từ 02/2018), Binance nến ngày BTCUSDT (từ 17/08/2017, có khối lượng), giá trực tiếp Binance hoặc CoinGecko. Khi chạy qua `chay_bot_xac_suat.py`, mọi yêu cầu đi qua `/proxy` và được lưu bản sao.
2. `buildSeries` ghép theo ngày (ưu tiên Coin Metrics, thiếu thì dùng giá Binance), lấp ngày trống bằng ngày trước, ước tính vốn hóa và MVRV cho tối đa 3 ngày cuối Coin Metrics chưa công bố, rồi thêm dòng "hôm nay" theo giá trực tiếp.
3. `computeRaw` tính 10 chỉ số theo ngày (xem mục 4).
4. Khi trang mở: `search` (tìm bộ chỉ số) → `compareOptions` (6 phương án) → `analyze` bộ đang chọn (mặc định: phương án hạng 1) → `priceLevels` → `sellSide` → vẽ giao diện.
5. Không có máy chủ nào tính sẵn: mỗi người xem tự tính lại trên máy của mình (khoảng 10–40 giây).

## 3. Lưu trữ và đăng trang web hiện tại (mục 10.1)

- Thư mục dự án không có `.github/workflows/`, nhánh `gh-pages`, `CNAME`, thư mục `docs/` làm nguồn Pages, `netlify.toml` hay `vercel.json`. Kho git trên máy chưa nối với GitHub (không có `remote`).
- Trang web đang chạy: https://hcvt8683-netizen.github.io/bot-btc/ (trả về 200). Đó là kho công khai riêng `hcvt8683-netizen/bot-btc`, nhánh duy nhất `main`, chỉ có một file `index.html` tải lên bằng tay ngày 27/10/2026 (bản sao của `bot-xac-suat.html`, giống từng byte với `dist/web/index.html`). Pages lấy từ nhánh `main`, thư mục gốc (người dùng tự cài trên trang GitHub; API công khai không cho đọc cài đặt này).
- Kết luận: **chưa có triển khai tự động**. Theo mục 10.1, giai đoạn 9 sẽ dùng GitHub Pages + GitHub Actions, giữ nguyên địa chỉ trang. Không có tên miền riêng.

## 4. Cách tính từng con số trên báo cáo

### 4.1 Chỉ số (theo ngày, `computeRaw`)
| Chỉ số | Công thức trong mã | Đưa vào mô hình |
|---|---|---|
| Fear & Greed | giá trị Alternative.me | giá trị/100 |
| MVRV | `CapMVRVCur` | phân vị trong 1.461 ngày gần nhất (cần ≥ 365 số liệu) |
| MVRV Z-Score | (vốn hóa − vốn hóa/MVRV) / độ lệch chuẩn mở rộng của vốn hóa | phân vị 4 năm |
| Giá / MA 200 tuần | giá / trung bình 1.400 ngày | phân vị 4 năm |
| Mayer | giá / trung bình 200 ngày | phân vị 4 năm |
| RSI 14 tuần | RSI trên giá cách nhau 7 ngày, 14 bước | giá trị/100 |
| Pi Cycle | trung bình 111 ngày / (2 × trung bình 350 ngày) | giá trị gốc |
| Puell | phát hành USD / trung bình 365 ngày (cần ≥ 300 ngày có số liệu) | phân vị 4 năm |
| Giảm từ đỉnh | (1 − giá/đỉnh cao nhất đến hôm đó) × 100 | giá trị/100 |
| Khối lượng tương đối | khối lượng quote 30 ngày / 365 ngày (Binance) | giá trị gốc |

### 4.2 Tỷ lệ nên mua, nên bán (`B3.analyze`)
- Mẫu: mỗi Chủ nhật đến trước ngày phân tích, cộng chính ngày phân tích.
- Với từng kỳ giữ H (mua: 4, 13, 26, 52 tuần; bán: 13, 26 tuần), mô hình logistic L2 (λ = 2) học theo kiểu đi tới. Nhãn mua: giá sau H tuần cao hơn. Nhãn bán: giá sau H tuần giảm hơn 10%. Một mẫu chỉ vào tập học khi nhãn của nó đã kết thúc (k + H ≤ j). Cần tối thiểu 78 mẫu; học lại mỗi 4 tuần.
- Mức chênh `e = p − p0`, trong đó `p0` là tỷ lệ nhãn dương trung bình đã biết. "Vị trí" là phân vị của `e` trong thang so sánh: mức chênh dự báo lại của mọi mẫu đã học, tính bằng mô hình vừa học.
- **Tỷ lệ nên mua** = trung bình vị trí của 4 kỳ giữ. Phải mua ≥ 80, Cân nhắc mua 60–80. **Tỷ lệ nên bán** = trung bình 2 kỳ. Nên bán ≥ 85, Cân nhắc bán 70–85.
- Bảng "Bộ tiêu chí": với mỗi khung, tỷ lệ thắng thực tế ở từng kỳ giữ, Wilson 95% tính trên **số tuần**. Đợt độc lập = chuỗi tuần liền nhau cùng khung.
- Ô "Xác suất thắng nếu mua": các tuần trước có mức chênh gần mức hôm nay (dải ±0,03, nới dần đến khi có ≥ 25 tuần), tỷ lệ thắng của những tuần đó, Wilson.
- Trọng số trên giao diện: hệ số chuẩn hóa của mô hình 6 tháng × chiều kinh tế (`dir`).

### 4.3 So sánh phương án và "bộ tốt nhất"
- `compareOptions`: chạy PA1–PA6 tại ngày phân tích; giai đoạn chấm chung bắt đầu từ ngày muộn nhất trong các phương án nhưng không trước 01/01/2021. Hạng xếp theo **trung bình cận dưới Wilson của tỷ lệ thắng khung Phải mua** qua các kỳ giữ có ≥ 10 tuần, với điều kiện khung có ≥ 20 tuần và ≥ 2 đợt. Phương án ít tín hiệu xếp sau theo khung từ 60%. Nút mặc định "Tự động: phương án tốt nhất" dùng hạng 1 cho đồng hồ chính.
- `search` (PA6 "Bộ bot tự tìm"): thêm dần từng chỉ số (tối đa 6), mỗi bước chọn chỉ số làm tăng nhiều nhất cùng mục tiêu trên cùng giai đoạn, dừng khi tăng < 0,005. Sau đó xếp hạng thêm 4 bộ cố định và từng chỉ số riêng.

### 4.4 Giá đề xuất, bên bán, khối lượng
- Giá đề xuất (`priceLevels`): tính lại chỉ số với giá giả định tại ngày phân tích, giữ nguyên mô hình đã học; dò giá mỗi bước 1%, rồi chia đôi.
- Bên bán (`sellSide`): 13 tiêu chí (7 ngưỡng kinh điển, 5 ngưỡng "5% cao nhất 4 năm", 1 mô hình). Đợt = các tuần bật cách nhau ≤ 8 tuần. "Đúng" = giá 182 ngày sau thấp hơn. Tiêu chí đáng tin khi có ≥ 3 đợt và cận dưới Wilson cao hơn mốc. Đếm số nhóm đáng tin đang bật: 1 nhóm → Chốt lời một phần, 3 nhóm → Bán phần lớn. Mô phỏng giữ 1 BTC từ 2014, 2018, 2021.
- Khối lượng (`volumeStudy`): phân loại tuần theo biến động giá và khối lượng so với trung bình 20 tuần, kèm tỷ lệ thắng 4 và 13 tuần sau.

## 5. Rủi ro nhìn trước tương lai
1. **Độ trễ công bố của Coin Metrics.** Mẫu Chủ nhật dùng MVRV, vốn hóa và phát hành của chính ngày đó, nhưng Coin Metrics công bố sau ít nhất 1 ngày (đã gặp thực tế: thiếu MVRV ngày cuối). Trong kiểm tra lịch sử, bot dùng trước khoảng 1 ngày. Ảnh hưởng nhỏ với chỉ số chậm, nhưng trái quy tắc "ghép theo thời điểm công bố".
2. **Mua đúng giá đóng cửa dùng để tính tín hiệu.** Các phép đo lịch sử (tỷ lệ thắng, mô phỏng bên bán) giả định mua hoặc bán ngay ở giá đóng cửa đã dùng để tính chỉ số. Thực tế cần một khoảng trễ.
3. **Chọn bộ chỉ số trên cùng dữ liệu dùng để báo kết quả** (thiên lệch chọn lựa, mục 7).
4. **Dữ liệu đã chỉnh sửa về sau.** Coin Metrics trả về bản số liệu mới nhất. Quá khứ có thể đã được sửa, nên đây không phải ảnh chụp đúng lúc đó.
5. Những phần đã đúng: phân vị chỉ dùng dữ liệu quá khứ; thang so sánh `ref` chỉ gồm mẫu đã biết kết quả; ngưỡng khung cố định; đỉnh cao nhất và độ lệch chuẩn MVRV Z là đại lượng mở rộng; bài kiểm tra 19/06/2022 trong `test_engine.js` vẫn đúng.

## 6. Thổi phồng số mẫu do nhãn chồng nhau
- Mẫu lấy mỗi tuần nhưng nhãn kéo dài 4–52 tuần. Với kỳ 26 tuần, 26 tuần liền nhau có nhãn gần như trùng nhau. Số mẫu thật sự độc lập chỉ khoảng **số tuần ÷ H**.
- Khoảng tin cậy Wilson trên giao diện tính trên số tuần, nên **hẹp hơn thực tế nhiều lần**. Ví dụ: PA3 khung Phải mua có 80 tuần nhưng chỉ 5 đợt. Khoảng tin cậy hiển thị chỉ hợp lý nếu có 80 mẫu độc lập.
- Mô hình logistic học trên các mẫu chồng nhau, không có cắt bỏ (purge) hay khoảng đệm (embargo). Không rò rỉ vì chỉ dùng nhãn đã kết thúc, nhưng mô hình tự tin quá mức.
- Bên bán gộp tuần thành đợt (cách nhau ≤ 8 tuần) nên đếm sát thực tế hơn.

## 7. Cách chọn "bộ tốt nhất" và số lần thử
- Mỗi lần chạy, `search` đánh giá khoảng 10 chỉ số riêng + tối đa 6 vòng × 10 tổ hợp + 4 bộ cố định (khoảng 40–70 lần thử), cộng 6 phương án. Tất cả đều trên cùng giai đoạn từ 2021, rồi chọn bộ cao nhất và báo luôn tỷ lệ thắng của bộ đó trên chính giai đoạn ấy. Không có điều chỉnh cho việc thử nhiều lần.
- Giao diện chỉ cảnh báo khi bộ được tìm bằng dữ liệu **sau** ngày phân tích. Với ngày hôm nay, không có cảnh báo dù kết quả là trong mẫu.

## 8. Kiểm chứng 7 giả thuyết ở mục 0 (dữ liệu thật đến 26/10/2026)
| # | Giả thuyết | Kết luận | Bằng chứng |
|---|---|---|---|
| 1 | Mục tiêu là tỷ lệ thắng | **Đúng** | Nhãn là "giá sau H cao hơn"; mục tiêu xếp hạng là cận dưới Wilson của tỷ lệ thắng. Không có lợi nhuận hay giá vốn (mô phỏng 100 $/tuần cũ là mã chết). |
| 2 | Lịch sử ngắn | **Đúng** | Chấm từ 01/01/2021; PA3 Phải mua 80 tuần, **5 đợt**; Pi riêng 66 tuần, 2 đợt. Tiêu chí bán có 2–7 đợt (RSI ≥ 80: 17). |
| 3 | Thiên lệch chọn lựa | **Đúng** | Mục 7. |
| 4 | Không ổn định | **Đúng** | PA1 Phải mua thắng 22/22/27/24% (1t/3t/6t/1n), PA2 21/21/28/21%; mốc 51/51/60/53%. PA4 6 tháng: nửa đầu 60% (40 tuần), nửa sau 25% (4 tuần). Trọng số PA3: Fear & Greed −1,09, Pi −0,21, MVRV +1,37. |
| 5 | 10 chỉ số kém hơn chỉ Pi | **Đúng** | "Tất cả chỉ số" thắng 59% sau 6 tháng (37 tuần, 4 đợt) so với Pi riêng 84% (68 tuần, 2 đợt). Pi có ít đợt hơn nên 84% cũng chưa đáng tin. |
| 6 | Không có lợi thế ở 1 tháng | **Đúng** | PA3 Phải mua thắng 54% sau 1 tháng, mốc 51%. 8/10 chỉ số là chỉ số chu kỳ chậm. |
| 7 | Khung bậc thang, không định cỡ lệnh, không so với DCA | **Đúng** | Giao diện chỉ có 3 khung, không có số tiền đề xuất hay so sánh mua đều. |

## 9. Giao diện hiện tại (mục 6.4, không được đổi)
Toàn bộ định nghĩa nằm trong khối `<style>` của `src/page.html`. Màu trên canvas đọc từ biến CSS; màu theo khung đặt ở `ZCOL`, `FAMCOL`, `VTONE` trong `src/ui.js`. Bản chụp chính xác: `tests/snapshots/theme.css`, `ui_styles_*.json`, ảnh trong `tests/snapshots/ui/win32/`.

- **Màu (sáng / tối):** nền `--bg` #EEF1F4 / #0F151C; khung `--panel` #FFFFFF / #18212B; chữ `--ink` #17212C / #E5EAEF; chữ phụ `--muted` #5C6773 / #98A4B0; viền `--line` #D5DCE2 / #2C3946; nền nhạt `--soft` #F4F6F8 / #1F2a35; xanh ngọc `--jade` #1E7B57 / #5BC496 (Phải mua, tốt); vàng đồng `--brass` #9A6B12 / #DDB160 (Cân nhắc); đỏ son `--cinnabar` #B23A27 / #EB8570 (Nên bán, xấu); xanh dương `--blue` #2B5BA8 / #84A9EC (ngày phân tích, nhãn). Chế độ tối theo cài đặt máy (`prefers-color-scheme`).
- **Phông:** Be Vietnam Pro 400/500/600/700 (Google Fonts), dự phòng Segoe UI, system-ui, Arial. Chữ thân 15px/1,55; h1 18px đậm 700; h2 19px 700; dòng dẫn `.lead` 14px màu phụ; số dùng `font-variant-numeric: tabular-nums` (`.num`).
- **Bố cục:** khung rộng tối đa 1.100px, đệm 18px; các khung `.panel` bo góc 14px, đệm 18×20px, cách nhau 16px; lưới `.duo`, `.tiles`, `.two` tự xuống hàng; dưới 680px nhãn điều khiển nằm trên.
- **Bảng:** chữ 14px, ô đệm 9×12px, đường kẻ ngang `--line`, tiêu đề 13px màu phụ trên nền `--soft`, không xuống dòng; cột số căn phải (`.r`); dòng mốc `tr.base` màu phụ; dòng hiện tại `tr.here` nền xanh dương nhạt, ô đầu đậm; chữ phụ `.sub` 12px; bảng rộng cuộn ngang trong `.scroll` (viền, bo 12px).
- **Thành phần khác:** nút `.btn` và `.btn.main` (nền mực); nút tròn `.seg`; nhãn `.tag` (xanh dương nhạt); hộp cảnh báo `.warn` (vàng đồng nhạt); hộp đồng thuận `.cons`; đồng hồ `.gauge` số 58px; ô `.tile` số 40px; thanh khung `.zbar`.
- **Đậm và biểu tượng:** dùng `<b>` cho nhãn chính và con số; báo cáo .md dùng `**đậm**` cho tỷ lệ và khung. Giao diện **không dùng emoji**; ký hiệu dùng: ≤ ≥ – → … ⚠ (chưa dùng).
- **Thứ tự phần, bên mua:** đầu trang (tên, giá, thời điểm) → bảng điều khiển → đồng hồ mua/bán → Giá đề xuất mua và bán → So sánh các phương án (2 biểu đồ) → Xác suất thắng nếu mua và giữ → Bộ tiêu chí đánh giá → Bộ chỉ số khuyến cáo → Tỷ lệ nên mua, nên bán qua thời gian → Giá trị các chỉ số → Biểu đồ từng chỉ số → Hỏi Claude → Nguồn dữ liệu → câu miễn trừ.
- **Thứ tự phần, bên bán:** Nên giữ hay chốt lời → Giữ tiếp có lợi không → Bộ tiêu chí chốt lời → Mốc giá chốt lời → Các lần tiêu chí bật → Nếu đã giữ 1 BTC → đồng hồ → Giá đề xuất → các phần chung.

## 10. Chữ hiển thị đang viết cứng
Danh sách đầy đủ từng chuỗi kèm số dòng: [`docs/AUDIT_STRINGS.md`](AUDIT_STRINGS.md) (tạo bằng `python tools/list_strings.py`). Tổng 688 chuỗi tiếng Việt:

| File | Số chuỗi | Ghi chú |
|---|---|---|
| `src/page.html` | 80 | tiêu đề phần, dòng dẫn, nút, nhãn |
| `src/ui.js` | 233 | câu ghép với số liệu, tiêu đề bảng, nhãn biểu đồ, thông báo lỗi, lời nhắc hệ thống gửi Claude |
| `src/analysis.js` | 125 | báo cáo .md, tên khung, tên phương án, tiêu chí bán, tiêu đề cột CSV |
| `src/engine.js` | 161 | tên và giải thích 10 chỉ số, thông báo lỗi dữ liệu; khoảng 120 chuỗi thuộc mã chết |
| `chay_bot_xac_suat.py`, `build.py` | 8 | thông báo dòng lệnh |
| `Mo-Bot-BTC.command`, `HUONG_DAN_*.txt` | 81 | hướng dẫn người dùng (file `.bat` chỉ dùng ASCII) |

Ngoài ra có nhãn ASCII hiển thị: `MVRV`, `Pi`, `F&G`, `Fear & Greed`, hậu tố `k` trên trục, ` $`.

**Định dạng số:** có ba bộ hàm định dạng trùng nhau (`ui.js`: `nf, usd, pc, spc, fmtDate`; `analysis.js`: `P, SP, D, usdT`; `engine.js`: `P, D, PC, SPC, SK, USD`). Phần lớn đã đúng kiểu Việt Nam (`80.754 $`, `0,49`, `28/10/2026`). Lệch chuẩn đã thấy:
- `analysis.js` báo cáo .md: cột "Quy ra BTC" dùng `toFixed(3)` nên ra dấu chấm thập phân (`1.234`).
- Dấu âm: giao diện dùng "−" (U+2212), báo cáo .md dùng "-".
- CSV cố ý dùng dấu chấm thập phân (theo CLAUDE.md, để Excel đọc được); đây không phải giao diện.

## 11. Kiểm tra đã thêm ở giai đoạn này
- `tests/snapshot_report.js` (+ `tests/test_js.py`): đóng băng báo cáo .md và 3 file CSV trên bộ dữ liệu giả lập cố định đến 27/10/2026 (`tests/snapshots/report.md`, `weekly.csv`, `options.csv`, `sell.csv`).
- `tests/test_ui_snapshot.py`: mở trang thật trong Chromium với dữ liệu giả lập cố định và đồng hồ cố định (03:00 UTC 28/10/2026), ở 3 khung nhìn (1280 sáng, 390 sáng, 1280 tối). Đóng băng toàn bộ chữ bên mua và bên bán, kiểu dáng tính toán của 20 thành phần, khối CSS, và ảnh chụp (so sánh ảnh chỉ trên cùng hệ điều hành). Kiểm tra không có lỗi JavaScript và không cuộn ngang.
- `tests/gen_data.js` thêm hàm `make(ngày cuối)` để có dữ liệu cố định; dữ liệu mặc định giữ nguyên như cũ.
- Lệnh: `python -m pytest` (chạy cả `node tests/test_engine.js`). Cập nhật ảnh chụp sau khi duyệt: `UPDATE_SNAPSHOTS=1 python -m pytest` và `node tests/snapshot_report.js --update`.
