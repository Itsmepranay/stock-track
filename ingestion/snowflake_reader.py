import logging
from datetime import date
from typing import Optional
import snowflake.connector
from config.settings import SNOWFLAKE, HOLDINGS_TABLE, OHLCV_TABLE

logger = logging.getLogger(__name__)


def _get_connection():
    return snowflake.connector.connect(**SNOWFLAKE)


def get_holdings() -> list[dict]:
    """
    Pull portfolio holdings from Snowflake.
    Expected table schema:
        ticker VARCHAR, company_name VARCHAR, qty NUMBER,
        buy_price FLOAT, sector VARCHAR
    Returns list of dicts.
    """
    query = f"""
        SELECT ticker, company_name, qty, buy_price, sector
        FROM {SNOWFLAKE['database']}.{SNOWFLAKE['schema']}.{HOLDINGS_TABLE}
        WHERE is_active = TRUE
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cols = [desc[0].lower() for desc in cur.description]
        holdings = [dict(zip(cols, row)) for row in rows]
        cur.close()
        conn.close()
        logger.info(f"Fetched {len(holdings)} holdings from Snowflake")
        return holdings
    except Exception as e:
        logger.error(f"Failed to fetch holdings: {e}")
        raise


def get_ohlcv(tickers: list[str], run_date: Optional[date] = None) -> dict[str, dict]:
    """
    Pull latest OHLCV data for given tickers from STOCK_DAILY table.
    Expected table schema (STOCK_DAILY in GOLD schema):
        symbol VARCHAR, date DATE, open FLOAT, high FLOAT,
        low FLOAT, close FLOAT, volume NUMBER, average_volume NUMBER,
        currency VARCHAR, fifty_two_week_high FLOAT, fifty_two_week_low FLOAT,
        delivery_qty NUMBER, delivery_pct FLOAT, total_traded_qty NUMBER
    Returns dict keyed by symbol.
    """
    if not tickers:
        return {}

    run_date = run_date or date.today()
    symbol_list = ", ".join(f"'{t.upper()}'" for t in tickers)

    query = f"""
        SELECT 
            symbol, date, open, high, low, close, volume, 
            average_volume, currency, fifty_two_week_high, fifty_two_week_low,
            delivery_qty, delivery_pct, total_traded_qty
        FROM {SNOWFLAKE['database']}.GOLD.STOCK_DAILY
        WHERE symbol IN ({symbol_list})
          AND date = (
              SELECT MAX(date)
              FROM {SNOWFLAKE['database']}.GOLD.STOCK_DAILY
              WHERE date <= '{run_date}'
          )
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cols = [desc[0].lower() for desc in cur.description]
        result = {}
        for row in rows:
            d = dict(zip(cols, row))
            symbol = d["symbol"]
            # Calculate price change percentage if close and fifty_two_week_low available
            if d.get("close") and d.get("open"):
                d["change_pct"] = round(
                    ((d["close"] - d["open"]) / d["open"]) * 100, 2
                )
            else:
                d["change_pct"] = 0.0
            result[symbol] = d
        cur.close()
        conn.close()
        logger.info(f"Fetched OHLCV for {list(result.keys())}")
        return result
    except Exception as e:
        logger.error(f"Failed to fetch OHLCV: {e}")
        raise