import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Ensure robust SQLAlchemy execution in all restricted/AppControl environments
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

class Settings:
    PROJECT_NAME: str = "FitBuddy – AI Fitness Plan Generator"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_WORKOUT_MODEL: str = os.getenv("GEMINI_WORKOUT_MODEL", "gemini-2.5-flash").strip()
    GEMINI_NUTRITION_MODEL: str = os.getenv("GEMINI_NUTRITION_MODEL", "gemini-2.5-flash").strip()
    
    # Database URL: Handles Render/Heroku postgres:// -> postgresql:// normalization
    _raw_db_url: str = os.getenv("DATABASE_URL", "sqlite:///./fitbuddy.db")
    if _raw_db_url.startswith("postgres://"):
        DATABASE_URL: str = _raw_db_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL: str = _raw_db_url

    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    
    # JWT Security Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fitbuddy-super-secret-jwt-key-change-in-production-2026")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days default
    
    # Stripe Monetization Settings
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "").strip()
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    STRIPE_PRO_PRICE_ID: str = os.getenv("STRIPE_PRO_PRICE_ID", "price_pro_monthly").strip()
    FREE_TIER_MONTHLY_LIMIT: int = int(os.getenv("FREE_TIER_MONTHLY_LIMIT", "3"))

    # Production Observability & Error Tracking
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "").strip()
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # CORS Origins (comma separated in env)
    ALLOWED_ORIGINS: List[str] = [
        origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",") if origin.strip()
    ]

settings = Settings()
