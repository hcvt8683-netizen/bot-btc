# -*- coding: utf-8 -*-
"""Ghép mã nguồn trong src/ thành một file bot-xac-suat.html chạy được.
Chạy: python build.py          -> tạo bot-xac-suat.html ở thư mục gốc
      python build.py --zip    -> tạo thêm dist/BotBTC-Windows.zip và dist/BotBTC-Mac.zip
      python build.py --site   -> tạo site/index.html để đăng GitHub Pages
"""
import json, os, re, sys, time, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
VI_YAML = os.path.join(ROOT, "bot", "i18n", "vi.yaml")


def web_strings():
    """The `web` part of bot/i18n/vi.yaml (all text of the page); also written to src/vi.json for the node tests."""
    sys.path.insert(0, ROOT)
    from bot.config import load_yaml
    y = load_yaml(VI_YAML)
    vi = {"web": y["web"], "sources": y["sources"]}
    with open(os.path.join(SRC, "vi.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(vi, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    return vi


def fill_page(page, vi):
    """Replace {{web.page.key}} placeholders with the text from vi.yaml (missing keys stop the build)."""
    def one(m):
        node = vi
        for k in m.group(1).split("."):
            node = node[k]
        return node
    return re.sub(r"\{\{(web\.[a-z0-9_.]+)\}\}", one, page)


def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return f.read()


def recommendation(path=None):
    """data/recommendation.json from the daily job (python -m bot.cli report), or None when it does not exist yet."""
    path = path or os.path.join(ROOT, "data", "recommendation.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build(out=None, kn_path=None):
    vi = web_strings()
    page = fill_page(read("page.html"), vi)
    i18n = read("i18n.js").replace("if (typeof module !== 'undefined') module.exports = I18N;\n", "").replace(
        "/*VI_JSON*/null", json.dumps(vi, ensure_ascii=False, sort_keys=True))
    engine = read("engine.js").replace("if (typeof module !== 'undefined') module.exports = BOT;\n", "")
    analysis = read("analysis.js").replace("if (typeof module !== 'undefined') module.exports = B3;\n", "")
    for mark in ("/*I18N*/", "/*CORE*/", "/*B3*/", "/*UI*/"):
        if page.count(mark) != 1:
            sys.exit(f"Lỗi: page.html phải có đúng một chỗ {mark}")
    html = page.replace("/*I18N*/", i18n).replace("/*CORE*/", engine).replace("/*B3*/", analysis).replace("/*UI*/", read("ui.js").replace("/*KN_JSON*/null", json.dumps(recommendation(kn_path), ensure_ascii=False)))
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


def site():
    """site/index.html for GitHub Pages (relative paths only, so it works under /bot-btc/)."""
    d = os.path.join(ROOT, "site"); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, ".nojekyll"), "w").close()
    return build(os.path.join(d, "index.html"))


if __name__ == "__main__":
    if "--site" in sys.argv:
        site()
        sys.exit(0)
    build()
    if "--zip" in sys.argv:
        package()
