import logging
from config.sources import HOLDINGS_METADATA
from config.settings import MAX_ARTICLES_PER_RUN

logger = logging.getLogger(__name__)


def _build_keyword_map(holdings: list[dict]) -> dict[str, list[str]]:
    """
    Build a map of ticker -> list of lowercase keywords to match against article text.
    Uses HOLDINGS_METADATA for company name variants; falls back to ticker + company_name from DB.
    """
    keyword_map = {}
    for h in holdings:
        ticker = h["ticker"].upper()
        meta = HOLDINGS_METADATA.get(ticker, {})
        keywords = list(meta.get("company_names", []))

        # Always include the ticker itself and DB company name
        keywords.append(ticker.lower())
        if h.get("company_name"):
            keywords.append(h["company_name"].lower())

        keyword_map[ticker] = list(set(keywords))
    return keyword_map


def _get_holding_industry_tags(ticker: str) -> set[str]:
    meta = HOLDINGS_METADATA.get(ticker.upper(), {})
    return set(meta.get("industry_tags", []))


def filter_articles(articles: list[dict], holdings: list[dict]) -> list[dict]:
    """
    Two-pass filter:
    Pass 1 — ticker/company keyword match in title or summary.
    Pass 2 — industry tag overlap between article source tags and holding tags.
    An article passes if it matches either pass for at least one holding.
    Returns articles sorted by relevance (keyword matches first), capped at MAX_ARTICLES_PER_RUN.
    """
    keyword_map = _build_keyword_map(holdings)
    all_holding_industry_tags = set()
    for h in holdings:
        all_holding_industry_tags |= _get_holding_industry_tags(h["ticker"])

    filtered = []
    for article in articles:
        search_text = (article["title"] + " " + article["summary"]).lower()
        article_source_tags = set(article.get("source_industry_tags", []))
        matched_tickers = []
        match_type = None

        # Pass 1: keyword match
        for ticker, keywords in keyword_map.items():
            if any(kw in search_text for kw in keywords):
                matched_tickers.append(ticker)
                match_type = "keyword"

        # Pass 2: industry tag match (only if no keyword match)
        if not matched_tickers:
            overlap = article_source_tags & all_holding_industry_tags
            if overlap:
                matched_tickers = [h["ticker"] for h in holdings
                                   if _get_holding_industry_tags(h["ticker"]) & overlap]
                match_type = "industry"

        if matched_tickers:
            article["matched_tickers"] = list(set(matched_tickers))
            article["match_type"] = match_type
            filtered.append(article)

    # Sort: keyword matches first, then industry matches; most recent within each group
    filtered.sort(key=lambda a: (
        0 if a.get("match_type") == "keyword" else 1,
        a.get("published", ""),
    ), reverse=False)
    filtered.sort(key=lambda a: a.get("match_type") == "keyword", reverse=True)

    logger.info(
        f"Filter: {len(articles)} in -> {len(filtered)} relevant "
        f"(keyword: {sum(1 for a in filtered if a.get('match_type')=='keyword')}, "
        f"industry: {sum(1 for a in filtered if a.get('match_type')=='industry')}) "
        f"-> capped at {MAX_ARTICLES_PER_RUN}"
    )
    return filtered[:MAX_ARTICLES_PER_RUN]