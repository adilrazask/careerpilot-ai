from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"]
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/careerpilot.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "careerpilot-super-secure-secret-key-development-mode")
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "cp_admin_audit_secret_token_9876")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # AI Providers
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Web Search & Discovery
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "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")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    APOLLO_API_KEY: str = os.getenv("APOLLO_API_KEY", "apol_live_test_key_xyz987")
    HUNTER_API_KEY: str = os.getenv("HUNTER_API_KEY", "")
    ZEROBOUNCE_API_KEY: str = os.getenv("ZEROBOUNCE_API_KEY", "")

    # Email Dispatch Provider (smtp, dry_run, gmail_api)
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "dry_run" if "pytest" in sys.modules else "smtp")
    GMAIL_API_TOKEN: str = os.getenv("GMAIL_API_TOKEN", "")
    
    # Outbound Email (SMTP)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "adilrazask@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "rkektianbnqytjkc")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "adilrazask@gmail.com")
    
    # Inbound Email (IMAP)
    IMAP_HOST: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", 993))
    IMAP_USERNAME: str = os.getenv("IMAP_USERNAME", "adilrazask@gmail.com")
    IMAP_PASSWORD: str = os.getenv("IMAP_PASSWORD", "rkektianbnqytjkc")
    INBOUND_POLL_INTERVAL_MINUTES: int = 15
    
    # Owner Defaults
    CAREER_FULL_NAME: str = os.getenv("CAREER_FULL_NAME", "SK Adil Raja")
    CAREER_PHONE: str = os.getenv("CAREER_PHONE", "+91 9583029294")
    CAREER_EMAIL: str = os.getenv("CAREER_EMAIL", "adilrazask@gmail.com")
    CAREER_LOCATION: str = os.getenv("CAREER_LOCATION", "Hyderabad, India")
    CAREER_LINKEDIN: str = os.getenv("CAREER_LINKEDIN", "")
    
    # Policy Defaults
    AUTONOMOUS_ENABLED: bool = False
    MAX_APPLICATIONS_PER_DAY: int = 5
    MAX_APPLICATIONS_PER_COMPANY_PER_MONTH: int = 2
    MIN_MATCH_SCORE: int = 65
    MAX_EMAILS_PER_HOUR: int = 10
    SEARCH_INTERVAL_MINUTES: int = 240
    FOLLOW_UP_FIRST_DAYS: int = 5
    FOLLOW_UP_SECOND_DAYS: int = 7
    FOLLOW_UP_INTERVAL_DAYS: int = 15
    MAX_FOLLOW_UPS: int = 3

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
