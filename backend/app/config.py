from __future__ import annotations
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/careerpilot.db"
    
    # Security
    SECRET_KEY: str = "careerpilot-super-secure-secret-key-development-mode"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # AI Providers
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Web Search & Discovery
    TAVILY_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    APOLLO_API_KEY: str = ""
    
    # Outbound Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    
    # Inbound Email (IMAP)
    IMAP_HOST: str = "imap.gmail.com"
    IMAP_PORT: int = 993
    IMAP_USERNAME: str = ""
    IMAP_PASSWORD: str = ""
    INBOUND_POLL_INTERVAL_MINUTES: int = 15
    
    # Owner Defaults
    CAREER_FULL_NAME: str = "Operations Professional"
    CAREER_PHONE: str = "+91 9876543210"
    CAREER_EMAIL: str = ""
    CAREER_LOCATION: str = "Hyderabad, India"
    CAREER_LINKEDIN: str = ""
    
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
