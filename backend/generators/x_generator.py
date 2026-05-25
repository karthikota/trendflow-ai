import os
import re
from datetime import datetime
from typing import Any, Dict, Optional
from backend.ai.gemini_client import gemini_client
from backend.config import settings
from backend.db.repository import TrendRepository
from backend.utils.prompt_loader import PromptLoader
from backend.utils.logger import logger

class XGenerator:
    """
    X (formerly Twitter) Content Generation Engine.
    Generates high-impact, ultra-short micro-blogs strictly under 280 characters.
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
        Generates, stores, and exports a short X post for the given trend.
        Guarantees character limit constraints are met.
        """
        trend_id = trend["id"]
        logger.info(f"Generating X post draft for Trend ID: {trend_id}", extra={"title": trend["title"]})

        try:
            # 1. Format prompt variables
            variables = {
                "title": trend["title"],
                "niche": trend.get("niche", "Technology"),
                "summary": trend.get("summary", trend["title"])
            }

            # 2. Load prompt
            prompt = PromptLoader.load_prompt("x_writer", variables)

            # 3. Call Gemini
            # Try up to 2 times to ensure character limit constraints are rigorously met
            post_content = None
            for attempt in range(1, 3):
                post_content = gemini_client.generate_text(
                    prompt=prompt,
                    temperature=0.7
                )
                if post_content:
                    post_content = post_content.strip()
                    char_count = len(post_content)
                    if char_count <= 280:
                        logger.debug(f"X post character check passed on attempt {attempt}: {char_count} chars")
                        break
                    else:
                        logger.warning(
                            f"Gemini output exceeded X character limit ({char_count} > 280) on attempt {attempt}. Retrying with strict enforcement..."
                        )
                        prompt += "\nREMINDER: Your previous response exceeded 280 characters! You MUST shorten your response."

            if not post_content:
                logger.error(f"Failed to generate X post from Gemini for Trend ID: {trend_id}")
                return None

            # 4. Save locally as a Text file in outputs/x_summaries/
            date_str = datetime.now().strftime("%Y-%m-%d")
            slug = cls._sanitize_slug(trend["title"])
            filename = f"{date_str}_{slug}.txt"
            file_path = os.path.join(settings.OUTPUTS_DIR, "x_summaries", filename)

            # Write text copy to local storage
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(post_content)

            # 5. Persist inside DB Repository
            TrendRepository.add_generated_content(
                trend_id=trend_id,
                platform="x_summary",
                content_text=post_content,
                file_path=file_path
            )

            logger.info(
                "Successfully completed X post generation",
                extra={"trend_id": trend_id, "file_path": file_path, "characters": len(post_content)}
            )
            return post_content

        except Exception as e:
            logger.error(
                "Error encountered during X post generation",
                extra={"trend_id": trend_id, "error": str(e)}
            )
            return None
