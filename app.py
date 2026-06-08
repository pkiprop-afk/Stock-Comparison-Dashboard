import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Stock Dashboard", layout="wide")

TICKERS = ["AAPL", "GOOGL", "META"]
COLORS = {"AAPL": "#378ADD", "GOOGL": "#1D9E75", "META": "#D85A30"}

@st.cache_data(ttl=300)
def fetch_fundamentals(ticker):
    stock = yf.Ticker(ticker)
    
    # fast_info is more reliable than .info
    fi = stock.fast_info

    try:
        price = round(fi.last_price, 2)
    except Exception:
        price = None

    try:
        prev_close = fi.regular_market_previous_close
        change_pct = round((fi.last_price - prev_close) / prev_close * 100, 2)
    except Exception:
        change_pct = None

    try:
        pe  = round(fi.forward_pe, 2)
        eps = round(fi.last_price / fi.forward_pe, 2)
    except Exception:
        pe, eps = None, None

    try:
        income = stock.get_income_stmt(freq="yearly")
        rev_current = income.loc["TotalRevenue"].iloc[0]
        rev_prev    = income.loc["TotalRevenue"].iloc[1]
        net_income  = income.loc["NetIncome"].iloc[0]
        revenue_growth = round((rev_current - rev_prev) / rev_prev * 100, 2)
        net_margin     = round(net_income / rev_current * 100, 2)
    except Exception:
        revenue_growth = None
        net_margin     = None

    return {
        "name":           ticker,
        "price":          price,
        "change_pct":     change_pct,
        "pe":             pe,
        "eps":            eps,
        "revenue_growth": revenue_growth,
        "net_margin":     net_margin,
        "mkt_cap":        fi.market_cap,
    }

@st.cache_data(ttl=300)
def fetch_history(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period='1y')

st.title("Stock Comparison Dashboard")

with st.spinner("Fetching live data..."):
    data = {t: fetch_fundamentals(t) for t in TICKERS}
    history = {t: fetch_history(t) for t in TICKERS}

def fmt_mkt_cap(val):
    if val is None:
        return "N/A"
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    return f"${val/1e6:.2f}M"

st.subheader("Fundamentals")
cols = st.columns(len(TICKERS))
for col, ticker in zip(cols, TICKERS):
    d = data[ticker]
    with col:
        st.markdown(f"### {ticker}")
        st.metric("Price",          f"${d['price']}"        if d['price']          is not None else "N/A",
                                    f"{d['change_pct']}%"   if d['change_pct']     is not None else None)
        st.metric("P/E (Forward)",  d['pe']                 if d['pe']             is not None else "N/A")
        st.metric("EPS",            f"${d['eps']}"          if d['eps']            is not None else "N/A")
        st.metric("Revenue Growth", f"{d['revenue_growth']}%" if d['revenue_growth'] is not None else "N/A")
        st.metric("Net Margin",     f"{d['net_margin']}%"   if d['net_margin']     is not None else "N/A")
        st.metric("Market Cap",     fmt_mkt_cap(d['mkt_cap']))
