# -*- coding: utf-8 -*-
"""Run the JavaScript tests from pytest so `make test` covers everything."""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _node(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["node", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=900)


def test_engine_js() -> None:
    r = _node("tests/test_engine.js")
    assert r.returncode == 0 and "SAI:" not in r.stdout + r.stderr, r.stdout + r.stderr


def test_report_snapshot() -> None:
    r = _node("tests/snapshot_report.js")
    assert r.returncode == 0, r.stdout + r.stderr
