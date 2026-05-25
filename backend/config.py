import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """
    TrendFlow AI Configuration Manager.
    Loads settings from environment variables or .env file with sensible defaults.
    """
    # API Configurations
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")

    # Local Storage Paths (auto-created on startup)
    DB_PATH: str = Field(default=str(BASE_DIR / "trendflow.db"), description="Path to SQLite database file")
    PROMPTS_DIR: str = Field(default=str(BASE_DIR / "prompts"), description="Directory where generative prompts are stored")
    OUTPUTS_DIR: str = Field(default=str(BASE_DIR / "outputs"), description="Directory where generated posts are exported")
    LOGS_DIR: str = Field(default=str(BASE_DIR / "logs"), description="Directory where JSON and text logs are saved")

    # Trend Filtering Settings
    MIN_ENGAGEMENT_SCORE: int = Field(default=70, description="Minimum score (0-100) required to trigger content generation")
    
    # Reddit RSS Settings
    REDDIT_SUBREDDITS: List[str] = Field(
        default=["technology", "artificial", "programming", "news"],
        description="List of subreddits to scan for trending topics"
    )

    # API Server Config
    HOST: str = Field(default="127.0.0.1", description="FastAPI host address")
    PORT: int = Field(default=8000, description="FastAPI port number")

    # Pydantic configuration settings
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def ensure_directories(self) -> None:
        """
        Guarantees that all required local persistence directories exist.
        Prevents FileNotFoundError when writing logs, database, or outputs.
        """
        Path(self.PROMPTS_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.LOGS_DIR).mkdir(parents=True, exist_ok=True)
        
        # Subdirectories for outputs
        for platform in ["linkedin", "medium", "x_summaries"]:
            Path(os.path.join(self.OUTPUTS_DIR, platform)).mkdir(parents=True, exist_ok=True)
            
        # Ensure SQLite parent dir exists
        Path(self.DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# Instantiate a global settings object for importing across the app
settings = Settings()

# Call directory check on import
settings.ensure_directories()
