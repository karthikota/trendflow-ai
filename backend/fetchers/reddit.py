import hashlib
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from backend.config import settings
from backend.fetchers.base import BaseFetcher
from backend.utils.logger import logger
from backend.db.repository import TrendRepository

class RedditFetcher(BaseFetcher):
    """
    Reddit Ingestion Engine.
    Uses public Atom/RSS feeds of subreddits to fetch hot discussions
    without needing any developer registrations or API credentials.
    """

    def __init__(self):
        super().__init__(source_name="reddit")

    def fetch(self) -> Optional[str]:
        """
        Base fetch method. For Reddit, we override run() to support multiple
        subreddits, but keep this method as a fallback for single feeds.
        """
        if settings.REDDIT_SUBREDDITS:
            return self.fetch_subreddit_feed(settings.REDDIT_SUBREDDITS[0])
        return None

    def fetch_subreddit_feed(self, subreddit: str) -> Optional[str]:
        """
        Retrieves the raw Atom XML feed for a specific subreddit's hot threads.
        """
        url = f"https://www.reddit.com/r/{subreddit}/hot/.rss?limit=15"
        return self.fetch_feed(url)

    def parse(self, raw_content: str) -> List[Any]:
        """
        Parses the Reddit Atom feed.
        Reddit RSS feeds are Atom standard, which represent items as '<entry>' tags.
        """
        soup = BeautifulSoup(raw_content, "xml")
        entries = soup.find_all("entry")
        return entries

    def normalize(self, raw_item: Any) -> Dict[str, Any]:
        """
        Maps a raw Atom '<entry>' tag into the common TrendFlow schema.
        Extracts title, comment link, author, and timestamp.
        """
        # Extract title
        title_tag = raw_item.find("title")
        title = title_tag.text.strip() if title_tag else "Untitled Post"

        # Extract post URL (Atom links use the href attribute)
        # Typically there are multiple links, we want the primary thread link
        link_tag = raw_item.find("link")
        url = link_tag.get("href") if link_tag else None

        # Extract author name
        author_tag = raw_item.find("author")
        author = "Unknown"
        if author_tag:
            name_tag = author_tag.find("name")
            if name_tag:
                author = name_tag.text.strip()

        # Extract timestamp
        updated_tag = raw_item.find("updated")
        timestamp = updated_tag.text.strip() if updated_tag else ""

        # Extract subreddit from category tag if present
        category_tag = raw_item.find("category")
        subreddit = "Unknown"
        if category_tag:
            label = category_tag.get("label")
            if label:
                subreddit = label.replace("r/", "").strip()

        # Compile original payload for debugging and detailed AI ingestion
        raw_metadata = {
            "title": title,
            "author": author,
            "published_time": timestamp,
            "subreddit": subreddit,
            "original_url": url,
            "content_summary": raw_item.find("content").text[:1000] if raw_item.find("content") else ""
        }

        # Create a stable external ID based on the post URL or unique Atom ID tag
        id_tag = raw_item.find("id")
        unique_feed_id = id_tag.text.strip() if id_tag else url or title
        hash_digest = hashlib.md5(unique_feed_id.encode("utf-8")).hexdigest()
        external_id = f"reddit_{hash_digest}"

        return {
            "title": title,
            "source": f"reddit/r/{subreddit}",
            "url": url,
            "external_id": external_id,
            "raw_data": raw_metadata
        }

    def run(self) -> List[int]:
        """
        Overrides the BaseFetcher's pipeline to loop through all configured subreddits.
        """
        logger.info(
            "Starting execution of multi-subreddit Reddit fetcher pipeline",
            extra={"subreddits": settings.REDDIT_SUBREDDITS}
        )
        
        all_stored_ids: List[int] = []

        for subreddit in settings.REDDIT_SUBREDDITS:
            logger.info(f"Ingesting trends from subreddit: r/{subreddit}")
            
            # 1. Fetch Subreddit Feed
            raw_content = self.fetch_subreddit_feed(subreddit)
            if not raw_content:
                logger.warning(f"Skipping r/{subreddit}: No content retrieved")
                continue

            # 2. Parse Subreddit entries
            try:
                entries = self.parse(raw_content)
                logger.info(f"Found {len(entries)} posts in r/{subreddit}")
            except Exception as e:
                logger.error(f"Failed to parse Atom feed for r/{subreddit}", extra={"error": str(e)})
                continue

            # 3. Normalize and Store individual entries
            subreddit_stored_count = 0
            for entry in entries:
                try:
                    normalized = self.normalize(entry)
                    
                    if not normalized["title"] or not normalized["external_id"]:
                        continue

                    # Persist trend into database repository (auto-deduplicated)
                    trend_id = TrendRepository.add_trend(
                        title=normalized["title"],
                        source=normalized["source"],
                        url=normalized["url"],
                        external_id=normalized["external_id"],
                        raw_data=normalized["raw_data"]
                    )

                    if trend_id:
                        all_stored_ids.append(trend_id)
                        subreddit_stored_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to normalize/store entry from r/{subreddit}",
                        extra={"entry": str(entry)[:500], "error": str(e)}
                    )

            logger.info(f"Subreddit r/{subreddit} ingestion finished. Stored/Updated items: {subreddit_stored_count}")

        logger.info(
            "Reddit fetcher pipeline finished execution",
            extra={"total_stored_across_subreddits": len(all_stored_ids)}
        )
        return all_stored_ids
