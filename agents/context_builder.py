import logging
from datetime import date

logger = logging.getLogger(__name__)


def build_context(
    holdings: list[dict],
    ohlcv: dict[str, dict],
    articles: list[dict],
    run_date: date = None,
) -> dict:

    run_date = run_date or date.today()

    ticker_articles: dict[str, list[dict]] = {h["ticker"]: [] for h in holdings}
    unmatched = []

    for article in articles:
        placed = False
        for ticker in article.get("matched_tickers", []):
            if ticker in ticker_articles:
                ticker_articles[ticker].append(article)
                placed = True
        if not placed:
            unmatched.append(article)

    holding_contexts = []
    total_invested  = 0
    total_current   = 0

    for h in holdings:
        ticker        = h["ticker"].upper()
        price_data    = ohlcv.get(ticker, {})
        current_price = price_data.get("close", h.get("buy_price", 0))
        buy_price     = h.get("buy_price", 0)
        qty           = h.get("qty", 0)

        invested_value = round(buy_price * qty, 2)
        current_value  = round(current_price * qty, 2)
        pnl            = round(current_value - invested_value, 2)
        pnl_pct        = round(((current_price - buy_price) / buy_price) * 100, 2) if buy_price else 0

        # Day change (close vs open)
        open_price  = price_data.get("open", current_price)
        day_change  = round(current_price - open_price, 2)
        day_change_pct = round(((current_price - open_price) / open_price) * 100, 2) if open_price else 0

        total_invested += invested_value
        total_current  += current_value

        holding_contexts.append({
            "ticker":          ticker,
            "company_name":    h.get("company_name", ticker),
            "sector":          h.get("sector", ""),
            "qty":             qty,
            "buy_price":       buy_price,
            "current_price":   current_price,
            "open_price":      open_price,
            "day_change":      day_change,
            "day_change_pct":  day_change_pct,
            "invested_value":  invested_value,
            "current_value":   current_value,
            "pnl":             pnl,
            "pnl_pct":         pnl_pct,
            "change_pct":      price_data.get("change_pct", 0),
            "fifty_two_week_high": price_data.get("fifty_two_week_high", 0),
            "fifty_two_week_low":  price_data.get("fifty_two_week_low", 0),
            "volume":          price_data.get("volume", 0),
            "articles":        ticker_articles.get(ticker, []),
        })

    total_pnl     = round(total_current - total_invested, 2)
    total_pnl_pct = round(((total_current - total_invested) / total_invested) * 100, 2) if total_invested else 0

    context = {
        "run_date":                 str(run_date),
        "holdings":                 holding_contexts,
        "portfolio_summary": {
            "total_invested":  total_invested,
            "total_current":   total_current,
            "total_pnl":       total_pnl,
            "total_pnl_pct":   total_pnl_pct,
        },
        "unmatched_articles":       unmatched,
        "total_articles_processed": len(articles),
    }

    logger.info(
        f"[CONTEXT] Built context for {len(holding_contexts)} holdings | "
        f"Invested: ₹{total_invested:,.0f} | "
        f"Current: ₹{total_current:,.0f} | "
        f"P&L: ₹{total_pnl:,.0f} ({total_pnl_pct:+.2f}%)"
    )
    return context