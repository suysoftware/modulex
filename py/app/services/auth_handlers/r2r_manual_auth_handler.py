"""
R2R Manual Auth Handler - R2R-specific manual authentication
"""
from typing import Dict, Any
from .manual_auth_handler import BaseManualAuthHandler
from ...core.config import settings


class R2RManualAuthHandler(BaseManualAuthHandler):
    """R2R manual authentication handler"""
    
    def __init__(self):
        # R2R gets its config from settings directly
        super().__init__()
    
    async def get_auth_url(self, user_id: str) -> str:
        """Get R2R auth URL with user_id parameter"""
        auth_url = settings.R2R_AUTH_URL
        if not auth_url:
            raise ValueError("R2R_AUTH_URL not configured in environment")
        
        return f"{auth_url}?user_id={user_id}"
    
    async def process_auth_response(self, auth_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Process R2R authentication response"""
        from datetime import datetime
        
        credentials = {
            "auth_type": "manual",
            "authenticated_at": datetime.utcnow().isoformat(),
            "user_id": user_id
        }
        
        # Handle access_token if present
        if "access_token" in auth_data:
            credentials["access_token"] = auth_data["access_token"]
        
        # Include all other response data
        for key, value in auth_data.items():
            if key not in credentials:
                credentials[key] = value
        
        return credentials 