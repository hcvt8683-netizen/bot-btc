# -*- coding: utf-8 -*-
"""One-time migration (phase 8): move every Vietnamese string of the web page into bot/i18n/vi.yaml.

- JS (src/engine.js, src/analysis.js, src/ui.js): string literals become tx('web.<file>.<key>'); template literals with
  Vietnamese text become tx('web.<file>.<key>', expr0, expr1, …) with {0}, {1} placeholders. A small lexer skips
  comments and regular expressions and handles nested template expressions.
- HTML (src/page.html): Vietnamese text nodes and title/placeholder/aria-label/content attributes become {{web.page.<key>}},
  filled by build.py at build time (output byte-identical).
The snapshot tests (report, CSV, page text) prove the output did not change.
Run once: python tools/migrate_strings.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
VI = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.I)
REGEX_PREV = set("(,=:[!&|?{};+-*%<>~^") | {""}


def slug(text: str) -> str:
    s = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()
    words = re.findall(r"[a-z0-9]+", s)
    out = "_".join(words[:6])[:48].strip("_")
    if not out or out[0].isdigit() or out in {"y", "n", "yes", "no", "on", "off", "true", "false", "null"}:
        out = "s_" + out  # YAML 1.1 would read these as booleans or numbers
    return out


class Keys:
    def __init__(self, section: str):
        self.section, self.by_value, self.values = section, {}, {}

    def key(self, value: str) -> str:
        if value in self.by_value:
            return self.by_value[value]
        base = slug(value)
        k, n = base, 2
        while k in self.values:
            k, n = f"{base}_{n}", n + 1
        self.by_value[value], self.values[k] = k, value
        return k


def cook(raw: str) -> str:
    """Decode JS escapes in a string or template part."""
    out, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        n = raw[i + 1]
        if n == "n":
            out.append("\n")
        elif n == "t":
            out.append("\t")
        elif n == "u":
            if raw[i + 2] == "{":
                j = raw.index("}", i)
                out.append(chr(int(raw[i + 3:j], 16)))
                i = j + 1
                continue
            out.append(chr(int(raw[i + 2:i + 6], 16)))
            i += 6
            continue
        else:
            out.append(n)
        i += 2
    return "".join(out)


class JS:
    def __init__(self, src: str, keys: Keys):
        self.s, self.k = src, keys

    def read_string(self, i: int) -> int:
        q = self.s[i]
        j = i + 1
        while self.s[j] != q:
            j += 2 if self.s[j] == "\\" else 1
        return j + 1

    def read_regex(self, i: int) -> int:
        j, cls = i + 1, False
        while True:
            c = self.s[j]
            if c == "\\":
                j += 2
                continue
            if c == "[":
                cls = True
            elif c == "]":
                cls = False
            elif c == "/" and not cls:
                j += 1
                while j < len(self.s) and self.s[j].isalpha():
                    j += 1
                return j
            j += 1

    def read_expr(self, i: int) -> tuple[str, int]:
        """From just after '${' to the matching '}': returns (transformed expression, index after '}')."""
        out, j = self.transform(i, stop_at_brace=True)
        return out, j + 1

    def read_template(self, i: int) -> tuple[str, int]:
        parts, exprs, buf, j = [], [], [], i + 1
        while True:
            c = self.s[j]
            if c == "\\":
                buf.append(self.s[j:j + 2])
                j += 2
            elif c == "`":
                parts.append("".join(buf))
                j += 1
                break
            elif c == "$" and self.s[j + 1] == "{":
                parts.append("".join(buf))
                buf = []
                e, j = self.read_expr(j + 2)
                exprs.append(e)
            else:
                buf.append(c)
                j += 1
        cooked = [cook(p) for p in parts]
        if any(VI.search(p) for p in cooked):
            value = "".join(p + (f"{{{n}}}" if n < len(exprs) else "") for n, p in enumerate(cooked))
            key = self.k.key(value)
            args = "".join(", " + e.strip() for e in exprs)
            return f"tx('web.{self.k.section}.{key}'{args})", j
        rebuilt = "`" + "".join(p + ("${" + exprs[n] + "}" if n < len(exprs) else "") for n, p in enumerate(parts)) + "`"
        return rebuilt, j

    def transform(self, i: int = 0, stop_at_brace: bool = False) -> tuple[str, int]:
        out, depth, prev = [], 0, ""
        s = self.s
        while i < len(s):
            c = s[i]
            if c == "/" and s[i + 1:i + 2] == "/":
                j = s.find("\n", i)
                j = len(s) if j < 0 else j
                out.append(s[i:j])
                i = j
                continue
            if c == "/" and s[i + 1:i + 2] == "*":
                j = s.index("*/", i) + 2
                out.append(s[i:j])
                i = j
                continue
            if c in "'\"":
                j = self.read_string(i)
                val = cook(s[i + 1:j - 1])
                out.append(f"tx('web.{self.k.section}.{self.k.key(val)}')" if VI.search(val) else s[i:j])
                i, prev = j, "a"
                continue
            if c == "`":
                txt, j = self.read_template(i)
                out.append(txt)
                i, prev = j, "a"
                continue
            if c == "/" and (prev in REGEX_PREV or re.search(r"\b(return|typeof|case)\s*$", "".join(out[-3:]))):
                j = self.read_regex(i)
                out.append(s[i:j])
                i, prev = j, "a"
                continue
            if stop_at_brace:
                if c == "{":
                    depth += 1
                elif c == "}":
                    if depth == 0:
                        return "".join(out), i
                    depth -= 1
            out.append(c)
            if not c.isspace():
                prev = c if not (c.isalnum() or c in "_$)]") else "a"
            i += 1
        return "".join(out), i


def migrate_js(name: str, section: str) -> dict:
    p = ROOT / "src" / name
    keys = Keys(section)
    new, _ = JS(p.read_text(encoding="utf-8"), keys).transform()
    p.write_text(new, encoding="utf-8", newline="\n")
    return keys.values


def migrate_html() -> dict:
    p = ROOT / "src" / "page.html"
    t = p.read_text(encoding="utf-8")
    keys = Keys("page")
    head, body = t.split("</style>", 1)
    css_start = head.index("<style>")
    pre, css = head[:css_start], head[css_start:]

    def text_node(m: re.Match) -> str:
        txt = m.group(1)
        if not VI.search(txt):
            return m.group(0)
        lead, core, trail = re.match(r"(\s*)(.*?)(\s*)$", txt, re.S).groups()
        return ">" + lead + "{{web.page." + keys.key(core) + "}}" + trail + "<"

    def attr(m: re.Match) -> str:
        if not VI.search(m.group(2)):
            return m.group(0)
        return f'{m.group(1)}="{{{{web.page.{keys.key(m.group(2))}}}}}"'

    def html_part(x: str) -> str:
        parts = re.split(r"(<script>.*?</script>)", x, flags=re.S)
        for n in range(0, len(parts), 2):
            parts[n] = re.sub(r"\b(title|placeholder|aria-label|content)=\"([^\"]*)\"", attr, parts[n])
            parts[n] = re.sub(r">([^<>]+)<", text_node, parts[n])
        return "".join(parts)

    p.write_text(html_part(pre) + css + "</style>" + html_part(body), encoding="utf-8", newline="\n")
    return keys.values


def yaml_block(section: str, values: dict) -> str:
    lines = [f"  {section}:"]
    for k, v in values.items():
        lines.append(f"    {k}: {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    blocks = {"page": migrate_html()}
    for f, sec in (("engine.js", "engine"), ("analysis.js", "analysis"), ("ui.js", "ui")):
        blocks[sec] = migrate_js(f, sec)
    y = ROOT / "bot" / "i18n" / "vi.yaml"
    text = y.read_text(encoding="utf-8").rstrip() + "\n\n# Chữ của trang web (src/page.html, src/*.js), chuyển từ mã ở giai đoạn 8\nweb:\n"
    text += "\n".join(yaml_block(s, v) for s, v in blocks.items()) + "\n"
    y.write_text(text, encoding="utf-8", newline="\n")
    print({s: len(v) for s, v in blocks.items()})


if __name__ == "__main__":
    main()
