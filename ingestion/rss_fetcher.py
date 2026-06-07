import logging
import time
from datetime import datetime, timezone
from typing import Optional
import feedparser
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.sources import RSS_SOURCES

logger = logging.getLogger(__name__)


def _parse_published(entry) -> str:
    """Extract published date from feed entry, fallback to now."""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def _fetch_with_retry(url: str, source_name: str, max_attempts: int = 3) -> list[dict]:
    """
    Fetch a single RSS feed with exponential backoff retry.
    Returns empty list (never raises) — pipeline must not die on one bad source.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                raise ValueError(f"Feed parse error: {feed.bozo_exception}")
            articles = []
            for entry in feed.entries:
                articles.append({
                    "title":       getattr(entry, "title", "").strip(),
                    "url":         getattr(entry, "link", ""),
                    "published":   _parse_published(entry),
                    "source_name": source_name,
                    "summary":     getattr(entry, "summary", "").strip(),
                    "matched_tickers": [],
                    "sentiment":   None,
                })
            logger.info(f"[{source_name}] Fetched {len(articles)} articles (attempt {attempt})")
            return articles
        except Exception as e:
            logger.warning(f"[{source_name}] Attempt {attempt}/{max_attempts} failed: {e}")
            if attempt < max_attempts:
                time.sleep(2 ** attempt)

    logger.error(f"[{source_name}] All {max_attempts} attempts failed — skipping source")
    return []


def fetch_all_feeds(sources: Optional[list[dict]] = None) -> list[dict]:
    """
    Fetch all configured RSS sources.
    Returns flat list of article dicts, deduplicated by URL.
    """
    sources = sources or RSS_SOURCES
    all_articles = []
    seen_urls = set()

    for source in sources:
        articles = _fetch_with_retry(source["url"], source["name"])
        for article in articles:
            if article["url"] and article["url"] not in seen_urls:
                article["source_industry_tags"] = source.get("industry_tags", [])
                all_articles.append(article)
                seen_urls.add(article["url"])

    logger.info(f"Total unique articles fetched: {len(all_articles)}")
    return all_articles