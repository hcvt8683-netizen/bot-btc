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
