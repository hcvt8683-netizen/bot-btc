# -*- coding: utf-8 -*-
"""Phase 8 tests: fail-safe recommendation, events window, text keys and vi.json in sync with vi.yaml."""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re

from bot.config import ROOT, load_yaml
from bot.report import vi_report

NOW = dt.datetime(2026, 10, 28, 1, 0)


def _setup(tmp_path: pathlib.Path, monkeypatch, passed: bool, cm_last: str) -> None:
    (tmp_path / "results").mkdir()
    summary = json.loads((ROOT / "data" / "results" / "final_summary.json").read_text(encoding="utf-8"))
    summary["passed"] = passed
    (tmp_path / "results" / "final_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (tmp_path / "status.json").write_text(json.dumps({"sources": {"coinmetrics": {"ok": True, "last": cm_last}}}), encoding="utf-8")
    monkeypatch.setattr(vi_report, "DATA", tmp_path)
    monkeypatch.setattr(vi_report, "SUMMARY", tmp_path / "results" / "final_summary.json")
    monkeypatch.setattr(vi_report, "OUT", tmp_path / "recommendation.json")


def test_failed_model_falls_back_to_dca(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, passed=False, cm_last="2026-10-27")
    rec = vi_report.build(NOW, write=True)
    assert rec["multiplier"] == 1.0 and rec["mode"] == "safe" and rec["reasons"] == ["model_failed"]
    assert json.loads((tmp_path / "recommendation.json").read_text(encoding="utf-8"))["multiplier"] == 1.0
    assert "budget" not in json.dumps(rec) and rec["amount_example_usd"] == 100  # nothing personal in the public file


def test_stale_data_falls_back_and_says_why(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, passed=False, cm_last="2026-10-20")
    rec = vi_report.build(NOW, write=False)
    assert rec["multiplier"] == 1.0 and "data_stale" in rec["reasons"]
    assert "Dữ liệu thiếu hoặc cũ → mua đều như DCA (hệ số 1,0)" in vi_report.console(rec)


def test_events_in_next_7_days_and_personal_budget_only_local(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, passed=False, cm_last="2026-10-27")
    rec = vi_report.build(NOW, write=False)
    assert {"type": "fomc", "time": "2026-10-28T18:00Z"} in rec["events"]
    assert all(e["time"] <= "2026-11-04T01:00Z" for e in rec["events"])
    monkeypatch.setattr(vi_report, "personal", lambda: {"budget": {"weekly_usd": 250}})
    out = vi_report.console(rec)
    assert "250 $/tuần" in out and "01:00 29/10/2026 (giờ Việt Nam): Quyết định lãi suất FOMC" in out


def test_every_text_key_exists_and_vi_json_is_in_sync():
    vi = load_yaml(ROOT / "bot" / "i18n" / "vi.yaml")
    def has(key: str) -> bool:
        node = vi
        for k in key.split("."):
            if not isinstance(node, dict) or k not in node:
                return False
            node = node[k]
        return True
    used = set()
    for f in ("engine.js", "analysis.js", "ui.js"):
        used |= set(re.findall(r"tx\('((?:web|sources)\.[a-z0-9_.]+)'(?!\s*\+)", (ROOT / "src" / f).read_text(encoding="utf-8")))
    used |= {f"web.kn.ev_{e}" for e in ("fomc", "cpi", "pce", "opex")} | {f"web.kn.layer_{x}" for x in "ABC"}  # keys built at run time
    used |= set(re.findall(r"\{\{(web\.[a-z0-9_.]+)\}\}", (ROOT / "src" / "page.html").read_text(encoding="utf-8")))
    missing = sorted(k for k in used if not has(k))
    assert not missing, missing
    assert json.loads((ROOT / "src" / "vi.json").read_text(encoding="utf-8")) == {"web": vi["web"], "sources": vi["sources"]}, "run python build.py"


def test_source_errors_are_shown_in_vietnamese():
    assert vi_report._friendly("FetchError: HTTP 451 (https://fapi.binance.com/...)") == \
        "bị chặn khi tải từ máy chủ GitHub ở Mỹ (HTTP 451); không dùng trong khuyến nghị"
    assert vi_report._friendly("TimeoutError: timed out") == "không tải được, đang dùng bản gần nhất"
    assert vi_report._friendly("") == ""
