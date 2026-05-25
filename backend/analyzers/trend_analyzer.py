import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, conint
from backend.ai.gemini_client import gemini_client
from backend.db.repository import TrendRepository
from backend.utils.prompt_loader import PromptLoader
from backend.utils.logger import logger

class TrendAnalysisSchema(BaseModel):
    """
    Pydantic schema to enforce structured analysis output from Google Gemini.
    Enables reliable, typed schema translation directly into relational database columns.
    """
    engagement_score: int = Field(
        ..., 
        description="A value from 0 to 100 rating the digital virality and discussion potential of this topic."
    )
    sentiment: str = Field(
        ..., 
        description="The overriding emotional tone: 'Positive', 'Negative', or 'Neutral'."
    )
    angle: str = Field(
        ..., 
        description="The best content marketing angle to pursue: 'Educational', 'Industry News', 'Controversy / Debate', or 'Thought Leadership'."
    )
    niche: str = Field(
        ..., 
        description="The strategic domain category this trend belongs to (e.g. AI, Programming, cybersecurity, cloud, Web Dev, General Tech)."
    )
    summary: str = Field(
        ..., 
        description="A concise 3-4 sentence summary of what this trend is, why it's popular, and its strategic implications."
    )

class TrendAnalyzer:
    """
    Trend Evaluation & Scoring Orchestrator.
    Retrieves unanalyzed raw trends, evaluates them using Gemini, and logs/saves insights.
    """

    @staticmethod
    def analyze_single_trend(trend: Dict[str, Any]) -> Optional[int]:
        """
        Analyzes a single raw trend dictionary using Gemini structured outputs.
        Saves analysis results to the SQLite DB.
        """
        trend_id = trend["id"]
        logger.info(f"Starting Gemini analysis for Trend ID: {trend_id}", extra={"title": trend["title"]})

        try:
            # 1. Format dynamic prompt variables
            raw_metadata = trend.get("raw_data", {})
            variables = {
                "title": trend["title"],
                "source": trend["source"],
                "url": trend.get("url") or "No link available",
                "raw_context": json.dumps(raw_metadata, indent=2)
            }

            # 2. Load prompt template from prompts/analyzer.txt
            prompt = PromptLoader.load_prompt("analyzer", variables)

            # 3. Call Gemini enforcing structural output schema
            analysis_dict = gemini_client.generate_structured_json(
                prompt=prompt,
                response_schema=TrendAnalysisSchema,
                temperature=0.1  # Low temperature for analytical accuracy and structural formatting
            )

            if not analysis_dict:
                logger.error(f"Gemini returned null analysis for trend ID: {trend_id}")
                return None

            # 4. Save analysis to Database Repository
            analysis_id = TrendRepository.add_analysis(
                trend_id=trend_id,
                engagement_score=int(analysis_dict["engagement_score"]),
                sentiment=analysis_dict["sentiment"],
                angle=analysis_dict["angle"],
                niche=analysis_dict["niche"],
                summary=analysis_dict["summary"],
                analysis_raw=analysis_dict
            )
            
            logger.info(
                f"Successfully completed trend analysis",
                extra={
                    "trend_id": trend_id,
                    "analysis_id": analysis_id,
                    "score": analysis_dict["engagement_score"],
                    "niche": analysis_dict["niche"]
                }
            )
            return analysis_id

        except Exception as e:
            logger.error(
                f"Exception encountered during single trend analysis pipeline",
                extra={"trend_id": trend_id, "error": str(e)}
            )
            return None

    @classmethod
    def run(cls, limit: int = 15) -> int:
        """
        Finds unanalyzed raw trends and runs them through the analyzer pipeline.
        Returns the count of successfully processed trends.
        """
        logger.info("Scanning database for unanalyzed trending topics...")
        
        unanalyzed_trends = TrendRepository.get_unanalyzed_trends(limit=limit)
        if not unanalyzed_trends:
            logger.info("No unanalyzed trends found in database. Trend Analyzer is idle.")
            return 0

        logger.info(f"Found {len(unanalyzed_trends)} unanalyzed trends to process.")
        
        success_count = 0
        for trend in unanalyzed_trends:
            analysis_id = cls.analyze_single_trend(trend)
            if analysis_id:
                success_count += 1
            import time
            time.sleep(4)  # Safe spacing to respect Gemini Free Tier 15 RPM rate limits

        logger.info(f"Trend Analyzer run completed. Analyzed {success_count}/{len(unanalyzed_trends)} trends.")
        return success_count
