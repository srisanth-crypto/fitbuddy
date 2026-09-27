import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("fitbuddy.ai")

# Check which Gemini SDK is available
_google_genai_client = None
_google_generativeai_available = False

if settings.GEMINI_API_KEY:
    # Try importing modern google-genai
    try:
        from google import genai
        _google_genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Initialized Google GenAI client successfully.")
    except Exception as e:
        logger.warning(f"Could not initialize google.genai: {e}. Trying google.generativeai...")
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=settings.GEMINI_API_KEY)
            _google_generativeai_available = True
            logger.info("Initialized legacy google.generativeai client successfully.")
        except Exception as e2:
            logger.error(f"Failed to initialize any Gemini SDK: {e2}")

def is_gemini_configured() -> bool:
    """Returns True if a Gemini API key is configured and client is ready."""
    return bool(settings.GEMINI_API_KEY and (_google_genai_client is not None or _google_generativeai_available))

def call_gemini(prompt: str, model_name: Optional[str] = None, system_instruction: Optional[str] = None) -> Optional[str]:
    """
    Centralized helper to send prompt to Gemini models safely.
    Handles rate limits, empty responses, errors, and SDK differences.
    """
    if not is_gemini_configured():
        logger.info("Gemini API key not configured or client unavailable. Using fallback.")
        return None

    target_model = model_name or settings.GEMINI_WORKOUT_MODEL

    # Method 1: New google-genai client
    if _google_genai_client is not None:
        try:
            config = {}
            if system_instruction:
                config["system_instruction"] = system_instruction
            response = _google_genai_client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config if config else None
            )
            if response and response.text:
                return response.text.strip()
        except Exception as err:
            logger.error(f"Error calling google.genai model {target_model}: {err}")

    # Method 2: Legacy google.generativeai
    if _google_generativeai_available:
        try:
            import google.generativeai as legacy_genai
            model = legacy_genai.GenerativeModel(
                model_name=target_model,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as err:
            logger.error(f"Error calling google.generativeai model {target_model}: {err}")

    return None
