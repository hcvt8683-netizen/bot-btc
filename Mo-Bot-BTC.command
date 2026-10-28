#!/bin/bash
# Bấm đúp để mở Bot xác suất BTC trên macOS.
cd "$(dirname "$0")" || exit 1
clear
echo "=== Bot xác suất BTC ==="
PY=""
for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3 python3 /usr/bin/python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" >/dev/null 2>&1; then
    PY="$c"; break
  fi
done
if [ -n "$PY" ]; then
  echo "Dùng Python: $PY"
  exec "$PY" chay_bot_xac_suat.py
else
  echo "Máy chưa có Python 3, nên mở bot trực tiếp trong trình duyệt."
  echo "Nếu mục Nguồn dữ liệu trong bot báo lỗi, hãy cài Python (xem HUONG_DAN.txt) rồi mở lại file này."
  open "bot-xac-suat.html"
  sleep 5
fi
