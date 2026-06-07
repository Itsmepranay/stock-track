import json
import logging

from pydantic import BaseModel, Field
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
# Output schema
# ==========================================================

class SentimentResult(BaseModel):
    title: str = Field(description="Article title")
    sentiment: str = Field(description="BULLISH, BEARISH, or NEUTRAL")
    reason: str = Field(description="Short explanation")


class SentimentResponse(BaseModel):
    results: list[SentimentResult]


structured_llm = llm.with_structured_output(SentimentResponse)


# ==========================================================
# Prompt
# ==========================================================

prompt = ChatPromptTemplate.from_template(
    """
You are a professional financial analyst.

Classify each article as:

- BULLISH
- BEARISH
- NEUTRAL

For each article provide a short reason.

Articles:

{articles}
"""
)


# ==========================================================
# Retry wrapper
# ==========================================================

@retry(
    wait=wait_exponential(multiplier=2, min=5, max=60),
    stop=stop_after_attempt(5),
)
def _invoke_chain(text: str):
    chain = prompt | structured_llm
    return chain.invoke({"articles": text})


# ==========================================================
# Main function
# ==========================================================

def tag_all(articles: list[dict]) -> list[dict]:

    if not articles:
        return []

    article_text = []

    for idx, article in enumerate(articles):

        article_text.append(
            f"""
ARTICLE {idx}

Title:
{article.get("title","")}

Summary:
{article.get("summary","")[:400]}
"""
        )

    try:

        logger.info(
            f"Running batch sentiment analysis for {len(articles)} articles"
        )

        response = _invoke_chain("\n".join(article_text))

        sentiment_map = {
            item.title: item
            for item in response.results
        }

        for article in articles:

            result = sentiment_map.get(article["title"])

            if result:
                article["sentiment"] = result.sentiment
                article["sentiment_reason"] = result.reason
            else:
                article["sentiment"] = "NEUTRAL"
                article["sentiment_reason"] = ""

    except Exception as e:

        logger.warning(f"Batch sentiment failed: {e}")

        for article in articles:
            article["sentiment"] = "NEUTRAL"
            article["sentiment_reason"] = ""

    logger.info(
        f"Sentiment tagging complete ({len(articles)} articles)"
    )

    return articles