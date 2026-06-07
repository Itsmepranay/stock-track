import logging

from tenacity import retry, wait_exponential, stop_after_attempt

from langchain_core.prompts import ChatPromptTemplate

from config.settings import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)


# ==========================================================
# LLM
# ==========================================================

from llm_factory import get_llm

llm = get_llm()

# ==========================================================
# Prompts
# ==========================================================

SUMMARY_PROMPT = ChatPromptTemplate.from_template(
    """
You are a senior equity analyst writing a daily portfolio brief.

Company: {company_name} ({ticker})
Sector: {sector}

Current price: ₹{current_price}
Daily move: {change_pct:+.2f}%

Portfolio P&L:
₹{pnl}
({pnl_pct:+.2f}%)

News Articles:

{articles_text}

Write:

1. What happened today
2. Whether news supports the move
3. Main risk/opportunity

Keep to 3-5 sentences.
"""
)

NO_NEWS_PROMPT = ChatPromptTemplate.from_template(
    """
You are a senior equity analyst.

No company-specific news was found today for
{company_name} ({ticker}).

Write one sentence explaining that the move
is likely driven by market or sector factors.

Today's move:
{change_pct:+.2f}%
"""
)


# ==========================================================
# Retry
# ==========================================================

@retry(
    wait=wait_exponential(multiplier=2, min=5, max=60),
    stop=stop_after_attempt(5),
)
def _invoke(prompt, variables):

    chain = prompt | llm

    return chain.invoke(variables)


# ==========================================================
# Helpers
# ==========================================================

def _format_articles(articles: list[dict]) -> str:

    if not articles:
        return "No relevant articles."

    rows = []

    for idx, article in enumerate(articles[:5], start=1):

        rows.append(
            f"""
{idx}.
Title: {article["title"]}

Sentiment:
{article.get("sentiment","NEUTRAL")}

Summary:
{article.get("summary","")[:250]}
"""
        )

    return "\n".join(rows)


# ==========================================================
# Holding Summary
# ==========================================================

def summarize_holding(holding: dict) -> dict:

    articles = holding.get("articles", [])

    try:

        if articles:
            logger.info(
                f"Generating summary for {holding['ticker']} with {len(articles)} articles"
            )
            response = _invoke(
                SUMMARY_PROMPT,
                {
                    "company_name": holding["company_name"],
                    "ticker": holding["ticker"],
                    "sector": holding.get("sector", "N/A"),
                    "current_price": holding["current_price"],
                    "change_pct": holding["change_pct"],
                    "pnl": holding["pnl"],
                    "pnl_pct": holding["pnl_pct"],
                    "articles_text": _format_articles(articles),
                },
            )

        else:

            response = _invoke(
                NO_NEWS_PROMPT,
                {
                    "company_name": holding["company_name"],
                    "ticker": holding["ticker"],
                    "change_pct": holding["change_pct"],
                },
            )

        holding["summary"] = response.content.strip()

    except Exception as e:

        logger.error(
            f"Summary generation failed for {holding['ticker']}: {e}"
        )

        holding["summary"] = (
            f"Summary unavailable for {holding['ticker']} today."
        )

    return holding


# ==========================================================
# Portfolio Summaries
# ==========================================================

def summarize_all(context: dict) -> dict:

    for holding in context["holdings"]:

        summarize_holding(holding)

        logger.info(
            f"Generated summary for {holding['ticker']}"
        )

    return context