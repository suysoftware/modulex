"""
Core Configuration for ModuleX
"""
import os
from typing import List, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

class Settings:
    """Application settings"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/modulex")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")  # Encryption key for sensitive data
    MODULEX_API_KEY: str = os.getenv("MODULEX_API_KEY", "")  # API key for ModuleX endpoints
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # OAuth Settings
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    
    SLACK_CLIENT_ID: str = os.getenv("SLACK_CLIENT_ID", "")
    SLACK_CLIENT_SECRET: str = os.getenv("SLACK_CLIENT_SECRET", "")
    
    R2R_BASE_URL: str = os.getenv("R2R_BASE_URL", "")
    R2R_AUTH_URL: str = os.getenv("R2R_AUTH_URL", "")
    
    # Server
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]  # In production, specify exact hosts


settings = Settings()


# API Key Authentication
security = HTTPBearer(auto_error=False)


async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Verify API key for ModuleX endpoints
    
    Rules:
    1. If MODULEX_API_KEY is not set or empty -> Allow all requests (development mode)
    2. If MODULEX_API_KEY is set -> Require "Bearer {key}" in Authorization header
    """
    
    # If no API key is configured, allow all requests (development mode)
    if not settings.MODULEX_API_KEY:
        return True
    
    # If API key is configured, require authentication
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required. Use: Authorization: Bearer your-api-key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if the provided key matches
    if credentials.credentials != settings.MODULEX_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True


def get_api_key_info():
    """Get API key configuration info for documentation"""
    if settings.MODULEX_API_KEY:
        return {
            "api_key_required": True,
            "api_key_configured": True,
            "usage": "Authorization: Bearer your-api-key"
        }
    else:
        return {
            "api_key_required": False,
            "api_key_configured": False,
            "usage": "No API key required (development mode)"
        } 