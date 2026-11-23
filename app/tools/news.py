import urllib.parse

import feedparser
import httpx


def search_news(query: str, max_items: int = 5) -> list[dict]:
    """Search Google News RSS and return headlines with links and dates."""
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )
    response = httpx.get(url, timeout=10, follow_redirects=True)
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    return [
        {"title": entry.title, "link": entry.link, "published": entry.get("published", "")}
        for entry in feed.entries[:max_items]
    ]
