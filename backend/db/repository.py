import json
import sqlite3
from typing import Any, Dict, List, Optional
from backend.db.connection import transaction, get_db_connection
from backend.utils.logger import logger

class TrendRepository:
    """
    Data Access Object (DAO) for TrendFlow AI.
    Encapsulates all SQLite operations for trends, analyses, and generated content.
    """

    # --- TREND CRUD OPERATIONS ---

    @staticmethod
    def add_trend(
        title: str,
        source: str,
        url: Optional[str],
        external_id: str,
        raw_data: Dict[str, Any]
    ) -> Optional[int]:
        """
        Inserts a new trend topic if it doesn't already exist.
        If it exists (duplicate external_id), returns the existing trend's ID.
        This prevents double-fetching and duplicate workflows.
        """
        # First, check if the external_id already exists to avoid conflict
        try:
            with transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM trends WHERE external_id = ?",
                    (external_id,)
                )
                row = cursor.fetchone()
                if row:
                    logger.debug("Trend already exists in DB, returning existing ID", extra={"external_id": external_id})
                    return int(row["id"])

                # Otherwise, execute fresh insert
                cursor.execute(
                    """
                    INSERT INTO trends (title, source, url, external_id, raw_data)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (title, source, url, external_id, json.dumps(raw_data))
                )
                new_id = cursor.lastrowid
                logger.info(
                    "Successfully stored new raw trend",
                    extra={"trend_id": new_id, "title": title, "source": source}
                )
                return new_id
        except sqlite3.Error as e:
            logger.error("Failed to add trend to database", extra={"error": str(e), "external_id": external_id})
            raise

    @staticmethod
    def get_trend(trend_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetches a single trend by its database ID.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trends WHERE id = ?", (trend_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                data = dict(row)
                data["raw_data"] = json.loads(data["raw_data"]) if data["raw_data"] else {}
                return data
            return None
        except sqlite3.Error as e:
            logger.error("Failed to fetch trend", extra={"error": str(e), "trend_id": trend_id})
            raise

    @staticmethod
    def get_all_trends(limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves recent trends up to the specified limit.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM trends ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                data = dict(row)
                data["raw_data"] = json.loads(data["raw_data"]) if data["raw_data"] else {}
                results.append(data)
            return results
        except sqlite3.Error as e:
            logger.error("Failed to fetch all trends", extra={"error": str(e)})
            raise

    @staticmethod
    def get_unanalyzed_trends(limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches trends that have been fetched but do not have an analysis entry yet.
        Used by the Trend Analyzer stage in the pipeline.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.* FROM trends t
                LEFT JOIN analyses a ON t.id = a.trend_id
                WHERE a.id IS NULL
                ORDER BY t.created_at ASC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                data = dict(row)
                data["raw_data"] = json.loads(data["raw_data"]) if data["raw_data"] else {}
                results.append(data)
            return results
        except sqlite3.Error as e:
            logger.error("Failed to fetch unanalyzed trends", extra={"error": str(e)})
            raise

    # --- ANALYSIS CRUD OPERATIONS ---

    @staticmethod
    def add_analysis(
        trend_id: int,
        engagement_score: int,
        sentiment: str,
        angle: str,
        niche: str,
        summary: str,
        analysis_raw: Dict[str, Any]
    ) -> int:
        """
        Stores Gemini trend analysis inside the database.
        Uses INSERT OR REPLACE to overwrite if an analysis already exists.
        """
        try:
            with transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO analyses 
                    (trend_id, engagement_score, sentiment, angle, niche, summary, analysis_raw)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trend_id,
                        engagement_score,
                        sentiment,
                        angle,
                        niche,
                        summary,
                        json.dumps(analysis_raw)
                    )
                )
                analysis_id = cursor.lastrowid
                logger.info(
                    "Stored trend analysis",
                    extra={"trend_id": trend_id, "score": engagement_score, "niche": niche}
                )
                return int(analysis_id)
        except sqlite3.Error as e:
            logger.error("Failed to add trend analysis", extra={"error": str(e), "trend_id": trend_id})
            raise

    @staticmethod
    def get_analysis(trend_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetches the analysis record associated with a specific trend.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analyses WHERE trend_id = ?", (trend_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                data = dict(row)
                data["analysis_raw"] = json.loads(data["analysis_raw"]) if data["analysis_raw"] else {}
                return data
            return None
        except sqlite3.Error as e:
            logger.error("Failed to fetch analysis", extra={"error": str(e), "trend_id": trend_id})
            raise

    # --- GENERATED CONTENT CRUD OPERATIONS ---

    @staticmethod
    def add_generated_content(
        trend_id: int,
        platform: str,
        content_text: str,
        file_path: Optional[str] = None
    ) -> int:
        """
        Stores generated social media draft content associated with a trend.
        Uses INSERT OR REPLACE to support updating/regenerating drafts.
        """
        try:
            with transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO generated_content 
                    (trend_id, platform, content_text, file_path)
                    VALUES (?, ?, ?, ?)
                    """,
                    (trend_id, platform.lower(), content_text, file_path)
                )
                content_id = cursor.lastrowid
                logger.info(
                    "Stored generated content draft",
                    extra={"trend_id": trend_id, "platform": platform, "file_path": file_path}
                )
                return int(content_id)
        except sqlite3.Error as e:
            logger.error("Failed to add generated content", extra={"error": str(e), "trend_id": trend_id, "platform": platform})
            raise

    @staticmethod
    def get_generated_content(trend_id: int, platform: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the generated draft for a specific trend on a given platform.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM generated_content WHERE trend_id = ? AND platform = ?",
                (trend_id, platform.lower())
            )
            row = cursor.fetchone()
            conn.close()

            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(
                "Failed to fetch generated content",
                extra={"error": str(e), "trend_id": trend_id, "platform": platform}
            )
            raise

    @staticmethod
    def get_all_content_for_trend(trend_id: int) -> List[Dict[str, Any]]:
        """
        Fetches all platform drafts generated for a specific trend.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM generated_content WHERE trend_id = ?",
                (trend_id,)
            )
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Failed to fetch all content for trend", extra={"error": str(e), "trend_id": trend_id})
            raise

    @staticmethod
    def get_trends_ready_for_generation(min_score: int = 70) -> List[Dict[str, Any]]:
        """
        Fetches trends that have been analyzed with a score >= min_score,
        but DO NOT have any generated content drafts yet.
        Ideal for the content generation orchestrator.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.*, a.engagement_score, a.sentiment, a.angle, a.niche, a.summary 
                FROM trends t
                JOIN analyses a ON t.id = a.trend_id
                LEFT JOIN generated_content gc ON t.id = gc.trend_id
                WHERE a.engagement_score >= ? AND gc.id IS NULL
                ORDER BY a.engagement_score DESC
                """,
                (min_score,)
            )
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                data = dict(row)
                data["raw_data"] = json.loads(data["raw_data"]) if data.get("raw_data") else {}
                results.append(data)
            return results
        except sqlite3.Error as e:
            logger.error("Failed to fetch trends ready for content generation", extra={"error": str(e)})
            raise
