# Price action so với "một ngày bất kỳ"

Sinh tự động bằng `python -m bot.cli price-action` lúc 16:46 03/11/2026 (mã `9400d51`), nến ngày Bitstamp đến 01/11/2026. Cách làm đăng ký trước trong `config/candidates.yaml` mục `price_action`, lưu git trước khi tính (xem `docs/REBUILD_LOG.md`). Công cụ tham khảo, không phải lời khuyên đầu tư.

## Price action là gì

Price action (hành động giá) là cách đọc chính biểu đồ giá, không dùng chỉ báo: giá hay dừng ở đâu (hỗ trợ, kháng cự), đang đi lên hay xuống (chuỗi đỉnh và đáy), và hình dạng cây nến tại những chỗ đó (pin bar có bóng dài, inside bar nằm gọn trong nến trước, phá vỡ giả). Người dùng price action tin rằng những hình ảnh này báo trước hướng giá. Ở đây mỗi ý được viết thành một quy tắc bằng số, rồi đếm xem sau khi quy tắc bật, giá có đi đúng hướng nhiều hơn một ngày bất kỳ hay không.

## Kết luận

- **Không tiêu chí price action nào đoán hướng giá tốt hơn một ngày bất kỳ**: 0/48 cặp tiêu chí × kỳ hạn hơn mốc sau hiệu chỉnh Holm.
- Chưa có lợi thế: 44 cặp; ít đợt, không kết luận: 4 cặp.
- Gần nhất với "hơn mốc" là Chạm kháng cự và bị đẩy xuống (30 ngày), xếp loại ít đợt (không kết luận). Đúng 52,0% so với mốc 42,5% (456 lần, 29 đợt; tính theo đợt chỉ đúng 41,4%, Wilson 25,5%–59,3%), p trước hiệu chỉnh 0,002, sau Holm 0,096; nửa đầu +7,3%, nửa sau +10,3%.
- Trước hiệu chỉnh có 5/48 cặp p < 0,05 (2 hơn, 3 kém mốc). Chỉ do may rủi, 48 phép thử đã cho khoảng 2,4 cặp như vậy, nên chừng đó chưa nói lên lợi thế.
- Bộ tiêu chí (ít nhất 2 trong 5 tiêu chí cùng hướng), 8 cặp: chưa có lợi thế 8.
- "Mốc" là tỷ lệ của mọi ngày trong cùng giai đoạn: BTC tăng giá nên một ngày bất kỳ đã có hơn một nửa số lần giá cao hơn sau k ngày. Tiêu chí tăng phải vượt tỷ lệ đó; tiêu chí giảm phải vượt tỷ lệ giá thấp hơn.
- Theo đăng ký trước: không có cặp nào hơn mốc, nên **trang không dùng price action làm tín hiệu vào lệnh**. Theo yêu cầu của người dùng, chế độ Long/Short có mục "Price action" (mục `pa_sheet`) để xem hành động giá lúc này và kiểm tra điểm vào; mục đó luôn ghi price action chưa có lợi thế và không đổi kết luận Long/Short.

## Cách kiểm định

- Giai đoạn nghiên cứu: ngày tín hiệu và ngày kết quả từ 01/01/2016 đến 01/11/2026. Nến trước 2016 (từ 08/2011) chỉ dùng để tính ATR, đỉnh và đáy.
- Tín hiệu ở ngày T chỉ dùng nến đến T. Đỉnh / đáy cục bộ cần 5 nến bên phải, nên chỉ được dùng từ khi nến thứ 5 sau nó đóng; mức hỗ trợ / kháng cự chốt trước nến T (đỉnh / đáy đã biết đến T − 1, so với giá đóng T − 1).
- Kết quả: giá đóng ngày sau k ngày cao hơn (tiêu chí tăng) hoặc thấp hơn (tiêu chí giảm) giá đóng ngày T; bằng nhau là sai.
- Số đợt: tín hiệu cách nhau không quá k ngày gộp thành một đợt (kết quả chồng nhau). Khoảng Wilson 95% tính theo số đợt.
- Khoảng tin cậy của chênh lệch: bootstrap khối dừng (2000 lần, khối trung bình k ngày). p đã hiệu chỉnh Holm trên cả 48 cặp. "Hơn / kém mốc" khi p Holm < 0,05 và chênh lệch cùng dấu ở cả hai nửa giai đoạn; dưới 30 đợt hoặc dưới 5 đợt ở một nửa thì không kết luận.
- Với 2000 lần lấy lại, p nhỏ nhất là 0,001, sau Holm trên 48 cặp là 0,048: một cặp chỉ "hơn mốc" khi gần như mọi lần lấy lại đều cho chênh lệch dương. Ngưỡng này tương đương đòi hỏi của hiệu chỉnh nhiều phép thử, không khắt khe hơn.

## Định nghĩa (đăng ký trước)

Mức hỗ trợ / kháng cự: mức tại T, chốt trước nến T: S = hỗ trợ gần nhất = đáy cục bộ cao nhất có mức < đóng(T − 1), trong các đáy đã biết đến T − 1 (j + 5 ≤ T − 1) có j ≥ T − 1 − 365; R = kháng cự gần nhất = đỉnh cục bộ thấp nhất có mức > đóng(T − 1), cùng điều kiện. w = 0,5 × ATR(T − 1). Không có S (hoặc R, hoặc ATR) thì các tiêu chí dùng nó không bật

| Tiêu chí | Hướng | Định nghĩa | Số ngày bật (giai đoạn nghiên cứu) |
|---|---|---|---|
| Chạm hỗ trợ và giữ | tăng | chạm hỗ trợ và giữ: S − w ≤ thấp(T) ≤ S + w, đóng(T) > S, đóng(T − 1) > S + w (hôm trước còn ở trên vùng) | 480 |
| Chạm kháng cự và bị đẩy xuống | giảm | chạm kháng cự và bị đẩy xuống: R − w ≤ cao(T) ≤ R + w, đóng(T) < R, đóng(T − 1) < R − w | 461 |
| Cấu trúc tăng (đỉnh cao hơn, đáy cao hơn) | tăng | cấu trúc tăng: trong hai đỉnh cục bộ đã biết gần nhất, đỉnh sau cao hơn đỉnh trước; trong hai đáy cục bộ đã biết gần nhất, đáy sau cao hơn đáy trước; và đóng(T) > đáy cục bộ đã biết gần nhất (cấu trúc chưa gãy) | 1.365 |
| Cấu trúc giảm (đỉnh thấp hơn, đáy thấp hơn) | giảm | cấu trúc giảm: đỉnh sau thấp hơn đỉnh trước, đáy sau thấp hơn đáy trước, và đóng(T) < đỉnh cục bộ đã biết gần nhất | 748 |
| Pin bar tăng tại hỗ trợ | tăng | pin bar tăng tại hỗ trợ: biên > 0, bóng dưới ≥ 2/3 biên, thấp(T) ≤ S + w và đóng(T) > S | 106 |
| Pin bar giảm tại kháng cự | giảm | pin bar giảm tại kháng cự: biên > 0, bóng trên ≥ 2/3 biên, cao(T) ≥ R − w và đóng(T) < R | 56 |
| Inside bar tại hỗ trợ | tăng | inside bar tại hỗ trợ: cao(T) < cao(T − 1) và thấp(T) > thấp(T − 1) (nến mẹ là T − 1), và nến mẹ chạm vùng hỗ trợ: thấp(T − 1) ≤ S + w (S, w của ngày T) | 398 |
| Inside bar tại kháng cự | giảm | inside bar tại kháng cự: cao(T) < cao(T − 1), thấp(T) > thấp(T − 1), và cao(T − 1) ≥ R − w | 361 |
| Phá vỡ giả phía dưới | tăng | phá vỡ giả phía dưới: thấp(T) < S − w (thủng quá vùng hỗ trợ) nhưng đóng(T) > S (đóng cửa quay lại trên hỗ trợ) | 53 |
| Phá vỡ giả phía trên | giảm | phá vỡ giả phía trên: cao(T) > R + w nhưng đóng(T) < R | 40 |
| Bộ tiêu chí tăng (≥ 2/5) | tăng | bộ tiêu chí tăng: ít nhất combo_m = 2 trong 5 tiêu chí tăng (ho_tro, cau_truc_tang, pin_bar_ho_tro, inside_bar_ho_tro, pha_vo_gia_duoi) bật cùng ngày T | 348 |
| Bộ tiêu chí giảm (≥ 2/5) | giảm | bộ tiêu chí giảm: ít nhất 2 trong 5 tiêu chí giảm (khang_cu, cau_truc_giam, pin_bar_khang_cu, inside_bar_khang_cu, pha_vo_gia_tren) bật cùng ngày T | 225 |

## Từng tiêu chí × kỳ hạn

| Tiêu chí | Kỳ hạn | Số lần | Số đợt | Đúng | Đúng theo đợt (Wilson 95%) | Mốc | Chênh lệch (KTC 95%) | p Holm | Nửa đầu / nửa sau | Kết luận |
|---|---|---|---|---|---|---|---|---|---|---|
| Chạm hỗ trợ và giữ | 1 ngày | 480 | 348 | 52,3% | 52,0% (46,8%–57,2%) | 52,1% | +0,2% (-4,3% đến +4,4%) | 1,000 | -0,2% / +1,1% | chưa có lợi thế |
| Chạm hỗ trợ và giữ | 3 ngày | 479 | 242 | 54,5% | 55,0% (48,7%–61,1%) | 54,6% | -0,1% (-4,6% đến +4,4%) | 1,000 | +1,1% / -0,2% | chưa có lợi thế |
| Chạm hỗ trợ và giữ | 7 ngày | 479 | 146 | 55,5% | 58,2% (50,1%–65,9%) | 54,1% | +1,4% (-3,3% đến +6,0%) | 1,000 | +3,3% / +0,9% | chưa có lợi thế |
| Chạm hỗ trợ và giữ | 30 ngày | 473 | 30 | 57,1% | 70,0% (52,1%–83,3%) | 57,5% | -0,4% (-5,9% đến +5,4%) | 1,000 | -3,0% / +2,7% | chưa có lợi thế |
| Chạm kháng cự và bị đẩy xuống | 1 ngày | 461 | 340 | 48,8% | 48,8% (43,6%–54,1%) | 47,8% | +1,0% (-3,3% đến +5,4%) | 1,000 | +0,6% / +0,8% | chưa có lợi thế |
| Chạm kháng cự và bị đẩy xuống | 3 ngày | 460 | 248 | 45,4% | 44,8% (38,7%–51,0%) | 45,4% | 0,0% (-4,4% đến +4,4%) | 1,000 | -1,4% / +0,7% | chưa có lợi thế |
| Chạm kháng cự và bị đẩy xuống | 7 ngày | 458 | 148 | 52,6% | 48,6% (40,7%–56,6%) | 45,9% | +6,7% (+1,7% đến +11,7%) | 0,470 | +1,7% / +10,1% | chưa có lợi thế |
| Chạm kháng cự và bị đẩy xuống | 30 ngày | 456 | 29 | 52,0% | 41,4% (25,5%–59,3%) | 42,5% | +9,5% (+3,6% đến +15,2%) | 0,096 | +7,3% / +10,3% | ít đợt (không kết luận) |
| Cấu trúc tăng (đỉnh cao hơn, đáy cao hơn) | 1 ngày | 1.365 | 92 | 53,2% | 52,2% (42,1%–62,1%) | 52,1% | +1,1% (-1,1% đến +3,3%) | 1,000 | +4,2% / -4,4% | chưa có lợi thế |
| Cấu trúc tăng (đỉnh cao hơn, đáy cao hơn) | 3 ngày | 1.365 | 80 | 55,6% | 48,8% (38,1%–59,5%) | 54,6% | +1,0% (-1,9% đến +3,9%) | 1,000 | +5,1% / -5,8% | chưa có lợi thế |
| Cấu trúc tăng (đỉnh cao hơn, đáy cao hơn) | 7 ngày | 1.365 | 72 | 55,0% | 43,1% (32,3%–54,6%) | 54,1% | +0,9% (-3,0% đến +4,9%) | 1,000 | +4,6% / -5,4% | chưa có lợi thế |
| Cấu trúc tăng (đỉnh cao hơn, đáy cao hơn) | 30 ngày | 1.361 | 34 | 58,3% | 50,0% (34,1%–65,9%) | 57,5% | +0,8% (-5,9% đến +6,8%) | 1,000 | +4,5% / -6,3% | chưa có lợi thế |
| Cấu trúc giảm (đỉnh thấp hơn, đáy thấp hơn) | 1 ngày | 747 | 64 | 48,6% | 40,6% (29,5%–52,9%) | 47,8% | +0,8% (-2,3% đến +4,1%) | 1,000 | +2,1% / -0,9% | chưa có lợi thế |
| Cấu trúc giảm (đỉnh thấp hơn, đáy thấp hơn) | 3 ngày | 745 | 55 | 45,6% | 58,2% (45,0%–70,3%) | 45,4% | +0,3% (-3,8% đến +4,2%) | 1,000 | +1,5% / -1,3% | chưa có lợi thế |
| Cấu trúc giảm (đỉnh thấp hơn, đáy thấp hơn) | 7 ngày | 741 | 53 | 44,4% | 52,8% (39,7%–65,6%) | 45,9% | -1,5% (-7,1% đến +4,3%) | 1,000 | +2,1% / -5,0% | chưa có lợi thế |
| Cấu trúc giảm (đỉnh thấp hơn, đáy thấp hơn) | 30 ngày | 728 | 32 | 35,2% | 34,4% (20,4%–51,7%) | 42,5% | -7,3% (-16,8% đến +1,7%) | 1,000 | -6,6% / -9,0% | chưa có lợi thế |
| Pin bar tăng tại hỗ trợ | 1 ngày | 106 | 104 | 44,3% | 44,2% (35,1%–53,8%) | 52,1% | -7,8% (-17,0% đến +1,6%) | 1,000 | -10,3% / -5,3% | chưa có lợi thế |
| Pin bar tăng tại hỗ trợ | 3 ngày | 106 | 94 | 45,3% | 45,7% (36,0%–55,8%) | 54,6% | -9,3% (-18,3% đến +0,2%) | 1,000 | -10,7% / -7,6% | chưa có lợi thế |
| Pin bar tăng tại hỗ trợ | 7 ngày | 106 | 76 | 54,7% | 55,3% (44,1%–65,9%) | 54,1% | +0,6% (-8,6% đến +9,6%) | 1,000 | +2,9% / -0,2% | chưa có lợi thế |
| Pin bar tăng tại hỗ trợ | 30 ngày | 104 | 43 | 56,7% | 58,1% (43,3%–71,6%) | 57,5% | -0,8% (-9,7% đến +9,0%) | 1,000 | +2,4% / -2,2% | chưa có lợi thế |
| Pin bar giảm tại kháng cự | 1 ngày | 56 | 54 | 48,2% | 46,3% (33,7%–59,4%) | 47,8% | +0,4% (-13,6% đến +13,3%) | 1,000 | +11,8% / -5,1% | chưa có lợi thế |
| Pin bar giảm tại kháng cự | 3 ngày | 56 | 51 | 44,6% | 45,1% (32,3%–58,6%) | 45,4% | -0,7% (-12,6% đến +12,1%) | 1,000 | +0,2% / -2,9% | chưa có lợi thế |
| Pin bar giảm tại kháng cự | 7 ngày | 56 | 48 | 48,2% | 50,0% (36,4%–63,6%) | 45,9% | +2,3% (-10,5% đến +15,4%) | 1,000 | 0,0% / +1,1% | chưa có lợi thế |
| Pin bar giảm tại kháng cự | 30 ngày | 55 | 30 | 49,1% | 36,7% (21,9%–54,5%) | 42,5% | +6,6% (-7,6% đến +20,5%) | 1,000 | +4,9% / +4,2% | chưa có lợi thế |
| Inside bar tại hỗ trợ | 1 ngày | 398 | 354 | 53,8% | 55,6% (50,4%–60,7%) | 52,1% | +1,6% (-3,2% đến +6,3%) | 1,000 | +8,4% / -3,2% | chưa có lợi thế |
| Inside bar tại hỗ trợ | 3 ngày | 397 | 235 | 52,6% | 49,8% (43,4%–56,1%) | 54,6% | -2,0% (-6,8% đến +2,3%) | 1,000 | +0,6% / -3,5% | chưa có lợi thế |
| Inside bar tại hỗ trợ | 7 ngày | 397 | 123 | 54,7% | 50,4% (41,7%–59,1%) | 54,1% | +0,6% (-4,5% đến +5,6%) | 1,000 | +2,0% / +0,1% | chưa có lợi thế |
| Inside bar tại hỗ trợ | 30 ngày | 390 | 29 | 58,5% | 55,2% (37,5%–71,6%) | 57,5% | +1,0% (-5,1% đến +7,0%) | 1,000 | +0,8% / +1,9% | ít đợt (không kết luận) |
| Inside bar tại kháng cự | 1 ngày | 361 | 326 | 42,9% | 43,3% (38,0%–48,7%) | 47,8% | -4,9% (-9,7% đến -0,1%) | 1,000 | -7,5% / -3,2% | chưa có lợi thế |
| Inside bar tại kháng cự | 3 ngày | 360 | 224 | 48,1% | 51,8% (45,3%–58,2%) | 45,4% | +2,7% (-1,9% đến +7,7%) | 1,000 | 0,0% / +4,4% | chưa có lợi thế |
| Inside bar tại kháng cự | 7 ngày | 360 | 125 | 46,7% | 44,8% (36,4%–53,5%) | 45,9% | +0,8% (-5,0% đến +6,1%) | 1,000 | -3,3% / +3,6% | chưa có lợi thế |
| Inside bar tại kháng cự | 30 ngày | 354 | 30 | 44,4% | 46,7% (30,2%–63,9%) | 42,5% | +1,9% (-5,1% đến +8,5%) | 1,000 | -4,0% / +6,1% | chưa có lợi thế |
| Phá vỡ giả phía dưới | 1 ngày | 53 | 53 | 41,5% | 41,5% (29,3%–54,9%) | 52,1% | -10,6% (-24,0% đến +2,3%) | 1,000 | -9,7% / -10,2% | chưa có lợi thế |
| Phá vỡ giả phía dưới | 3 ngày | 53 | 49 | 47,2% | 46,9% (33,7%–60,6%) | 54,6% | -7,4% (-20,5% đến +6,6%) | 1,000 | -2,4% / -9,4% | chưa có lợi thế |
| Phá vỡ giả phía dưới | 7 ngày | 53 | 46 | 56,6% | 58,7% (44,3%–71,7%) | 54,1% | +2,5% (-12,0% đến +16,8%) | 1,000 | +2,9% / +3,5% | chưa có lợi thế |
| Phá vỡ giả phía dưới | 30 ngày | 52 | 27 | 40,4% | 51,9% (34,0%–69,3%) | 57,5% | -17,1% (-32,4% đến -0,6%) | 1,000 | -17,0% / -15,5% | ít đợt (không kết luận) |
| Phá vỡ giả phía trên | 1 ngày | 40 | 38 | 27,5% | 28,9% (17,0%–44,8%) | 47,8% | -20,3% (-33,1% đến -5,9%) | 0,470 | -32,0% / -14,4% | chưa có lợi thế |
| Phá vỡ giả phía trên | 3 ngày | 40 | 36 | 40,0% | 36,1% (22,5%–52,4%) | 45,4% | -5,4% (-20,4% đến +10,1%) | 1,000 | -9,3% / -4,1% | chưa có lợi thế |
| Phá vỡ giả phía trên | 7 ngày | 40 | 32 | 45,0% | 37,5% (22,9%–54,7%) | 45,9% | -0,9% (-15,9% đến +15,2%) | 1,000 | -2,9% / -0,9% | chưa có lợi thế |
| Phá vỡ giả phía trên | 30 ngày | 40 | 25 | 42,5% | 36,0% (20,2%–55,5%) | 42,5% | 0,0% (-19,2% đến +20,4%) | 1,000 | -11,3% / +5,0% | ít đợt (không kết luận) |
| Bộ tiêu chí tăng (≥ 2/5) | 1 ngày | 348 | 253 | 48,9% | 52,6% (46,4%–58,6%) | 52,1% | -3,3% (-8,4% đến +1,5%) | 1,000 | +2,8% / -7,5% | chưa có lợi thế |
| Bộ tiêu chí tăng (≥ 2/5) | 3 ngày | 348 | 183 | 49,7% | 49,7% (42,6%–56,9%) | 54,6% | -4,9% (-10,3% đến +0,1%) | 1,000 | -2,5% / -6,2% | chưa có lợi thế |
| Bộ tiêu chí tăng (≥ 2/5) | 7 ngày | 348 | 123 | 53,2% | 51,2% (42,5%–59,9%) | 54,1% | -0,9% (-6,6% đến +4,8%) | 1,000 | +3,0% / -3,4% | chưa có lợi thế |
| Bộ tiêu chí tăng (≥ 2/5) | 30 ngày | 342 | 33 | 55,0% | 60,6% (43,7%–75,3%) | 57,5% | -2,5% (-9,4% đến +4,4%) | 1,000 | -2,5% / -1,7% | chưa có lợi thế |
| Bộ tiêu chí giảm (≥ 2/5) | 1 ngày | 225 | 170 | 45,8% | 47,1% (39,7%–54,5%) | 47,8% | -2,1% (-8,3% đến +4,2%) | 1,000 | +3,7% / -7,1% | chưa có lợi thế |
| Bộ tiêu chí giảm (≥ 2/5) | 3 ngày | 223 | 140 | 49,3% | 50,0% (41,8%–58,2%) | 45,4% | +3,9% (-2,7% đến +10,9%) | 1,000 | +4,8% / +2,7% | chưa có lợi thế |
| Bộ tiêu chí giảm (≥ 2/5) | 7 ngày | 221 | 108 | 52,0% | 54,6% (45,2%–63,7%) | 45,9% | +6,1% (-1,0% đến +13,3%) | 1,000 | +2,4% / +8,2% | chưa có lợi thế |
| Bộ tiêu chí giảm (≥ 2/5) | 30 ngày | 217 | 42 | 49,8% | 45,2% (31,2%–60,1%) | 42,5% | +7,3% (-2,8% đến +16,8%) | 1,000 | -0,7% / +12,4% | chưa có lợi thế |

## Đã biết trước, không thử lại

Đã biết trước khi đăng ký và KHÔNG thử lại ở đây: (1) mục candles: 12 mẫu nến kinh điển trên nến ngày Bitstamp (nhấn chìm, búa, sao băng, doji sau giảm / tăng, sao mai / sao hôm, ba chàng lính trắng / ba quạ đen, xuyên tăng, mây đen), không mẫu nào thắng một ngày bất kỳ; (2) nhánh claude/eloquent-boyd-80d429 (chưa gộp): 7 mẫu nến trên nến ngày và nến tuần, 0/42 cặp hơn mốc; (3) mục trend: động lượng, giá so với MA 200 ngày, định giá MVRV, đảo chiều ngắn hạn 7 ngày, kết hợp: 0/80 phép so sánh thắng tỷ lệ gốc về hướng; (4) mục trend_plus: học máy logistic 16 đặc trưng (gồm 11 cờ mẫu nến), kém tỷ lệ gốc ở 16/16 kỳ hạn; (5) mục perp và perp_trade: Long/Short trên nến giờ hợp đồng vĩnh cửu gồm theo xu hướng 20 ngày, phá đỉnh / thủng đáy 20 ngày (đóng cửa vượt ra ngoài), đánh ngược sau 24 giờ tăng / giảm mạnh, điều chỉnh trong xu hướng, funding ngược: chưa có lợi thế (chấm đi tới −0,09R); (6) mục entry / exit: đặt lệnh chờ thấp hơn / cao hơn không tốt hơn mua / bán ngay; (7) tín hiệu tuần của bot đạt 0/6 tiêu chí. Vì mọi cách đoán hướng trước đây đều chưa thắng, kỳ vọng trước khi chạy là 'chưa có lợi thế'. Chưa tính con số nào của các tiêu chí dưới đây trên dữ liệu BTC.

## Giai đoạn kiểm tra cuối mới

- Tín hiệu từ 03/11/2026 (ngày đăng ký). Chỉ chạy một lần bằng `python -m bot.cli price-action --final` khi có ít nhất 365 ngày đã biết kết quả 30 ngày (hiện có 0); lệnh ghi vào `experiments/final_runs.log` và từ chối lần chạy thứ hai.
- Chỉ xác nhận các cặp hơn / kém mốc ở giai đoạn nghiên cứu; không có cặp nào thì chỉ báo cáo mô tả.
