# -*- coding: utf-8 -*-
"""Ghép mã nguồn trong src/ thành một file bot-xac-suat.html chạy được.
Chạy: python build.py          -> tạo bot-xac-suat.html ở thư mục gốc
      python build.py --zip    -> tạo thêm dist/BotBTC-Windows.zip và dist/BotBTC-Mac.zip
"""
import os, sys, time, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")


def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return f.read()


def build(out=None):
    page = read("page.html")
    engine = read("engine.js").replace("if (typeof module !== 'undefined') module.exports = BOT;\n", "")
    analysis = read("analysis.js").replace("if (typeof module !== 'undefined') module.exports = B3;\n", "")
    for mark in ("/*CORE*/", "/*B3*/", "/*UI*/"):
        if page.count(mark) != 1:
            sys.exit(f"Lỗi: page.html phải có đúng một chỗ {mark}")
    html = page.replace("/*CORE*/", engine).replace("/*B3*/", analysis).replace("/*UI*/", read("ui.js"))
    out = out or os.path.join(ROOT, "bot-xac-suat.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"Đã tạo {out} ({len(html):,} ký tự)")
    return out


def package():
    dist = os.path.join(ROOT, "dist"); os.makedirs(dist, exist_ok=True)
    common = ["bot-xac-suat.html", "chay_bot_xac_suat.py"]
    sets = {"BotBTC-Windows.zip": common + ["Mo-Bot-BTC.bat", ("HUONG_DAN_WINDOWS.txt", "HUONG_DAN.txt")],
            "BotBTC-Mac.zip": common + ["Mo-Bot-BTC.command", ("HUONG_DAN_MAC.txt", "HUONG_DAN.txt")]}
    for zname, files in sets.items():
        with zipfile.ZipFile(os.path.join(dist, zname), "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                src, dst = f if isinstance(f, tuple) else (f, f)
                info = zipfile.ZipInfo("BotBTC/" + dst, date_time=time.localtime()[:6])
                mode = 0o755 if dst.endswith((".command", ".py")) else 0o644
                info.external_attr = (0o100000 | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(os.path.join(ROOT, src), "rb") as fh:
                    z.writestr(info, fh.read())
        print("Đã đóng gói", os.path.join("dist", zname))


if __name__ == "__main__":
    build()
    if "--zip" in sys.argv:
        package()
