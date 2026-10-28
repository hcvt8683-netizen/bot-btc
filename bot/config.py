"""Configuration loading (config/*.yaml) and project paths."""
from __future__ import annotations

import copy
import functools
import hashlib
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = ROOT / "config"


def load_yaml(path: pathlib.Path) -> Any:
    """Load a YAML file with PyYAML when available, else the pure-Python ruamel.yaml."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        from ruamel.yaml import YAML

        return YAML(typ="safe", pure=True).load(text)


def _merge(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        out[k] = _merge(out.get(k, {}), v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


@functools.lru_cache(maxsize=1)
def cfg() -> dict:
    """bot.yaml; personal.yaml (git-ignored) is not merged here, see personal()."""
    return load_yaml(CONFIG / "bot.yaml")


def personal() -> dict:
    """Personal settings for local output only (budget, holdings). Empty when the file is absent."""
    p = CONFIG / "personal.yaml"
    return (load_yaml(p) or {}) if p.exists() else {}


def config_hash(extra: dict | None = None) -> str:
    """Short stable hash of the config plus experiment parameters, for the registry."""
    blob = json.dumps(_merge(cfg(), extra or {}), sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def disabled_features() -> set[str]:
    return set((cfg().get("features") or {}).get("disabled") or [])
