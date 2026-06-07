import logging
from datetime import date

logger = logging.getLogger(__name__)


def build_context(
    holdings: list[dict],
    ohlcv: dict[str, dict],
    articles: list[dict],
    run_date: date = None,
) -> dict:
    """
    Assemble a structured context object passed to LLM chains.
    Returns:
    {
        "run_date": "YYYY-MM-DD",
        "holdings": [
            {
                "ticker": "RELIANCE",
                "company_name": "...",
                "qty": 10,
                "buy_price": 2500.0,
                "current_price": 2891.0,
                "change_pct": 1.2,
                "pnl": ...,
                "articles": [ {title, url, source_name, summary, published}, ... ]
            },
            ...
        ],
        "unmatched_articles": [...],   # relevant but not ticker-specific
        "total_articles_processed": N,
    }
    """
    run_date = run_date or date.today()

    # Group articles by matched ticker
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
    for h in holdings:
        ticker = h["ticker"].upper()
        price_data = ohlcv.get(ticker, {})
        current_price = price_data.get("close", h.get("buy_price", 0))
        buy_price = h.get("buy_price", 0)
        qty = h.get("qty", 0)
        pnl = round((current_price - buy_price) * qty, 2) if buy_price else 0
        pnl_pct = round(((current_price - buy_price) / buy_price) * 100, 2) if buy_price else 0

        holding_contexts.append({
            "ticker":          ticker,
            "company_name":    h.get("company_name", ticker),
            "sector":          h.get("sector", ""),
            "qty":             qty,
            "buy_price":       buy_price,
            "current_price":   current_price,
            "change_pct":      price_data.get("change_pct", 0),
            "pnl":             pnl,
            "pnl_pct":         pnl_pct,
            "articles":        ticker_articles.get(ticker, []),
        })

    context = {
        "run_date":                 str(run_date),
        "holdings":                 holding_contexts,
        "unmatched_articles":       unmatched,
        "total_articles_processed": len(articles),
    }

    logger.info(
        f"Context built: {len(holding_contexts)} holdings, "
        f"{sum(len(h['articles']) for h in holding_contexts)} ticker-matched articles, "
        f"{len(unmatched)} unmatched"
    )
    return context