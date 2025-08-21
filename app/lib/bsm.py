from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class BSInputs:
	spot_price: float
	strike_price: float
	risk_free_rate: float  # annualized, continuous comp, e.g., 0.045
	dividend_yield: float = 0.0  # annualized, continuous comp
	implied_vol: float = 0.0  # annualized
	time_to_expiry_years: float = 0.0
	is_call: bool = False


def _ensure_positive(value: float, fallback: float) -> float:
	if value is None or not np.isfinite(value) or value <= 0:
		return fallback
	return float(value)


def _norm_cdf(x: float) -> float:
	# Standard normal CDF using error function
	return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def compute_d1_d2(spot_price: float, strike_price: float, risk_free_rate: float, dividend_yield: float, implied_vol: float, time_to_expiry_years: float) -> Tuple[float, float]:
	S = _ensure_positive(spot_price, np.nan)
	K = _ensure_positive(strike_price, np.nan)
	sigma = _ensure_positive(implied_vol, np.nan)
	T = _ensure_positive(time_to_expiry_years, np.nan)
	if any(np.isnan(x) for x in (S, K, sigma, T)):
		return (np.nan, np.nan)
	if sigma == 0 or T == 0:
		return (np.nan, np.nan)
	mu = risk_free_rate - dividend_yield
	sqrtT = math.sqrt(T)
	d1 = (math.log(S / K) + (mu + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
	d2 = d1 - sigma * sqrtT
	return (d1, d2)


def put_delta(spot_price: float, strike_price: float, risk_free_rate: float, dividend_yield: float, implied_vol: float, time_to_expiry_years: float) -> float:
	d1, _ = compute_d1_d2(spot_price, strike_price, risk_free_rate, dividend_yield, implied_vol, time_to_expiry_years)
	if np.isnan(d1):
		return np.nan
	# With dividends, put delta = -exp(-qT) * N(-d1)
	T = max(time_to_expiry_years, 0.0)
	return -math.exp(-dividend_yield * T) * _norm_cdf(-d1)


def probability_expiring_otm_put(spot_price: float, strike_price: float, risk_free_rate: float, dividend_yield: float, implied_vol: float, time_to_expiry_years: float) -> float:
	"""Risk-neutral probability that S_T > K for a put (i.e., put expires OTM)."""
	_, d2 = compute_d1_d2(spot_price, strike_price, risk_free_rate, dividend_yield, implied_vol, time_to_expiry_years)
	if np.isnan(d2):
		return np.nan
	return float(_norm_cdf(d2))


def breakeven_price(strike_price: float, premium_per_share: float) -> float:
	if strike_price is None or premium_per_share is None:
		return np.nan
	try:
		return float(strike_price) - float(premium_per_share)
	except Exception:
		return np.nan


def annualized_return_on_capital(premium_per_share: float, strike_price: float, days_to_expiry: float) -> float:
	"""Approximate ROC: premium / strike capital, annualized by 365 days."""
	if any(v is None for v in (premium_per_share, strike_price, days_to_expiry)):
		return np.nan
	if strike_price <= 0 or days_to_expiry <= 0:
		return np.nan
	try:
		roc_simple = float(premium_per_share) / float(strike_price)
		return roc_simple * (365.0 / float(days_to_expiry))
	except Exception:
		return np.nan

