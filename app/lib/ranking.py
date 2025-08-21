from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .bsm import (
	annualized_return_on_capital,
	breakeven_price,
	probability_expiring_otm_put,
	put_delta,
)
from .options_data import compute_mid_price


@dataclass
class RankingParams:
	min_open_interest: int = 50
	min_volume: int = 1
	max_spread_ratio: float = 0.5  # (ask-bid)/mid <= max
	min_prob_otm: float = 0.55
	min_annualized_roc: float = 0.10
	min_abs_delta: float = 0.10
	max_abs_delta: float = 0.35
	min_otm_pct: float = 0.05  # strike at least 5% below spot


def _compute_spread_ratio(row: pd.Series) -> float:
	bid = row.get("bid", np.nan)
	ask = row.get("ask", np.nan)
	mid = row.get("mid", np.nan)
	if not np.isfinite(bid) or not np.isfinite(ask) or not np.isfinite(mid) or mid <= 0:
		return np.nan
	return float((ask - bid) / mid) if ask >= bid else np.nan


def prepare_put_candidates(df_puts: pd.DataFrame, spot: float, rfr: float, div_yield: float) -> pd.DataFrame:
	df = df_puts.copy()
	if df.empty:
		return df
	# Add derived fields
	df["mid"] = df.apply(compute_mid_price, axis=1)
	df["spread_ratio"] = df.apply(_compute_spread_ratio, axis=1)
	df["days_to_expiry"] = (pd.to_datetime(df["expiry"]) - pd.Timestamp.today().normalize()).dt.days.clip(lower=0)
	df["T"] = df["days_to_expiry"] / 365.0
	df["premium"] = df["mid"]
	df["breakeven"] = df.apply(lambda r: breakeven_price(r.get("strike", np.nan), r.get("premium", np.nan)), axis=1)
	df["prob_otm"] = df.apply(
		lambda r: probability_expiring_otm_put(spot, r.get("strike", np.nan), rfr, div_yield, r.get("impliedVolatility", np.nan), r.get("T", np.nan)),
		axis=1,
	)
	df["annualized_roc"] = df.apply(lambda r: annualized_return_on_capital(r.get("premium", np.nan), r.get("strike", np.nan), r.get("days_to_expiry", np.nan)), axis=1)
	df["delta"] = df.apply(
		lambda r: put_delta(
			spot,
			r.get("strike", np.nan),
			rfr,
			div_yield,
			r.get("impliedVolatility", np.nan),
			r.get("T", np.nan),
		),
		axis=1,
	)
	df["abs_delta"] = df["delta"].abs()
	# OTM percent for puts: strike below spot ratio
	df["otm_pct"] = df.apply(
		lambda r: (max(spot - float(r.get("strike", np.nan)), 0.0) / spot) if spot and np.isfinite(spot) else np.nan,
		axis=1,
	)
	return df


def rank_puts(df_candidates: pd.DataFrame, params: RankingParams) -> pd.DataFrame:
	df = df_candidates.copy()
	if df.empty:
		return df
	# Apply liquidity and risk filters
	liquidity_mask = (
		(df["openInterest"].fillna(0) >= params.min_open_interest)
		& (df["volume"].fillna(0) >= params.min_volume)
	)
	spread_mask = df["spread_ratio"].fillna(999.0) <= params.max_spread_ratio
	prob_mask = df["prob_otm"].fillna(0) >= params.min_prob_otm
	roc_mask = df["annualized_roc"].fillna(0) >= params.min_annualized_roc
	delta_mask = (df["abs_delta"].fillna(1.0) >= params.min_abs_delta) & (df["abs_delta"].fillna(1.0) <= params.max_abs_delta)
	otm_mask = df["otm_pct"].fillna(0) >= params.min_otm_pct
	mask = liquidity_mask & spread_mask & prob_mask & roc_mask & delta_mask & otm_mask
	df = df.loc[mask].copy()
	if df.empty:
		return df
	# Score: blend of ROC and probability
	df["score"] = 0.6 * df["annualized_roc"].fillna(0) + 0.4 * df["prob_otm"].fillna(0)
	df = df.sort_values(["score", "annualized_roc", "prob_otm"], ascending=[False, False, False])
	return df