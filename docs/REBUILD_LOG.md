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

**Quyết định của bạn (29/10/2026):** chấm điểm bằng **giá đóng thứ Hai**. Tín hiệu vẫn tính ở giá đóng Chủ nhật. Ghi trong `config/bot.yaml`, mục `rebuild.execution: monday_close`.

## Phần B: Thước đo (xong 29/10/2026, chờ xác nhận)

**Đã làm** (`bot/backtest/measure.py`, cấu hình cố định ở `config/bot.yaml` mục `rebuild`)
- **Lợi thế giá vốn so với mua đều, cùng tổng tiền nạp.** Có quỹ dự trữ: tuần mua ít thì phần dư vào quỹ, tuần mua nhiều thì rút từ quỹ, không bao giờ vay. Tiền dư cuối kỳ tính theo giá cuối kỳ. Khi đó lợi thế giá vốn đúng bằng (tỷ số tài sản − 1); bài kiểm tra chứng minh đẳng thức này. Hệ số giới hạn 0,5–1,5.
- **Đợt** = các tuần liên tiếp cùng khung; khoảng ngắt ≤ 4 tuần thì gộp. Mọi bảng ghi cả số tuần lẫn số đợt.
- **Khoảng tin cậy thống nhất cho mọi bảng.** Bootstrap khối dừng (stationary), độ dài khối trung bình bằng kỳ hạn tính theo tuần, 2.000 lần, tính cho **mức chênh so với mốc của cùng các tuần đó**. Kèm Wilson theo đợt để đối chiếu. Lợi thế giá vốn dùng khối trung bình 26 tuần.
- **Mốc so sánh** luôn là mọi tuần của cùng bảng, cùng giai đoạn. Sửa lỗi 9: các bảng không còn dùng mốc khác nhau (33%, 37%, 40%).
- Thước đo phụ: tỷ lệ thắng 1 tháng, 3 tháng, 6 tháng, 1 năm; chênh so với mốc; lãi trung vị và tứ phân vị; sụt giảm trung vị trong kỳ giữ.
- **Hiệu chỉnh xác suất:** Brier so với tỷ lệ nền của cửa sổ huấn luyện, có khoảng tin cậy bootstrap; bảng độ tin cậy theo thập phân vị. Không tốt hơn mốc thì chỉ hiển thị thứ hạng.
- Kết luận cho mỗi ô: "hơn mốc" / "kém mốc" khi khoảng tin cậy của mức chênh không chứa 0; "chưa có lợi thế" khi chứa 0; **"ít đợt, chưa kết luận" khi dưới 3 đợt** (xem thay đổi thiết kế bên dưới).
- Đo lại bot hiện tại bằng thước đo mới, dữ liệu đến 31/12/2023: `docs/MEASURE_B.md`, `data/results/measure_b.json`. Lệnh: `python -c "from bot.report import measure_b; measure_b.run()"`.

**Kết quả đo lại bot hiện tại (đến 31/12/2023)**
| | PA3 cố định | Chế độ Tự động |
|---|---|---|
| Số tuần có điểm / từ | 179 / 02/08/2020 | 161 / 06/12/2020 |
| Số đợt "Phải mua" | **1** (70 tuần liền) | 6 |
| Ô nào "hơn mốc" có đủ đợt? | không ô nào | không ô nào |
| Khung xếp đúng thứ tự ở kỳ hạn nào? | không kỳ hạn nào | không kỳ hạn nào |
| Lợi thế giá vốn khi dùng khung làm hệ số | +2,5% (khoảng tin cậy −35,6% đến +33,4%): chưa có lợi thế | +2,8% (−20,7% đến +10,3%): chưa có lợi thế |
| Xác suất của mô hình (Brier so với mốc) | kém hơn hoặc không hơn mốc ở cả 4 kỳ hạn → **không hiển thị xác suất** | — |

- Bảng độ tin cậy của mô hình 6 tháng: khi mô hình báo 1–13% thì thực tế thắng 56–89%, khi báo 49–59% thì thực tế 6–17%. Xác suất hiện tại không có nghĩa.
- Đúng như lỗi 2: "Phải mua" của PA3 trông như 70 tuần nhưng chỉ là 1 đợt; Wilson theo đợt là 0–79%.

**Thay đổi thiết kế sau khi xem kết quả (ghi theo yêu cầu)**
- Thêm quy tắc **dưới 3 đợt → "ít đợt, chưa kết luận"**. Lý do: với PA3, ô "Phải mua, 1 năm" có bootstrap 0,15 đến 0,77 (sẽ ghi "hơn mốc"), nhưng cả 31 tuần là một đợt duy nhất. Bootstrap theo tuần không đo được bất định của một sự kiện chỉ xảy ra một lần. Quy tắc này chỉ làm kết luận **khắt khe hơn**, không làm kết quả đẹp hơn.

**Quyết định của bạn (29/10/2026):** giữ quy tắc "dưới 3 đợt → ít đợt, chưa kết luận".

## Phần C: Mô hình và chống khớp quá mức (xong 29/10/2026, chờ xác nhận)

**Đăng ký trước.** `config/candidates.yaml` (8 bộ chỉ số, mỗi bộ có lý do kinh tế; λ ∈ {0,3; 1; 3}; nhãn 26 tuần; vòng trong 52 tuần; mốc; kiểm định) đã lưu git ở commit `da803d6`, **trước** khi có dòng mã mô hình nào chạy trên dữ liệu thật.

**Test rò rỉ trước tiên.** `tests/test_leak_model.py`: thay mọi thứ sau tuần t (chỉ số xáo trộn; giá đi ngược nhãn gần nhất, để nhãn thật sự đổi) thì điểm ngoài mẫu đến t không đổi, ở 14 mốc t liên tiếp. Đã thử cài rò rỉ 1, 5 và 26 tuần (học cả nhãn chưa biết): cả ba đều bị bắt. Bản đầu của bài kiểm tra **không** bắt được, vì cách xáo trộn không làm đổi nhãn; đã sửa trước khi chạy dữ liệu thật.

**Đã làm** (`bot/models/wf_logit.py`, `bot/models/part_c.py`, báo cáo `docs/MODEL_C.md`, số liệu `data/results/part_c.json`, danh sách cấu hình `experiments/rebuild_configs.csv`)
- Đi tới lồng nhau: vòng ngoài học lại mỗi 13 tuần, cửa sổ mở rộng, cắt bỏ nhãn chồng (mẫu chỉ được học khi nhãn đã biết trước lần học). Vòng trong chọn bộ và λ theo log-loss trên 52 tuần gần nhất; không cấu hình nào hơn tỷ lệ nền thì không dùng mô hình.
- Hồi quy logistic L2 với ràng buộc dấu (trọng số của "độ rẻ" ≥ 0, sai dấu thì loại và ghi lại).
- 24 cấu hình cố định (8 bộ × 3 λ) cùng mô hình lồng nhau và 2 quy tắc 1 chỉ số; kiểm định hoán vị dịch vòng (≥ 52 tuần, 1.000 lần), hiệu chỉnh max-statistic và Holm; bỏ từng chu kỳ; kiểm tra đơn điệu và gộp khung.

**Kết quả (đến 31/12/2023)**
| Mục | Kết quả |
|---|---|
| Mô hình lồng nhau | 260/372 tuần **tự chọn không dùng mô hình**. Khi có chọn: tương quan với lợi suất 26 tuần −0,11; lợi thế giá vốn −8,6% (−16,3% đến +3,4%); Brier kém mốc → chỉ thứ hạng |
| Cấu hình cố định | tương quan âm ở mọi bộ (−0,04 đến −0,44); lợi thế giá vốn −0,7% đến −6,2%; không cấu hình nào có ý nghĩa (p hiệu chỉnh = 1,000) |
| Quy tắc đơn giản | MVRV: tương quan −0,05, lợi thế −6,1% (từ 2013). Giá/MA 200 tuần: tương quan +0,28 (p thô 0,195, hiệu chỉnh 0,943), lợi thế −3,7% (từ 2017) |
| Ràng buộc dấu | MVRV học ra dấu ngược ở phần lớn các lần học; **Fear & Greed bị loại ở mọi lần học**, nên bộ có và không có Fear & Greed như nhau. Chỉ báo thay thế (MA 20 tuần) cũng bị loại |
| Bỏ từng chu kỳ | chu kỳ 2016–2020: mọi bộ thua mua đều 16–24%; chu kỳ 2020–2023: chỉ Giá/MA 200 tuần (+0,3%) và Pi (+1,4%) dương nhẹ |
| Đơn điệu | không ở bất kỳ cách nào, kể cả sau khi gộp → bỏ khung |
| Kết luận | **chưa có lợi thế → mua đều (hệ số 1,0)** |

**Ghi chú thiết kế**
- Lợi thế giá vốn với hệ số 0,5 + thứ hạng có giới hạn cấu trúc: tuần nào cũng "rẻ" (như 2022–2023 với Giá/MA 200 tuần) thì không có tuần mua ít để dành tiền, nên kết quả trùng mua đều (0,0%). Đây là đặc điểm của thước đo cùng tổng vốn, không phải lỗi.
- S1 và S6 cho kết quả giống hệt: cả hai rút về chỉ còn Giá/MA 200 tuần sau ràng buộc dấu.

## Phần D: Khung mua và hệ số giải ngân (xong 29/10/2026, chờ xác nhận)

**Đăng ký trước** (`config/candidates.yaml`, mục `zones` và `multiplier`, commit `c7eeb48`, trước khi chạy):
- ngưỡng 80/60 theo thứ hạng, vùng trễ 5 điểm;
- hệ số 0,5–1,5, m = 1 + 2 × cận khoảng tin cậy của lợi thế khung (tỷ lệ thắng 26 tuần trừ mốc);
- dưới 3 đợt → 1,0; ước lượng lại mỗi 13 tuần chỉ bằng các tuần đã biết kết quả;
- cổng Phần I.

**Test rò rỉ.** Bài kiểm tra kiểu hộp đen (đổi giá sau tuần t, hệ số đến t không đổi) đạt. Nhưng khi thử cài rò rỉ thì nó **không bắt được**, vì hệ số hoặc là 1,0, hoặc chạm trần/sàn, nên thay đổi nhỏ không lộ. Đã thêm bài kiểm tra trực tiếp: mỗi lần ước lượng lại ở tuần T chỉ nhận đúng dữ liệu của các tuần 0..T−1. Bài này bắt được cả rò rỉ 1 tuần.

**Đã làm** (`bot/models/zones.py`, `bot/models/part_d.py`, báo cáo `docs/ZONES_D.md`, số liệu `data/results/part_d.json`)
- "Tỷ lệ nên mua" định nghĩa lại là **thứ hạng** của điểm tuần này trong các điểm ngoài mẫu trước đó, không phải xác suất có lãi. Câu này sẽ ghi trên báo cáo.
- Khung có vùng trễ; hệ số tính đi tới theo cận khoảng tin cậy; cổng Phần I (chưa có kết quả Phần I → 1,0, lý do "chưa chạy kiểm định Phần I").

**Kết quả (đến 31/12/2023)**
| Cách | Số tuần | Đổi khung: không vùng trễ → có vùng trễ | Tuần hệ số theo quy tắc khác 1,0 | Lợi thế giá vốn nếu dùng | Tuần cuối trước holdout |
|---|---|---|---|---|---|
| Mô hình lồng nhau | 59 (từ 02/2022) | 3 → 1 | 0% | 0,0% | thứ hạng 4, Không nên mua, hệ số 1,0 |
| Quy tắc MVRV | 547 (từ 07/2013) | 51 → 41 | 0% | 0,0% | thứ hạng 19, Không nên mua, hệ số 1,0 |
| Quy tắc Giá/MA 200 tuần | 347 (từ 05/2017) | 30 → 24 | 0% | 0,0% | thứ hạng 55, Không nên mua, hệ số 1,0 |

- Lần ước lượng cuối: khoảng tin cậy lợi thế của **mọi khung đều chứa 0**. Ví dụ "Phải mua" theo MVRV: 162 tuần, 7 đợt, chênh +0,3 điểm %, khoảng tin cậy −23% đến +28%. Hệ số 1,0 là đúng quy tắc, không phải lỗi.
- Khung vẫn không đơn điệu ở mọi kỳ hạn.
- Hệ số dùng thực tế: **1,0** (cổng Phần I chưa mở).
