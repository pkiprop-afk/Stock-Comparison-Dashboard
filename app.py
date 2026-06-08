import os
from datetime import datetime
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Stock Dashboard", layout="wide")

JOURNAL_FILE = "journal.csv"
DEFAULT_TICKERS = ["AAPL", "GOOGL", "META"]
COLOR_PALETTE = [
    "#378ADD", "#1D9E75", "#D85A30", "#9B59B6",
    "#F39C12", "#1ABC9C", "#E74C3C", "#2ECC71",
]

# --- Sidebar: ticker input ---
st.sidebar.title("Tickers")
raw_input = st.sidebar.text_input(
    "Enter comma-separated tickers",
    value=", ".join(DEFAULT_TICKERS),
)
TICKERS = [t.strip().upper() for t in raw_input.split(",") if t.strip()]
if not TICKERS:
    TICKERS = DEFAULT_TICKERS
COLORS = {t: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, t in enumerate(TICKERS)}


# --- Data fetching ---
@st.cache_data(ttl=300)
def fetch_fundamentals(ticker):
    stock = yf.Ticker(ticker)
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
    return stock.history(period="1y")


# --- Helpers ---
def fmt_mkt_cap(val):
    if val is None:
        return "N/A"
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    return f"${val/1e6:.2f}M"

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        return pd.read_csv(JOURNAL_FILE, dtype=str)
    return pd.DataFrame(columns=["timestamp", "tickers", "note"])

def save_journal_entry(tickers, note):
    df = load_journal()
    new_row = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tickers":   ", ".join(tickers),
        "note":      note,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(JOURNAL_FILE, index=False)


# --- Load data ---
with st.spinner("Fetching live data..."):
    data    = {t: fetch_fundamentals(t) for t in TICKERS}
    history = {t: fetch_history(t) for t in TICKERS}


# --- Metric cards ---
st.title("Stock Comparison Dashboard")
st.subheader("Fundamentals")
cols = st.columns(len(TICKERS))
for col, ticker in zip(cols, TICKERS):
    d = data[ticker]
    with col:
        st.markdown(f"### {ticker}")
        st.metric("Price",          f"${d['price']}"           if d["price"]          is not None else "N/A",
                                    f"{d['change_pct']}%"      if d["change_pct"]     is not None else None)
        st.metric("P/E (Forward)",  d["pe"]                    if d["pe"]             is not None else "N/A")
        st.metric("EPS",            f"${d['eps']}"             if d["eps"]            is not None else "N/A")
        st.metric("Revenue Growth", f"{d['revenue_growth']}%"  if d["revenue_growth"] is not None else "N/A")
        st.metric("Net Margin",     f"{d['net_margin']}%"      if d["net_margin"]     is not None else "N/A")
        st.metric("Market Cap",     fmt_mkt_cap(d["mkt_cap"]))


# --- 1-Year price performance line chart ---
st.subheader("1-Year Price Performance")
fig_line = go.Figure()
for ticker in TICKERS:
    df = history[ticker]
    if df.empty:
        continue
    df_norm = (df["Close"] / df["Close"].iloc[0] - 1) * 100
    fig_line.add_trace(go.Scatter(
        x=df.index,
        y=df_norm.round(2),
        name=ticker,
        line=dict(color=COLORS[ticker], width=2),
        hovertemplate=f"<b>{ticker}</b><br>Date: %{{x|%b %d, %Y}}<br>Return: %{{y:.2f}}%<extra></extra>",
    ))
fig_line.update_layout(
    yaxis_title="Return (%)",
    xaxis_title="Date",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=0, r=0, t=40, b=0),
    height=400,
)
fig_line.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.4)
st.plotly_chart(fig_line, use_container_width=True)


# --- Bar chart metric comparison ---
st.subheader("Metric Comparison")
METRIC_OPTIONS = {
    "P/E Ratio (Forward)": "pe",
    "EPS":                 "eps",
    "Revenue Growth (%)":  "revenue_growth",
    "Net Margin (%)":      "net_margin",
}
selected_label  = st.selectbox("Select metric", list(METRIC_OPTIONS.keys()))
selected_metric = METRIC_OPTIONS[selected_label]

bar_tickers = [t for t in TICKERS if data[t][selected_metric] is not None]
bar_values  = [data[t][selected_metric] for t in bar_tickers]
bar_colors  = [COLORS[t] for t in bar_tickers]

fig_bar = go.Figure(go.Bar(
    x=bar_tickers,
    y=bar_values,
    marker_color=bar_colors,
    text=[str(v) for v in bar_values],
    textposition="outside",
))
fig_bar.update_layout(
    yaxis_title=selected_label,
    margin=dict(l=0, r=0, t=40, b=0),
    height=350,
    showlegend=False,
)
st.plotly_chart(fig_bar, use_container_width=True)


# --- Investment journal ---
st.subheader("Investment Journal")

with st.form("journal_form", clear_on_submit=True):
    note = st.text_area("Add a note about your market reasoning")
    submitted = st.form_submit_button("Save entry")
    if submitted and note.strip():
        save_journal_entry(TICKERS, note.strip())
        st.success("Entry saved.")

journal_df = load_journal()
if not journal_df.empty:
    for _, row in journal_df.iloc[::-1].iterrows():
        with st.expander(f"{row['timestamp']}  —  {row['tickers']}"):
            st.write(row["note"])
