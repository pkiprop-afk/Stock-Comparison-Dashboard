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
    info = stock.info
    return {
        "name": info.get("longName", ticker),
        "price": info.get("currentPrice", 0),
        "change_pct": info.get("regularMarketChangePercent", 0),
        "pe": info.get("trailingPE", None),
        "eps": info.get("trailingEps", None),
        "revenue_growth": info.get("revenueGrowth", None),
        "net_margin": info.get("profitMargins", None),
        "mkt_cap": info.get("marketCap", None),
        "fcf_yield": info.get("freeCashflow", None),
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
