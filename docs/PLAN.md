# Kế hoạch giải ngân một khoản tiền

Đăng ký trước: `config/candidates.yaml` mục `plan` (commit `0be9828`). Mã: `bot/models/deploy_plan.py`. Trang web hiện bảng này và lập lịch theo số tiền bạn nhập.

- Với mỗi tuần bắt đầu trong quá khứ: chia số tiền thành N phần, mua mỗi thứ Hai (giá đóng thứ Hai, phí 0,10% + trượt giá 0,05%). Tiền chưa mua giữ nguyên, lãi 0%. Đọc tổng giá trị 52 tuần sau lần mua đầu.
- ROI cao nhất: phương án có trung vị lợi nhuận sau 52 tuần cao nhất. Không kém đáng kể: khoảng tin cậy 95% của trung vị chênh lệch theo từng tuần bắt đầu, bootstrap khối 52 tuần, chứa 0.
- Đề xuất (mục `plan.stable`, từ 04/11/2026): chỉ nêu một phương án là 'đề xuất' khi mọi phương án khác đều kém phương án ROI cao nhất đáng kể (khoảng tin cậy 95% như mục rule không chứa 0); đề xuất khi đó là phương án ROI cao nhất. Nếu không: nếu từ 2 phương án trở lên không kém đáng kể: trang nói các cách đó gần như ngang nhau trong lịch sử, liệt kê từng cách với trung vị và 10% xấu nhất, chỉ ra cách có trung vị cao nhất và cách có 10% xấu nhất ít thiệt nhất trong nhóm, không nêu 'đề xuất' và không chọn sẵn lịch (người dùng bấm một cách).
- Không nghiêng theo tín hiệu: kiểm định 6 tiêu chí (Phần I) không đạt, nên mọi phương án chia đều theo thời gian.

## 3 chu kỳ gần nhất (dùng trên web): 10/07/2016 → 02/11/2025, 487 tuần bắt đầu, khoảng 9 đợt độc lập

| Phương án | Trung vị sau 1 năm | 10% xấu nhất | 10% tốt nhất | Xấu nhất | Tỷ lệ lỗ | Giảm sâu nhất (trung vị / tệ nhất) | Thắng giải ngân một lần (Wilson theo đợt) | Kém ROI cao nhất (KTC 95%) |
|---|---|---|---|---|---|---|---|---|
| Giải ngân một lần **ROI cao nhất** (ngang nhau) | +56% | -45% | +457% | -82% | 32% | -48% / -82% | — | 0% (0% đến 0%) |
| Chia đều 4 tuần | +51% | -46% | +458% | -78% | 32% | -48% / -81% | 44% (19%–73%) | +1% (0% đến +4%) |
| Chia đều 13 tuần (ngang nhau) | +53% | -48% | +371% | -71% | 32% | -46% / -72% | 41% (19%–73%) | +5% (0% đến +21%) |
| Chia đều 26 tuần (ngang nhau) | +44% | -46% | +320% | -64% | 32% | -40% / -69% | 40% (19%–73%) | +11% (-2% đến +41%) |
| Chia đều 52 tuần (ngang nhau) | +26% | -31% | +206% | -55% | 30% | -28% / -64% | 34% (12%–65%) | +27% (-1% đến +67%) |

## Toàn bộ lịch sử (tham khảo): 02/12/2012 → 02/11/2025, 675 tuần bắt đầu, khoảng 12 đợt độc lập

| Phương án | Trung vị sau 1 năm | 10% xấu nhất | 10% tốt nhất | Xấu nhất | Tỷ lệ lỗ | Giảm sâu nhất (trung vị / tệ nhất) | Thắng giải ngân một lần (Wilson theo đợt) | Kém ROI cao nhất (KTC 95%) |
|---|---|---|---|---|---|---|---|---|
| Giải ngân một lần | +70% | -51% | +525% | -82% | 31% | -48% / -82% | — | -1% (-4% đến 0%) |
| Chia đều 4 tuần **ROI cao nhất** (ngang nhau) | +70% | -50% | +514% | -78% | 31% | -48% / -81% | 44% (19%–68%) | 0% (0% đến 0%) |
| Chia đều 13 tuần (ngang nhau) | +67% | -51% | +475% | -71% | 31% | -45% / -72% | 42% (19%–68%) | +4% (-1% đến +16%) |
| Chia đều 26 tuần (ngang nhau) | +55% | -49% | +342% | -64% | 32% | -38% / -69% | 40% (19%–68%) | +10% (-2% đến +35%) |
| Chia đều 52 tuần | +35% | -32% | +211% | -55% | 30% | -27% / -64% | 35% (14%–61%) | +36% (+3% đến +67%) |

Giới hạn: các cửa sổ 1 năm chồng lấn nhau nên số đợt độc lập ít (khoảng tin cậy rộng); BTC đã tăng mạnh trong lịch sử nên giải ngân sớm thường lợi hơn, nhưng không có gì bảo đảm điều đó lặp lại. Công cụ tham khảo, không phải lời khuyên đầu tư.
