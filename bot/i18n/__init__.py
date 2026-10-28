"""User-facing text lookup. All Vietnamese strings live in bot/i18n/<lang>.yaml; code only uses keys.

    t("quality.stale", last="27/10/2026", days=3)
"""
from __future__ import annotations

import functools
import pathlib
from typing import Any

from bot.config import cfg, load_yaml

HERE = pathlib.Path(__file__).resolve().parent


@functools.lru_cache(maxsize=4)
def strings(lang: str | None = None) -> dict:
    lang = lang or (cfg().get("ui") or {}).get("language", "vi")
    return load_yaml(HERE / f"{lang}.yaml")


def t(key: str, **kw: Any) -> str:
    """Look up a dotted key and fill {placeholders}. Missing keys raise, so tests catch them."""
    node: Any = strings()
    for part in key.split("."):
        node = node[part]
    return str(node).format(**kw) if kw else str(node)
