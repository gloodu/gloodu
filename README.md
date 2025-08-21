## Cash-Secured Put Screener (Streamlit)

This app helps screen stocks for selling cash-secured out-of-the-money (OTM) put options. It fetches options chains, computes Black–Scholes Greeks and risk metrics, and ranks candidates by yield, probability of expiring OTM, and other filters.

### Features
- Ticker input (comma-separated)
- DTE window filter and expirations selection
- OTM put filter with delta band
- Liquidity filters: minimum open interest, minimum volume, max spread
- Yield metrics: static and annualized
- Risk metrics: delta, probability of expiring OTM, breakeven
- Earnings before expiry flag and exclusion option
- Scatter and payoff charts
- CSV export of ranked candidates

### Quick start

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

### Notes
- Data provided by `yfinance` and may lag or be incomplete. Always verify quotes with your broker.
- Probability metrics are risk-neutral and indicative only.
- This is not financial advice.

# Hi There, I'm Gary Loodu 👋

Experienced technology leader with a passion for cloud computing and AI, currently focusing on driving innovation at Oracle. 


## 🛠️ Skills
- **Leadership**: technical leadership and exective management. 

## 🌱 Currently Learning
- Advanced Go concepts
- Machine Learning with Python
- Oracle AI  https://www.oracle.com/artificial-intelligence/
  
Feel free to follow me, email me, or send me a connection request on LinkedIn — they are listed in the left sidebar .
