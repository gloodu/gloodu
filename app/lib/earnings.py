from __future__ import annotations

from typing import Optional

import pandas as pd
import yfinance as yf


def get_next_earnings_date(ticker: str) -> Optional[pd.Timestamp]:
	"""Return the next earnings date if available."""
	try:
		t = yf.Ticker(ticker)
		# Prefer new API if available
		try:
			ed = t.get_earnings_dates(limit=1)
			if ed is not None and len(ed.index) > 0:
				# DataFrame indexed by dates
				return pd.to_datetime(ed.index[0]).tz_localize(None)
		except Exception:
			pass
		# Fallback to calendar
		cal = t.calendar
		if isinstance(cal, pd.DataFrame) and "Earnings Date" in cal.index:
			val = cal.loc["Earnings Date"][0]
			return pd.to_datetime(val).tz_localize(None)
		return None
	except Exception:
		return None


def has_earnings_before_expiry(ticker: str, expiry: pd.Timestamp) -> bool:
	try:
		next_ed = get_next_earnings_date(ticker)
		if next_ed is None or pd.isna(next_ed):
			return False
		return pd.Timestamp(next_ed) <= pd.Timestamp(expiry)
	except Exception:
		return False

