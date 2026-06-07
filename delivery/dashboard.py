import json
from datetime import date, timedelta
import streamlit as st
import snowflake.connector
import pandas as pd

st.set_page_config(
    page_title="Portfolio intelligence",
    page_icon="📊",
    layout="wide",
)

SENTIMENT_COLOR = {
    "BULLISH": "green",
    "BEARISH": "red",
    "MIXED":   "orange",
    "NEUTRAL": "gray",
}

SENTIMENT_EMOJI = {
    "BULLISH": "▲",
    "BEARISH": "▼",
    "MIXED":   "~",
    "NEUTRAL": "—",
}


@st.cache_resource
def get_connection():
    return snowflake.connector.connect(**st.secrets["snowflake"])


@st.cache_data(ttl=300)
def load_latest_summaries(run_date: str) -> pd.DataFrame:
    conn = get_connection()
    query = f"""
        SELECT ticker, company_name, current_price, change_pct, pnl, pnl_pct,
               sentiment, summary_text, article_urls, overall_summary, overall_sentiment
        FROM PORTFOLIO_SUMMARIES
        WHERE run_date = '{run_date}'
        ORDER BY ticker
    """
    return pd.read_sql(query, conn)


@st.cache_data(ttl=300)
def load_available_dates() -> list[str]:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT DISTINCT run_date FROM PORTFOLIO_SUMMARIES ORDER BY run_date DESC LIMIT 30",
        conn,
    )
    return df["RUN_DATE"].astype(str).tolist()


def sentiment_badge(sentiment: str) -> str:
    color = {"BULLISH": "#1D9E75", "BEARISH": "#E24B4A",
             "MIXED": "#BA7517", "NEUTRAL": "#888780"}.get(sentiment, "#888780")
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
        f'font-size:12px;font-weight:600;background:{color}20;color:{color};'
        f'border:1px solid {color}40">{sentiment}</span>'
    )


def main():
    st.markdown(
        '<h1 style="font-size:24px;font-weight:600;margin-bottom:4px">Portfolio intelligence</h1>',
        unsafe_allow_html=True,
    )

    # Date selector
    available_dates = load_available_dates()
    if not available_dates:
        st.warning("No data found. Run the pipeline first.")
        return

    selected_date = st.selectbox(
        "Report date",
        options=available_dates,
        index=0,
        label_visibility="collapsed",
    )

    df = load_latest_summaries(selected_date)
    if df.empty:
        st.warning(f"No data for {selected_date}")
        return

    overall_summary   = df["OVERALL_SUMMARY"].iloc[0]
    overall_sentiment = df["OVERALL_SENTIMENT"].iloc[0]

    # Stat cards
    total_pnl     = df["PNL"].sum()
    n_bullish     = (df["SENTIMENT"] == "BULLISH").sum()
    n_bearish     = (df["SENTIMENT"] == "BEARISH").sum()
    n_holdings    = len(df)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total P&L", f"₹{total_pnl:,.0f}")
    with col2:
        st.metric("Holdings", n_holdings)
    with col3:
        st.metric("Bullish signals", n_bullish)
    with col4:
        st.metric("Bearish signals", n_bearish)

    st.divider()

    # Two-column layout: holdings + summary
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("#### Holdings")
        for _, row in df.iterrows():
            chg_color = "green" if row["CHANGE_PCT"] >= 0 else "red"
            pnl_color = "green" if row["PNL"] >= 0 else "red"
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(f"**{row['TICKER']}**  \n{row['COMPANY_NAME']}")
                with c2:
                    st.markdown(
                        f"₹{row['CURRENT_PRICE']:,.2f} "
                        f"<span style='color:{chg_color}'>{row['CHANGE_PCT']:+.2f}%</span>  \n"
                        f"P&L: <span style='color:{pnl_color}'>₹{row['PNL']:,.0f}</span>",
                        unsafe_allow_html=True,
                    )
                with c3:
                    st.markdown(
                        sentiment_badge(row["SENTIMENT"]),
                        unsafe_allow_html=True,
                    )
                if row["SUMMARY_TEXT"]:
                    st.caption(row["SUMMARY_TEXT"])

    with right:
        st.markdown("#### AI summary")
        st.markdown(
            f'{sentiment_badge(overall_sentiment)}'
            f'<p style="margin-top:12px;font-size:14px;line-height:1.7">{overall_summary}</p>',
            unsafe_allow_html=True,
        )

        # Citations
        st.markdown("**Sources**")
        for _, row in df.iterrows():
            try:
                urls = json.loads(row["ARTICLE_URLS"]) if row["ARTICLE_URLS"] else []
            except Exception:
                urls = []
            for article in urls:
                s = row["SENTIMENT"]
                color = {"BULLISH":"#1D9E75","BEARISH":"#E24B4A",
                         "MIXED":"#BA7517","NEUTRAL":"#888780"}.get(s,"#888780")
                st.markdown(
                    f'<a href="{article["url"]}" target="_blank" style="display:inline-block;'
                    f'margin:3px 4px 3px 0;padding:3px 10px;border-radius:20px;font-size:11px;'
                    f'text-decoration:none;background:{color}15;color:{color};'
                    f'border:1px solid {color}30">'
                    f'{article["source"]} — {article["title"][:45]}...</a>',
                    unsafe_allow_html=True,
                )

    st.divider()

    # Live news feed
    st.markdown("#### Live news feed")
    all_articles = []
    for _, row in df.iterrows():
        try:
            urls = json.loads(row["ARTICLE_URLS"]) if row["ARTICLE_URLS"] else []
            for a in urls:
                a["ticker"] = row["TICKER"]
                a["sentiment"] = row["SENTIMENT"]
                all_articles.append(a)
        except Exception:
            pass

    if not all_articles:
        st.info("No news articles found for this date.")
    else:
        cols = st.columns(2)
        for i, article in enumerate(all_articles[:12]):
            s = article.get("sentiment", "NEUTRAL")
            dot_color = {"BULLISH":"#1D9E75","BEARISH":"#E24B4A",
                         "NEUTRAL":"#888780","MIXED":"#BA7517"}.get(s,"#888780")
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(
                        f'<span style="width:8px;height:8px;border-radius:50%;'
                        f'background:{dot_color};display:inline-block;margin-right:6px"></span>'
                        f'<span style="font-size:11px;color:#999">{article.get("source","")}</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{article.get('title','')}**")
                    tc1, tc2 = st.columns([1, 1])
                    with tc1:
                        st.caption(f"#{article.get('ticker','')}")
                    with tc2:
                        st.markdown(
                            f'<a href="{article.get("url","")}" target="_blank" '
                            f'style="font-size:12px;color:#378ADD">Read →</a>',
                            unsafe_allow_html=True,
                        )


if __name__ == "__main__":
    main()