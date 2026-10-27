# Bắt đầu phát triển bot bằng Claude Code

1. Giải nén thư mục này vào chỗ cố định, ví dụ `Documents\BotBTC-source`.
2. Mở Claude Code (ứng dụng Claude trên máy tính, thẻ Code; hoặc tiện ích trong VS Code), chọn mở đúng thư mục này.
3. Claude Code tự đọc `CLAUDE.md` để hiểu dự án và các nguyên tắc.
4. Câu lệnh đầu tiên nên gửi (sao chép nguyên văn):

   > Đọc CLAUDE.md và toàn bộ src/. Khởi tạo git cho thư mục này và tạo lần lưu đầu tiên. Chạy `python build.py` và `node tests/test_engine.js`, báo cho tôi kết quả. Sau đó chạy `python chay_bot_xac_suat.py`, mở bot với dữ liệu thật và tóm tắt cho tôi các con số chính (tỷ lệ nên mua, nên bán, phương án đứng đầu, tiêu chí chốt lời đáng tin). Chưa sửa gì.

5. Khi muốn thêm tính năng, mô tả bằng tiếng Việt và yêu cầu theo từng bước nhỏ, ví dụ:

   > Thêm tính năng X. Trước khi viết mã, nói cho tôi cách làm và cách kiểm chứng không nhìn trước tương lai. Làm xong thì ghép lại, chạy hai bài kiểm tra, chạy với dữ liệu thật, rồi lưu git với mô tả tiếng Việt.

6. Nếu một thay đổi làm hỏng bot: "Quay lại bản lưu git trước đó".
7. Đóng gói cho máy khác: "Chạy `python build.py --zip`" → lấy file trong `dist/`.
