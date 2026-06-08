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
    if not tickers:
        return {}

    run_date = run_date or date.today()

    # Build conditions to match both 'HDFCBANK' and 'HDFCBANK.NS'
    symbol_conditions = " OR ".join(
        f"UPPER(symbol) IN ('{t.upper()}', '{t.upper()}.NS', '{t.upper()}.BO')"
        for t in tickers
    )

    query = f"""
        SELECT 
            symbol, date, open, high, low, close, volume, 
            average_volume, currency, fifty_two_week_high, fifty_two_week_low,
            delivery_qty, delivery_pct, total_traded_qty
        FROM {SNOWFLAKE['database']}.GOLD.STOCK_DAILY
        WHERE ({symbol_conditions})
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
            raw_symbol = d["symbol"]  # e.g. "HDFCBANK.NS"

            # Strip suffix so key matches holdings ticker e.g. "HDFCBANK"
            plain = raw_symbol.upper().replace(".NS", "").replace(".BO", "")

            if d.get("close") and d.get("open"):
                d["change_pct"] = round(
                    ((d["close"] - d["open"]) / d["open"]) * 100, 2
                )
            else:
                d["change_pct"] = 0.0

            d["symbol"] = plain
            result[plain] = d  # keyed by 'HDFCBANK' not 'HDFCBANK.NS'

        cur.close()
        conn.close()

        # ── Logs ─────────────────────────────────────────────
        logger.info("=" * 55)
        logger.info("[OHLCV] Fetch complete")
        logger.info(f"[OHLCV]   Requested : {tickers}")
        logger.info(f"[OHLCV]   Matched   : {list(result.keys())}")
        missing = [t for t in tickers if t.upper() not in result]
        if missing:
            logger.warning(f"[OHLCV]   No data for: {missing}")
        for sym, d in result.items():
            logger.info(
                f"[OHLCV]   {sym:<12} | close=₹{d['close']:<10.4f} | "
                f"open=₹{d['open']:<10.4f} | change={d['change_pct']:+.2f}%"
            )
        logger.info("=" * 55)
        return result
        

    except Exception as e:
        logger.error(f"[OHLCV] Failed to fetch: {e}")
        raise