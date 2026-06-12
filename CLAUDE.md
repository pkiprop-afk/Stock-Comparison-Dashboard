# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirement.txt

# Run the app
streamlit run app.py
```

## Architecture

The entire app lives in a single file: `app.py`. It follows a top-to-bottom Streamlit execution model — the file runs from top to bottom on every user interaction. There are no modules, classes, or separate pages.

**Execution order:**
1. Sidebar widgets are rendered first (ticker input, indicator multiselect) — their values are immediately available as `TICKERS`, `COLORS`, and `selected_indicators`
2. All data is fetched inside a `st.spinner` block before any chart or card is rendered
3. UI sections render sequentially: metric cards → line chart → bar chart → correlation heatmap → journal

**Data layer (`@st.cache_data(ttl=300)`):**
- `fetch_fundamentals(ticker)` — calls `yf.Ticker.fast_info` for price/PE/EPS and `get_income_stmt` for revenue growth and net margin
- `fetch_history(ticker)` — returns a 1-year OHLCV DataFrame; also used for `^GSPC` (S&P 500 benchmark for Beta)

**Risk metrics** are computed at render time (not cached) via `compute_risk_metrics(df, market_df)` — Sharpe ratio (4% risk-free rate), Max Drawdown, and Beta vs `^GSPC`

**Technical overlays** are normalized to the same `(price / first_close - 1) * 100` basis as the price line so SMAs and Bollinger Bands overlay correctly on the return-% axis

**Journal persistence** writes to `journal.csv` in the working directory via `save_journal_entry` / `load_journal`; entries are shown newest-first using `iloc[::-1]`

**Color assignment** is deterministic: `COLORS = {ticker: COLOR_PALETTE[i % len(COLOR_PALETTE)]}` — palette has 8 entries, cycles for larger watchlists
