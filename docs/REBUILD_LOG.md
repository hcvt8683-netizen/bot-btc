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

## Phần E: Bên bán (xong 29/10/2026, chờ xác nhận)

**Đăng ký trước** (`config/candidates.yaml` mục `sell`, commit `d7a47ce`, trước khi chạy):
- tiêu chí bật khi chỉ số thuộc 5% đắt nhất 4 năm trước (phân vị trượt, bỏ ngưỡng tuyệt đối như MVRV Z ≥ 7, Pi ≥ 1);
- đếm theo 4 nhóm (định giá on-chain, xu hướng giá, thợ đào, tâm lý);
- **một hệ thống**: 0 nhóm → Giữ, 1–2 → Chốt lời một phần, ≥ 3 → Bán phần lớn;
- quy tắc thực thi: bán X% (10/20/30%) một lần khi đợt tín hiệu bắt đầu, kích hoạt ≥ 1 nhóm hoặc ≥ 3 nhóm;
- mua lại khi giá ≤ 80% giá bán bình quân hoặc sau 52 tuần; nền vẫn mua đều.

**Test rò rỉ.** Giá sau tuần t sụp mạnh (để điều kiện mua lại sẽ bật nếu nhìn thấy được), tài sản và giao dịch đến t không đổi, quét 80 mốc t. Đã thử cài cho điều kiện mua lại nhìn giá tuần sau: bị bắt.

**Lỗi đã sửa trong lúc làm.** Mô phỏng theo chu kỳ lúc đầu trừ vị trí tuần bán hai lần, nên chu kỳ 2016–2020 và 2020–2023 không có lần bán nào. Đã sửa trước khi đọc kết quả để kết luận.

**Kết quả (2012 → 31/12/2023)**
| Cấu hình | Chu kỳ có lợi so với giữ nguyên | Cả giai đoạn | Số lần bán (mua lại rẻ hơn / đã mua lại) |
|---|---|---|---|
| Bán 10/20/30% khi ≥ 1 nhóm | 0/3 | −37,8% / −62,1% / −77,4% | 9 (1/8) |
| Bán 10/20/30% khi ≥ 3 nhóm | 2/3 (2012–2016, 2016–2020; lỗ 2020–2023) | +4,7% / +9,0% / +12,8% | 4 (2/4) |

- Phần lợi của "≥ 3 nhóm" gần như đến từ **một** lần bán đúng ở chu kỳ 2012–2016. Chỉ 4 lần bán trong 11 năm: quá ít để tin.
- Từng tiêu chí: không tiêu chí nào đúng nhiều hơn mốc ở cả 2 chu kỳ gần nhất có dữ liệu, nên **không có tiêu chí "đáng tin"**. Muốn xét "đáng tin" phải có chu kỳ 2021–2025, tức dữ liệu holdout, nên chấm ở Phần I.
- Một số tiêu chí (Mayer, Puell, độ lệch MA 20 tuần) có bootstrap theo tuần "tốt hơn mốc", nhưng chỉ 3–6 đợt, Wilson theo đợt rất rộng (ví dụ Mayer 2/4 đợt đúng, 15–85%). Bootstrap theo tuần đánh giá quá cao khi các tuần dính chùm trong một đợt.
- Tuần cuối trước holdout (24/12/2023): 0 nhóm bật → Giữ.

**Kết luận:** bên bán **chưa có lợi thế đáng tin**. Chỉ hiển thị mức Giữ / Chốt lời một phần / Bán phần lớn để tham khảo, kèm số đợt, không khuyên tỷ lệ bán.

## Phần F: Kịch bản giá động (xong 29/10/2026, chờ xác nhận)

**Đăng ký trước** (`config/candidates.yaml` mục `scenarios`, commit `f44bab8`, trước khi chạy):
- lưới giá −30% đến +50%, đạt tới sau 1, 2, 4 tuần theo đường đều trên thang log;
- chỉ số tính từ giá tính lại đúng theo đường giả định, bằng cùng hàm dựng bảng tuần như dữ liệu thật;
- vốn hóa thực, nguồn cung, BTC phát hành mỗi ngày, hash rate giữ ở giá trị cuối;
- Fear & Greed theo mô hình phản ứng ΔF&G = a + b × lợi suất log + c × (F&G − 50), khoảng = phân vị 10–90% phần dư;
- kiểm ngoài mẫu: học đến 2021, thử 2022–2023.

**Test.** Kịch bản cho đi đúng đường giá thật cho ra đúng bảng thật (mọi chỉ số trừ khối lượng tương đối). Đổi dữ liệu sau ngày phân tích không làm kịch bản đổi. Mô hình F&G tìm lại được quan hệ đã biết trên dữ liệu giả.

**Đổi thiết kế sau lần chạy đầu.** Lần chạy đầu, thứ hạng quy tắc MVRV không có khoảng (quy tắc không dùng F&G), trong khi Phần F yêu cầu "kèm khoảng dao động". Đã thêm `rc_band`: cho vốn hóa thực thay đổi theo phân vị 10% và 90% của thay đổi k tuần trong 208 tuần trước ngày phân tích. Trường hợp giữa vẫn giữ nguyên vốn hóa thực như đăng ký. Thay đổi này chỉ nới khoảng, không đổi ngưỡng hay kết quả giữa.

**Kết quả (ngày phân tích 31/12/2023, giá 42.217 $)**
- Mô hình F&G: b ≈ 73–93 điểm cho mỗi đơn vị lợi suất log, R² 0,56–0,73. Ngoài mẫu 2022–2023, sai số trung bình 4,3–5,9 điểm so với 5,9–10,6 điểm nếu giữ nguyên F&G. Độ phủ khoảng 98–100% (cao hơn 80% kỳ vọng: khoảng hơi rộng, thận trọng).
- Sau 4 tuần: quy tắc Giá/MA 200 tuần và quy tắc MVRV chỉ vào Cân nhắc mua khi giá giảm ≥ 20%; đi ngang hoặc tăng thì Không nên mua.
- Bên bán: Chốt lời một phần khi giá tăng ≥ 20% (RSI 14 tuần vào 5% cao nhất 4 năm). Không mức nào tới Bán phần lớn.
- So với cách cũ giữ nguyên F&G: số nhóm bên bán chỉ khác ở 1/30 kịch bản (1 tuần, +30%: 1 → 2 nhóm).

**Kết luận:** kịch bản giờ tính lại đầy đủ và có khoảng. Đây là mô tả bot sẽ đọc thế nào, không phải dự báo; hệ số giải ngân vẫn 1,0.

## Phần G: Vĩ mô và sự kiện (xong 29/10/2026, chờ xác nhận)

**Đăng ký trước** (`config/candidates.yaml` mục `macro`, commit `1548ac2`, trước khi chạy):
- tách kết quả khung của 4 chiến lược (PA3 của bot hiện tại, mô hình lồng nhau, quy tắc MVRV, quy tắc Giá/MA 200 tuần) theo chế độ Fed tăng / giữ / giảm;
- mốc là mọi tuần cùng chế độ; bảng chính kỳ 26 tuần, các kỳ khác trong file JSON;
- cảnh báo khi chế độ hiện tại có dưới 3 đợt trong giai đoạn đánh giá;
- sự kiện: chỉ liệt kê sau mốc chốt dữ liệu (giá đóng Chủ nhật), gắn cờ sự kiện giữa mốc chốt và lúc phát hành, cảnh báo lịch thiếu.

**Lỗi cũ được sửa.** Báo cáo tuần cũ liệt kê sự kiện từ lúc chạy báo cáo, nên sự kiện xảy ra sau Chủ nhật nhưng trước lúc chạy bị bỏ qua im lặng. Module mới `bot/report/events.py` lấy mốc chốt dữ liệu làm điểm bắt đầu. Báo cáo trên web chưa dùng module này: chờ bước tích hợp cuối, khi bạn đồng ý.

**Test.** Sự kiện trước mốc chốt không bao giờ được liệt kê. Sự kiện giữa mốc chốt và lúc phát hành có cờ, kèm ngày chạy lại. Lịch thiếu được nêu tên. Đã thử hai lỗi cài sẵn: danh sách bắt đầu từ lúc phát hành như cách cũ, và danh sách lọt sự kiện 3 ngày trước mốc chốt. Test bắt được cả hai.

**Tách Phần D thành hàm.** Thứ hạng của 3 chiến lược Phần D giờ nằm trong hàm `strategy_ranks` để Phần G dùng lại. Chạy lại Phần D cho kết quả giống hệt từng byte.

**Kết quả (đến 31/12/2023)**
- Chế độ hiện tại (Chủ nhật 25/10/2026): **tăng**, từ 20/09/2026. Từ 2011 đến nay có 4 đợt tăng, gồm cả đợt hiện tại (chưa có kết quả).
- Trong giai đoạn đánh giá, chế độ tăng có 1 đợt với PA3 và mô hình lồng nhau, 2 đợt với quy tắc Giá/MA 200 tuần, 3 đợt với quy tắc MVRV. **Cảnh báo** cho 3 chiến lược đầu.
- 25 ô có dữ liệu ở kỳ 26 tuần: 0 hơn mốc, 1 kém mốc (quy tắc MVRV, Cân nhắc mua, chế độ tăng: 5 đợt, −38,6 điểm %), 9 chưa có lợi thế, 15 ít đợt. Với 25 phép so, 1 ô kém mốc nằm trong mức may rủi (khoảng 1,25 ô ở ngưỡng 5%).
- Sự kiện lúc chạy: FOMC 28/10/2026 (sau mốc chốt 25/10) được gắn cờ, đề nghị chạy lại sau Chủ nhật 01/11/2026. Lịch CPI chỉ tới 14/10/2026: cảnh báo cần cập nhật.

**Kết luận:** chưa có khung nào có lợi thế trong một chế độ Fed riêng. Chế độ Fed chỉ để chia nhóm báo cáo.

## Phần H: Kiểm định đi tới (xong 29/10/2026, chờ xác nhận)

**Đăng ký trước** (`config/candidates.yaml` mục `forward`, commit `13daebf`, trước khi chạy):
- đóng băng mô hình lồng nhau một lần, không học lại khi theo dõi;
- mỗi tuần một dòng `forward_log.csv` (ngày, giá đóng tuần, điểm, thứ hạng, khung, hệ số, phiên bản), kèm hai quy tắc đơn giản và bên bán;
- mã phiên bản sha256 của mã, cấu hình và trạng thái đóng băng; đổi bất kỳ thứ gì → phiên bản mới, nhật ký mới;
- chấm sau 26 và 52 tuần bằng giá thứ Hai;
- đóng băng thật làm ngay sau lần chạy holdout của Phần I.

**Vì sao chưa đóng băng thật.** Đóng băng tại hôm nay cần học mô hình trên dữ liệu 2024–2026, tức nhìn vào holdout trước lần chạy duy nhất của Phần I. Vì vậy Phần H chỉ dựng và kiểm tra quy trình, rồi chạy thử trên 2023. Lệnh `python -m bot.cli forward freeze` từ chối chạy khi chưa có `data/results/acceptance.json`.

**Tách mã, kết quả cũ không đổi.**
- `wf_logit._fit_at`: chọn cấu hình và học tại một tuần, dùng chung cho đi tới và đóng băng. Đầu ra mô hình lồng nhau và từng cấu hình cố định giống hệt trước khi tách. Đóng băng tại tuần học lại đầu tiên cho đúng mô hình của đi tới.
- `zones.step` (vùng trễ từng tuần) và `zones.edges` (lợi thế từng khung). Phần D chạy lại giống hệt từng byte.

**Test** (`tests/test_forward.py`, 6 bài):
- chỉ thêm dòng; ghi lại cùng tuần không làm gì;
- đổi cấu hình thì dừng ghi, đóng băng lại tạo `v2-…` với nhật ký mới, nhật ký cũ giữ nguyên;
- sửa tay `model.json` bị phát hiện; mã băm không phụ thuộc kiểu xuống dòng;
- dòng không đổi khi dữ liệu sau Chủ nhật của nó đổi;
- dùng đúng trọng số đóng băng, khi ghi gọi hàm học lại sẽ báo lỗi;
- chấm chỉ đếm dòng đã đủ kỳ hạn.

Đã cài thử 3 lỗi (sửa dòng cũ, nhìn trước 4 tuần, học lại mỗi tuần): test bắt được cả 3.

**Chạy thử 2023** (đóng băng 25/12/2022, dữ liệu đã dùng ở Phần B–E, không phải kiểm định):
- Mô hình đóng băng: bộ S3; MVRV bị bỏ do sai dấu, còn Puell với trọng số 0,07. Điểm gần như không đổi (0,56–0,61), thứ hạng 1–24.
- Kết quả: cả 54 tuần ở Không nên mua, đúng năm giá tăng mạnh. Hệ số dùng thực tế 1,0.
- Chấm: 27 dòng đủ kỳ 26 tuần, 1 dòng đủ kỳ 52 tuần; mỗi khung chỉ 1 đợt → "ít đợt".

**Kết luận:** quy trình đi tới đã sẵn sàng và có test. Phiên bản thật bắt đầu sau Phần I; nhật ký đi tới là phép thử ngoài mẫu thật duy nhất.

## Phần I: Tiêu chí chấp nhận và lần chạy holdout duy nhất (xong 29/10/2026)

**Đăng ký trước** (`config/candidates.yaml` mục `acceptance`, commit `60ddb0a`, trước khi đọc bất kỳ số nào của holdout):
- định nghĩa chính xác 6 tiêu chí;
- quyết định bằng hệ số Phần D (thứ sẽ dùng thật); hệ số so sánh 0,5 + thứ hạng chỉ để tham khảo;
- bên bán "đáng tin" khi đúng hơn mốc ở cả hai chu kỳ 2020–2024 (đỉnh 2021) và 2024–nay (đỉnh 10/2025).

**Diễn tập** trên holdout giả 2022–2023 (dữ liệu đã xem), cùng mã. Bắt được 4 lỗi, đã sửa TRƯỚC lần chạy thật:
- p hoán vị hiện 0,001 khi không tính được (quyết định vẫn đúng là không đạt);
- chu kỳ bán không cắt ở cuối dữ liệu;
- số tuần holdout đếm lệch nhau;
- số lần bỏ chỉ số đếm theo tuần nhưng ghi là "lần học lại".

**Lần chạy thật:** 29/10/2026 05:32 UTC, mã `af7ccea`, ghi trong `experiments/final_runs.log`. Lệnh từ chối chạy lần hai (có test).

**Kết quả: không đạt cả 6 tiêu chí → giữ mua đều, hệ số 1,0.**
- Holdout 01/01/2024 → 25/10/2026, 147 tuần. Mô hình lồng nhau có 121 tuần có mô hình.
- 1–2, 6: hệ số Phần D bằng 1,0 suốt holdout (không khung nào có khoảng tin cậy lợi thế loại trừ 0), nên lợi thế giá vốn đúng bằng 0.
- 3: p hoán vị đã hiệu chỉnh của mô hình 1,000 (IC 26 tuần +0,169, nhưng mọi độ dịch đều cho IC cao hơn).
- 4: khung không đơn điệu ở cả 4 kỳ hạn. Mọi tuần có mô hình đều phải bỏ ít nhất một chỉ số sai dấu (MVRV, Fear & Greed).
- 5: Brier 0,193 so với tỷ lệ gốc 0,189 (95 tuần), tệ hơn.
- Tham khảo, hệ số so sánh: mô hình −0,3% (−11,3% đến +6,0%), thua quy tắc MVRV (+0,8%) và Giá/MA 200 tuần (+2,7%, KTC −5,5% đến +6,7%).
- Quy tắc Giá/MA 200 tuần có p hoán vị đã hiệu chỉnh 0,001 cho lợi thế theo hệ số so sánh. Nhưng khoảng tin cậy bootstrap chứa 0 và khung không đơn điệu, nên nó cũng không qua tiêu chí 2 và 4. Chỉ ghi nhận, không đổi gì.

**Bên bán:** 0 tiêu chí đáng tin. Ở chu kỳ 2024–2026 không có lần nào ≥ 3 nhóm bật (không có "Bán phần lớn" ở đỉnh 10/2025). Mức ≥ 1 nhóm đúng 1/2 đợt. Bán 10–30% khi ≥ 1 nhóm: lợi +1,4% đến +3,6% ở 2024–2026, nhưng lỗ ở 2016–2020 và 2020–2024.

**Giới hạn của kiểm định này:**
- Holdout ngắn: với 121 tuần và độ dịch ≥ 52 tuần, chỉ có khoảng 18 độ dịch khác nhau, nên phép hoán vị thô.
- Holdout 2024–2026 đã được con người nhìn thấy khi làm bot cũ (lần chạy giai đoạn 7 ngày 28/10/2026), nên đây không hoàn toàn mù.

**Nhật ký đi tới bắt đầu.** Phiên bản thật `v1-f46ea015fc`, đóng băng tại 25/10/2026:
- bộ S1, MVRV bị bỏ do sai dấu, còn Giá/MA 200 tuần (trọng số 0,52); cổng Phần I: chưa đạt.
- Dòng đầu: giá 80.039 $, điểm 0,716, thứ hạng 76 → Cân nhắc mua, hệ số dùng thực tế 1,0 (mua đều).
- Hai quy tắc đều ở Cân nhắc mua; bên bán 0 nhóm → Giữ.
- Các khung này chỉ để tham khảo: đã kiểm định là **chưa có lợi thế**.

## Tính năng: kế hoạch giải ngân một khoản tiền (29/10/2026)

**Yêu cầu:** nhập số tiền muốn giải ngân, bot đề xuất cách giải ngân "best ROI" kèm các mốc thời gian.

**Vì sao không nghiêng theo tín hiệu.** Phần I không đạt, nên "mua nhiều khi bot báo rẻ" là tự đặt ra một lợi thế không có thật. Các phương án chỉ khác nhau về thời gian giải ngân.

**Đăng ký trước** (`config/candidates.yaml` mục `plan`, commit `0be9828`, trước khi tính):
- 5 phương án: một lần, chia đều 4, 13, 26 hoặc 52 tuần;
- so giá trị 52 tuần sau lần mua đầu, giá đóng thứ Hai, có phí; tiền chưa mua không có lãi;
- dữ liệu từ 07/2016 (toàn bộ lịch sử chỉ để tham khảo);
- ROI cao nhất = trung vị cao nhất;
- đề xuất = phân vị 10% cao nhất trong các phương án không kém ROI cao nhất đáng kể.

**Kết quả** (486 tuần bắt đầu, khoảng 9 đợt độc lập; chi tiết `docs/PLAN.md`):
- ROI cao nhất và đề xuất đều là **giải ngân một lần**: trung vị +56%, 10% xấu nhất −45%, xấu nhất −82%, 32% số tuần bắt đầu lỗ sau 1 năm.
- Chia đều 13 và 26 tuần không kém đáng kể. Chia đều 4 tuần kém đáng kể (+0,3 đến +3,6 điểm, vì giá thường tăng trong 4 tuần), chia đều 52 tuần cũng kém đáng kể.
- Toàn bộ lịch sử từ 2012: ROI cao nhất là chia đều 4 tuần, đề xuất là chia đều 26 tuần. Kết quả nhạy với giai đoạn chọn, nên giao diện nói rõ khoảng tin cậy rộng.

**Thêm sau khi xem kết quả, chỉ ở cách trình bày, không đổi quy tắc:**
- Dòng "nếu ngại mua đúng đỉnh": phương án không kém đáng kể có mức xấu nhất nhẹ nhất (chia đều 26 tuần: −64% so với −82%).
- Làm tròn giá trị dự kiến 3 chữ số, mỗi lần mua bằng VNĐ làm tròn nghìn đồng.

**Kiểm tra:** `tests/test_plan.py` (số học, chỉ dùng giá trong cửa sổ của mình, quy tắc chọn). Chạy thử trên trình duyệt với dữ liệu thật:
- 100.000.000 ₫ chia 26 tuần: 26 lần từ 02/11/2026 đến 26/04/2027, tổng đúng bằng số tiền;
- USD có số lẻ; số nhập sai bị báo;
- CSV có BOM UTF-8;
- không tràn ngang ở 390 px; chỉ hiện ở chế độ Bên mua.

## Tính năng: dự báo dải giá theo ngày (29/10/2026)

**Yêu cầu:** dự báo giá BTC từng ngày trong 7 ngày tới và mốc 1 tháng, để người dùng tự kiểm chứng bot.

**Vì sao là dải, không phải một con số.** Phần I cho thấy tín hiệu không đoán được hướng giá. Một con số giá sẽ là bịa. Dải giá thì kiểm chứng được: dải 80% đúng khi giá thật rơi vào trong khoảng 80% số lần.

**Đăng ký trước** (`config/candidates.yaml` mục `forecast`, commit `c15af8c`, trước khi tính):
- giá đóng ngày Coin Metrics; kỳ 1–7 ngày và 30 ngày; phân vị 10/25/50/75/90;
- lợi suất k ngày chia cho độ dao động 30 ngày, lấy phân vị trong 4 năm trước ngày gốc (chỉ những lần đã biết kết quả), nhân lại với độ dao động hiện tại;
- cách không chỉnh độ dao động chỉ để so sánh;
- nhật ký mỗi ngày một lần, chỉ thêm dòng, không ghi bù, chỉ ghi ngày đích chưa tới.

**Kiểm chứng lịch sử** (mỗi ngày từ 01/01/2018, khoảng 3.200 lần mỗi kỳ hạn):
- dải 80% chứa giá thật ở 80–81% số lần, dải 50% ở 49–53%, với mọi kỳ hạn từ 1 đến 30 ngày;
- cách không chỉnh độ dao động có dải rộng thừa (phủ 83–85%).

**Test** (`tests/test_forecast.py`):
- dải không đổi khi giá sau ngày gốc đổi;
- cửa sổ trượt bằng đúng cách tính trực tiếp;
- dải đúng tỷ lệ trên bước ngẫu nhiên giả;
- nhật ký chỉ thêm dòng, không ghi trùng ngày gốc, bỏ ngày đích đã qua.

Đã cài thử 2 lỗi nhìn trước (cửa sổ lấn một ngày, độ dao động tính cả ngày mai): test bắt được cả 2.

**Nhật ký trực tiếp:**
- dòng đầu ghi lúc 29/10/2026 06:48 UTC, ngày gốc 28/10/2026 (giá đóng 81.237 $);
- Daily trên GitHub ghi tiếp mỗi ngày (`python -m bot.cli forecast`);
- trang web hiện bảng kiểm chứng khi dự báo đến hạn.

## Trang web: đưa kết luận bản xây lại lên (29/10/2026)

- **Khuyến nghị giải ngân tuần này:** lý do lấy từ 6 tiêu chí của Phần I; bảng 6 tiêu chí kèm kết quả thay cho bảng giai đoạn 7 cũ.
- **Sự kiện:** chỉ liệt kê sau mốc chốt dữ liệu (giá đóng Chủ nhật cuối, lấy từ `data/status.json`). Sự kiện đã xảy ra trước lúc cập nhật được gắn ⚑, kèm đề nghị xem lại sau giá đóng tuần kế tiếp; lịch thiếu được cảnh báo. Sửa lỗi 9 trên trang.
- **Mục mới "Tuần này theo bản xây lại (đã kiểm định)":** thứ hạng của mô hình đóng băng và hai quy tắc (ghi rõ không phải xác suất), khung tuần này trong lịch sử tính theo đợt kèm khoảng tin cậy và kết luận, bên bán, chế độ Fed kèm cảnh báo, kịch bản giá sau 4 tuần (Fear & Greed đổi theo giá). Sửa lỗi 1, 2, 7, 8 trên trang.
- **Thứ tự trang:** phần đã kiểm định lên đầu (khuyến nghị, tuần này, dự báo dải giá, kế hoạch giải ngân). Phần phân tích cũ tính trong trình duyệt xuống dưới một cảnh báo rõ ràng; dưới mỗi đồng hồ "Tỷ lệ nên mua / nên bán" có dòng "phân tích cũ, không phải xác suất, chưa có lợi thế".
- **Báo cáo tải về:** dòng lý do và dòng thứ hạng tuần này theo bản xây lại; sự kiện có ⚑.
- **Kiểm tra:** test sự kiện theo mốc chốt (gắn cờ, không liệt kê sự kiện trước mốc chốt); ảnh chụp giao diện và báo cáo đã duyệt khác biệt.
- **Chưa làm:** phần phân tích cũ trong trình duyệt chưa được tính lại theo thước đo thống nhất; nó chỉ còn để tham khảo.

## Dự báo dải giá: so 32 cách tính trên dữ liệu từ 2010 (29/10/2026)

**Yêu cầu:** chạy lại từ dữ liệu cũ, tìm cách dự báo chính xác nhất, cập nhật nếu cần.

**Vì sao không chọn theo tỷ lệ trúng.** Dải càng rộng càng trúng. Thước đo là điểm phân vị trên log giá: thưởng cho dải vừa trúng đúng tỷ lệ vừa hẹp.

**Đăng ký trước** (`config/candidates.yaml` mục `forecast_search`, commit `c3b4f52`, trước khi tính):
- 32 cách: 5 kiểu độ dao động × 3 độ dài lịch sử × có / không xu hướng, cộng 2 cách phân phối chuẩn;
- chọn trên 2014–2021, xác nhận trên 2022 → nay;
- chỉ thay nếu khoảng tin cậy của chênh lệch nằm hẳn dưới 0 và dải 80% phủ 75–85%. "Phủ 75–85%" được hiểu là trung bình qua 8 kỳ hạn; cách hiểu này chốt trước khi chạy.

**Kết quả** (`docs/FORECAST_SEARCH.md`, mọi cấu hình trong `experiments/forecast_configs.csv`):
- Tốt nhất giai đoạn chọn: phân phối chuẩn với độ dao động EWMA 0,94, điểm 0,979 (cách đang dùng = 1).
- Ở giai đoạn xác nhận (1.732 ngày): chênh −0,1%, khoảng tin cậy −1,1% đến +0,8%, tức chứa 0. **Giữ nguyên cách đang dùng.**
- Cách đang dùng ở 2022 → nay: dải 80% trúng 79,8–80,8% ở mọi kỳ hạn, dải 50% trúng 49–55%. Đoán đúng hướng chỉ 50–52% (54% ở 2014–2021, do xu hướng tăng).
- Cách không chuẩn hóa theo độ dao động với toàn bộ lịch sử có dải quá rộng: trúng hơn 90%, điểm kém nhất.

**Trang web:** thêm một dòng ghi chú ở mục dự báo. Không sửa `price_forecast.py`, nên phiên bản dự báo và nhật ký kiểm chứng giữ nguyên.

## Xác suất có lãi đã hiệu chỉnh (29/10/2026)

**Yêu cầu:** xác suất có lãi nếu mua và giữ 1, 3, 6 tháng, để chọn điểm mua tốt nhất.

**Đăng ký trước** (`config/candidates.yaml` mục `calib`, commit `7b2ca74`, trước khi tính):
- 3 cách: tỷ lệ gốc 208 tuần; 5 nhóm theo thứ hạng Giá / MA 200 tuần co về tỷ lệ gốc; hồi quy logistic trên 3 chỉ số rẻ;
- chấm bằng sai số Brier từ 2016; chỉ dùng mô hình để chọn điểm mua khi khoảng tin cậy của mức cải thiện so với tỷ lệ gốc nằm hẳn trên 0.

**Thêm sau lần chạy đầu (chỉ mô tả):** bảng "khi mô hình báo ≥ 80%, thực tế có lãi bao nhiêu" (`said80`). Không dùng để chọn cách tính.

**Mở rộng, đăng ký trước khi chạy** (cùng mục, commit này):
- thêm kỳ hạn 1 năm (52 tuần);
- lợi nhuận dự đoán: phân vị 10/50/90% của lợi nhuận h tuần, tỷ lệ gốc 208 tuần so với 5 nhóm Giá / MA 200 tuần, chấm bằng điểm phân vị; chỉ dùng nhóm khi khoảng tin cậy nằm hẳn trên 0; báo tỷ lệ trúng dải 10–90%;
- trang web nhân phân vị với giá lúc tra để ra giá dự kiến;
- bên bán: xác suất giá thấp hơn = 1 − xác suất có lãi; báo thêm những tuần mô hình nói ≤ 20% và 20% tuần có xác suất thấp nhất (mô tả).

**Kết quả** (`data/results/calib.json`, chấm đi tới từ 2016; các tuần đầu được chấm khi đủ dữ liệu, từ 08/2018):

| Kỳ hạn | Tuần chấm | Brier gốc / tốt nhất (khoảng tin cậy mức cải thiện) | Xác suất tuần 25/10/2026 | Logistic nói | Logistic nói ≥ 80% thì thực tế có lãi | Lợi nhuận giữa (8/10 lần) | Dải 8/10 trúng |
|---|---|---|---|---|---|---|---|
| 1 tháng | 425 | 0,250 / 0,257 nhóm (−0,017 đến 0,002) | 57% | 63% | 35% (1 đợt) | +2% (−13% đến +24%) | 85% |
| 3 tháng | 407 | 0,247 / 0,271 logistic (−0,075 đến 0,021) | 60% | 68% | 70% (8 đợt) | +6% (−21% đến +54%) | 86% |
| 6 tháng | 381 | 0,240 / 0,254 logistic (−0,088 đến 0,047) | 68% | 80% | 74% (2 đợt) | +20% (−31% đến +71%) | 87% |
| 1 năm | 329 | 0,268 / 0,229 logistic (−0,014 đến 0,089) | 62% | 99% | 77% (3 đợt) | +42% (−44% đến +141%) | 87% |

- Không cách nào vượt tỷ lệ gốc ở kỳ hạn nào: hiển thị tỷ lệ gốc, ghi "chưa chọn được điểm mua / điểm bán".
- Lợi nhuận theo nhóm Giá / MA 200 tuần kém tỷ lệ gốc ở mọi kỳ hạn (6 tháng và 1 năm kém có ý nghĩa); dùng tỷ lệ gốc. Dải 10–90% trúng 85–87%, rộng hơn mục tiêu 80% một chút.
- Bên bán: mô hình chưa từng báo xác suất có lãi ≤ 20%; 20% tuần có xác suất thấp nhất giảm 40–52% số lần so với mốc 35–45%, khoảng tin cậy chứa 0 hoặc quá ít đợt.
- Kỳ hạn 1 năm chỉ có khoảng 6 năm không chồng nhau: rất không chắc.
- Nhật ký đi tới: `data/calib/calib_log.csv` (xác suất) và `data/calib/ret_log.csv` (lợi nhuận), Daily ghi mỗi tuần một lần.
- Trang web: mục `#cp-sec` đổi theo chế độ Mua / Bán; giá dự kiến = giá lúc tra × (1 + lợi nhuận). Báo cáo tải về, gói claude.ai và hồ sơ gửi Claude có đủ phần này.

## Giá chờ mua, mua ngay hay chờ, ngày rẻ nhất 7 ngày tới (02/11/2026)

**Yêu cầu:** biết lúc tra cứu nên mua ngày nào, ở giá nào là tốt nhất.

**Đăng ký trước** (`config/candidates.yaml` mục `entry`, commit `293f7ec`, trước khi tính bất kỳ con số nào):
- (A) giá thấp nhất trong k ngày tới (1–7 và 30 ngày): z = log(giá thấp nhất của các nến k ngày tới / giá đóng) / (độ dao động 30 ngày × √k), phân vị trong 4 năm trước, chỉ cửa sổ đã biết kết quả; nến ngày Bitstamp (có giá thấp nhất ngày, từ 2011);
- (B) mua ngay hay đặt lệnh chờ thấp hơn x% (1, 2, 3, 5, 8%) trong k ngày (1, 3, 7, 30), không khớp thì mua ở giá đóng ngày thứ k; bootstrap khối, Holm trên 20 cấu hình, cùng chiều ở hai nửa giai đoạn;
- (C) vị trí 1..7 của ngày có giá thấp nhất trong 7 ngày tới, so với 1/7 ở hai nửa giai đoạn từ 2016.

**Kiểm tra rò rỉ:** `tests/test_entry.py`. Đã cài thử hai lỗi nhìn trước (phân vị dùng cửa sổ chưa đóng: `z.shift(k - 1)`; tỷ lệ ngày rẻ nhất dùng cửa sổ chưa đóng: `shift(days - 1)`): cả hai bị bắt (2 bài kiểm tra hỏng mỗi lần), rồi khôi phục.

**Kết quả** (`data/results/entry.json`, đi tới mỗi ngày từ 01/01/2016):
- (A) Dải 8/10 của giá thấp nhất trúng 80,2% (1 ngày), 81,1% (7 ngày, Wilson 77,6–84,1%, 564 lần độc lập), 81,3% (30 ngày, 130 lần độc lập): đúng tỷ lệ ở mọi kỳ hạn. Xác suất chạm khớp thực tế, ví dụ 7 ngày: mức −2% bot nói 71,1%, thực tế 72,4%; mức −5% nói 41,8%, thực tế 43,3%. Sai số Brier thấp hơn cách không chỉnh độ dao động ở mọi kỳ hạn (7 ngày: 0,157 so với 0,166). **Công cụ này đáng tin để đặt lệnh chờ.**
- (B) Không cách chờ nào tốt hơn mua ngay. 6/20 cách **kém hơn rõ ràng** (Holm p < 0,05, cùng chiều hai nửa): chờ −1% hoặc −2% trong 3, 7, 30 ngày, thua 0,2–1,2% (ví dụ −2% trong 7 ngày: khớp 72% số lần nhưng trung bình thua 0,51%, khoảng tin cậy −0,82% đến −0,21%). Các cách còn lại: chưa có lợi thế. Nửa sau (2021–2026) chênh lệch nhỏ hơn nhiều nửa đầu.
- (C) Ngày đầu tiên là ngày rẻ nhất 34,7% (2016–2021, Wilson 29,4–40,5%) và 27,0% (2021–2026, Wilson 22,1–32,4%) số lần, cao hơn hẳn 1/7 ở cả hai nửa; ngày cuối đứng thứ hai (14–19%); các ngày giữa 9–13%. Đúng với lý thuyết giá đi ngẫu nhiên có xu hướng tăng; nghĩa thực tế: không có lý do chờ sang ngày khác trong tuần.
- Không thay khuyến nghị mua đều; không phải dự báo hướng giá.

**Sau lần chạy đầu (không đổi phương pháp, kết quả không đổi):** thêm tham số `end` cho `run()` để dựng dữ liệu mẫu cố định cho bài kiểm tra giao diện; phiên bản mã đổi theo (nhật ký `data/entry/` chưa có dòng nào nên không ảnh hưởng). Trang web coi lúc tra như giá đóng ngày gốc (đúng mục `entry.touch.live`), nên các ngày được đếm từ hôm nay (giờ UTC) kể cả khi số liệu chậm một ngày.

**Trang web làm mới:** đầu trang có giá trực tiếp lớn và % so với giá đóng; chia 7 thẻ (Tổng quan, Giá & ngày mua, Giải ngân, Dự báo, Kiểm định, Phân tích cũ, Hỏi Claude); thẻ tổng quan có 4 thẻ số chính và biểu đồ giá thấp nhất 7 ngày tới; nút nền sáng / tối; phần phân tích cũ chuyển vào thẻ riêng kèm cảnh báo (bước A2 mới làm phần thu gọn, chưa gỡ hay tính lại). Phần tổng quan, giá chờ mua và dự báo hiện ngay khi mở trang, không phải chờ phân tích cũ tải xong. Báo cáo tải về, gói claude.ai và hồ sơ gửi Claude có thêm phần giá chờ mua.

## Bên bán: giá chờ bán, bán ngay hay chờ, ngày có giá cao nhất; giá thời gian thực (02/11/2026)

**Yêu cầu:** bên bán có bộ công cụ như bên mua (khi chọn "Bên bán" trang vẫn hiện công cụ mua); giá trên trang cập nhật liên tục.

**Đăng ký trước** (`config/candidates.yaml` mục `exit`, commit `f58a558`, trước khi tính): mặt kia của mục `entry` trên giá **cao nhất** ngày Bitstamp: (A) giá cao nhất trong 1–7 và 30 ngày và khả năng chạm mức cao hơn; (B) bán ngay hay đặt lệnh chờ bán cao hơn x% (1, 2, 3, 5, 8%) trong k ngày (1, 3, 7, 30), không khớp thì bán ở giá đóng ngày thứ k, Holm trên 20 cấu hình; (C) vị trí ngày có giá cao nhất trong 7 ngày tới. Module riêng `bot/models/exit_timing.py` (không sửa `entry_timing.py`, nên phiên bản nhật ký bên mua giữ nguyên).

**Kiểm tra rò rỉ:** `tests/test_exit.py`; đã cài thử hai lỗi nhìn trước (`z.shift(k - 1)`, `shift(days - 1)`): cả hai bị bắt, rồi khôi phục.

**Kết quả** (`data/results/exit.json`, đi tới mỗi ngày từ 01/01/2016, dữ liệu đến 01/11/2026):
- (A) Dải 8/10 của giá cao nhất trúng 81,4% (1 ngày) đến 82,9% (30 ngày), trong 75–85% ở mọi kỳ hạn. Bot hơi thận trọng: 7 ngày mức +2% nói 73,3%, thực tế 75,8%; +5% nói 46,4%, thực tế 48,8% (xu hướng tăng dài hạn của BTC). Brier tốt hơn cách không chỉnh độ dao động ở 1–7 ngày; ở 30 ngày kém hơn một chút (0,134 so với 0,132).
- (B) Gần như ngang nhau: 19/20 cách chưa có lợi thế; "đặt cao hơn 8%, chờ 1 ngày" hơn bán ngay rõ ràng nhưng rất nhỏ (+0,17%, chỉ khớp 4% số lần). Không cách nào kém hơn rõ ràng. Lợi trung bình của các cách từ −0,06% đến +1,34%.
- (C) Ngày đầu (23,0% và 24,4%) và ngày cuối (25,0% và 21,0%) hay có giá cao nhất ở cả hai nửa giai đoạn, cao hơn hẳn 1/7; các ngày giữa 9–13%.
- Không thay hệ thống bán đã đăng ký (Giữ / Chốt lời một phần / Bán phần lớn).

**Trang web:** thẻ "Giá & ngày mua" đổi thành "Giá & ngày bán" ở chế độ Bán (ô giá muốn bán, mức +1%…+10%, bảng nhiệt, biểu đồ giá cao nhất, bán ngay hay chờ); thẻ tổng quan bên bán có giá chờ bán và ngày có giá cao nhất. Đầu trang nhận giá qua luồng WebSocket Binance (`btcusdt@miniTicker`): giá nhảy từng giây, % và cao/thấp 24 giờ, đường giá 24 giờ (nến 15 phút); các công cụ tính lại theo giá mới tối đa 10 giây một lần; mất luồng thì nối lại và lấy giá REST 15 giây một lần. Bài kiểm tra ảnh chụp tắt luồng (`window.BOT_NO_WS`). Bảng kịch bản ở thẻ Kiểm định có thêm dòng "Cách đọc".

## Long/Short có giá vào, cắt lỗ, chốt lời: tìm công thức tốt nhất mà không dò trên dữ liệu chấm (02/11/2026)

**Yêu cầu:** cải tiến thẻ Long/Short: kiểm tra trên dữ liệu cũ, tìm bộ công thức tốt nhất, hiện giá vào lệnh, cắt lỗ, xác suất thắng; giao diện đẹp.

**Đăng ký trước** (`config/candidates.yaml` mục `perp_trade`, commit `87e2b34`, trước khi tính): 1152 công thức = 6 tín hiệu (long/short luôn, theo xu hướng 20 ngày, phá đỉnh / thủng đáy 20 ngày, đánh ngược sau 24 giờ tăng / giảm mạnh, đánh ngược funding, điều chỉnh trong xu hướng) × 2 phía × 2 cách vào (ngay, lệnh chờ cách 0,5 ATR trong 6 giờ) × cắt lỗ 0,5 / 1 / 1,5 / 2 ATR × chốt lời 1 / 1,5 / 2 / 3R × giữ tối đa 24 / 72 / 168 giờ, trên nến giờ hợp đồng vĩnh cửu từ 2020, phí taker 0,05% + trượt giá 0,02% mỗi chiều và funding. "Tốt nhất" không chọn một lần trên toàn bộ dữ liệu: mỗi đầu tháng từ 07/2021 chọn công thức có t cao nhất trên các lệnh **đã đóng trước tháng đó** (ít nhất 30 lệnh, t ≥ 2, không đạt thì đứng ngoài), rồi chấm chính cách chọn này ở các tháng sau. Module mới `bot/models/perp_trade.py`; không sửa `perp_signal.py` hay nhật ký `data/perp/`.

**Đã biết trước khi đăng ký:** kết quả mục `perp` (không ô nào có lợi thế; cao nhất là long sau khi giảm mạnh). Ghi rõ trong mục `known_before`.

**Sửa sau khi tính (không đổi phương pháp):**
- Mục `baseline` ghi "96 quy tắc mốc"; thực ra 2 phía × 2 cách vào × 4 × 4 × 3 = **192** (bài kiểm tra số công thức bắt được). Định nghĩa ("mọi quy tắc mốc") giữ nguyên, sửa chữ thành 192. Mốc chỉ để so sánh, không vào kết luận.
- Chi tiết cài đặt chọn trước lần chạy đầu: mọi công thức bắt đầu cùng lúc, từ giờ đầu tiên có đủ ATR và phân vị (30/06/2020); lệnh vào ngay giữ đúng H giờ (ra ở giá đóng t + H).
- Sau lần chạy đầu thêm số liệu hiển thị (thống kê đi tới riêng từng công thức, số tháng đứng ngoài của mốc): phiên bản mã đổi, kết quả không đổi.

**Kiểm tra rò rỉ và tính đúng:** `tests/test_perp_trade.py` (12 bài). Kết quả từng lệnh khớp một vòng lặp từng nến viết riêng theo đúng lời đăng ký (cắt lỗ thắng khi một nến chạm cả hai, lệnh chờ khớp đúng giá và nến khớp chỉ xét cắt lỗ, funding trong lúc giữ). Đã cài thử 5 lỗi nhìn trước (giá cao nhất / thấp nhất 20 ngày gồm nến sau, trung bình 20 ngày lệch 2 giờ, ATR lệch 3 giờ, bước chọn thấy thêm 48 giờ): cả 5 bị bắt. Lần đầu bài kiểm tra chỉ cho giá tương lai sập nên lỗi "giá cao nhất gồm nến sau" lọt; đã sửa để thử cả giá tương lai tăng vọt.

**Kết quả** (`data/results/perp_trade.json`, nến đến 02/11/2026 09:00 UTC, funding đến 31/10/2026):
- Chấm đi tới 07/2021 → 10/2026 (65 tháng, đứng ngoài 2): **167 lệnh, thắng 43,1%** (Wilson 35,8–50,7%), chạm chốt lời 7%, chạm cắt lỗ 31%, hết giờ 62%; **R trung bình −0,09** (bootstrap theo tháng −0,24 đến +0,06), tổng −15,1R, sụt sâu nhất 17,2R. Nửa đầu −0,04R, nửa sau −0,14R. **Chưa có lợi thế** → trang ghi "Không nên vào lệnh".
- Cách chọn gần như luôn chọn long (xu hướng 43 tháng, phá đỉnh 16, funding thấp 4; chưa tháng nào chọn short): công thức đẹp nhất trong quá khứ chủ yếu phản ánh BTC tăng giá 2020–2021, không lặp lại khi chấm đi tới.
- Mốc (chỉ chọn long luôn / short luôn): 69 lệnh, thắng 50,7%, R trung bình −0,00 (−0,19 đến +0,20), đứng ngoài 52 tháng. Tín hiệu không thêm gì so với mốc.
- Công thức của tháng 11/2026: long theo xu hướng, vào ngay, cắt lỗ 2 ATR, chốt lời 2R, giữ tối đa 7 ngày (t = 2,31 trên 265 lệnh đã đóng). Trên toàn bộ lịch sử công thức này thắng 52,8% (lạc quan vì được chọn trong 1152); những tháng được chọn trước khi biết kết quả: 65 lệnh, thắng 52,3%, +0,02R mỗi lệnh.

**Trang web:** thẻ Long/Short làm lại: phần chính "giá vào, cắt lỗ, chốt lời" (kết luận, công thức của tháng, tín hiệu đang bật hay mức giá làm nó bật, 4 ô giá vào / cắt lỗ / chốt lời / giữ tối đa, thang giá có giá lúc này và giá thanh lý, xác suất thắng kèm khoảng tin cậy và tách chạm chốt lời / hết giờ / chạm cắt lỗ, tỷ lệ thắng cần để hòa vốn, tiền theo ký quỹ và đòn bẩy, cảnh báo khi thanh lý đến trước cắt lỗ và đòn bẩy tối đa); phần "Kiểm tra trên dữ liệu cũ" (5 thẻ số, đường lãi lũy kế so với mốc, bảng công thức tốt nhất của từng tín hiệu có nút Xem kế hoạch, bảng công thức từng tháng). Nghiên cứu giữ đúng kỳ hạn chuyển vào "Xem thêm". Lệnh `python -m bot.cli perp-trade` (quy trình Daily), nhật ký `data/perp_trade/select_log.csv` (mỗi tháng một dòng, chỉ thêm), chấm lần đầu khi đủ 1 năm (11/2027).

**Bổ sung cùng ngày theo yêu cầu người dùng (mỗi phần ghi vào `config/candidates.yaml` và lưu git trước khi tính):**
- *Thời gian giữ do người dùng chọn* (mục `hold_view`, commit `955c9e1`): 1–24 giờ và 1–7 ngày; với công thức đang xem chỉ thay thời gian giữ, hiện tỷ lệ thắng (Wilson), chạm chốt lời / cắt lỗ, hết giờ có lãi / lỗ. Chỉ là thống kê lịch sử trong mẫu, không vào bước chọn hay kết luận; trang ghi rõ khi thời gian chọn khác thời gian của công thức. Ví dụ công thức tháng 11/2026 giữ 4 giờ: 7.544 lệnh, thắng 41,5%, gần như không lệnh nào chạm chốt lời hay cắt lỗ (cắt lỗ 2 ATR ≈ 5% quá xa cho 4 giờ).
- *Chọn riêng từng phía và 6 tiêu chí* (mục `sides`, `checklist`, commit `2c8d665`): thêm **sau khi** đã thấy kết quả cách chọn chung. Mỗi tháng chọn riêng công thức long (576) và short (576); lúc kiểm tra mỗi phía chấm 6 tiêu chí (có công thức của tháng; ≥ 100 lệnh đi tới; cận dưới bootstrap > 0; hai nửa dương; tín hiệu đang bật; thanh lý xa hơn cắt lỗ), chỉ đề xuất phía đạt đủ 6/6. Kết quả: riêng long giống hệt cách chọn chung (167 lệnh, −0,09R; đạt c1, c2, trượt c3, c4); **riêng short chưa tháng nào có công thức đạt t ≥ 2** (đứng ngoài 65/65 tháng, 0 lệnh). Lúc 02/11/2026: Long 3/6 (4/6 khi tín hiệu bật), Short 1/6 → "Không nên vào lệnh".
- *Tiêu chí áp trong quá khứ* (người dùng hỏi: nếu đạt 6/6 thì thắng bao nhiêu). Áp đúng 6 tiêu chí ở từng tháng từ 07/2021 chỉ bằng dữ liệu có đến đầu tháng đó: **chưa tháng nào đạt 6/6** ở cả hai phía, nên không có tỷ lệ thắng 6/6 để đo. Long đạt 4/6: 26 tháng, 72 lệnh, thắng 43,1%, −0,16R/lệnh; đạt 3/6: 36 tháng, 95 lệnh, thắng 43,2%, −0,04R/lệnh. Short: cao nhất 1/6. Người dùng đề nghị thêm tiêu chí nếu chưa đủ; **không thêm**: tiêu chí chỉ lọc bớt lệnh, không tạo lợi thế, và chọn thêm tiêu chí bằng cách nhìn kết quả quá khứ là điều mục "Không nên làm" cấm. Đường đúng: chờ nhật ký từ 03/11/2026, hoặc dữ liệu mới (bước C1, C2) có đăng ký trước.

## Dự báo xu hướng, Chốt lời dần, lịch CPI và rà soát (02–03/11/2026)

**Yêu cầu:** thêm phần "Dự báo xu hướng" (giá hiện tại, tăng hay giảm, bao nhiêu, 1–7 ngày, 1–4 tuần, 1–6 tháng; chính xác cao, nhiều mô hình độc lập, đối chiếu các phần khác); ở Bên bán thay thẻ Giải ngân bằng công cụ bán BTC theo đợt; cập nhật lịch CPI; hồi cứu cả 4 phần trên dữ liệu cũ, sửa lỗi, đẩy lên GitHub.

**Xu hướng** (đăng ký trước: `config/candidates.yaml` mục `trend`, commit `9dffa7b`; mã `bot/models/trend.py`, giao diện `src/trend.js`, chế độ thứ 4 ở đầu trang). Tỷ lệ gốc 4 năm và 5 mô hình (động lượng, MA 200 ngày, định giá MVRV, đảo chiều ngắn, kết hợp), 16 kỳ hạn, chấm mỗi ngày từ 01/01/2016 đến ngày cuối đã biết kết quả (3.778–3.957 ngày mỗi kỳ hạn), Holm trên 80 phép so sánh:
- **Hướng giá: không mô hình nào thắng tỷ lệ gốc ở kỳ hạn nào** (p nhỏ nhất trước hiệu chỉnh 0,09 ở 1 ngày; sau Holm 1,00). Trang hiện tỷ lệ gốc và ghi rõ "không phải tín hiệu riêng của lúc này". Tỷ lệ gốc đúng hướng 54% (7 ngày), 57% (30 ngày), 60% (90 ngày), 65% (180 ngày), đều là do BTC tăng nhiều hơn giảm.
- **Biên độ:** mô hình kết hợp ước lượng khoảng giá 1 ngày tốt hơn tỷ lệ gốc (điểm phân vị giảm 0,00003, khoảng tin cậy 0,00001–0,00005, Holm 0,04, cả hai nửa), nên khoảng giá 1 ngày dùng mô hình đó. Khoảng 8/10 lần trúng 80–84% ở mọi kỳ hạn.
- Đối chiếu: dải giá 1/7/30 ngày trùng thẻ Dự báo; xác suất tăng 28/90/180 ngày 58/62/71% so với xác suất có lãi 4/13/26 tuần 57/60/69%.
- Kiểm tra rò rỉ `tests/test_trend.py`: đã cài thử 2 lỗi nhìn trước (cửa sổ đã biết lệch 1 ngày; thứ hạng nhìn thấy ngày sau), cả hai bị bắt.
- Một phiên Claude khác (bản tách của cùng cuộc trò chuyện) làm song song cùng việc này trong cùng thư mục và đã ghi đè một file kiểm tra; phiên đó đã được nhắn dừng và đã dừng. **Đối chiếu hai bản mã viết độc lập** theo cùng đăng ký (`trend.py` đang dùng và `trend_forecast.py` của phiên kia, không đưa vào dự án): trên cùng dữ liệu, 96 xác suất tăng, 192 điểm Brier và tỷ lệ đúng hướng, 48 phân vị khoảng giá, mô hình được chọn và nhãn ở cả 16 kỳ hạn **trùng khít** (chênh 0,0). Daily trên GitHub (commit `f3bec77`) cũng cho cùng phiên bản `067156b504` và cùng kết quả.

**Chốt lời dần** (đăng ký trước: mục `sell_plan`, commit `673c217`; mã `bot/models/sell_plan.py`, báo cáo tuần `KN.sell_plan`, thẻ "Chốt lời dần" ở Bên bán). 486 tuần bắt đầu từ 2016 (khoảng 9 đợt độc lập): bán đều 52 tuần thu trung vị +30% so với giá lúc quyết định, nhưng 10% lần xấu nhất −30%; bán hết một lần thu đúng giá lúc đó trừ phí. Đề xuất theo quy tắc đăng ký là chia 52 tuần (chỉ phương án này không kém phương án tốt nhất); trang nói rõ lý do (BTC tăng trong phần lớn lịch sử) và rủi ro nếu bán để tránh giá giảm.

**Lịch CPI:** bộ tải chỉ đọc trang lưu trữ các lần đã công bố của BLS nên không bao giờ có ngày sắp tới; thêm bộ đọc trang lịch phát hành (`parse_cpi_schedule`, có test). `config/events.yaml` có thêm 14 ngày CPI (10/11/2026 → 10/12/2027). `tools/update_events.py` giữ lại các ngày PCE đã qua (trang BEA chỉ có lịch sắp tới).

**Sửa lỗi rà soát (docs/DE_XUAT_NANG_CAP.md):** L1 câu thừa ở Giải ngân khi chưa nhập số tiền; L2 Bên bán có thẻ Chốt lời dần thay dòng nhắc; L3 `tests/test_report.py` ghi đè `data/results/calib.json` và có thể chèn dòng giả vào nhật ký `data/calib/` (nay ghi vào thư mục tạm); L5 kiểm chứng trực tiếp dải giá ghi số ngày gốc độc lập, Wilson và "còn quá ít để kết luận"; L6 `tests/test_browser.py` kẹt vì giả lập nến đòi `startTime` và chờ thẻ đang ẩn hiện lên (nay qua trọn ở 1280 sáng, 390 sáng, 1280 tối).

**Hồi cứu cắt ngang** (`tools/hoi_cuu.py` → `docs/HOI_CUU.md`, 24 thời điểm 11/2024 → 10/2026): dải giá 7 và 30 ngày trúng 79% (mục tiêu 80%); giá chờ mua −3%/7 ngày bot nói 53%, chạm 50%; **giá chờ bán +3%/7 ngày bot nói 55%, chạm 79% (Wilson 60–91%)**: trong giai đoạn này bot đánh giá thấp khả năng chạm giá bán (kiểm chứng dài hạn trước đó cũng thấy bot hơi thận trọng ở bên bán); xác suất có lãi 4/13 tuần nằm trong khoảng tin cậy; Long/Short chưa tháng nào đạt 6/6 và nếu vẫn long theo công thức mọi tháng thì 59 lệnh, −8,1R; xu hướng 30 ngày chỉ nghiêng một phía 3 lần. Không đổi phương pháp nào theo kết quả này.

## Thẻ Xu hướng: mô hình nến, học máy, khoảng 9/10 lần, kiểm chứng trên giá Bitstamp (03/11/2026)

**Yêu cầu:** kiểm chứng mô hình với dữ liệu khác, so với mô hình nến, thêm bộ tiêu chí nếu cần, mô hình độc lập mạnh, "xác suất dự báo đúng trên 90%", giao diện dễ dùng.

**Nói rõ với người dùng trước khi làm:** đoán hướng giá BTC đúng trên 90% là không thực tế (mọi kiểm định trước đều quanh 50–65%, phần lớn do BTC hay tăng). Con số 90% làm được một cách trung thực là **khoảng giá 9/10 lần** đã kiểm chứng.

**Đăng ký trước** (`config/candidates.yaml` mục `candles` và `trend_plus`, commit `3fa3cd0`, trước khi tính; ghi rõ là thêm sau khi đã thấy kết quả mục `trend`). Mã: `bot/models/candles.py` (mới), `bot/models/trend.py` (thêm phân vị 5/95%, học máy, kiểm chứng Bitstamp; 5 mô hình cũ không đổi).

**Kết quả:**
- **Khoảng 9/10 lần** (phân vị 5–95% của z, mô hình biên độ đang dùng): độ phủ đi tới từ 2016 là **88,7–92,5% ở cả 16 kỳ hạn** (1 ngày 90,2%, Wilson 89,3–91,1%), đúng mục tiêu 90% và trong khoảng 87–93% đã đăng ký. Trang hiện ô "Điều bot nói chắc được" (1 ngày, 7 ngày, 1 tháng) và dòng 9/10 lần trên mỗi thẻ, vùng nhạt trên biểu đồ quạt.
- **12 mẫu nến kinh điển** (nến ngày Bitstamp từ 2012, nhị thức, Holm 36): **không mẫu nào thắng một ngày bất kỳ**. Gần nhất "ba chàng lính trắng" sau 7 ngày đúng 65,8% so với 54,9% (158 lần độc lập, Holm 0,13). Xuyên tăng và mây đen gần như không xuất hiện (BTC giao dịch 24/7, hiếm khoảng trống giá).
- **Học máy** (logistic L2, 16 đặc trưng gồm 11 cờ mẫu nến, học lại mỗi 30 ngày, Holm 16): **kém tỷ lệ gốc ở 16/16 kỳ hạn** (Holm 1,00). Thêm đặc trưng làm mô hình học thuộc quá khứ.
- **Kiểm chứng trên giá Bitstamp** (thay cho Coin Metrics): cùng kết luận ở 16/16 kỳ hạn; khoảng 9/10 lần trúng 89,0–92,5%.
- Kiểm tra rò rỉ `tests/test_candles.py`: cài thử 2 lỗi nhìn trước (cờ mẫu nến biết sớm một ngày; học máy học trên kết quả chưa biết), cả hai bị bắt. Lần đầu bài kiểm tra học máy chỉ thử ở một ngày nên không bắt được lỗi cài thử; đã sửa để thử ngay sau các ngày học lại.
- Không đổi kết luận về hướng: trang vẫn dùng tỷ lệ gốc cho hướng.

## Price action: hỗ trợ / kháng cự, cấu trúc, pin bar, inside bar, phá vỡ giả (03/11/2026)

**Yêu cầu:** người dùng hỏi "price action là gì, nếu price action hiệu quả thì xây bộ tiêu chí price action". Kiểm định trung thực trước; chỉ khi qua mới đề xuất (hỏi người dùng) đưa lên trang. Phiên phụ làm trên nhánh `claude/price-action`, không đụng giao diện.

**Đăng ký trước** (`config/candidates.yaml` mục `price_action`, commit `5bb5550`, trước khi tính bất kỳ con số nào): 10 tiêu chí = 5 loại × 2 hướng trên nến ngày Bitstamp: chạm hỗ trợ và giữ / chạm kháng cự và bị đẩy xuống (mức lấy từ đỉnh / đáy cục bộ 5 nến mỗi bên trong 365 ngày, vùng ± 0,5 ATR 14 ngày), cấu trúc tăng / giảm (hai đỉnh và hai đáy đã biết gần nhất cùng cao dần / thấp dần), pin bar tại vùng (bóng dài ≥ 2/3 biên), inside bar có nến mẹ chạm vùng, phá vỡ giả (thủng quá vùng rồi đóng cửa quay lại); thêm bộ tiêu chí "ít nhất 2 trong 5 tiêu chí cùng hướng". Kỳ hạn 1/3/7/30 ngày; mốc = mọi ngày cùng giai đoạn (01/01/2016 → 01/11/2026); Wilson theo đợt độc lập, bootstrap khối dừng 2000 lần, Holm trên 48 cặp, cùng chiều ở hai nửa; dưới 30 đợt (hoặc dưới 5 đợt ở một nửa) thì không kết luận. Không dùng nến giờ hợp đồng vĩnh cửu. Mã `bot/models/price_action.py`, lệnh `python -m bot.cli price-action` (commit `00d60cc`, lưu trước khi chạy trên dữ liệu thật).

**Đã biết trước, không thử lại** (mục `known_before`): 12 mẫu nến (`candles`), 7 mẫu nến của nhánh `claude/eloquent-boyd-80d429`, 5 mô hình xu hướng (`trend`), học máy (`trend_plus`), phá đỉnh / thủng đáy 20 ngày, theo xu hướng, điều chỉnh trong xu hướng, đánh ngược (`perp_trade`). Kỳ vọng ghi trước khi chạy: chưa có lợi thế. Cấu trúc thị trường gần với "theo xu hướng" đã thử nhưng định nghĩa khác (đỉnh / đáy cục bộ), nên vẫn kiểm.

**Cách hiểu chốt trước khi chạy:** khi một cặp vừa đạt Holm vừa có dưới 30 đợt, "ít đợt" thắng (không kết luận), như `bot/backtest/measure.py`.

**Kiểm tra rò rỉ và tính đúng:** `tests/test_price_action.py` (10 bài): định nghĩa từng tiêu chí, đỉnh / đáy chỉ được dùng từ khi nến thứ 5 bên phải đóng, đổi mọi nến sau T không đổi gì đến T, đợt độc lập, bắt được lợi thế giả lập, khóa kiểm tra cuối. Đã cài thử 5 lỗi nhìn trước vào mã nguồn (mức hỗ trợ / kháng cự dùng đỉnh đáy chưa đủ 5 nến bên phải; cấu trúc cũng vậy; vùng dùng ATR của ngày hôm sau; mức chốt theo giá đóng ngày T + 1; "hôm trước" lấy nến hôm sau): cả 5 bị bắt, rồi khôi phục. Một bản viết lại độc lập bằng vòng lặp thô theo đúng lời đăng ký (không dùng hàm nào của module) cho cờ của cả 10 tiêu chí và mọi đỉnh / đáy **trùng khít** với module trên toàn bộ nến 2011–2026 (0 ngày khác).

**Kết quả** (`docs/PRICE_ACTION.md`, `data/results/price_action.json`, nến đến 01/11/2026):
- **0/48 cặp hơn mốc, 0 kém mốc**; 44 chưa có lợi thế, 4 ít đợt. Bộ tiêu chí ≥ 2/5: 8/8 chưa có lợi thế.
- Gần nhất: chạm kháng cự rồi 30 ngày sau giá thấp hơn 52,0% số lần so với mốc 42,5%, nhưng chỉ 29 đợt (ít đợt), tính theo đợt chỉ 41,4% (Wilson 25,5–59,3%), Holm 0,096. Cùng tiêu chí sau 7 ngày: 52,6% so với 45,9% (148 đợt), khoảng tin cậy trước hiệu chỉnh +1,7 đến +11,7 điểm nhưng Holm 0,47.
- 5/48 cặp có p < 0,05 trước hiệu chỉnh (2 hơn, 3 kém mốc); chỉ do may rủi, 48 phép thử đã cho khoảng 2,4 cặp như vậy.
- Phá vỡ giả nghiêng về ngược điều sách nói (giá hay đi tiếp theo hướng vừa phá): phá vỡ giả phía trên, giá thấp hơn sau 1 ngày chỉ 27,5% so với mốc 47,8% (38 đợt, Holm 0,47). Chưa có ý nghĩa, ghi để biết.
- Cấu trúc tăng: hơn mốc 0,8–1,1 điểm, nửa đầu dương nửa sau âm; cấu trúc giảm từ −7,3 đến +0,8 điểm: không ổn định. Pin bar tăng tại hỗ trợ kém mốc 8–9 điểm ở 1 và 3 ngày (chưa có ý nghĩa).
- **Không đưa lên trang** (đúng mục `web` đã đăng ký và lời dặn của người dùng); không sửa `src/ui.js`, `src/page.html`.

**Sau lần chạy đầu (chỉ mô tả, không đổi phương pháp, kết quả không đổi):** báo cáo ghi thêm số cặp p < 0,05 so với may rủi và độ phân giải của bootstrap (p nhỏ nhất 0,001, sau Holm trên 48 cặp là 0,048: một cặp chỉ "hơn mốc" khi gần như mọi lần lấy lại đều cho chênh lệch dương).

**Giai đoạn kiểm tra cuối mới:** tín hiệu từ 03/11/2026 (nến 02/11/2026 không thuộc giai đoạn nào), chạy một lần bằng `python -m bot.cli price-action --final` khi có ít nhất 365 ngày đã biết kết quả 30 ngày (sớm nhất khoảng 12/2027), ghi vào `experiments/final_runs.log`. Vì không cặp nào hơn / kém mốc, lần đó chỉ báo cáo mô tả.

## Mục Price action trong chế độ Long/Short: kiểm tra điểm vào (03/11/2026)

**Yêu cầu** (sau khi người dùng đã biết kết quả 0/48 ở trên): "xây dựng 1 sheet price action, với khả năng xác suất cao nhất… điểm vào lệnh đã phù hợp chưa", rồi "giao diện thân thiện dễ dùng, đẩy github, cập nhật price action cho sheet long/short, tăng độ hành động giá". Người dùng gọi các thẻ / chế độ của trang là "sheet".

**Nói rõ:** price action không đoán được hướng tốt hơn một ngày bất kỳ, nên không có "xác suất cao nhất" về hướng để hiện. Con số trung thực trả lời "điểm vào đã phù hợp chưa" là: với giá vào, cắt lỗ, chốt lời này, trong lịch sử giá chạm chốt lời trước bao nhiêu lần, so với tỷ lệ cần để hòa vốn. "Tăng độ hành động giá" được làm bằng cách hiện price action rõ hơn trong thẻ Long/Short; **kết luận Long/Short không đổi** (vẫn theo `perp_trade`), vì cho price action quyết định thay sẽ trái kết quả kiểm định.

**Đăng ký trước** (`config/candidates.yaml` mục `pa_sheet`, commit `e7a615f`; đổi từ file Excel sang trang web theo yêu cầu thứ hai, commit `9400d51`; cả hai trước khi tính bất kỳ con số nào của mục): hành động giá ở nến cuối đã đóng theo đúng định nghĩa mục `price_action`; hỗ trợ / kháng cự tính theo giá vào người dùng nhập; cắt lỗ gợi ý = hỗ trợ − 0,5 ATR (Short: kháng cự + 0,5 ATR), chốt lời gợi ý = kháng cự − 0,5 ATR (không có thì 2 lần khoảng cắt lỗ); bảng đếm "chạm mức lên / xuống trước" theo ATR (0,25–8 ATR, bước 0,25) trên mọi ngày từ 2016, chờ 7 hoặc 30 ngày, cùng một nến chạm cả hai tính là chạm cắt lỗ; kết luận "Có lợi / Bất lợi / Ngang hòa vốn" theo khoảng tin cậy Wilson của tỷ lệ chạm chốt lời trước so với mức hòa vốn (chưa tính phí).

**Mã:** `bot/models/pa_sheet.py` (lệnh `python -m bot.cli pa-sheet`, quy trình Daily, ghi `data/results/pa.json`), `src/pact.js` (nhúng qua chỗ đánh dấu `/*PACT*/`), mục `#pact-sec` trong `#ls-app` của `src/page.html`, chữ ở `web.pact` (`bot/i18n/vi.yaml`). Nút "Lấy giá từ kế hoạch Long/Short ở trên" đọc `window.LT_PLAN` (một dòng thêm vào `renderPlan` của `src/ls.js`). Đăng ký ghi `#pa-sec` và `src/pa.js`; đổi thành `#pact-sec`, `src/pact.js` vì `#pa-sec` đã có trong trang (phần phương án cũ). Không sửa `src/ui.js`.

**Kiểm tra:** `tests/test_pa_sheet.py` (lần chạm đầu trùng vòng lặp thô; số đếm cộng lại không vượt số ngày và giảm khi mức xa hơn; trạng thái chỉ gồm đỉnh / đáy đã biết; cắt lỗ / chốt lời gợi ý và kết luận đúng lời đăng ký) và `tests/test_pact_ui.py` (trình duyệt, 1280 và 390 điểm ảnh: không lỗi; hàm `check` của trang cho kết quả **trùng** `pa_sheet.check` ở 43 trường hợp ngẫu nhiên; cắt lỗ sai phía bị từ chối; nút lấy giá từ kế hoạch Long/Short; không trượt ngang trên điện thoại). Ảnh chụp `tests/snapshots/theme.css` cập nhật sau khi duyệt khác biệt (chỉ thêm khối CSS của mục mới).

**Lúc làm** (nến 01/11/2026, giá đóng 78.233 $): ATR 1.925 $, hỗ trợ gần nhất 76.229 $, kháng cự 79.500 $, cấu trúc giảm (tiêu chí đang bật: cấu trúc giảm, chưa có lợi thế). Mua ở giá đóng với giá gợi ý: chốt lời 0,2 ATR so với cắt lỗ 1,5 ATR (kháng cự quá gần) → "Bất lợi". Bảng phụ (mua, chờ 30 ngày, cắt lỗ 1 hoặc 2 ATR, chốt lời 0,5–3 lần): tỷ lệ chạm chốt lời trước từ 30% đến 71% nhưng cả 10 cách đều "ngang hòa vốn": xác suất thắng cao chỉ đổi lấy mỗi lần lời ít hơn.

## Thẻ Price action riêng: hỗ trợ / kháng cự theo khung, bật lại hay xuyên qua (03/11/2026)

**Yêu cầu:** tách price action khỏi Long/Short thành thẻ riêng; kháng cự / hỗ trợ trong 1–24 giờ, 1–7 ngày, 1–8 tuần, 1–12 tháng (người dùng chọn số); khi giá chạm thì bật lại hay xuyên qua, xác suất bao nhiêu.

**Đăng ký trước** (`config/candidates.yaml` mục `sr_levels`, commit `da7ac7f`, trước khi tính): kháng cự = giá cao nhất của W nến gần nhất, hỗ trợ = giá thấp nhất (nến giờ BTCUSDT vĩnh cửu cho khung giờ / ngày, nến ngày Bitstamp cho khung tuần / tháng); chạm = nến kế tiếp vào vùng ± 0,25 ATR, đến từ phía bên kia; bật lại = đi ngược 1 ATR trước khi có nến đóng cửa vượt 0,5 ATR (một nến làm cả hai tính xuyên qua); đợt độc lập; so với **mức giả** (khoảng cách tương đối của một cửa sổ cũ không trùng, đặt vào giá hôm nay); kiểm định hai tỷ lệ, Holm trên 102 khung × phía, cùng chiều ở hai nửa. Module mới `bot/models/sr_levels.py`.

**Kiểm tra rò rỉ:** `tests/test_sr_levels.py` (12 bài): mức và lần chạm không đổi khi nến sau thay đổi (cả sập và tăng vọt), kết quả khớp vòng lặp từng nến, lần chạm khớp định nghĩa viết tay. Đã cài thử 2 lỗi: mức nhìn nến sau (bị bắt); "chạm" dùng mức có cả nến đang chạm — **lần đầu lọt**, đã thêm bài so lần chạm với định nghĩa viết tay, sau đó bị bắt.

**Kết quả** (nến giờ 07/2020 → 02/11/2026, nến ngày 2016 → 02/11/2026): **0/102 mức thật bật lại tốt hơn mức giả**; 1/102 hay bị xuyên qua hơn: kháng cự 3 ngày (bật xuống 53,5% trên 411 đợt so với 65,4% của mức giả, p Holm 0,047, cả hai nửa cùng chiều; sát ngưỡng); 80 như mức bất kỳ; 21 ít dữ liệu (khung nhiều tuần / nhiều tháng). Chưa hiệu chỉnh có 6/102 p < 0,05, gần với 5 mong đợi do may rủi. Tỷ lệ bật lại khoảng 55–65% có ở cả mức giả: do cách đo (1 ATR so với 0,5 ATR), không phải sức mạnh của mức. Khả năng chạm theo khoảng cách (mô tả): ví dụ kháng cự 1 ngày, cách 2–4 ATR, chạm trong 24 giờ 40% số lần.

**Trang web:** chế độ thứ năm "Price action" (nút `#mode-pa`, `src/pa.js`): chọn khung và số, giá lúc này, thang giá có vùng kháng cự / hỗ trợ và mức bật 1 ATR, hai thẻ (khoảng cách, khả năng chạm, bật lại / xuyên qua so với mức giả, kết luận), bảng mọi số của cùng đơn vị (bấm dòng để chọn); mức lúc này tính từ nến Binance khi mở thẻ, tự cập nhật mỗi phút. Bảng "Kiểm tra điểm vào" (mục `pa_sheet`) chuyển từ Long/Short sang đây, cách tính không đổi (ghi ở `pa_sheet.moved`). Sửa thêm một lỗi có từ trước: khi phần phân tích bên mua tải xong, nó tô sáng lại nút Bên mua dù đang ở Long/Short, Xu hướng hay Price action (`applyMode` trong `src/ui.js`).

## Nút Hold, đồ thị nến, vì sao giá gợi ý khác nhau (03/11/2026)

**Yêu cầu:** thêm nút Hold cạnh Long / Short trong bảng Kiểm tra điểm vào; chỉ quyết định khi hành động giá đã rõ, "chính xác trên 99%"; đồ thị giá lúc này và kháng cự; giải thích vì sao giá gợi ý ở Price action khác Long/Short.

**Đăng ký trước** (`config/candidates.yaml` mục `pa_hold`, commit `f6f09ef`): đề xuất Long chỉ khi Long/Short đạt đủ 6/6 phía long **và** price action nến ngày cuối rõ hướng tăng (có tiêu chí tăng, không tiêu chí giảm); Short đối xứng; còn lại Hold. Chỉ hiển thị lại kết quả đã có. **Không có cách nào đúng 99%**: mọi cách đoán hướng đã kiểm đều chưa thắng một ngày bất kỳ, nên trang nói rõ và để Hold làm mặc định.

**Lúc này (nến 02/11/2026): Hold.** Long/Short: Long 3/6, Short 1/6; price action mâu thuẫn (chạm hỗ trợ và giữ, chạm kháng cự và bị đẩy xuống, cấu trúc giảm cùng bật); kiểm định 0/48. Nút Hold cho biết chờ gì: giữ hỗ trợ, phá vỡ giả, nến rút chân ở hỗ trợ gần nhất (Long) hoặc kháng cự gần nhất (Short), kèm mức giá và tỷ lệ đúng hướng lịch sử của từng điều kiện (gần như một ngày bất kỳ).

**Đồ thị:** thẻ Price action vẽ nến Binance của khung đang chọn (2 × độ dài khung, 48–240 nến giờ hoặc 60–390 nến ngày) với vùng kháng cự / hỗ trợ, giá lúc này và mức bật 1 ATR (thay thang giá cũ); bảng Kiểm tra điểm vào vẽ 120 nến ngày Bitstamp với hỗ trợ / kháng cự, giá vào, cắt lỗ, chốt lời. `pa.json` và `sr.json` thêm nến gần đây để vẽ khi chưa tải được giá trực tiếp; số liệu kiểm định không đổi (vẫn 0/102, 0/48).

**Vì sao giá gợi ý khác nhau** (ghi trên trang, mục "Vì sao giá gợi ý ở đây khác thẻ Long/Short?"): Long/Short đặt cắt lỗ k × ATR của nến giờ Binance quanh giá lúc này hoặc giá kích hoạt, không nhìn đỉnh / đáy; Kiểm tra điểm vào đặt cắt lỗ dưới đáy cục bộ gần nhất − 0,5 ATR ngày của nến Bitstamp, giá vào = giá đóng nến ngày cuối; hỗ trợ / kháng cự theo khung là cao nhất / thấp nhất của khung. Ba cách khác dữ liệu và mục đích; không gộp.

## Mua giữ lâu dài (03/11/2026)

**Yêu cầu:** thêm lựa chọn "Mua giữ lâu dài" cạnh Long / Short / Hold, kèm giá nên mua và giữ bao lâu thì có lãi.

**Đăng ký trước** (`config/candidates.yaml` mục `long_hold`, commit `27e5f0c`): mua ở giá đóng ngày Coin Metrics của mọi ngày từ 01/01/2016, giữ 7 / 30 / 90 / 180 / 365 / 730 / 1461 ngày, phí và trượt giá 0,15% mỗi chiều; tỷ lệ có lãi, lãi trung vị, phân vị 10% / 90%, Wilson theo số lần độc lập (số ngày / h), hai nửa; "giữ ít nhất" = kỳ hạn ngắn nhất có lãi ≥ 80% ở cả hai nửa với cận dưới Wilson ≥ 50%. Giá nên mua đọc lại mục `entry` (không tính mới). Module mới `bot/models/long_hold.py`, test `tests/test_long_hold.py`.

**Kết quả** (đến 02/11/2026): có lãi 52% khi giữ 1 tuần (565 lần độc lập), 57% 1 tháng, 60% 3 tháng, 64% 6 tháng, 70% 1 năm (10 lần độc lập), 80% 2 năm (4 lần), 100% 4 năm (2 lần, Wilson 34–100%). Lãi trung vị +0%, +3%, +10%, +26%, +64%, +186%, +372%. **Chưa kỳ hạn nào đạt quy tắc "giữ ít nhất"**: 2 năm có nửa sau 70%; 4 năm đúng mọi lần nhưng chỉ 2 giai đoạn độc lập. Giá nên mua: mua dần quanh giá hiện tại (20 cách chờ giá thấp hơn, 0 cách tốt hơn, 6 cách kém hơn rõ), kèm khả năng khớp lệnh chờ −1 … −10% trong 7 / 30 ngày và khoảng giá thấp nhất 30 ngày tới.

**Trang web:** nút "Mua giữ lâu dài" (thứ tư) trong bảng Kiểm tra điểm vào: giá nên mua, bảng lệnh chờ, thanh tỷ lệ có lãi theo thời gian giữ (có khoảng tin cậy, vạch 50% và 80%), bảng chi tiết với giá thường gặp khi bán, cảnh báo BTC 2016–2026 tăng rất mạnh. Lệnh `python -m bot.cli long-hold` trong quy trình Daily (`data/results/hold.json`).

## Đợt 1 của kế hoạch tổng quan: Tóm tắt quyết định, gỡ Phân tích cũ, R1, test trình duyệt trong CI (03/11/2026)

- **S1 Tóm tắt quyết định** (mục `summary`, commit `dcdd376`): bảng ở đầu Tổng quan, mỗi công cụ một dòng (khuyến nghị tuần, dải giá 7 ngày, giá chờ mua / bán, xác suất có lãi / giá thấp hơn, xu hướng, Long/Short, price action, mua giữ lâu dài), mức tin cậy lấy đúng bảng của `docs/DANH_GIA_TONG_QUAN.md`, nút Mở đúng thẻ / chế độ. Chỉ đọc số đã tính; các chế độ riêng báo kết luận qua `window.LS_VERDICT` và `window.BOT_SUMMARY`.
- **A2 gỡ Phân tích cũ** (phương án 1): bỏ thẻ khỏi thanh thẻ (địa chỉ `#old` về Tổng quan); báo cáo tải về, gói claude.ai và báo cáo gửi API không còn tỷ lệ nên mua / bán, giá đề xuất, xác suất thắng theo khung, bộ chỉ số, so sánh phương án, bên bán cũ, trọng số mô hình (`B3.report(..., {legacy: false})`, có câu giải thích). Mã tính cũ còn giữ (chạy ẩn) vì `tests/test_engine.js` và chỉ số thô của báo cáo dùng nó.
- **R1** (mục `exit_calib`, commit `d9ac53b`, chỉ báo cáo): khả năng chạm giá chờ bán **không lệch có hệ thống** ở cả hai nửa giai đoạn ở mọi mức +1 … +8% và kỳ hạn 7 / 30 ngày; trung bình bot thận trọng 2–4 điểm (ví dụ +3% / 7 ngày: nói 63%, thật 66%, Wilson 61–69%); từng năm lệch qua lại (2017 +15 điểm, 2018 −6 điểm); trên / dưới MA 200 ngày gần như nhau. Con số 55% / 79% của hồi cứu 24 thời điểm là nhiễu. Không đổi phương pháp. Báo cáo: `docs/R1_GIA_CHO_BAN.md`.
- **L7**: `tests/test_browser.py` viết lại thành bài pytest (đánh dấu `slow`, bỏ khỏi `make test` mặc định) chạy cả trang trên dữ liệu giả qua đường tải thật ở 1280 sáng / 390 sáng / 1280 tối: không lỗi trang, không trượt ngang, thẻ cũ đã gỡ, báo cáo không còn phần cũ. Khoảng 22 giây. CI chạy bằng `python -m pytest -m slow`; **chưa bật trong Daily** (chờ người dùng duyệt, đúng câu lệnh L7).
