"""Deflated Sharpe Ratio (Bailey & López de Prado, 2014).

DSR = Φ( (SR − SR0) √(T − 1) / √(1 − γ3 SR + (γ4 − 1)/4 SR²) ), with the expected maximum Sharpe of N trials
SR0 = √V[SR] · ((1 − γ) Φ⁻¹(1 − 1/N) + γ Φ⁻¹(1 − 1/(N e))), γ ≈ 0.5772 (Euler–Mascheroni).
SR, skewness γ3 and kurtosis γ4 are of the candidate's per-period returns; here the weekly active return
(strategy minus DCA, both time-weighted).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

EULER = 0.5772156649015329


def expected_max_sr(n_trials: int, var_sr: float) -> float:
    if n_trials <= 1 or var_sr <= 0:
        return 0.0
    z = stats.norm.ppf
    return math.sqrt(var_sr) * ((1 - EULER) * z(1 - 1 / n_trials) + EULER * z(1 - 1 / (n_trials * math.e)))


def deflated_sharpe(returns: np.ndarray, n_trials: int, var_sr: float) -> dict:
    """Probability that the true Sharpe exceeds what the best of `n_trials` random strategies would show."""
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    T = len(r)
    sd = r.std(ddof=1)
    if T < 10 or sd == 0:
        return {"sr": None, "sr0": None, "dsr": None, "T": T}
    sr = r.mean() / sd
    g3 = float(stats.skew(r))
    g4 = float(stats.kurtosis(r, fisher=False))
    sr0 = expected_max_sr(n_trials, var_sr)
    den = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr * sr))
    return {"sr": float(sr), "sr_annual": float(sr * math.sqrt(52)), "sr0": float(sr0), "skew": g3, "kurt": g4, "T": T,
            "n_trials": n_trials, "dsr": float(stats.norm.cdf((sr - sr0) * math.sqrt(T - 1) / den))}
