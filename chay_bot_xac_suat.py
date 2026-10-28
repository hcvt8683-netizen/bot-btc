# -*- coding: utf-8 -*-
"""
Bot xác suất BTC - máy chủ chạy trên máy (macOS, Windows, Linux).
Chạy: python3 chay_bot_xac_suat.py   (Mac: bấm đúp Mo-Bot-BTC.command; Windows: bấm đúp Mo-Bot-BTC.bat)

- Máy bạn tự lấy dữ liệu thay cho trình duyệt, nên không bị chặn bởi chính sách CORS.
- Mỗi lần tải thành công, dữ liệu được lưu vào thư mục du_lieu_tam/. Khi mất mạng
  hoặc nguồn lỗi, bot dùng bản lưu gần nhất và báo rõ trên màn hình.
- Chỉ dùng thư viện có sẵn của Python 3.7+.
"""
import hashlib, http.server, json, os, shutil, socket, socketserver, ssl, subprocess, sys, threading, time, urllib.parse, urllib.request, webbrowser

PORT = 8789
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "du_lieu_tam")
PAGE = "bot-xac-suat.html"
ALLOWED = {"api.alternative.me", "community-api.coinmetrics.io", "api.binance.com",
           "data-api.binance.vision", "api.coingecko.com"}
UA = {"User-Agent": "Mozilla/5.0 bot-xac-suat-btc"}


def fetch(url):
    """Tải bằng urllib; nếu lỗi chứng chỉ (hay gặp với Python cài từ python.org trên Mac) thì dùng curl của hệ thống."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
            return r.read()
    except Exception as e:  # noqa: BLE001
        is_ssl = isinstance(getattr(e, "reason", None), ssl.SSLError) or "CERTIFICATE" in str(e).upper()
        if is_ssl and shutil.which("curl"):
            out = subprocess.run(["curl", "-sSfL", "--max-time", "90", "-A", UA["User-Agent"], url],
                                 capture_output=True, timeout=100)
            if out.returncode == 0 and out.stdout:
                return out.stdout
            raise RuntimeError("curl: " + out.stderr.decode("utf-8", "replace")[:200])
        raise


def cache_path(url):
    return os.path.join(CACHE, hashlib.sha1(url.encode("utf-8")).hexdigest() + ".json")


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/proxy?"):
            return self.proxy()
        if self.path in ("/", ""):
            self.path = "/" + PAGE
        return super().do_GET()

    def proxy(self):
        url = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("url", [""])[0]
        if (urllib.parse.urlparse(url).hostname or "") not in ALLOWED:
            return self.send_error(403, "Nguon khong duoc phep")
        body, saved_at = None, None
        try:
            body = fetch(url)
            json.loads(body.decode("utf-8"))  # chỉ lưu khi đúng là JSON
            os.makedirs(CACHE, exist_ok=True)
            tmp = cache_path(url) + ".tmp"
            with open(tmp, "wb") as f:
                f.write(body)
            os.replace(tmp, cache_path(url))
        except Exception as e:  # noqa: BLE001
            p = cache_path(url)
            if os.path.exists(p):
                with open(p, "rb") as f:
                    body = f.read()
                saved_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(p)))
            else:
                return self.send_error(502, str(e)[:200])
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if saved_at:
            self.send_header("X-Ban-Luu", saved_at)
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        if not self.path.startswith("/proxy?"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def main():
    try:
        sys.stdout.reconfigure(errors="replace")  # tránh lỗi in tiếng Việt trên cửa sổ dòng lệnh cũ
    except Exception:  # noqa: BLE001
        pass
    os.chdir(HERE)
    link = f"http://127.0.0.1:{PORT}/"
    # Trên Windows, SO_REUSEADDR cho phép 2 máy chủ chiếm cùng một cổng, nên chỉ bật trên Mac/Linux
    socketserver.ThreadingTCPServer.allow_reuse_address = os.name != "nt"
    try:
        server = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        # cổng đang bận: thường là bot đã chạy ở cửa sổ khác, chỉ cần mở trình duyệt
        print("Bot đã chạy sẵn, đang mở trình duyệt:", link)
        webbrowser.open(link)
        return
    print("Bot xác suất BTC đang chạy tại", link)
    print("Giữ cửa sổ này mở trong lúc dùng. Đóng cửa sổ (hoặc bấm Ctrl+C) để tắt bot.")
    if not os.environ.get("BOT_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(link)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã tắt bot.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
