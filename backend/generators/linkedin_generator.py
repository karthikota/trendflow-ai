import os
import re
from datetime import datetime
from typing import Any, Dict, Optional
from backend.ai.gemini_client import gemini_client
from backend.config import settings
from backend.db.repository import TrendRepository
from backend.utils.prompt_loader import PromptLoader
from backend.utils.logger import logger

class LinkedInGenerator:
    """
    LinkedIn Content Generation Engine.
    Leverages copywriting prompts to write and export high-performance professional LinkedIn posts.
    """

    @staticmethod
    def _sanitize_slug(title: str) -> str:
        """Helper to convert standard titles into clean URL-friendly filesystem slugs."""
        slug = title.lower().strip()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "_", slug)
        return slug[:50].strip("_")

    @classmethod
    def generate(cls, trend: Dict[str, Any]) -> Optional[str]:
        """
        Generates, stores, and exports a LinkedIn post draft for the given trend.
        """
        trend_id = trend["id"]
        logger.info(f"Generating LinkedIn post draft for Trend ID: {trend_id}", extra={"title": trend["title"]})

        try:
            # 1. Format prompt variables
            variables = {
                "title": trend["title"],
                "niche": trend.get("niche", "Technology"),
                "sentiment": trend.get("sentiment", "Neutral"),
                "angle": trend.get("angle", "Educational"),
                "summary": trend.get("summary", trend["title"])
            }

            # 2. Load prompt
            prompt = PromptLoader.load_prompt("linkedin_writer", variables)

            # 3. Call Gemini
            post_content = gemini_client.generate_text(
                prompt=prompt,
                temperature=0.7  # Higher temperature for creative hooks and language variation
            )

            if not post_content:
                logger.error(f"Failed to generate LinkedIn post content from Gemini for Trend ID: {trend_id}")
                return None

            # 4. Save locally as a Markdown file in outputs/linkedin/
            date_str = datetime.now().strftime("%Y-%m-%d")
            slug = cls._sanitize_slug(trend["title"])
            filename = f"{date_str}_{slug}.md"
            file_path = os.path.join(settings.OUTPUTS_DIR, "linkedin", filename)

            # Write formatted markdown draft to local storage
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"--- \n")
                f.write(f"Title: {trend['title']} \n")
                f.write(f"Date: {date_str} \n")
                f.write(f"Niche: {trend.get('niche')} \n")
                f.write(f"--- \n\n")
                f.write(post_content)

            # 5. Persist inside DB Repository linked to the trend
            TrendRepository.add_generated_content(
                trend_id=trend_id,
                platform="linkedin",
                content_text=post_content,
                file_path=file_path
            )

            logger.info(
                "Successfully completed LinkedIn post generation",
                extra={"trend_id": trend_id, "file_path": file_path}
            )
            return post_content

        except Exception as e:
            logger.error(
                "Error encountered during LinkedIn post generation",
                extra={"trend_id": trend_id, "error": str(e)}
            )
            return None
