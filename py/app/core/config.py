"""
Core Configuration for ModuleX
"""
import os
from typing import List

class Settings:
    """Application settings"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/modulex")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # OAuth Settings
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    SLACK_CLIENT_ID: str = os.getenv("SLACK_CLIENT_ID", "")
    SLACK_CLIENT_SECRET: str = os.getenv("SLACK_CLIENT_SECRET", "")
    
    # Server
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]  # In production, specify exact hosts


settings = Settings() 