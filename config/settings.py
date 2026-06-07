import os
from dotenv import load_dotenv

load_dotenv()

SNOWFLAKE = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
    "user":      os.getenv("SNOWFLAKE_USER"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD"),
    "database":  os.getenv("SNOWFLAKE_DATABASE"),
    "schema":    os.getenv("SNOWFLAKE_SCHEMA"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "role":      os.getenv("SNOWFLAKE_ROLE"),
}

GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
GMAIL_USER         = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
REPORT_RECIPIENT   = os.getenv("REPORT_RECIPIENT", GMAIL_USER)

# Snowflake table names
HOLDINGS_TABLE  = "PORTFOLIO_HOLDINGS"
OHLCV_TABLE     = "stock_daily"
SUMMARIES_TABLE = "PORTFOLIO_SUMMARIES"

# LLM
GEMINI_MODEL    = "gemini-2.5-flash"
MAX_ARTICLES_PER_RUN = 20   # cap to control token cost

import os

XAI_API_KEY = os.getenv("XAI_API_KEY")

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "grok-3-mini"
)