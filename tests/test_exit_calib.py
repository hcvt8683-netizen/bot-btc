# -*- coding: utf-8 -*-
"""R1 (bot/models/exit_calib.py): the calibration cell and its 'systematic' side follow the registered rule."""
from __future__ import annotations

import pandas as pd

from bot.models import exit_calib as ec


def test_cell_reports_which_side_the_actual_rate_falls():
    idx = pd.date_range("2020-01-01", periods=700, freq="D")
    g = pd.DataFrame({"pred_0.03": 0.40, "hit_0.03": [1.0] * 420 + [0.0] * 280}, index=idx)     # said 40%, touched 60%
    c = ec.cell(g, 0.03, 7)
    assert c["n_eff"] == 100 and abs(c["actual"] - 0.6) < 1e-12 and c["side"] == "above"
    c2 = ec.cell(g.assign(**{"pred_0.03": 0.6}), 0.03, 7)
    assert c2["side"] == "inside"
    assert ec.cell(g.iloc[:0], 0.03, 7) == {"n": 0}


def test_markdown_says_no_systematic_gap_when_there_is_none():
    o = {"systematic": [], "horizons": {}}
    assert "Không ô nào lệch có hệ thống" in ec.markdown(o)
