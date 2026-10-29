# -*- coding: utf-8 -*-
"""Part I tests: the holdout run happens once (a second call refuses before computing anything); weeks before a strategy
exists are plain DCA; a multiplier of 1.0 everywhere has exactly zero advantage, so it can never pass criteria 1, 2 or 6."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from bot.models import part_i


def test_second_final_run_is_refused_before_any_work(tmp_path, monkeypatch):
    log = tmp_path / "final_runs.log"
    log.write_text(json.dumps({"command": "final", "phase": "phase7"}) + "\n", encoding="utf-8")
    assert not part_i.already_run(log)
    log.write_text(log.read_text(encoding="utf-8") + json.dumps({"phase": part_i.PHASE, "status": "start"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(part_i, "run", lambda *a, **k: pytest.fail("holdout touched on a second run"))
    with pytest.raises(part_i.AlreadyRun):
        part_i.run_final(log)


def test_missing_weeks_are_dca_and_neutral_multiplier_has_zero_edge():
    idx = pd.date_range("2024-01-07", periods=60, freq="W-SUN")
    s = {"idx": idx[10:], "m": np.full(50, 1.3), "m_cmp": np.full(50, 0.7)}
    m = part_i.on_window(s, idx, "m")
    assert (m[:10] == 1.0).all() and (m[10:] == 1.3).all()
    price = 100 * np.exp(np.cumsum(np.random.default_rng(3).normal(0, 0.05, 60)))
    assert part_i.cba(price, np.ones(60)) == pytest.approx(0.0, abs=1e-12)
    st = {"idx": idx, "price": price, "m": np.ones(60)}
    assert part_i.years(st, "m", pd.Timestamp("2025-06-01")) == {"2024": pytest.approx(0.0, abs=1e-12)}  # 2025 has < 26 weeks before the cut
