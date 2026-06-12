import os
import math
from datetime import datetime
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Stock Dashboard", layout="wide")

JOURNAL_FILE    = "journal.csv"
DEFAULT_TICKERS = ["AAPL", "GOOGL", "META"]
COLOR_PALETTE   = [
    "#378ADD", "#1D9E75", "#D85A30", "#9B59B6",
    "#F39C12", "#1ABC9C", "#E74C3C", "#2ECC71",
]
RISK_FREE_RATE  = 0.04  # annual, used for Sharpe calculation


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("Settings")

raw_input = st.sidebar.text_input(
    "Enter comma-separated tickers",
    value=", ".join(DEFAULT_TICKERS),
)
TICKERS = [t.strip().upper() for t in raw_input.split(",") if t.strip()]
if not TICKERS:
    TICKERS = DEFAULT_TICKERS
COLORS = {t: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, t in enumerate(TICKERS)}

INDICATOR_OPTIONS  = ["20-day SMA", "50-day SMA", "Lower/Upper Bollinger Bands", "RSI (14-day)", "MACD"]
selected_indicators = st.sidebar.multiselect("Select Technical Indicators", INDICATOR_OPTIONS)


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_fundamentals(ticker):
    stock = yf.Ticker(ticker)
    fi    = stock.fast_info

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
        income      = stock.get_income_stmt(freq="yearly")
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
    return yf.Ticker(ticker).history(period="1y")


# ---------------------------------------------------------------------------
# Risk metric helpers
# ---------------------------------------------------------------------------
def compute_risk_metrics(df, market_df):
    """Return (sharpe, mdd, beta) for a price DataFrame vs a market DataFrame."""
    try:
        daily_returns = df["Close"].pct_change().dropna()
        excess        = daily_returns - (RISK_FREE_RATE / 252)
        sharpe = round(excess.mean() / excess.std() * math.sqrt(252), 2) \
                 if excess.std() > 0 else None
    except Exception:
        sharpe = None

    try:
        drawdown = (df["Close"] - df["Close"].cummax()) / df["Close"].cummax()
        mdd = round(drawdown.min() * 100, 2)
    except Exception:
        mdd = None

    try:
        stock_ret  = df["Close"].pct_change().dropna()
        market_ret = market_df["Close"].pct_change().dropna()
        aligned    = pd.concat([stock_ret, market_ret], axis=1, join="inner").dropna()
        aligned.columns = ["stock", "market"]
        cov  = aligned.cov()
        beta = round(cov.loc["stock", "market"] / cov.loc["market", "market"], 2)
    except Exception:
        beta = None

    return sharpe, mdd, beta


# ---------------------------------------------------------------------------
# Technical indicator calculations
# ---------------------------------------------------------------------------
def compute_rsi(close, period=14):
    delta     = close.diff()
    gain      = delta.clip(lower=0)
    loss      = -delta.clip(upper=0)
    # Wilder's smoothing via EWM (alpha = 1/period, adjust=False)
    avg_gain  = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss  = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs        = avg_gain / avg_loss.replace(0, float("nan"))
    return (100 - (100 / (1 + rs))).round(2)


def compute_macd(close, fast=12, slow=26, signal=9):
    ema_fast    = close.ewm(span=fast, adjust=False).mean()
    ema_slow    = close.ewm(span=slow, adjust=False).mean()
    macd_line   = (ema_fast - ema_slow).round(4)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean().round(4)
    histogram   = (macd_line - signal_line).round(4)
    return macd_line, signal_line, histogram


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------
def fmt_mkt_cap(val):
    if val is None:
        return "N/A"
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    return f"${val/1e6:.2f}M"


def hex_to_rgba(hex_color, alpha=0.12):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def load_journal():
    if os.path.exists(JOURNAL_FILE):
        return pd.read_csv(JOURNAL_FILE, dtype=str)
    return pd.DataFrame(columns=["timestamp", "tickers", "note"])


def save_journal_entry(tickers, note):
    df      = load_journal()
    new_row = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tickers":   ", ".join(tickers),
        "note":      note,
    }])
    pd.concat([df, new_row], ignore_index=True).to_csv(JOURNAL_FILE, index=False)


# ---------------------------------------------------------------------------
# Load all data
# ---------------------------------------------------------------------------
with st.spinner("Fetching live data..."):
    data           = {t: fetch_fundamentals(t) for t in TICKERS}
    history        = {t: fetch_history(t) for t in TICKERS}
    market_history = fetch_history("^GSPC")


# ---------------------------------------------------------------------------
# Fundamentals + Risk Metrics cards
# ---------------------------------------------------------------------------
st.title("Stock Comparison Dashboard")
st.subheader("Fundamentals & Risk Metrics")

cols = st.columns(len(TICKERS))
for col, ticker in zip(cols, TICKERS):
    d = data[ticker]
    sharpe, mdd, beta = compute_risk_metrics(history[ticker], market_history)
    with col:
        st.markdown(f"### {ticker}")
        st.metric("Price",
                  f"${d['price']}"       if d["price"]          is not None else "N/A",
                  f"{d['change_pct']}%"  if d["change_pct"]     is not None else None)
        st.metric("P/E (Forward)",  d["pe"]                   if d["pe"]             is not None else "N/A")
        st.metric("EPS",            f"${d['eps']}"            if d["eps"]            is not None else "N/A")
        st.metric("Revenue Growth", f"{d['revenue_growth']}%" if d["revenue_growth"] is not None else "N/A")
        st.metric("Net Margin",     f"{d['net_margin']}%"     if d["net_margin"]     is not None else "N/A")
        st.metric("Market Cap",     fmt_mkt_cap(d["mkt_cap"]))
        st.divider()
        st.metric("Sharpe Ratio",       sharpe          if sharpe is not None else "N/A")
        st.metric("Max Drawdown",       f"{mdd}%"       if mdd    is not None else "N/A")
        st.metric("Beta (vs S&P 500)",  beta            if beta   is not None else "N/A")


# ---------------------------------------------------------------------------
# 1-Year Price Performance line chart + technical overlays
# ---------------------------------------------------------------------------
st.subheader("1-Year Price Performance")

fig_line = go.Figure()

for ticker in TICKERS:
    df = history[ticker]
    if df.empty:
        continue

    first_close = df["Close"].iloc[0]
    df_norm     = (df["Close"] / first_close - 1) * 100

    fig_line.add_trace(go.Scatter(
        x=df.index,
        y=df_norm.round(2),
        name=ticker,
        line=dict(color=COLORS[ticker], width=2),
        hovertemplate=(
            f"<b>{ticker}</b><br>"
            "Date: %{x|%b %d, %Y}<br>"
            "Return: %{y:.2f}%<extra></extra>"
        ),
    ))

    # --- Technical overlays (normalized to same % base as price series) ---
    def norm(series):
        return ((series / first_close - 1) * 100).round(2)

    color = COLORS[ticker]

    if "20-day SMA" in selected_indicators:
        sma20 = df["Close"].rolling(20).mean()
        fig_line.add_trace(go.Scatter(
            x=df.index, y=norm(sma20),
            name=f"{ticker} SMA20",
            line=dict(color=color, width=1, dash="dash"),
            hovertemplate=f"<b>{ticker} SMA20</b><br>%{{y:.2f}}%<extra></extra>",
        ))

    if "50-day SMA" in selected_indicators:
        sma50 = df["Close"].rolling(50).mean()
        fig_line.add_trace(go.Scatter(
            x=df.index, y=norm(sma50),
            name=f"{ticker} SMA50",
            line=dict(color=color, width=1, dash="dot"),
            hovertemplate=f"<b>{ticker} SMA50</b><br>%{{y:.2f}}%<extra></extra>",
        ))

    if "Lower/Upper Bollinger Bands" in selected_indicators:
        sma20    = df["Close"].rolling(20).mean()
        std20    = df["Close"].rolling(20).std()
        bb_upper = sma20 + 2 * std20
        bb_lower = sma20 - 2 * std20
        fig_line.add_trace(go.Scatter(
            x=df.index, y=norm(bb_upper),
            name=f"{ticker} BB Upper",
            line=dict(color=color, width=1, dash="longdash"),
            opacity=0.6,
            legendgroup=f"{ticker}_bb",
            hovertemplate=f"<b>{ticker} BB+</b><br>%{{y:.2f}}%<extra></extra>",
        ))
        fig_line.add_trace(go.Scatter(
            x=df.index, y=norm(bb_lower),
            name=f"{ticker} BB Lower",
            line=dict(color=color, width=1, dash="longdash"),
            opacity=0.6,
            fill="tonexty",
            fillcolor=hex_to_rgba(color, 0.08),
            legendgroup=f"{ticker}_bb",
            showlegend=False,
            hovertemplate=f"<b>{ticker} BB-</b><br>%{{y:.2f}}%<extra></extra>",
        ))

fig_line.update_layout(
    yaxis_title="Return (%)",
    xaxis_title="Date",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=0, r=0, t=40, b=0),
    height=420,
)
fig_line.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.4)
st.plotly_chart(fig_line, use_container_width=True)


# ---------------------------------------------------------------------------
# RSI chart (conditional)
# ---------------------------------------------------------------------------
if "RSI (14-day)" in selected_indicators:
    st.subheader("RSI — 14-Day Relative Strength Index")
    fig_rsi = go.Figure()

    for ticker in TICKERS:
        df = history[ticker]
        if df.empty:
            continue
        rsi = compute_rsi(df["Close"])
        fig_rsi.add_trace(go.Scatter(
            x=df.index,
            y=rsi,
            name=ticker,
            line=dict(color=COLORS[ticker], width=1.5),
            hovertemplate=f"<b>{ticker}</b><br>Date: %{{x|%b %d, %Y}}<br>RSI: %{{y:.1f}}<extra></extra>",
        ))

    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red",  opacity=0.5,
                      annotation_text="Overbought (70)", annotation_position="top left")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5,
                      annotation_text="Oversold (30)", annotation_position="bottom left")
    fig_rsi.update_layout(
        yaxis=dict(title="RSI", range=[0, 100]),
        xaxis_title="Date",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=40, b=0),
        height=300,
    )
    st.plotly_chart(fig_rsi, use_container_width=True)


# ---------------------------------------------------------------------------
# MACD chart (conditional)
# ---------------------------------------------------------------------------
if "MACD" in selected_indicators:
    st.subheader("MACD — 12/26/9")

    for ticker in TICKERS:
        df = history[ticker]
        if df.empty:
            continue

        macd_line, signal_line, histogram = compute_macd(df["Close"])
        color = COLORS[ticker]

        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(
            x=df.index, y=macd_line,
            name="MACD",
            line=dict(color=color, width=1.5),
            hovertemplate="MACD: %{y:.4f}<extra></extra>",
        ))
        fig_macd.add_trace(go.Scatter(
            x=df.index, y=signal_line,
            name="Signal",
            line=dict(color="#AAAAAA", width=1.5, dash="dash"),
            hovertemplate="Signal: %{y:.4f}<extra></extra>",
        ))
        # Histogram bars colored green (positive) / red (negative)
        bar_colors = ["#1D9E75" if v >= 0 else "#D85A30" for v in histogram.fillna(0)]
        fig_macd.add_trace(go.Bar(
            x=df.index, y=histogram,
            name="Histogram",
            marker_color=bar_colors,
            opacity=0.5,
            hovertemplate="Hist: %{y:.4f}<extra></extra>",
        ))
        fig_macd.add_hline(y=0, line_color="gray", opacity=0.4)
        fig_macd.update_layout(
            title=dict(text=ticker, font=dict(color=color)),
            yaxis_title="Value",
            xaxis_title="Date",
            hovermode="x unified",
            barmode="overlay",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=0, r=0, t=50, b=0),
            height=300,
        )
        st.plotly_chart(fig_macd, use_container_width=True)


# ---------------------------------------------------------------------------
# Bar chart metric comparison
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Correlation matrix heatmap
# ---------------------------------------------------------------------------
st.subheader("Portfolio Correlation Analysis")

if len(TICKERS) < 2:
    st.info("Add at least two tickers to see correlation analysis.")
else:
    returns_dict = {
        t: history[t]["Close"].pct_change().dropna()
        for t in TICKERS
        if not history[t].empty
    }
    if len(returns_dict) >= 2:
        corr = pd.DataFrame(returns_dict).dropna().corr()

        annotations = [[f"{v:.2f}" for v in row] for row in corr.values]
        fig_corr = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=annotations,
            texttemplate="%{text}",
            colorbar=dict(title="Pearson r"),
        ))
        fig_corr.update_layout(
            height=380,
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig_corr, use_container_width=True)


# ---------------------------------------------------------------------------
# Investment journal
# ---------------------------------------------------------------------------
st.subheader("Investment Journal")

with st.form("journal_form", clear_on_submit=True):
    note      = st.text_area("Add a note about your market reasoning")
    submitted = st.form_submit_button("Save entry")
    if submitted and note.strip():
        save_journal_entry(TICKERS, note.strip())
        st.success("Entry saved.")

journal_df = load_journal()
if not journal_df.empty:
    for _, row in journal_df.iloc[::-1].iterrows():
        with st.expander(f"{row['timestamp']}  —  {row['tickers']}"):
            st.write(row["note"])
