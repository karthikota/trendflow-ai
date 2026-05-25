from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import requests
from backend.utils.logger import logger
from backend.db.repository import TrendRepository

class BaseFetcher(ABC):
    """
    Abstract Base Class for all Trend Fetchers in TrendFlow AI.
    Provides standard interface and common logic for fetching, parsing,
    normalizing, and storing trending topics.
    """

    def __init__(self, source_name: str):
        self.source_name = source_name

    def fetch_feed(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Helper method to fetch raw string content from an HTTP/HTTPS endpoint.
        Handles connection timeouts, logging, and exceptions cleanly.
        """
        if not headers:
            # Set a modern user agent to prevent blocks from RSS endpoints
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

        logger.info(f"Initiating HTTP request for {self.source_name} feed", extra={"url": url})
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            logger.debug(f"Successfully fetched feed data from {self.source_name}", extra={"status_code": response.status_code, "bytes": len(response.content)})
            return response.text
        except requests.RequestException as e:
            logger.error(
                f"Network request failed while fetching {self.source_name} feed",
                extra={"url": url, "error": str(e)}
            )
            return None

    @abstractmethod
    def fetch(self) -> Optional[str]:
        """
        Abstract method to retrieve the raw feed content (e.g. XML/JSON).
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def parse(self, raw_content: str) -> List[Any]:
        """
        Abstract method to parse the raw string content into structured items.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def normalize(self, raw_item: Any) -> Dict[str, Any]:
        """
        Abstract method to map a raw parsed item into the unified TrendFlow schema.
        Unified Schema Structure:
        {
            "title": str,
            "source": str,
            "url": Optional[str],
            "external_id": str,  # Unique hash or ID to prevent duplicates
            "raw_data": dict     # Full parsed metadata dict for future debugging
        }
        """
        pass

    def run(self) -> List[int]:
        """
        Executes the entire ingestion pipeline:
        Fetch -> Parse -> Normalize -> Persist via DB Repository.
        Returns a list of database IDs of successfully stored/found trends.
        """
        logger.info(f"Starting execution of {self.source_name} fetcher pipeline")
        
        # 1. Fetch
        raw_data = self.fetch()
        if not raw_data:
            logger.warning(f"Ingestion pipeline stopped: No data fetched for {self.source_name}")
            return []

        # 2. Parse
        try:
            parsed_items = self.parse(raw_data)
            logger.info(f"Parsed {len(parsed_items)} items from {self.source_name} feed")
        except Exception as e:
            logger.error(f"Failed to parse data for {self.source_name}", extra={"error": str(e)})
            return []

        # 3. Normalize & Store
        stored_ids: List[int] = []
        duplicate_count = 0
        success_count = 0

        for item in parsed_items:
            try:
                normalized = self.normalize(item)
                
                # Verify basic schema requirements
                if not normalized.get("title") or not normalized.get("external_id"):
                    logger.warning("Skipping item: missing title or external_id", extra={"item": str(item)})
                    continue

                # 4. Save using the SQLite Repository
                trend_id = TrendRepository.add_trend(
                    title=normalized["title"],
                    source=normalized["source"],
                    url=normalized["url"],
                    external_id=normalized["external_id"],
                    raw_data=normalized["raw_data"]
                )

                if trend_id:
                    stored_ids.append(trend_id)
                    # Check if this was a fresh insert or an existing duplicate by checking database records, 
                    # but simple count tracking is fine.
                    success_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to normalize/store item from {self.source_name}",
                    extra={"item": str(item), "error": str(e)}
                )

        logger.info(
            f"Ingestion complete for {self.source_name}",
            extra={
                "source": self.source_name,
                "total_parsed": len(parsed_items),
                "total_stored": success_count
            }
        )
        return stored_ids
