import logging
import sys
import os
from datetime import date
from typing import Optional

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prefect import flow, task, get_run_logger

from ingestion.snowflake_reader import get_holdings, get_ohlcv
from ingestion.rss_fetcher import fetch_all_feeds
from agents.filter_agent import filter_articles
from agents.context_builder import build_context
from chains.sentiment import tag_all
from chains.summarizer import summarize_all
from chains.report_generator import generate_report
from storage.silver_writer import write_summary
from delivery.email_sender import send_report


@task(name="fetch-holdings", retries=2, retry_delay_seconds=10)
def task_fetch_holdings():
    logger = get_run_logger()
    holdings = get_holdings()
    logger.info(f"Holdings fetched: {[h['ticker'] for h in holdings]}")
    return holdings


@task(name="fetch-ohlcv", retries=2, retry_delay_seconds=10)
def task_fetch_ohlcv(holdings: list[dict], run_date: date):
    tickers = [h["ticker"] for h in holdings]
    return get_ohlcv(tickers, run_date)


@task(name="fetch-rss-feeds", retries=1)
def task_fetch_feeds():
    logger = get_run_logger()
    articles = fetch_all_feeds()
    logger.info(f"Raw articles fetched: {len(articles)}")
    return articles


@task(name="filter-news")
def task_filter(articles: list[dict], holdings: list[dict]):
    logger = get_run_logger()
    filtered = filter_articles(articles, holdings)
    logger.info(f"Filtered articles: {len(filtered)}")
    return filtered


@task(name="build-context")
def task_build_context(holdings, ohlcv, articles, run_date):
    return build_context(holdings, ohlcv, articles, run_date)


@task(name="tag-sentiment")
def task_sentiment(context: dict):
    all_articles = []
    for h in context["holdings"]:
        all_articles.extend(h.get("articles", []))
    tag_all(all_articles)
    return context


@task(name="summarize-holdings")
def task_summarize(context: dict):
    return summarize_all(context)


@task(name="generate-report")
def task_report(context: dict):
    return generate_report(context)


@task(name="write-to-snowflake", retries=2, retry_delay_seconds=15)
def task_write_silver(context: dict):
    write_summary(context)


@task(name="send-email", retries=2, retry_delay_seconds=20)
def task_send_email(context: dict):
    send_report(context)


@flow(name="portfolio-intelligence-daily", log_prints=True)
def daily_flow(run_date: Optional[date] = None):
    """
    Main daily orchestration flow.
    Run manually: python flows/daily_flow.py
    Or schedule via Prefect deployment.
    """
    run_date = run_date if run_date is not None else date.today()
    logger = get_run_logger()
    logger.info(f"Starting portfolio intelligence pipeline for {run_date}")

    holdings = task_fetch_holdings()
    ohlcv    = task_fetch_ohlcv(holdings, run_date)
    articles = task_fetch_feeds()
    filtered = task_filter(articles, holdings)
    context  = task_build_context(holdings, ohlcv, filtered, run_date)
    context  = task_sentiment(context)
    context  = task_summarize(context)
    context  = task_report(context)
    task_write_silver(context)
    task_send_email(context)

    logger.info(
        f"Pipeline complete. "
        f"Overall sentiment: {context.get('overall_sentiment')}. "
        f"Citations: {len(context.get('citations', []))}"
    )
    return context


if __name__ == "__main__":
    daily_flow()