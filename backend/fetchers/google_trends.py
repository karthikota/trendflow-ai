import hashlib
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from backend.fetchers.base import BaseFetcher
from backend.utils.logger import logger

class GoogleTrendsFetcher(BaseFetcher):
    """
    Google Trends Ingestion Engine.
    Fetches the daily trending searches RSS feed and parses detailed search metadata.
    """
    
    # Standard RSS feed for US Daily Trends (zero credentials needed)
    FEED_URL = "https://trends.google.com/trending/rss?geo=US"

    def __init__(self):
        super().__init__(source_name="google_trends")

    def fetch(self) -> Optional[str]:
        """
        Retrieves the raw Google Trends RSS XML feed.
        """
        return self.fetch_feed(self.FEED_URL)

    def parse(self, raw_content: str) -> List[Any]:
        """
        Parses Google Trends XML using BeautifulSoup with XML parsing logic.
        Extracts all '<item>' tags.
        """
        # Parse XML content using the high-performance 'xml' parser supported by bs4/lxml
        soup = BeautifulSoup(raw_content, "xml")
        items = soup.find_all("item")
        return items

    def normalize(self, raw_item: Any) -> Dict[str, Any]:
        """
        Maps a raw BeautifulSoup '<item>' tag into the common TrendFlow schema.
        Extracts custom Google Trends tags (namespace ht:) like search volume and news articles.
        """
        # Helper to find tag ending with a name (ignores XML namespace prefix issues)
        def find_ns_tag(element: Any, tag_suffix: str) -> Optional[Any]:
            return element.find(lambda tag: tag.name.endswith(tag_suffix))

        # Extract standard text tags
        title_tag = raw_item.find("title")
        title = title_tag.text.strip() if title_tag else ""
        
        link_tag = raw_item.find("link")
        url = link_tag.text.strip() if link_tag else None
        
        description_tag = raw_item.find("description")
        description = description_tag.text.strip() if description_tag else ""
        
        pub_date_tag = raw_item.find("pubDate")
        pub_date = pub_date_tag.text.strip() if pub_date_tag else ""

        # Extract Google custom namespace tags
        traffic_tag = find_ns_tag(raw_item, "approx_traffic")
        search_traffic = traffic_tag.text.strip() if traffic_tag else "Unknown"

        picture_tag = find_ns_tag(raw_item, "picture")
        picture_url = picture_tag.text.strip() if picture_tag else None

        # Extract associated news articles related to this trending search
        news_articles = []
        news_items = raw_item.find_all(lambda tag: tag.name.endswith("news_item"))
        for news in news_items:
            news_title = find_ns_tag(news, "news_item_title")
            news_url = find_ns_tag(news, "news_item_url")
            news_source = find_ns_tag(news, "news_item_source")
            news_snippet = find_ns_tag(news, "news_item_snippet")

            if news_title:
                news_articles.append({
                    "title": news_title.text.strip(),
                    "url": news_url.text.strip() if news_url else "",
                    "source": news_source.text.strip() if news_source else "Unknown",
                    "snippet": news_snippet.text.strip() if news_snippet else ""
                })

        # Assemble full original metadata for future reference / AI ingestion
        raw_metadata = {
            "title": title,
            "description": description,
            "pub_date": pub_date,
            "search_traffic": search_traffic,
            "picture_url": picture_url,
            "news_articles": news_articles,
            "original_url": url
        }

        # Create a stable unique external ID based on the lowercased search query
        # Hash is used to prevent duplicate trend entries if the feed is polled repeatedly
        clean_title = title.lower().strip()
        hash_digest = hashlib.md5(clean_title.encode("utf-8")).hexdigest()
        external_id = f"google_trends_{hash_digest}"

        return {
            "title": title,
            "source": "google_trends",
            "url": url,
            "external_id": external_id,
            "raw_data": raw_metadata
        }
