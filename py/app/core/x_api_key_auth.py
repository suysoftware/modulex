"""
X-API-KEY Authentication Module for ModuleX

X-API-KEY header authentication for various endpoints.
"""

import os
import logging
from typing import Optional
from fastapi import HTTPException, Depends, status, Header

logger = logging.getLogger(__name__)

async def verify_x_api_key(x_api_key: Optional[str] = Header(None)):
    """
    Verify X-API-KEY header for endpoints that require it
    
    Rules:
    - X-API-KEY header is required
    - Value must match MODULEX_API_KEY environment variable
    - No Bearer prefix, just the raw key
    """
    
    modulex_api_key = os.getenv("MODULEX_API_KEY")
    
    if not modulex_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MODULEX_API_KEY not configured on server"
        )
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-KEY header required",
            headers={"WWW-Authenticate": "X-API-KEY"},
        )
    
    if x_api_key != modulex_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-API-KEY",
            headers={"WWW-Authenticate": "X-API-KEY"},
        )
    
    return True

# Alias for backward compatibility and specific use cases
verify_system_api_key = verify_x_api_key 