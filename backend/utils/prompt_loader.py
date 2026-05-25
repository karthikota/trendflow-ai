import os
from typing import Dict, Any
from backend.config import settings
from backend.utils.logger import logger

class PromptLoader:
    """
    Utility class to load and format prompt templates stored in the /prompts directory.
    Keeps AI prompts separate from python logic for easier testing and editing.
    """

    @staticmethod
    def load_prompt(filename: str, variables: Dict[str, Any]) -> str:
        """
        Reads a prompt template from file and formats it using keyword variables.
        """
        # Ensure it has the correct extension
        if not filename.endswith(".txt"):
            filename += ".txt"

        prompt_path = os.path.join(settings.PROMPTS_DIR, filename)
        
        if not os.path.exists(prompt_path):
            logger.error("Prompt template file not found", extra={"path": prompt_path})
            raise FileNotFoundError(f"Prompt template not found at: {prompt_path}")

        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
            
            # Format the template with provided variables
            formatted_prompt = template.format(**variables)
            return formatted_prompt
            
        except KeyError as e:
            logger.error(
                "KeyError while formatting prompt template",
                extra={"filename": filename, "missing_key": str(e), "provided_keys": list(variables.keys())}
            )
            raise ValueError(f"Prompt template {filename} requires key: {e}") from e
        except Exception as e:
            logger.error("Failed to load prompt template", extra={"filename": filename, "error": str(e)})
            raise
