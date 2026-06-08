import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Stock Dashboard", layout="Wide")
st.title("Stock Comparison Dashboard")
st.write("AAPL . GOOGL . META")