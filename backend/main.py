import argparse
import os
import sys
import time
from pathlib import Path
from typing import List

# Force UTF-8 encoding on standard output streams for Windows command prompt
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure backend root can be resolved for standalone CLI executions
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.utils.logger import logger
from backend.db.connection import get_db_connection, init_db
from backend.db.repository import TrendRepository
from backend.fetchers.google_trends import GoogleTrendsFetcher
from backend.fetchers.reddit import RedditFetcher
from backend.analyzers.trend_analyzer import TrendAnalyzer
from backend.generators.linkedin_generator import LinkedInGenerator
from backend.generators.medium_generator import MediumGenerator
from backend.generators.x_generator import XGenerator
from backend.ai.gemini_client import gemini_client

def run_health_check() -> bool:
    """
    Validates systems readiness:
    - SQLite database connectivity
    - Gemini API credentials & ping validation
    - Outputs file subdirectories accessibility
    - Logs directory accessibility
    """
    print("\n" + "="*50)
    print("        TRENDFLOW AI SYSTEMS INTEGRATION CHECK")
    print("="*50)
    
    passed_all = True
    
    # 1. Check SQLite DB
    print("[*] 1. Validating Database Connection...")
    try:
        init_db()  # Ensures tables exist
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version();")
        version = cursor.fetchone()[0]
        conn.close()
        print(f"    [✓] Database Connected. SQLite Version: {version}")
    except Exception as e:
        print(f"    [!] DB Error: {e}")
        passed_all = False

    # 2. Check Gemini Connection
    print("\n[*] 2. Validating Gemini API Key and SDK client connectivity...")
    try:
        api_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if not api_key:
            print("    [!] API Key Error: GEMINI_API_KEY is blank in environment and .env")
            passed_all = False
        else:
            # Send a fast text validation (safe request)
            print("       - Sending lightweight handshake token request to Gemini...")
            ping_response = gemini_client.generate_text("Say the word PONG")
            if ping_response and len(ping_response.strip()) > 0:
                print(f"    [✓] Gemini API Handshake Success. Connection is active. (Received: '{ping_response.strip()}')")
            else:
                print("    [!] API Handshake Failed: Gemini returned empty or invalid text.")
                passed_all = False
    except Exception as e:
        print(f"    [!] Gemini SDK/Network Error: {e}")
        passed_all = False

    # 3. Check Folders
    print("\n[*] 3. Validating storage folders structure and permissions...")
    try:
        settings.ensure_directories()
        directories = [
            ("Base Outputs", settings.OUTPUTS_DIR),
            ("LinkedIn Exports", os.path.join(settings.OUTPUTS_DIR, "linkedin")),
            ("Medium Exports", os.path.join(settings.OUTPUTS_DIR, "medium")),
            ("X Summaries Exports", os.path.join(settings.OUTPUTS_DIR, "x_summaries")),
            ("Workflow Logs", settings.LOGS_DIR)
        ]
        
        for name, path in directories:
            # Attempt to create subfolders if missing, verify write accessibility
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            test_file = p / ".write_test"
            test_file.touch()
            test_file.unlink()
            print(f"    [✓] Folder Access: '{name}' is writable.")
    except Exception as e:
        print(f"    [!] Storage Access Error: {e}")
        passed_all = False

    print("\n" + "="*50)
    if passed_all:
        print("    [✓] ALL SYSTEMS ARE ONLINE AND READY FOR PIPELINE RUNS.")
        print("="*50 + "\n")
        return True
    else:
        print("    [!] SYSTEMS ARE OFFLINE. PLEASE FIX ERRORS SHOWN ABOVE.")
        print("="*50 + "\n")
        return False

def run_fetch_trends() -> List[int]:
    """Runs all raw trend RSS ingestion scrapers and registers new topics in DB."""
    logger.info("Executing fetch-trends CLI operation")
    start_time = time.time()
    
    print("\n[*] Triggering Multi-Source Fetching System...")
    
    # Run Google trends RSS fetcher
    print("    - Scanning Google Trends feed...")
    gt_stored = GoogleTrendsFetcher().run()
    
    # Run Reddit subreddit Atom fetcher
    print("    - Scanning configured Subreddit hot feeds...")
    reddit_stored = RedditFetcher().run()
    
    total_stored = len(gt_stored) + len(reddit_stored)
    duration = time.time() - start_time
    
    print(f"[✓] Fetch operations finished in {duration:.2f}s.")
    print(f"    - Ingested Google Trends topics: {len(gt_stored)}")
    print(f"    - Ingested Reddit Subreddits topics: {len(reddit_stored)}")
    print(f"    - Total stored/updated entries: {total_stored}")
    
    logger.info(
        "CLI fetch-trends completed successfully", 
        extra={"duration_seconds": duration, "google_trends_count": len(gt_stored), "reddit_count": len(reddit_stored)}
    )
    
    return gt_stored + reddit_stored

def run_analyze_trends(limit: int = 2) -> int:
    """Trigger scoring logic using Gemini structured JSON outputs on unanalyzed trends."""
    logger.info("Executing analyze-trends CLI operation", extra={"limit": limit})
    start_time = time.time()
    
    print(f"\n[*] Running Gemini Trend Analyzer (Batch Limit: {limit})...")
    
    analyzed_count = TrendAnalyzer.run(limit=limit)
    duration = time.time() - start_time
    
    print(f"[✓] Analysis pipeline finished in {duration:.2f}s.")
    print(f"    - Newly analyzed topics scored: {analyzed_count}")
    
    logger.info(
        "CLI analyze-trends completed successfully", 
        extra={"duration_seconds": duration, "analyzed_count": analyzed_count}
    )
    
    return analyzed_count

def run_generate_content(limit: int = 1) -> int:
    """Looks for highly rated analyzed trends and generates marketing drafts."""
    logger.info("Executing generate-content CLI operation", extra={"limit": limit})
    start_time = time.time()
    
    min_score = settings.MIN_ENGAGEMENT_SCORE
    print(f"\n[*] Identifying qualified trends with engagement score >= {min_score} (Limit: {limit})...")
    
    all_ready = TrendRepository.get_trends_ready_for_generation(min_score=min_score)
    qualified_trends = all_ready[:limit]
    
    if not qualified_trends:
        print("    [o] No new qualified trends ready for generation found.")
        print(f"        (Verify that you have run 'analyze-trends' and scored topics >= {min_score})")
        return 0
        
    print(f"    [+] Found {len(qualified_trends)} new trends ready for content generation.")
    
    success_count = 0
    for idx, trend in enumerate(qualified_trends):
        print(f"\n    ({idx+1}/{len(qualified_trends)}) Generating posts for: '{trend['title']}' (Score: {trend['engagement_score']})")
        
        # 1. LinkedIn Post
        print("       - Writing LinkedIn post...")
        li_post = LinkedInGenerator.generate(trend)
        time.sleep(4)  # Safe spacing to respect Gemini Free Tier 15 RPM rate limits
        
        # 2. Medium Essay
        print("       - Writing Medium article...")
        med_post = MediumGenerator.generate(trend)
        time.sleep(4)  # Safe spacing to respect Gemini Free Tier 15 RPM rate limits
        
        # 3. X Twitter post
        print("       - Writing X summary...")
        x_post = XGenerator.generate(trend)
        time.sleep(4)  # Safe spacing to respect Gemini Free Tier 15 RPM rate limits
        
        if li_post or med_post or x_post:
            success_count += 1
            print(f"       [✓] Generated outputs written to DB and disk folders.")
            
    duration = time.time() - start_time
    print(f"\n[✓] Content generation finished in {duration:.2f}s.")
    print(f"    - Successfully generated platform drafts for {success_count}/{len(qualified_trends)} trends.")
    
    logger.info(
        "CLI generate-content completed successfully", 
        extra={"duration_seconds": duration, "generated_count": success_count}
    )
    
    return success_count

def run_all(limit: int = 1) -> None:
    """Executes the full pipeline sequentially: Ingestion ➔ Analysis ➔ Content Generation."""
    logger.info("Executing run-all CLI operation (Full Sequenced Pipeline)", extra={"limit": limit})
    print("\n" + "="*60)
    print("         STARTING FULL AI CONTENT INGESTION PIPELINE")
    print("="*60)
    
    start_time = time.time()
    
    # 1. Ingest/Fetch RSS feeds
    run_fetch_trends()
    
    # 2. Analyze using Gemini (limit items for safety)
    run_analyze_trends(limit=limit)
    
    # 3. Write Platform drafts (limit items for safety)
    run_generate_content(limit=limit)
    
    duration = time.time() - start_time
    print("\n" + "="*60)
    print(f"     PIPELINE RUN COMPLETED SUCCESSFULLY IN {duration:.2f}s.")
    print("="*60 + "\n")
    
    logger.info("CLI run-all sequencing completed successfully", extra={"total_duration_seconds": duration})

def main():
    """Main CLI execution handler."""
    parser = argparse.ArgumentParser(
        description="TrendFlow AI - Centralized AI-assisted Content Automation Pipeline CLI Utility.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Ingestion & automation pipelines")
    
    # Individual CLI Subcommands
    subparsers.add_parser("fetch-trends", help="Scrapes current trending topics from Google Trends & Subreddit feeds")
    
    parser_analyze = subparsers.add_parser("analyze-trends", help="Evaluates and scores unanalyzed database trends using Gemini API")
    parser_analyze.add_argument("--limit", type=int, default=1, help="Maximum number of trends to analyze (default: 1)")
    
    parser_generate = subparsers.add_parser("generate-content", help="Writes copywriting drafts for high-value scored trends (LinkedIn, Medium, X)")
    parser_generate.add_argument("--limit", type=int, default=1, help="Maximum number of trends to generate posts for (default: 1)")
    
    parser_run_all = subparsers.add_parser("run-all", help="Executes fetch, analyze, and generate pipelines end-to-end in sequence")
    parser_run_all.add_argument("--limit", type=int, default=1, help="Maximum number of trends to analyze/generate in batch (default: 1)")
    
    subparsers.add_parser("health-check", help="Performs a full systems integration checklist (DB, API connection, folder privileges)")

    args = parser.parse_args()

    # Route subcommands
    try:
        if args.command == "health-check":
            success = run_health_check()
            sys.exit(0 if success else 1)
            
        elif args.command == "fetch-trends":
            run_fetch_trends()
            sys.exit(0)
            
        elif args.command == "analyze-trends":
            run_analyze_trends(limit=args.limit)
            sys.exit(0)
            
        elif args.command == "generate-content":
            run_generate_content(limit=args.limit)
            sys.exit(0)
            
        elif args.command == "run-all":
            run_all(limit=args.limit)
            sys.exit(0)
            
    except Exception as e:
        logger.exception(f"Unhandled exception during CLI '{args.command}' execution", extra={"error": str(e)})
        print(f"\n[!] CLI Execution crashed due to unhandled error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
