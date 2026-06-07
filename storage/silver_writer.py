import json
import logging
from datetime import date
import snowflake.connector
from config.settings import SNOWFLAKE, SUMMARIES_TABLE

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {SUMMARIES_TABLE} (
    run_date          DATE        NOT NULL,
    ticker            VARCHAR(20) NOT NULL,
    company_name      VARCHAR(100),
    current_price     FLOAT,
    change_pct        FLOAT,
    pnl               FLOAT,
    pnl_pct           FLOAT,
    sentiment         VARCHAR(10),
    summary_text      TEXT,
    article_urls      VARIANT,
    overall_summary   TEXT,
    overall_sentiment VARCHAR(10),
    created_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_date, ticker)
)
"""


def _get_connection():
    return snowflake.connector.connect(**SNOWFLAKE)


def ensure_table_exists():
    """Create the PORTFOLIO_SUMMARIES table if it doesn't exist."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(f"USE DATABASE {SNOWFLAKE['database']}")
        cur.execute(f"USE SCHEMA {SNOWFLAKE['schema']}")
        cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Table {SUMMARIES_TABLE} is ready")
    except Exception as e:
        logger.error(f"Failed to ensure table exists: {e}")
        raise


def write_summary(context: dict):
    """
    Write per-holding summaries and overall report to Snowflake silver table.
    Uses MERGE to upsert — safe to re-run if Prefect retries the task.
    """
    ensure_table_exists()
    run_date = context["run_date"]
    overall_summary = context.get("overall_summary", "")
    overall_sentiment = context.get("overall_sentiment", "NEUTRAL")
    holdings = context["holdings"]

    rows = []
    for h in holdings:
        article_urls = json.dumps([
            {"title": a["title"], "url": a["url"], "source": a["source_name"]}
            for a in h.get("articles", [])
        ])
        # Dominant sentiment for this holding
        sentiments = [a.get("sentiment", "NEUTRAL") for a in h.get("articles", [])]
        if sentiments:
            dominant = max(set(sentiments), key=sentiments.count)
        else:
            dominant = "NEUTRAL"

        rows.append((
            run_date,
            h["ticker"],
            h["company_name"],
            h["current_price"],
            h["change_pct"],
            h["pnl"],
            h["pnl_pct"],
            dominant,
            h.get("summary", ""),
            article_urls,
            overall_summary,
            overall_sentiment,
        ))

    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(f"USE DATABASE {SNOWFLAKE['database']}")
        cur.execute(f"USE SCHEMA {SNOWFLAKE['schema']}")

        merge_sql = f"""
            MERGE INTO {SUMMARIES_TABLE} AS target
            USING (SELECT %s AS run_date, %s AS ticker) AS source
                ON target.run_date = source.run_date AND target.ticker = source.ticker
            WHEN MATCHED THEN UPDATE SET
                company_name = %s, current_price = %s, change_pct = %s,
                pnl = %s, pnl_pct = %s, sentiment = %s, summary_text = %s,
                article_urls = PARSE_JSON(%s), overall_summary = %s,
                overall_sentiment = %s, created_at = CURRENT_TIMESTAMP
            WHEN NOT MATCHED THEN INSERT
                (run_date, ticker, company_name, current_price, change_pct,
                 pnl, pnl_pct, sentiment, summary_text, article_urls,
                 overall_summary, overall_sentiment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s), %s, %s)
        """
        for row in rows:
            (rd, tk, cn, cp, chg, pnl, pnl_pct, sent, summ, urls, ov_summ, ov_sent) = row
            cur.execute(merge_sql, (
                rd, tk,
                cn, cp, chg, pnl, pnl_pct, sent, summ, urls, ov_summ, ov_sent,
                rd, tk, cn, cp, chg, pnl, pnl_pct, sent, summ, urls, ov_summ, ov_sent,
            ))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Written {len(rows)} holding summaries to {SUMMARIES_TABLE}")
    except Exception as e:
        logger.error(f"Failed to write summaries to Snowflake: {e}")
        raise