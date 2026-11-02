# Triển khai trang web bot BTC (giai đoạn 9)

## 1. Hiện trạng (cập nhật 28/10/2026, sau khi triển khai)
- Trang đang chạy: https://hcvt8683-netizen.github.io/bot-btc/. Kho công khai `hcvt8683-netizen/bot-btc` chỉ có một file `index.html` tải lên bằng tay, Pages lấy từ nhánh `main`, thư mục gốc.
- Bản đang chạy giống từng byte với `bot-xac-suat.html` ở thẻ `v1-before-upgrade`, nên quay lại bản cũ luôn làm được.
- **Đã triển khai ngày 28/10/2026**: bản nâng cấp đã gộp vào `main` (commit 377b7bf) và đẩy lên GitHub cùng thẻ `v1-before-upgrade` và nhánh `upgrade/best-roi`. Nguồn Pages là "GitHub Actions". Lần chạy `Daily` đầu tiên thành công: lưu dữ liệu (`data: cập nhật 28/10/2026`) và đăng trang mới.
- Giữ nguyên địa chỉ trang. Không có tên miền riêng. Trang chỉ dùng đường dẫn tương đối và là một file duy nhất, nên chạy đúng dưới `/bot-btc/`.

**Kiểm tra nguồn Pages:** nếu trong thẻ Actions vẫn thấy lần chạy "pages build and deployment" sau mỗi lần `main` thay đổi, nghĩa là nguồn Pages vẫn là "Deploy from a branch". Khi đó GitHub đăng lại `index.html` cũ ở thư mục gốc, và trang có thể quay về bản cũ cho tới lần chạy Daily kế tiếp. Cách sửa: Settings → Pages → Source → **GitHub Actions**.

## 2. Cách trang tự cập nhật sau khi triển khai
| Workflow | Khi nào chạy | Làm gì |
|---|---|---|
| `CI` (`.github/workflows/ci.yml`) | mỗi lần đẩy mã, mỗi pull request | Cài thư viện, chạy `make test` (đơn vị, ảnh chụp báo cáo và giao diện, không gọi mạng), dựng trang, để lại bản tải về `trang-web-<mã commit>` trong 30 ngày. |
| `Daily` (`daily.yml`) | 01:00 UTC mỗi ngày (08:00 giờ Việt Nam), mỗi lần đẩy mã lên `main`, và chạy tay | Kiểm tra từng nguồn từ máy chủ GitHub → tải dữ liệu và kiểm tra chất lượng → bảng chỉ số → khuyến nghị tuần → dựng trang → chạy kiểm tra → lưu dữ liệu mới vào `main` (`data: cập nhật dd/mm/yyyy`, tên `github-actions[bot]`) → đăng lên Pages. |
| `Rollback` (`rollback.yml`) | chạy tay | Dựng và đăng lại một phiên bản cũ (mặc định `v1-before-upgrade`). |

- Chỉ đăng từ `main`, và chỉ khi các bài kiểm tra trong lần chạy đó đạt. Kiểm tra lỗi thì trang giữ bản tốt gần nhất.
- Hai lần chạy không bao giờ chồng nhau (`concurrency: btc-bot`).
- Quyền: chỉ bước lưu dữ liệu có `contents: write`; bước đăng có `pages: write` và `id-token: write`.
- Mọi action chính thức được ghim theo mã commit:
  - `actions/checkout` v7.0.1;
  - `setup-python` v7.1.0;
  - `setup-node` v7.1.0;
  - `upload-artifact` v7.0.2;
  - `configure-pages` v6.0.0;
  - `upload-pages-artifact` v5.0.0;
  - `deploy-pages` v5.0.1.
- Một nguồn lỗi không làm hỏng cả lần chạy: dữ liệu lỗi không được lưu, khuyến nghị về mua đều (hệ số 1,0) và nói rõ lý do. Trang đã đăng vẫn hiện bản gần nhất. Nếu khuyến nghị cũ hơn 3 ngày, trang hiện băng "⚠ Dữ liệu chưa cập nhật…".
- Lưu ý của GitHub: lịch chạy có thể trễ vào giờ cao điểm. Với kho công khai, lịch chạy tự tắt sau 60 ngày kho không có hoạt động. Lần lưu dữ liệu hằng ngày giữ cho kho luôn có hoạt động.
- Dung lượng: bản chụp hằng ngày chỉ giữ 30 ngày gần nhất của mỗi nguồn, khoảng 15 MB mỗi năm. Khi `data/` vượt khoảng 100 MB, chuyển bản chụp cũ sang tài sản của bản phát hành (release assets).

## 3. Nguồn dữ liệu từ máy chủ GitHub
Máy chủ GitHub đặt ở Mỹ. Binance thường trả HTTP 451/403 cho `api.binance.com`, `fapi.binance.com` và `dapi.binance.com` từ đó.

| Nguồn | Từ máy ở Việt Nam (28/10/2026) | Từ máy chủ GitHub (lần chạy đầu, 28/10/2026) |
|---|---|---|
| Coin Metrics | 200 OK | OK |
| Alternative.me | 200 OK | OK |
| Binance api.binance.com (spot) | 200 OK | **bị chặn, HTTP 451** |
| Binance data-api.binance.vision (spot, dự phòng) | 200 OK | OK (bot tự chuyển sang địa chỉ này) |
| CoinGecko | 200 OK | OK |
| Binance fapi (funding, khối lượng hợp đồng mở) | 200 OK | **bị chặn, HTTP 451** |
| Binance dapi (hợp đồng quý) | 200 OK | **bị chặn, HTTP 451** |
| DefiLlama | 200 OK | OK |
| FRED (CSV) | 200 OK | OK |
| Binance data.binance.vision (kho file phái sinh, dự phòng từ 11/2026) | 200 OK (02/11/2026) | OK (Daily #19, 02/11/2026): funding, hợp đồng mở, hợp đồng quý tải qua kho |

Từ lần chạy sau, kết quả kiểm tra từng địa chỉ được lưu mỗi ngày trong `data/endpoint_check.json`; trạng thái tải của từng nguồn nằm trong `data/status.json`.
Bảng kết quả từ máy chủ cũng nằm ở phần tóm tắt (Summary) của mỗi lần chạy `Daily`. Vì Binance chặn hợp đồng tương lai:
- Giá và khối lượng spot tự chuyển sang `data-api.binance.vision`; giá lịch sử chính vẫn lấy từ Coin Metrics.
- Funding, khối lượng hợp đồng mở và giá hợp đồng quý: từ 30/10 đến 02/11/2026 không lấy được (HTTP 451). Từ bản 11/2026, khi API bị chặn, bot tự đọc kho file công khai `data.binance.vision` (`bot/data/fetchers/binance_vision.py`). Số liệu trong kho trùng hoàn toàn với API (đã so ngày 02/11/2026). Đổi lại, kho chậm hơn:
  - hợp đồng mở và hợp đồng quý chậm khoảng 1–2 ngày;
  - funding chỉ có file theo tháng, nên dòng mới nhất có thể cũ tới khoảng 1 tháng.
  Mục "Độ mới của dữ liệu" trên trang ghi rõ nguồn nào đang lấy từ kho và chậm bao nhiêu ngày. Độ trễ tối đa của kho ghi ở `archive_lag_days` trong `config/bot.yaml`. Cả ba nguồn vẫn **không dùng trong khuyến nghị** (lớp B không qua kiểm định; bước C2 chỉ nghiên cứu từ 11/2027).
- Nếu sau này kho cũng bị chặn từ Mỹ, chạy bước dữ liệu trên máy của bạn hoặc một VPS ở Việt Nam (self-hosted runner: Settings → Actions → Runners → New self-hosted runner, rồi đổi `runs-on: self-hosted` cho job `data`).
- FRED chỉ số đô la rộng (`DTWEXBGS`) không lỗi tải. Chuỗi này công bố mỗi tuần một lần (thứ Hai, chiều giờ Mỹ), nên sáng thứ Hai dòng mới nhất đã cũ 10 ngày. Ngưỡng "dữ liệu cũ" của riêng chuỗi này là 11 ngày (`fred.WEEKLY`).
- Phần tính trực tiếp trên trang (tỷ lệ nên mua, nên bán…) chạy trong trình duyệt của người xem ở Việt Nam, nên **không bị ảnh hưởng**.

## 4. Những việc bạn phải tự làm trên GitHub (sau khi nói "OK deploy")
1. **Đăng nhập GitHub trên máy này** khi Git hỏi lúc đẩy mã lên lần đầu (cửa sổ Git Credential Manager). Tôi không nhập mật khẩu hay mã truy cập thay bạn.
2. **Settings → Pages → Build and deployment → Source: chọn "GitHub Actions"** (thay cho "Deploy from a branch").
3. **Settings → Actions → General → Workflow permissions: chọn "Read and write permissions"**, để bước "Lưu dữ liệu mới" ghi được vào `main`.
4. **Settings → Environments → github-pages → Deployment branches and tags: chỉ cho phép `main`** (môi trường này tự xuất hiện sau lần đăng đầu tiên).
5. Nên làm: **Settings → Branches → Add branch ruleset cho `main`**, bật "Require status checks to pass" và chọn kiểm tra `test` (workflow CI). Khi đó chỉ gộp được mã đã qua kiểm tra.
6. Không bắt buộc: thêm GitHub Secret `FRED_API_KEY` (khóa miễn phí của FRED), cách làm từng bước ở mục 8. Không có khóa thì bot dùng file CSV công khai, kết quả như nhau. Không cần khóa của sàn nào, và bot không bao giờ đặt lệnh.
7. Kho phải giữ **công khai**: Pages cho kho riêng tư cần gói trả phí, và trang vẫn công khai.

## 5. Các bước triển khai (tôi làm sau khi bạn nói "OK deploy")
1. Nối kho trên máy với `https://github.com/hcvt8683-netizen/bot-btc.git`, đẩy thẻ `v1-before-upgrade` và nhánh `upgrade/best-roi`. CI chạy trên nhánh và cho bản tải về để bạn xem lại.
2. Gộp vào `main`. Nhánh `main` trên GitHub có lịch sử khác (một lần tải `index.html` bằng tay), nên tôi gộp trên máy bằng `git merge --allow-unrelated-histories` và giữ lại lịch sử cũ. GitHub không cho tạo pull request giữa hai lịch sử khác nhau. Trang vẫn chạy bản cũ cho tới khi bạn đổi nguồn Pages sang "GitHub Actions".
3. Bạn đổi cài đặt ở mục 4 (bước 2–4).
4. Chạy tay workflow `Daily` (Actions → Daily → Run workflow). Kiểm tra trang, rồi điền bảng ở mục 3 bằng kết quả từ máy chủ.

## 6. Quay lại bản cũ (rollback)
Khi gộp, file `index.html` cũ ở thư mục gốc của `main` được giữ nguyên (giống từng byte với `v1-before-upgrade`). File `.nojekyll` ở thư mục gốc giúp GitHub phục vụ file đúng như cũ.
- **Cách 1, hủy hẳn nâng cấp:** trên máy chạy `git revert -m 1 <mã commit gộp>`, rồi đẩy `main`. Sau đó vào **Settings → Pages → Source: "Deploy from a branch", nhánh `main`, thư mục `/ (root)`**. Trang quay về đúng `index.html` cũ sau 1–3 phút. Bước revert xóa cả các workflow, nên không còn chạy hằng ngày.
- **Cách 2, giữ mã mới, chỉ đăng lại trang cũ:** Actions → Rollback → Run workflow, ô `ref` để `v1-before-upgrade` (hoặc thẻ, commit khác). Trang về bản trước nâng cấp sau 1–3 phút. Nếu workflow `Daily` vẫn bật, sáng hôm sau nó đăng lại bản trên `main`; muốn giữ bản cũ thì tắt `Daily` (Actions → Daily → … → Disable workflow).

## 7. Riêng tư
Trang là công khai. Trang chỉ ghi hệ số mua và số tiền trên mỗi 100 $ ngân sách. Ngân sách, số BTC đang giữ và giá vốn của bạn chỉ nằm trong trình duyệt (ô nhập ở bên bán) hoặc trong `config/personal.yaml` trên máy (không lưu git, chỉ dùng cho `python -m bot.cli report`). Khóa Claude API chỉ lưu trong trình duyệt khi bạn chọn ghi nhớ.

## 8. Thêm khóa FRED (không bắt buộc, miễn phí)
Không có khóa, bot tải file CSV công khai của FRED, số liệu như nhau. Có khóa, bot dùng API chính thức của FRED, ổn định hơn khi trang CSV chậm hoặc đổi cách trả lời. Khóa **không** làm chỉ số đô la rộng mới hơn, vì chuỗi này chỉ công bố mỗi tuần một lần (mục 3).

Bạn tự làm, không gửi khóa cho ai, kể cả Claude. Không dán khóa vào khung chat hay vào file nào trong dự án.

**Bước 1. Tạo tài khoản FRED**
1. Mở https://fredaccount.stlouisfed.org/login/secure/
2. Bấm **Create New Account**. Điền email và mật khẩu (hoặc đăng nhập bằng Google). Xác nhận email nếu FRED gửi thư.

**Bước 2. Lấy khóa API**
1. Đăng nhập xong, mở https://fredaccount.stlouisfed.org/apikeys (hoặc **My Account → API Keys**).
2. Bấm **Request API Key**.
3. Ô mô tả, ghi ngắn, ví dụ: "Bot BTC cá nhân, chỉ đọc số liệu công khai".
4. Đánh dấu ô đồng ý **Terms of Use**, rồi bấm **Request API key**.
5. FRED hiện một chuỗi 32 ký tự (chữ thường và số). Sao chép chuỗi này.

**Bước 3. Thêm khóa vào GitHub (GitHub Secret)**
1. Mở kho https://github.com/hcvt8683-netizen/bot-btc
2. Bấm thẻ **Settings** (trên cùng) → menu trái **Secrets and variables** → **Actions**.
3. Bấm **New repository secret**.
4. Ô **Name**: gõ đúng `FRED_API_KEY`. Ô **Secret**: dán khóa vừa sao chép.
5. Bấm **Add secret**. GitHub chỉ hiện tên, không bao giờ hiện lại khóa.

**Bước 4. Kiểm tra**
1. Vào thẻ **Actions** → **Daily** → **Run workflow** → **Run workflow**.
2. Chạy xong (khoảng 10–20 phút), bấm vào lần chạy → bước "Tải dữ liệu và kiểm tra chất lượng": các dòng `fred_...` phải ghi `OK`. Trong nhật ký, khóa luôn hiện thành `***`.
3. Trên trang, mục "Độ mới của dữ liệu" có các dòng FRED màu xanh.

Quy trình `Daily` đã đọc sẵn `FRED_API_KEY` (`.github/workflows/daily.yml`), không cần sửa gì thêm. Nếu tải FRED lỗi, thông báo lỗi ghi vào `data/status.json` đã che khóa (`api_key=***`). Muốn bỏ khóa thì xóa Secret; bot tự quay về file CSV.
