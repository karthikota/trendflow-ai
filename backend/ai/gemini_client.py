import time
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.errors import APIError
from backend.config import settings
from backend.utils.logger import logger

class GeminiClient:
    """
    Centralized communication client for Google Gemini API.
    Uses the new official 'google-genai' SDK to process text and structured JSON generation.
    """

    def __init__(self):
        self.model_name = "gemini-2.5-flash"
        self._client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """
        Safely initializes the official google-genai Client.
        Falls back to standard env variable checking if config is blank.
        """
        try:
            api_key = settings.GEMINI_API_KEY
            if api_key:
                logger.info("Initializing Gemini Client with config-supplied API key.")
                self._client = genai.Client(api_key=api_key)
            else:
                logger.warning("No GEMINI_API_KEY found in settings. Attempting environment auto-load...")
                self._client = genai.Client()
        except Exception as e:
            logger.error("Failed to initialize Google GenAI SDK client", extra={"error": str(e)})
            raise RuntimeError("Gemini Client initialization failed. Check API Key configuration.") from e

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None
    ) -> Optional[str]:
        """
        Sends a standard text prompt to Gemini 2.5 Flash.
        Handles errors gracefully, logs request latency and token usage.
        """
        if not self._client:
            logger.error("API request blocked: Gemini Client is not initialized.")
            return None

        logger.info("Sending text generation request to Gemini", extra={"model": self.model_name})
        start_time = time.time()

        try:
            # Build generation config
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )

            # Call SDK with robust transient error retries (e.g. 503 unavailable)
            max_retries = 3
            backoff = 2.0
            response = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    response = self._client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=config
                    )
                    break
                except APIError as e:
                    if attempt == max_retries:
                        raise e
                    # If it's a 429 Rate Limit error, sleep longer (e.g. 20s) to let the free quota refresh!
                    sleep_time = backoff
                    if e.code == 429 or "quota" in str(e).lower():
                        sleep_time = max(20.0, backoff)
                        logger.warning(
                            f"Gemini API Rate Limit (429) hit. Sleeping for {sleep_time}s to let quota refresh... (Attempt {attempt}/{max_retries})"
                        )
                    else:
                        logger.warning(
                            f"Gemini API returned code {e.code} ({e.message}). Retrying in {sleep_time}s... (Attempt {attempt}/{max_retries})",
                            extra={"error": str(e)}
                        )
                    time.sleep(sleep_time)
                    backoff *= 2

            duration = time.time() - start_time
            
            # Extract token details from usage metadata if available
            tokens_in = 0
            tokens_out = 0
            if response.usage_metadata:
                tokens_in = response.usage_metadata.prompt_token_count or 0
                tokens_out = response.usage_metadata.candidates_token_count or 0

            logger.info(
                "Gemini text generation completed successfully",
                extra={
                    "duration_seconds": round(duration, 3),
                    "prompt_tokens": tokens_in,
                    "completion_tokens": tokens_out,
                    "total_tokens": tokens_in + tokens_out
                }
            )

            return response.text

        except APIError as e:
            logger.error("Gemini API returned an error", extra={"error": str(e), "model": self.model_name})
            return None
        except Exception as e:
            logger.error("Unexpected error during Gemini text generation", extra={"error": str(e)})
            return None

    def generate_structured_json(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.1
    ) -> Optional[Dict[str, Any]]:
        """
        Sends a prompt to Gemini and enforces a strict structured JSON response
        matching the provided Pydantic model schema. Excellent for analyzers.
        """
        if not self._client:
            logger.error("API request blocked: Gemini Client is not initialized.")
            return None

        logger.info(
            "Sending structured JSON generation request to Gemini",
            extra={"model": self.model_name, "schema": response_schema.__name__}
        )
        start_time = time.time()

        try:
            # Enforce structured output via types configuration
            config = types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=response_schema
            )

            # Call SDK with robust transient error retries (e.g. 503 unavailable)
            max_retries = 3
            backoff = 2.0
            response = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    response = self._client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=config
                    )
                    break
                except APIError as e:
                    if attempt == max_retries:
                        raise e
                    # If it's a 429 Rate Limit error, sleep longer (e.g. 20s) to let the free quota refresh!
                    sleep_time = backoff
                    if e.code == 429 or "quota" in str(e).lower():
                        sleep_time = max(20.0, backoff)
                        logger.warning(
                            f"Gemini API Rate Limit (429) hit. Sleeping for {sleep_time}s to let quota refresh... (Attempt {attempt}/{max_retries})"
                        )
                    else:
                        logger.warning(
                            f"Gemini API returned code {e.code} ({e.message}). Retrying in {sleep_time}s... (Attempt {attempt}/{max_retries})",
                            extra={"error": str(e)}
                        )
                    time.sleep(sleep_time)
                    backoff *= 2

            duration = time.time() - start_time
            
            # Extract token details
            tokens_in = 0
            tokens_out = 0
            if response.usage_metadata:
                tokens_in = response.usage_metadata.prompt_token_count or 0
                tokens_out = response.usage_metadata.candidates_token_count or 0

            logger.info(
                "Gemini structured JSON generation completed successfully",
                extra={
                    "duration_seconds": round(duration, 3),
                    "prompt_tokens": tokens_in,
                    "completion_tokens": tokens_out,
                    "total_tokens": tokens_in + tokens_out
                }
            )

            import json
            raw_text = response.text
            if not raw_text:
                logger.error("Gemini returned empty text for JSON generation.")
                return None
                
            return json.loads(raw_text)

        except APIError as e:
            logger.error("Gemini API returned an error during JSON generation", extra={"error": str(e)})
            return None
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini output as JSON", extra={"raw_text": response.text if 'response' in locals() else None, "error": str(e)})
            return None
        except Exception as e:
            logger.error("Unexpected error during Gemini JSON generation", extra={"error": str(e)})
            return None

# Global singleton client
gemini_client = GeminiClient()
