from __future__ import annotations

import datetime as dt
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf


def _to_datetime(date_str: str) -> pd.Timestamp:
	try:
		return pd.to_datetime(date_str).tz_localize(None)
	except Exception:
		return pd.NaT


def get_spot_and_dividend_yield(ticker: str) -> Tuple[Optional[float], float]:
	try:
		info = yf.Ticker(ticker).fast_info
		spot = float(info.get("last_price") or info.get("last_close") or info.get("previous_close") or np.nan)
		q = info.get("dividend_yield")
		div_yield = float(q) if q is not None else 0.0
		return spot, max(div_yield, 0.0)
	except Exception:
		return None, 0.0


def list_expirations(ticker: str) -> List[pd.Timestamp]:
	try:
		exp_list = yf.Ticker(ticker).options or []
		return [
			_to_datetime(e)
			for e in exp_list
			if e
		]
	except Exception:
		return []


def fetch_puts_for_expiry(ticker: str, expiry: pd.Timestamp) -> pd.DataFrame:
	try:
		if isinstance(expiry, (pd.Timestamp, dt.date)):
			exp_str = pd.Timestamp(expiry).strftime("%Y-%m-%d")
		else:
			exp_str = str(expiry)
		chain = yf.Ticker(ticker).option_chain(exp_str)
		puts = chain.puts.copy()
		puts["expiry"] = pd.Timestamp(exp_str)
		puts["ticker"] = ticker.upper()
		# Normalize columns we rely on
		for col in ["bid", "ask", "lastPrice", "volume", "openInterest", "impliedVolatility", "strike", "contractSymbol"]:
			if col not in puts.columns:
				puts[col] = np.nan
		return puts
	except Exception:
		return pd.DataFrame()


def compute_mid_price(row: pd.Series) -> float:
	bid = row.get("bid", np.nan)
	ask = row.get("ask", np.nan)
	last = row.get("lastPrice", np.nan)
	# Prefer mid of bid/ask if both present; else fallback to last
	if np.isfinite(bid) and np.isfinite(ask) and bid > 0 and ask > 0 and ask >= bid:
		return float((bid + ask) / 2.0)
	if np.isfinite(last) and last > 0:
		return float(last)
	return np.nan

