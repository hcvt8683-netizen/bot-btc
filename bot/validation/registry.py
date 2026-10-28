"""Experiment registry: every evaluated candidate is one row in experiments/registry.csv.

Columns: timestamp, git hash, config hash, name, stage, features, params (JSON), metrics (JSON).
The number of rows is the number of trials used for the Deflated Sharpe Ratio and reported with results.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import pathlib
import subprocess

from bot.config import ROOT, config_hash

PATH = ROOT / "experiments" / "registry.csv"
COLUMNS = ["timestamp", "git", "config", "name", "stage", "features", "params", "metrics"]


def _git() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return r.stdout.strip() + ("+" if dirty else "")
    except OSError:
        return "?"


def log(name: str, stage: str, features: list[str] | str, params: dict, metrics: dict, path: pathlib.Path | None = None) -> None:
    """Append one trial."""
    p = path or PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(COLUMNS)
        w.writerow([dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), _git(), config_hash(params), name, stage,
                    features if isinstance(features, str) else "+".join(features),
                    json.dumps(params, sort_keys=True, default=str), json.dumps(metrics, sort_keys=True, default=lambda x: round(float(x), 6))])


def rows(path: pathlib.Path | None = None) -> list[dict]:
    p = path or PATH
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def n_trials(path: pathlib.Path | None = None, stage: str | None = None) -> int:
    return sum(1 for r in rows(path) if stage is None or r["stage"] == stage)


def sharpes(path: pathlib.Path | None = None) -> list[float]:
    """Weekly Sharpe ratios of active returns logged by trials (for the variance across trials in the DSR)."""
    out = []
    for r in rows(path):
        v = json.loads(r["metrics"] or "{}").get("sr_active")
        if v is not None:
            out.append(float(v))
    return out
