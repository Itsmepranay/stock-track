import json
import streamlit as st
import snowflake.connector
import pandas as pd

st.set_page_config(
    page_title="Portfolio Intelligence",
    page_icon="📊",
    layout="wide",
)

SENTIMENT_COLOR = {
    "BULLISH": "#1D9E75",
    "BEARISH": "#E24B4A",
    "MIXED":   "#BA7517",
    "NEUTRAL": "#888780",
}


def _run_query(query: str) -> pd.DataFrame:
    """Run a query using native snowflake cursor, return DataFrame. No SQLAlchemy needed."""
    creds = st.secrets["snowflake"]
    conn  = snowflake.connector.connect(**creds)
    cur   = conn.cursor()
    cur.execute(query)
    rows  = cur.fetchall()
    cols  = [desc[0].upper() for desc in cur.description]
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=cols)


@st.cache_data(ttl=300)
def load_summaries(run_date: str) -> pd.DataFrame:
    df = _run_query(f"""
        SELECT
            s.ticker,
            s.company_name,
            s.current_price,
            s.change_pct,
            s.pnl,
            s.pnl_pct,
            s.sentiment,
            s.summary_text,
            s.article_urls,
            s.overall_summary,
            s.overall_sentiment,
            h.buy_price,
            h.qty,
            ROUND(h.buy_price * h.qty, 2)     AS invested_value,
            ROUND(s.current_price * h.qty, 2) AS current_value
        FROM PORTFOLIO_SUMMARIES s
        LEFT JOIN PORTFOLIO_HOLDINGS h
            ON  s.ticker    = h.ticker
            AND h.is_active = TRUE
        WHERE s.run_date = '{run_date}'
        ORDER BY s.ticker
    """)

    # Fill NaN safely
    df["BUY_PRICE"]      = pd.to_numeric(df["BUY_PRICE"],      errors="coerce").fillna(0)
    df["QTY"]            = pd.to_numeric(df["QTY"],            errors="coerce").fillna(0).astype(int)
    df["INVESTED_VALUE"] = pd.to_numeric(df["INVESTED_VALUE"], errors="coerce").fillna(0)
    df["CURRENT_VALUE"]  = pd.to_numeric(df["CURRENT_VALUE"],  errors="coerce").fillna(0)
    df["PNL"]            = pd.to_numeric(df["PNL"],            errors="coerce").fillna(0)
    df["PNL_PCT"]        = pd.to_numeric(df["PNL_PCT"],        errors="coerce").fillna(0)
    df["CHANGE_PCT"]     = pd.to_numeric(df["CHANGE_PCT"],     errors="coerce").fillna(0)
    df["CURRENT_PRICE"]  = pd.to_numeric(df["CURRENT_PRICE"],  errors="coerce").fillna(0)

    return df


@st.cache_data(ttl=300)
def load_available_dates() -> list[str]:
    df = _run_query(
        "SELECT DISTINCT run_date FROM PORTFOLIO_SUMMARIES ORDER BY run_date DESC LIMIT 30"
    )
    return df["RUN_DATE"].astype(str).tolist()


def sentiment_badge(sentiment: str) -> str:
    color = SENTIMENT_COLOR.get(sentiment, "#888780")
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
        f'font-size:12px;font-weight:600;background:{color}20;color:{color};'
        f'border:1px solid {color}40">{sentiment}</span>'
    )


def arrow(val: float) -> str:
    return "▲" if val >= 0 else "▼"


def main():
    st.markdown("## 📊 Portfolio Intelligence")

    available_dates = load_available_dates()
    if not available_dates:
        st.warning("No data found. Run the pipeline first.")
        return

    selected_date = st.selectbox("Report date", options=available_dates, index=0)
    df = load_summaries(selected_date)
    if df.empty:
        st.warning(f"No data for {selected_date}")
        return

    overall_summary   = df["OVERALL_SUMMARY"].iloc[0]
    overall_sentiment = df["OVERALL_SENTIMENT"].iloc[0]

    # ── Portfolio level totals ────────────────────────────────
    total_invested = df["INVESTED_VALUE"].sum()
    total_current  = df["CURRENT_VALUE"].sum()
    total_pnl      = df["PNL"].sum()
    total_pnl_pct  = round(((total_current - total_invested) / total_invested) * 100, 2) if total_invested else 0
    n_bullish      = (df["SENTIMENT"] == "BULLISH").sum()
    n_bearish      = (df["SENTIMENT"] == "BEARISH").sum()

    st.divider()

    # ── Top level portfolio cards ─────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Invested", f"₹{total_invested:,.0f}")
    with c2:
        st.metric("Current Value", f"₹{total_current:,.0f}")
    with c3:
        st.metric(
            "Total P&L",
            f"{arrow(total_pnl)} ₹{abs(total_pnl):,.0f}",
            delta=f"{total_pnl_pct:+.2f}%",
        )
    with c4:
        st.metric("Bullish", int(n_bullish))
    with c5:
        st.metric("Bearish", int(n_bearish))

    st.divider()

    # ── Overall sentiment + AI summary ────────────────────────
    st.markdown(
        f"{sentiment_badge(overall_sentiment)}"
        f'<p style="margin-top:10px;font-size:14px;line-height:1.7;color:#333">'
        f"{overall_summary}</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Per holding cards ─────────────────────────────────────
    st.markdown("### Holdings")

    for _, row in df.iterrows():
        pnl          = row["PNL"]
        pnl_pct      = row["PNL_PCT"]
        chg          = row["CHANGE_PCT"]
        buy_price    = row["BUY_PRICE"]
        qty          = row["QTY"]
        invested_val = row["INVESTED_VALUE"]
        current_val  = row["CURRENT_VALUE"]
        pnl_color    = "#1D9E75" if pnl >= 0 else "#E24B4A"
        chg_color    = "#1D9E75" if chg >= 0 else "#E24B4A"

        with st.container(border=True):
            col1, col2, col3, col4, _ = st.columns([2, 2, 2, 2, 1])

            with col1:
                st.markdown(f"**{row['TICKER']}**")
                st.caption(row["COMPANY_NAME"])
                st.caption(f"{qty} shares @ ₹{buy_price:,.2f}")

            with col2:
                st.markdown(f"**Current: ₹{row['CURRENT_PRICE']:,.2f}**")
                st.markdown(
                    f'<span style="color:{chg_color};font-size:13px">'
                    f'{arrow(chg)} {abs(chg):.2f}% today</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="font-size:12px;color:#777;margin-top:6px">'
                    f'Invested: <b>₹{invested_val:,.0f}</b><br>'
                    f'Current Value: <b>₹{current_val:,.0f}</b></div>',
                    unsafe_allow_html=True,
                )

            with col3:
                st.markdown(
                    f'<div style="font-size:12px;color:#777">Overall P&L</div>'
                    f'<div style="font-size:22px;font-weight:700;color:{pnl_color}">'
                    f'{arrow(pnl)} ₹{abs(pnl):,.0f}</div>'
                    f'<div style="font-size:13px;color:{pnl_color}">{pnl_pct:+.2f}%</div>',
                    unsafe_allow_html=True,
                )

            with col4:
                st.markdown(sentiment_badge(row["SENTIMENT"]), unsafe_allow_html=True)

            if row["SUMMARY_TEXT"]:
                st.caption(row["SUMMARY_TEXT"])

    st.divider()

    # ── News feed ─────────────────────────────────────────────
    st.markdown("### News")
    all_articles = []
    for _, row in df.iterrows():
        try:
            urls = json.loads(row["ARTICLE_URLS"]) if row["ARTICLE_URLS"] else []
            for a in urls:
                a["ticker"]    = row["TICKER"]
                a["sentiment"] = row["SENTIMENT"]
                all_articles.append(a)
        except Exception:
            pass

    if not all_articles:
        st.info("No news articles for this date.")
    else:
        cols = st.columns(2)
        for i, article in enumerate(all_articles[:12]):
            s         = article.get("sentiment", "NEUTRAL")
            dot_color = SENTIMENT_COLOR.get(s, "#888780")
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(
                        f'<span style="width:8px;height:8px;border-radius:50%;'
                        f'background:{dot_color};display:inline-block;margin-right:6px"></span>'
                        f'<span style="font-size:11px;color:#999">'
                        f'{article.get("source","")} — #{article.get("ticker","")}</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{article.get('title','')}**")
                    st.markdown(
                        f'<a href="{article.get("url","")}" target="_blank"'
                        f' style="font-size:12px;color:#378ADD">Read →</a>',
                        unsafe_allow_html=True,
                    )


if __name__ == "__main__":
    main()