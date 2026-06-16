import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="Portfolio News", page_icon="📊", layout="wide")

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

st.title("📊 Portfolio News")

df_portfolio = load_data("portfolio_news.json")

if not df_portfolio.empty:
    # Convert timestamp to datetime objects
    df_portfolio['timestamp'] = pd.to_datetime(df_portfolio['timestamp'])
    
    # 1. Date Range Filter
    st.subheader("Filter News")
    default_start = datetime.now().date() - timedelta(days=3)
    default_end = datetime.now().date()
    
    date_range = st.date_input(
        "Select Date Range",
        value=(default_start, default_end),
        max_value=datetime.now().date()
    )
    
    # Apply the filter based on user selection
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range[0]
        
    mask = (df_portfolio['timestamp'].dt.date >= start_date) & (df_portfolio['timestamp'].dt.date <= end_date)
    df_filtered = df_portfolio.loc[mask]

    if not df_filtered.empty:
        # 2. Quick Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Articles", len(df_filtered))
        col2.metric("Positive Sentiment", len(df_filtered[df_filtered['sentiment'] == 'Positive']))
        col3.metric("Negative Sentiment", len(df_filtered[df_filtered['sentiment'] == 'Negative']))

        # 3. Sentiment Bar Chart
        st.subheader("Sentiment by Ticker")
        sentiment_counts = df_filtered.groupby(['ticker', 'sentiment']).size().unstack(fill_value=0)
        
        # Ensure consistent column order so colors map exactly to the right sentiment
        expected_columns = ['Negative', 'Neutral', 'Positive']
        for col in expected_columns:
            if col not in sentiment_counts.columns:
                sentiment_counts[col] = 0
        sentiment_counts = sentiment_counts[expected_columns]
        
        # Apply colors: Negative=Red, Neutral=Blue, Positive=Green
        st.bar_chart(sentiment_counts, color=["#FF0000", "#0000FF", "#008000"])

        # 4. Interactive Data Table (with colored text)
        st.subheader("Recent Analysis Feed")
        
        # Filter columns first, then apply the style map to the 'sentiment' column
        display_df = df_filtered[['timestamp', 'ticker', 'sentiment', 'analysis', 'title']]
        styled_df = display_df.style.map(style_sentiment, subset=['sentiment'])
        
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.warning("No portfolio news found in the selected date range.")
else:
    st.warning("No portfolio news collected yet. Waiting for the JSON to populate...")
