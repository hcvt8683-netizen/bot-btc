"""data/manifest.json: what data a result was computed from (snapshot files with SHA-256, rows, last date, fetch time),
plus the git commit, the config hash and the random seed."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess

from bot.config import DATA, ROOT, cfg, config_hash
from bot.data import pit_store as ps


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(write: bool = True) -> dict:
    status = json.loads((DATA / "status.json").read_text(encoding="utf-8")) if (DATA / "status.json").exists() else {"sources": {}}
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sources = {}
    for d in sorted(p for p in ps.RAW.iterdir() if p.is_dir()):
        snaps = ps.snapshots(d.name)
        st = status["sources"].get(d.name, {})
        sources[d.name] = {"snapshots": [{"file": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)} for p in snaps],
                           "last_row": st.get("last"), "rows": st.get("rows"), "ok": st.get("ok"), "errors": st.get("errors") or []}
    man = {"generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "git": git, "config_hash": config_hash(),
           "seed": cfg()["validation"].get("seed"), "status_fetched_at": status.get("fetched_at"), "sources": sources}
    if write:
        (DATA / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    return man
