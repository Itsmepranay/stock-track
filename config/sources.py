RSS_SOURCES = [
    {
        "name": "Moneycontrol Markets",
        "url": "https://www.moneycontrol.com/rss/marketsindia.xml",
        "industry_tags": ["banking", "it", "technology", "energy", "retail", "pharma", "auto", "fmcg"],
    },
    {
        "name": "Economic Times Markets",
        "url": "https://economictimes.indiatimes.com/markets/rss.cms",
        "industry_tags": ["banking", "it", "technology", "energy", "retail", "pharma", "auto", "fmcg"],
    },
    {
        "name": "LiveMint Markets",
        "url": "https://www.livemint.com/rss/markets",
        "industry_tags": ["banking", "it", "technology", "energy", "retail", "fmcg"],
    },
    {
        "name": "Business Standard Markets",
        "url": "https://www.business-standard.com/rss/markets-106.rss",
        "industry_tags": ["banking", "it", "technology", "energy", "auto", "pharma"],
    },
]

# Map each ticker to its industry tags and common name variants
# Add your actual holdings here
HOLDINGS_METADATA = {
    "RELIANCE": {
        "company_names": ["reliance", "ril", "jio", "reliance industries", "reliance retail"],
        "industry_tags": ["energy", "retail", "technology"],
    },
    "INFY": {
        "company_names": ["infosys", "infy"],
        "industry_tags": ["it", "technology"],
    },
    "TCS": {
        "company_names": ["tcs", "tata consultancy", "tata consultancy services"],
        "industry_tags": ["it", "technology"],
    },
    "HDFCBANK": {
        "company_names": ["hdfc bank", "hdfc", "hdfcbank"],
        "industry_tags": ["banking"],
    },
    "WIPRO": {
        "company_names": ["wipro"],
        "industry_tags": ["it", "technology"],
    },
    "ITC": {
        "company_names": ["itc", "itc ltd"],
        "industry_tags": ["fmcg"],
    },
}