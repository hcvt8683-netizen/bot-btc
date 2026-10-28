"""Train / validation / holdout splits, halving cycles, and the holdout lock.

Development code never sees prices from the holdout: `dev_end()` is the last allowed day unless `final=True`,
and every final run is appended to experiments/final_runs.log.
"""
from __future__ import annotations

import datetime as dt
import getpass
import json
import subprocess

import pandas as pd

from bot.config import ROOT, cfg

HALVINGS = [pd.Timestamp(d) for d in ("2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20")]
FINAL_LOG = ROOT / "experiments" / "final_runs.log"


class HoldoutLocked(RuntimeError):
    """Raised when development code asks for data inside the locked holdout."""


def split(name: str) -> tuple[pd.Timestamp, pd.Timestamp | None]:
    a, b = cfg()["splits"][name]
    return pd.Timestamp(str(a)), (pd.Timestamp(str(b)) if b else None)


def holdout_start() -> pd.Timestamp:
    return split("holdout")[0]


def dev_end(final: bool = False) -> pd.Timestamp | None:
    """Last day development code may use; None (no limit) only for a logged final run."""
    return None if final else holdout_start() - pd.Timedelta(days=1)


def guard(end: pd.Timestamp | None, final: bool = False) -> None:
    if not final and (end is None or end >= holdout_start()):
        raise HoldoutLocked(f"holdout from {holdout_start():%Y-%m-%d} is locked; use --final")


def cycles(end: pd.Timestamp) -> list[tuple[str, pd.Timestamp, pd.Timestamp, bool]]:
    """Halving-aligned periods (name, start, end, complete), clipped at `end`. The first period starts in 2011.
    `complete` is False when the period is cut by `end` (the running cycle, or the holdout lock)."""
    edges = [pd.Timestamp("2011-01-01"), *HALVINGS]
    out = []
    for k, a in enumerate(edges):
        if a > end:
            break
        nat = edges[k + 1] - pd.Timedelta(days=1) if k + 1 < len(edges) else None
        b = min(nat, end) if nat is not None else end
        out.append((f"{a:%m/%Y}–{b:%m/%Y}", a, b, nat is not None and nat <= end))
    return out


def log_final_run(args: dict) -> None:
    """Append one line per --final run (time, git hash, user, arguments)."""
    try:
        git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        git = "?"
    FINAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = {"time": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "git": git, "user": getpass.getuser(), **args}
    with FINAL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
