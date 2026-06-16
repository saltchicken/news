# app.py
import streamlit as st
import pandas as pd
import json

st.set_page_config(layout="wide", page_title="Stock News Dashboard")

@st.cache_data(ttl=60) # Refreshes data every 60 seconds
def load_data(filepath):
    try:
        with open(filepath, 'r') as f:
            return pd.DataFrame(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return pd.DataFrame()

st.title("📈 AI Stock News Analysis")

# Load your two files
df_portfolio = load_data("portfolio_news.json")
df_discoveries = load_data("stock_discoveries.json")

if not df_portfolio.empty:
    st.header("Portfolio News Overview")
    
    # 1. Quick Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Articles", len(df_portfolio))
    col2.metric("Positive Sentiment", len(df_portfolio[df_portfolio['sentiment'] == 'Positive']))
    col3.metric("Negative Sentiment", len(df_portfolio[df_portfolio['sentiment'] == 'Negative']))

    # 2. Interactive Data Table
    st.subheader("Recent Analysis")
    st.dataframe(df_portfolio[['timestamp', 'ticker', 'sentiment', 'analysis', 'title']], use_container_width=True)

    # 3. Sentiment Bar Chart
    st.subheader("Sentiment by Ticker")
    sentiment_counts = df_portfolio.groupby(['ticker', 'sentiment']).size().unstack(fill_value=0)
    st.bar_chart(sentiment_counts)
