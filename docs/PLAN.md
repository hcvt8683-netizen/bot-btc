# Kế hoạch giải ngân một khoản tiền

Đăng ký trước: `config/candidates.yaml` mục `plan` (commit `0be9828`). Mã: `bot/models/deploy_plan.py`. Trang web hiện bảng này và lập lịch theo số tiền bạn nhập.

- Với mỗi tuần bắt đầu trong quá khứ: chia số tiền thành N phần, mua mỗi thứ Hai (giá đóng thứ Hai, phí 0,10% + trượt giá 0,05%). Tiền chưa mua giữ nguyên, lãi 0%. Đọc tổng giá trị 52 tuần sau lần mua đầu.
- ROI cao nhất: phương án có trung vị lợi nhuận sau 52 tuần cao nhất. Đề xuất: đề xuất = trong phương án ROI cao nhất và các phương án không kém nó đáng kể (khoảng tin cậy 95% của trung vị chênh lệch theo từng tuần bắt đầu, bootstrap khối 52 tuần, chứa 0), chọn phương án có phân vị 10% cao nhất (ít thiệt nhất khi gặp lúc xấu).
- Không nghiêng theo tín hiệu: kiểm định 6 tiêu chí (Phần I) không đạt, nên mọi phương án chia đều theo thời gian.

## 3 chu kỳ gần nhất (dùng trên web): 10/07/2016 → 26/10/2025, 486 tuần bắt đầu, khoảng 9 đợt độc lập

| Phương án | Trung vị sau 1 năm | 10% xấu nhất | 10% tốt nhất | Xấu nhất | Tỷ lệ lỗ | Giảm sâu nhất (trung vị / tệ nhất) | Thắng giải ngân một lần (Wilson theo đợt) | Kém ROI cao nhất (KTC 95%) |
|---|---|---|---|---|---|---|---|---|
| Giải ngân một lần **ROI cao nhất** **← đề xuất** | +56% | -45% | +457% | -82% | 32% | -48% / -82% | — | 0% (0% đến 0%) |
| Chia đều 4 tuần | +52% | -46% | +463% | -78% | 32% | -48% / -81% | 43% (19%–73%) | +1% (0% đến +4%) |
| Chia đều 13 tuần | +53% | -48% | +372% | -71% | 32% | -46% / -72% | 41% (19%–73%) | +5% (0% đến +20%) |
| Chia đều 26 tuần | +44% | -46% | +321% | -64% | 32% | -40% / -69% | 40% (19%–73%) | +12% (-3% đến +39%) |
| Chia đều 52 tuần | +26% | -31% | +206% | -55% | 30% | -28% / -64% | 34% (12%–65%) | +27% (+1% đến +64%) |

## Toàn bộ lịch sử (tham khảo): 02/12/2012 → 26/10/2025, 674 tuần bắt đầu, khoảng 12 đợt độc lập

| Phương án | Trung vị sau 1 năm | 10% xấu nhất | 10% tốt nhất | Xấu nhất | Tỷ lệ lỗ | Giảm sâu nhất (trung vị / tệ nhất) | Thắng giải ngân một lần (Wilson theo đợt) | Kém ROI cao nhất (KTC 95%) |
|---|---|---|---|---|---|---|---|---|
| Giải ngân một lần | +70% | -51% | +526% | -82% | 31% | -48% / -82% | — | -1% (-4% đến 0%) |
| Chia đều 4 tuần **ROI cao nhất** | +71% | -50% | +515% | -78% | 31% | -48% / -81% | 44% (19%–68%) | 0% (0% đến 0%) |
| Chia đều 13 tuần | +68% | -51% | +475% | -71% | 31% | -45% / -72% | 42% (19%–68%) | +4% (-1% đến +15%) |
| Chia đều 26 tuần **← đề xuất** | +55% | -49% | +343% | -64% | 32% | -38% / -69% | 39% (19%–68%) | +10% (-3% đến +34%) |
| Chia đều 52 tuần | +35% | -32% | +212% | -55% | 30% | -27% / -64% | 34% (14%–61%) | +36% (+3% đến +67%) |

Giới hạn: các cửa sổ 1 năm chồng lấn nhau nên số đợt độc lập ít (khoảng tin cậy rộng); BTC đã tăng mạnh trong lịch sử nên giải ngân sớm thường lợi hơn, nhưng không có gì bảo đảm điều đó lặp lại. Công cụ tham khảo, không phải lời khuyên đầu tư.
