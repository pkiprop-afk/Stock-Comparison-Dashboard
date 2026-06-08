import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Stock Dashboard", layout="wide")

TICKERS = ["APPL", "GOOGL", "META"]
COLORS = {"APPL": "#378ADD", "GOOGL": "#1D9E75", "META": "#D85A30"}

@st.cache_data(ttl=300)
def fetch_fundamentals(ticker):
    stock = yf.Ticker(ticker)
    
    # fast_info is more reliable than .info
    fi = stock.fast_info

    # get financials for margin + revenue growth
    try:
        income = stock.get_income_stmt(freq="yearly")
        rev_current = income.loc["TotalRevenue"].iloc[0]
        rev_prev    = income.loc["TotalRevenue"].iloc[1]
        net_income  = income.loc["NetIncome"].iloc[0]
        revenue_growth = (rev_current - rev_prev) / rev_prev
        net_margin     = net_income / rev_current
    except Exception:
        revenue_growth = None
        net_margin     = None

    # P/E and EPS from fast_info
    try:
        pe  = round(fi.p_e_ratio, 2) if fi.p_e_ratio else None
        eps = round(fi.last_price / fi.p_e_ratio, 2) if fi.p_e_ratio else None
    except Exception:
        pe, eps = None, None

    return {
        "name":           ticker,
        "price":          round(fi.last_price, 2),
        "change_pct":     round(fi.regular_market_previous_close, 2),
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

st.success("Data loaded!")
st.write(data["APPL"])
