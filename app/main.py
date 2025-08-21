from __future__ import annotations

import datetime as dt
from typing import List

import numpy as np
import pandas as pd
import streamlit as st

from app.lib.bsm import put_delta
from app.lib.earnings import has_earnings_before_expiry
from app.lib.options_data import fetch_puts_for_expiry, get_spot_and_dividend_yield, list_expirations
from app.lib.ranking import RankingParams, prepare_put_candidates, rank_puts


st.set_page_config(page_title="Cash-Secured Put Screener", layout="wide")


@st.cache_data(show_spinner=False, ttl=600)
def cached_expirations(ticker: str) -> List[pd.Timestamp]:
	return list_expirations(ticker)


@st.cache_data(show_spinner=False, ttl=600)
def cached_puts(ticker: str, expiry: pd.Timestamp) -> pd.DataFrame:
	return fetch_puts_for_expiry(ticker, expiry)


@st.cache_data(show_spinner=False, ttl=300)
def cached_spot_div(ticker: str):
	return get_spot_and_dividend_yield(ticker)


def sidebar_controls():
	st.sidebar.header("Screen Settings")
	tickers = st.sidebar.text_input("Tickers (comma-separated)", value="AAPL,MSFT,TSLA").upper()
	ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]

	dte_min, dte_max = st.sidebar.slider("Days to Expiry window", min_value=1, max_value=180, value=(14, 60))
	min_oi = st.sidebar.number_input("Min Open Interest", value=50, min_value=0)
	min_vol = st.sidebar.number_input("Min Volume", value=1, min_value=0)
	max_spread = st.sidebar.number_input("Max Spread Ratio", value=0.5, min_value=0.0, max_value=5.0, step=0.05, format="%.2f")
	min_prob = st.sidebar.number_input("Min Prob OTM", value=0.55, min_value=0.0, max_value=0.99, step=0.01, format="%.2f")
	min_roc = st.sidebar.number_input("Min Annualized ROC", value=0.10, min_value=0.0, max_value=5.0, step=0.01, format="%.2f")
	delta_band = st.sidebar.slider("Target |delta| band", min_value=0.00, max_value=1.00, value=(0.10, 0.35), step=0.01)
	min_otm_pct = st.sidebar.number_input("Min OTM % (strike below spot)", value=5.0, min_value=0.0, max_value=50.0, step=0.5, format="%.1f")

	exclude_earnings = st.sidebar.checkbox("Exclude contracts with earnings before expiry", value=True)
	show_raw = st.sidebar.checkbox("Show raw chains table", value=False)

	rfr = st.sidebar.number_input("Risk-free rate (annual)", value=0.045, min_value=0.0, max_value=0.2, step=0.005, format="%.3f")

	return {
		"tickers": ticker_list,
		"dte_min": dte_min,
		"dte_max": dte_max,
		"params": RankingParams(
			min_open_interest=min_oi,
			min_volume=min_vol,
			max_spread_ratio=max_spread,
			min_prob_otm=min_prob,
			min_annualized_roc=min_roc,
			min_abs_delta=delta_band[0],
			max_abs_delta=delta_band[1],
			min_otm_pct=min_otm_pct / 100.0,
		),
		"exclude_earnings": exclude_earnings,
		"rfr": rfr,
		"show_raw": show_raw,
	}


def display_results(df_ranked: pd.DataFrame):
	if df_ranked.empty:
		st.info("No candidates matched filters.")
		return
	cols = [
		"ticker",
		"expiry",
		"contractSymbol",
		"strike",
		"bid",
		"ask",
		"mid",
		"volume",
		"openInterest",
		"impliedVolatility",
		"delta",
		"otm_pct",
		"premium",
		"prob_otm",
		"annualized_roc",
		"breakeven",
		"spread_ratio",
		"earnings_before_expiry",
		"score",
	]
	st.dataframe(
		df_ranked[cols].reset_index(drop=True),
		hide_index=True,
		use_container_width=True,
	)

	csv = df_ranked[cols].to_csv(index=False).encode("utf-8")
	st.download_button("Download CSV", data=csv, file_name="put_candidates.csv", mime="text/csv")


def main():
	st.title("Cash-Secured Put Screener")
	st.caption("Educational tool. Not financial advice. Quotes via yfinance; verify with your broker.")

	controls = sidebar_controls()
	all_ranked: List[pd.DataFrame] = []

	for ticker in controls["tickers"]:
		spot, div_yield = cached_spot_div(ticker)
		if spot is None or not np.isfinite(spot):
			st.warning(f"Could not get spot for {ticker}.")
			continue
		exp_list = cached_expirations(ticker)
		if not exp_list:
			st.warning(f"No expirations for {ticker}.")
			continue
		# Filter expirations by DTE
		exp_filtered = []
		for e in exp_list:
			if pd.isna(e):
				continue
			dte = (pd.Timestamp(e) - pd.Timestamp.today().normalize()).days
			if controls["dte_min"] <= dte <= controls["dte_max"]:
				exp_filtered.append(e)
		if not exp_filtered:
			continue

		per_ticker_frames: List[pd.DataFrame] = []
		for expiry in exp_filtered:
			df_puts = cached_puts(ticker, expiry)
			if df_puts.empty:
				continue
			if controls["show_raw"]:
				with st.expander(f"Raw puts: {ticker} {expiry.date()}"):
					st.dataframe(df_puts, use_container_width=True, hide_index=True)
			df_candidates = prepare_put_candidates(df_puts, spot, controls["rfr"], div_yield)
			earnings_flag = has_earnings_before_expiry(ticker, expiry)
			df_candidates["earnings_before_expiry"] = earnings_flag
			if controls["exclude_earnings"] and earnings_flag:
				# Drop these contracts entirely
				pass
			per_ticker_frames.append(df_candidates)
		if per_ticker_frames:
			all_ranked.append(pd.concat(per_ticker_frames, ignore_index=True))

	if not all_ranked:
		st.info("No data to rank yet. Adjust filters or tickers.")
		return

	combined = pd.concat(all_ranked, ignore_index=True)
	if controls["exclude_earnings"]:
		combined = combined.loc[~combined["earnings_before_expiry"].fillna(False)]
	ranked = rank_puts(combined, controls["params"])
	display_results(ranked)


if __name__ == "__main__":
	main()

