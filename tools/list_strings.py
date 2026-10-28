# -*- coding: utf-8 -*-
"""List every hard-coded user-facing (Vietnamese) string with its file and line.

Run: python tools/list_strings.py > docs/AUDIT_STRINGS.md
A string counts when it contains Vietnamese letters; ASCII-only labels (MVRV, Pi, " $") are noted in AUDIT.md.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = ["src/page.html", "src/ui.js", "src/analysis.js", "src/engine.js", "chay_bot_xac_suat.py", "build.py",
         "Mo-Bot-BTC.bat", "Mo-Bot-BTC.command", "HUONG_DAN_WINDOWS.txt", "HUONG_DAN_MAC.txt"]
VI = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.I)
JS_STR = re.compile(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`", re.S)
HTML_TEXT = re.compile(r">([^<>]+)<|(?:title|placeholder|aria-label)=\"([^\"]+)\"")


def strings(path: pathlib.Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    out: list[tuple[int, str]] = []
    if path.suffix in (".txt", ".bat", ".command"):
        return [(i + 1, ln.strip()) for i, ln in enumerate(text.splitlines()) if VI.search(ln) and not ln.lstrip().startswith(("#", "REM", "::"))]
    if path.suffix == ".html":
        body = re.sub(r"<style>.*?</style>|<script>.*?</script>", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
        for m in HTML_TEXT.finditer(body):
            s = (m.group(1) or m.group(2) or "").strip()
            if s and VI.search(s):
                out.append((body.count("\n", 0, m.start()) + 1, re.sub(r"\s+", " ", s)))
        return out
    # JS / Python: drop comments first, keep line numbers
    code = re.sub(r"(?m)^\s*(//|#).*$", "", text)
    code = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), code, flags=re.S)
    for m in JS_STR.finditer(code):
        s = m.group(0)[1:-1]
        if VI.search(s):
            out.append((code.count("\n", 0, m.start()) + 1, re.sub(r"\s+", " ", s)))
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    total = 0
    blocks = []
    for name in FILES:
        items = strings(ROOT / name)
        total += len(items)
        rows = "\n".join(f"| {ln} | {s[:180].replace('|', '\\|')}{'…' if len(s) > 180 else ''} |" for ln, s in items)
        blocks.append(f"## `{name}` ({len(items)} chuỗi)\n\n| Dòng | Chuỗi |\n|---|---|\n{rows}\n")
    print("# Danh sách chữ hiển thị đang viết cứng trong mã (giai đoạn 0)\n")
    print(f"Tạo tự động bằng `python tools/list_strings.py`. Tổng cộng {total} chuỗi tiếng Việt.\n")
    print("\n".join(blocks))


if __name__ == "__main__":
    main()
