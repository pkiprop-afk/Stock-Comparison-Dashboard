# Stock Comparison Dashboard

A live, interactive stock research tool built with Streamlit, yfinance, and Plotly. Compare multiple tickers side by side across fundamentals, risk metrics, price performance, and technical indicators — all in one dashboard that refreshes every 5 minutes.

## Purpose

Designed for investors who want a single view to evaluate and compare equities without switching between data sources. You type in any tickers, and the dashboard pulls live data and computes everything on the fly.

## Features

### Sidebar Controls
- **Ticker input** — type any comma-separated tickers (e.g. `AAPL, NVDA, TSLA`); the entire dashboard rerenders with the new selection
- **Technical indicator selector** — multiselect to toggle overlays on the price chart

### Fundamentals & Risk Metrics Cards
One column per ticker showing:

| Metric | Source |
|---|---|
| Price + daily % change | `fast_info.last_price` vs previous close |
| P/E Ratio (Forward) | `fast_info.forward_pe` |
| EPS | Derived: `last_price / forward_pe` |
| Revenue Growth | YoY from annual income statement |
| Net Margin | Net income / revenue from annual income statement |
| Market Cap | `fast_info.market_cap` |
| Sharpe Ratio | Annualized (4% risk-free rate, 252 trading days) |
| Max Drawdown | Rolling peak-to-trough over 1 year |
| Beta | Covariance vs S&P 500 (`^GSPC`) daily returns |

### 1-Year Price Performance Chart
- Normalized return chart — all tickers plotted as `% return from start of period` so they're directly comparable regardless of price
- Optional overlays (normalized to the same basis):
  - 20-day SMA
  - 50-day SMA
  - Bollinger Bands (20-day, ±2σ) with shaded band fill

### Metric Comparison Bar Chart
- Dropdown to switch between P/E, EPS, Revenue Growth, and Net Margin
- One bar per ticker, color-coded, with value labels

### Portfolio Correlation Heatmap
- Pearson correlation matrix of daily returns across all active tickers
- Diverging `RdBu` color scale anchored at 0, with exact values annotated in each cell

### Investment Journal
- Free-text note entry saved to `journal.csv` in the project directory
- Entries persist across restarts
- Displayed newest-first, each showing the timestamp and active tickers at time of writing

## Setup

```bash
pip install -r requirement.txt
streamlit run app.py
```

## Dependencies

```
streamlit
yfinance
plotly
pandas
```
