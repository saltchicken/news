import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="Stock Discoveries", page_icon="🔍", layout="wide")

@st.cache_data(ttl=60)
def load_data(filepath):
    try:
        with open(filepath, 'r') as f:
            return pd.DataFrame(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return pd.DataFrame()

# Styling function for the dataframe
def style_sentiment(val):
    color = 'green' if val == 'Positive' else 'red' if val == 'Negative' else 'blue' if val == 'Neutral' else 'black'
    return f'color: {color}'

st.title("🔍 Stock Discoveries")

df_discoveries = load_data("stock_discoveries.json")

if not df_discoveries.empty:
    # Convert timestamp to datetime objects
    df_discoveries['timestamp'] = pd.to_datetime(df_discoveries['timestamp'])
    
    st.subheader("Filter Discoveries")
    
    # 1. Setup layout for filters
    col1, col2 = st.columns(2)
    
    default_start = datetime.now().date() - timedelta(days=3)
    default_end = datetime.now().date()
    
    with col1:
        date_range = st.date_input(
            "Select Date Range",
            value=(default_start, default_end),
            max_value=datetime.now().date()
        )
        
    with col2:
        available_tickers = sorted(df_discoveries['ticker'].unique())
        selected_tickers = st.multiselect(
            "Filter by Ticker(s)", 
            options=available_tickers,
            help="Leave empty to show all tickers"
        )
    
    # Apply Date filter
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range[0]
        
    mask = (df_discoveries['timestamp'].dt.date >= start_date) & (df_discoveries['timestamp'].dt.date <= end_date)
    
    # Apply Ticker filter
    if selected_tickers:
        mask = mask & (df_discoveries['ticker'].isin(selected_tickers))
        
    df_filtered = df_discoveries.loc[mask]

    if not df_filtered.empty:
        # 2. Ticker Mention Frequency
        st.subheader("Most Mentioned Tickers")
        ticker_counts = df_filtered['ticker'].value_counts()
        st.bar_chart(ticker_counts)

        # 3. Interactive Data Table (with colored text)
        st.subheader("Discovery Feed")
        
        display_df = df_filtered[['timestamp', 'ticker', 'sentiment', 'analysis', 'source', 'title']]
        styled_df = display_df.style.map(style_sentiment, subset=['sentiment'])
        
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.warning("No discoveries found matching your filters.")
else:
    st.warning("No stock discoveries collected yet. Waiting for the JSON to populate...")
