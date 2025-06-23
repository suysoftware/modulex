"""
Form Manual Auth Handler - Form-based manual authentication (for N8N, etc.)
"""
from typing import Dict, Any
from .manual_auth_handler import BaseManualAuthHandler
from ...core.config import settings


class FormManualAuthHandler(BaseManualAuthHandler):
    """Form-based manual authentication handler (for tools like N8N)"""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__()
    
    async def get_auth_url(self, user_id: str) -> str:
        """Get form auth URL"""
        return f"{settings.BASE_URL}/auth/form/{self.tool_name}?user_id={user_id}"
    
    async def process_auth_response(self, auth_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Process form submission response"""
        from datetime import datetime
        
        return {
            "auth_type": "manual",
            "authenticated_at": datetime.utcnow().isoformat(),
            "user_id": user_id,
            **auth_data
        } 