import feedparser
import urllib.request

sources = {
    "Moneycontrol": "https://www.moneycontrol.com/rss/marketsindia.xml",
    "Economic Times": "https://economictimes.indiatimes.com/markets/rss.cms",
    "Business Standard": "https://www.business-standard.com/rss/markets-106.rss",
    "LiveMint": "https://www.livemint.com/rss/markets",
}

for name, url in sources.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=10).read()
        print(f"\n{'='*50}")
        print(f"{name}")
        print(f"Status: OK | Size: {len(raw)} bytes")
        print(f"First 300 chars:\n{raw[:300]}")
    except Exception as e:
        print(f"{name} — FAILED: {e}")