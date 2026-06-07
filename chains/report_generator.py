import logging
from langchain_core.prompts import ChatPromptTemplate
from llm_factory import get_llm

logger = logging.getLogger(__name__)

llm = get_llm()

REPORT_PROMPT = ChatPromptTemplate.from_template("""\
You are a senior equity analyst. Write a concise overall portfolio summary for {run_date}.

Portfolio holdings and their individual summaries:
{holdings_text}

Write 2-3 sentences covering:
1. Overall portfolio sentiment today (bullish / mixed / bearish)
2. The one or two most significant developments across the portfolio
3. Any sector-level theme emerging from today's news

Analyst tone, factual, no clichés. Do not list individual stocks — those appear separately below.
""")


def _format_holdings_for_report(holdings: list[dict]) -> str:
    lines = []
    for h in holdings:
        lines.append(
            f"- {h['ticker']} ({h['company_name']}): {h.get('summary', 'No summary')}"
        )
    return "\n".join(lines)


def _collect_citations(holdings: list[dict]) -> list[dict]:
    seen = set()
    citations = []
    for h in holdings:
        for a in h.get("articles", []):
            url = a.get("url", "")
            if url and url not in seen:
                citations.append({
                    "title":           a.get("title", ""),
                    "url":             url,
                    "source_name":     a.get("source_name", ""),
                    "sentiment":       a.get("sentiment", "NEUTRAL"),
                    "matched_tickers": h["ticker"],
                    "published":       a.get("published", ""),
                })
                seen.add(url)
    return citations


def _overall_sentiment(holdings: list[dict]) -> str:
    sentiments = []
    for h in holdings:
        for a in h.get("articles", []):
            s = a.get("sentiment", "NEUTRAL")
            if s:
                sentiments.append(s)
    if not sentiments:
        return "NEUTRAL"
    bullish = sentiments.count("BULLISH")
    bearish = sentiments.count("BEARISH")
    if bullish > bearish + 2:
        return "BULLISH"
    elif bearish > bullish + 2:
        return "BEARISH"
    return "MIXED"


def generate_report(context: dict) -> dict:
    holdings = context["holdings"]
    prompt_vars = {
        "run_date":     context["run_date"],
        "holdings_text": _format_holdings_for_report(holdings),
    }
    try:
        chain = REPORT_PROMPT | llm
        response = chain.invoke(prompt_vars)
        context["overall_summary"] = response.content.strip()
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        context["overall_summary"] = "Overall portfolio summary unavailable today."

    context["overall_sentiment"] = _overall_sentiment(holdings)
    context["citations"] = _collect_citations(holdings)

    logger.info(
        f"Report generated. Sentiment: {context['overall_sentiment']}. "
        f"Citations: {len(context['citations'])}"
    )
    return context