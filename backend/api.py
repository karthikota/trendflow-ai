import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

# Ensure backend root can be resolved for standalone web server executions
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.utils.logger import logger
from backend.db.connection import get_db_connection, init_db
from backend.db.repository import TrendRepository
from backend.ai.gemini_client import gemini_client

# Re-use existing business/orchestration logic to prevent code duplication!
from backend.main import (
    run_fetch_trends,
    run_analyze_trends,
    run_generate_content,
    run_all
)

# Initialize the FastAPI App
app = FastAPI(
    title="TrendFlow AI",
    description="API-driven Content Ingestion, Analysis, and Copylife Automation Engine.",
    version="1.0.0"
)

# --- PYDANTIC SCHEMAS ---

class HealthCheckStatus(BaseModel):
    database: str = Field(..., description="SQLite database status ('healthy' or 'unhealthy')")
    gemini_api: str = Field(..., description="Gemini SDK handshake status ('healthy' or 'unhealthy')")
    storage_folders: str = Field(..., description="Local outputs and logs folder status ('writable' or 'readonly')")

class HealthCheckResponse(BaseModel):
    status: str = Field("healthy", description="Global integration health status ('healthy' or 'unhealthy')")
    systems: HealthCheckStatus

class FetchResponse(BaseModel):
    status: str = "success"
    total_ingested: int = Field(..., description="Total new or updated raw trends stored in SQLite")
    message: str

class LimitRequest(BaseModel):
    limit: int = Field(default=1, ge=1, le=50, description="Max number of records to process")

class ProcessResponse(BaseModel):
    status: str = "success"
    processed_count: int = Field(..., description="Count of successfully scored or generated items")
    message: str

class StatsResponse(BaseModel):
    total_trends: int = Field(..., description="Aggregate trends stored in database")
    total_analyses: int = Field(..., description="Aggregate scored trends stored in database")
    total_content_drafts: int = Field(..., description="Aggregate platform post drafts stored in database")
    latest_trend: Optional[Dict[str, Any]] = Field(None, description="Detailed dictionary of the last fetched trend topic")

# --- MIDDLEWARE & HOOKS ---

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """
    Middleware that captures API requests execution time, endpoint routes,
    status codes, and writes them cleanly as structured JSON logs.
    """
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        "API Request processed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_seconds": round(duration, 3)
        }
    )
    return response

@app.on_event("startup")
def startup_event():
    """Initializes the database schema and verifies folder availability on service start."""
    logger.info("FastAPI service is starting up. Verifying integration environments...")
    settings.ensure_directories()
    init_db()

# --- API ENDPOINTS ---

@app.get("/health", response_model=HealthCheckResponse, tags=["Diagnostics"])
def get_health():
    """
    Performs full systems integration diagnostic:
    1. Checks SQLite read/write
    2. Runs light text ping to Gemini API
    3. Asserts local folder privileges
    """
    status_db = "healthy"
    status_gemini = "healthy"
    status_storage = "writable"
    global_status = "healthy"

    # 1. DB Test
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        conn.close()
    except Exception as e:
        status_db = "unhealthy"
        global_status = "unhealthy"
        logger.error("Health Check: SQLite DB is unreachable", extra={"error": str(e)})

    # 2. Gemini Test
    try:
        ping = gemini_client.generate_text("ping", max_output_tokens=5)
        if not ping or len(ping.strip()) == 0:
            status_gemini = "unhealthy"
            global_status = "unhealthy"
            logger.error("Health Check: Gemini API returned empty handshake")
    except Exception as e:
        status_gemini = "unhealthy"
        global_status = "unhealthy"
        logger.error("Health Check: Gemini API is unreachable", extra={"error": str(e)})

    # 3. Storage Test
    try:
        settings.ensure_directories()
        test_file = Path(settings.OUTPUTS_DIR) / ".api_write_test"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        status_storage = "readonly"
        global_status = "unhealthy"
        logger.error("Health Check: Local output storage directory is not writable", extra={"error": str(e)})

    response_status = HealthCheckStatus(
        database=status_db,
        gemini_api=status_gemini,
        storage_folders=status_storage
    )

    if global_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=HealthCheckResponse(status=global_status, systems=response_status).dict()
        )

    return HealthCheckResponse(status=global_status, systems=response_status)

@app.post("/fetch-trends", response_model=FetchResponse, tags=["Pipeline Trigger"])
def trigger_fetch_trends():
    """
    Triggers both Google Trends and Subreddit RSS fetch engines.
    Saves new normalized raw trends to database.
    """
    try:
        stored_ids = run_fetch_trends()
        return FetchResponse(
            status="success",
            total_ingested=len(stored_ids),
            message=f"Scraping completed. Ingested/updated {len(stored_ids)} trending topics in SQLite."
        )
    except Exception as e:
        logger.error("API error during fetch-trends execution", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fetch failed: {e}"
        )

@app.post("/analyze-trends", response_model=ProcessResponse, tags=["Pipeline Trigger"])
def trigger_analyze_trends(payload: Optional[LimitRequest] = None):
    """
    Pulls unanalyzed database trends and scores them using Gemini structured JSON outputs.
    Safe-limits batch sizes to prevent rate issues.
    """
    limit = payload.limit if payload else 1
    try:
        analyzed_count = run_analyze_trends(limit=limit)
        return ProcessResponse(
            status="success",
            processed_count=analyzed_count,
            message=f"Gemini trend evaluation finished. Scored {analyzed_count} unanalyzed topics."
        )
    except Exception as e:
        logger.error("API error during analyze-trends execution", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {e}"
        )

@app.post("/generate-content", response_model=ProcessResponse, tags=["Pipeline Trigger"])
def trigger_generate_content(payload: Optional[LimitRequest] = None):
    """
    Finds scored trends matching score threshold and writes LinkedIn, Medium, and X posts.
    """
    limit = payload.limit if payload else 1
    try:
        generated_count = run_generate_content(limit=limit)
        return ProcessResponse(
            status="success",
            processed_count=generated_count,
            message=f"Platform draft generation completed. Generated drafts for {generated_count} trends."
        )
    except Exception as e:
        logger.error("API error during generate-content execution", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation failed: {e}"
        )

@app.post("/run-all", response_model=ProcessResponse, tags=["Pipeline Trigger"])
def trigger_run_all(payload: Optional[LimitRequest] = None):
    """
    Chains Ingestion, Analysis, and Generation workflows end-to-end sequentially.
    """
    limit = payload.limit if payload else 1
    try:
        # Run sequentially
        run_all(limit=limit)
        return ProcessResponse(
            status="success",
            processed_count=limit,
            message=f"Full sequenced content automation pipeline executed successfully. Batch limit: {limit}."
        )
    except Exception as e:
        logger.error("API error during run-all sequential pipeline execution", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sequenced pipeline failed: {e}"
        )

@app.get("/stats", response_model=StatsResponse, tags=["Dashboard Metrics"])
def get_stats():
    """
    Returns database summary counts and details on the latest fetched trend.
    Excellent for n8n monitoring nodes.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM trends")
        total_trends = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM analyses")
        total_analyses = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM generated_content")
        total_content = cursor.fetchone()[0]
        
        conn.close()

        # Retrieve the latest trend row from SQLite repository
        recent_trends = TrendRepository.get_all_trends(limit=1)
        latest_trend = recent_trends[0] if recent_trends else None

        return StatsResponse(
            total_trends=total_trends,
            total_analyses=total_analyses,
            total_content_drafts=total_content,
            latest_trend=latest_trend
        )
    except Exception as e:
        logger.error("API error during get_stats database read", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch database statistics: {e}"
        )
