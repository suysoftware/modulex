"""
Base Manual Auth Handler - Abstract base class for manual authentication
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseManualAuthHandler(ABC):
    """Base class for manual authentication handlers"""
    
    @abstractmethod
    async def get_auth_url(self, user_id: str) -> str:
        """Get authentication URL for manual auth"""
        pass
    
    @abstractmethod
    async def process_auth_response(self, auth_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Process authentication response from manual auth"""
        pass


class R2RManualAuthHandler(BaseManualAuthHandler):
    """R2R manual authentication handler"""
    
    async def get_auth_url(self, user_id: str) -> str:
        """Get R2R auth URL with user_id parameter"""
        base_url = self.config.get("auth_url")
        if not base_url:
            raise ValueError("R2R auth_url not configured")
        
        return f"{base_url}?user_id={user_id}"
    
    async def process_auth_response(self, auth_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Process R2R authentication response"""
        credentials = {
            "auth_type": "manual",
            "authenticated_at": "datetime.utcnow().isoformat()",
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


class FormManualAuthHandler(BaseManualAuthHandler):
    """Form-based manual authentication handler (for tools like N8N)"""
    
    async def get_auth_url(self, user_id: str) -> str:
        """Get form auth URL"""
        base_url = self.config.get("base_url")
        tool_name = self.config.get("tool_name")
        
        return f"{base_url}/auth/form/{tool_name}?user_id={user_id}"
    
    async def process_auth_response(self, auth_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Process form submission response"""
        return {
            "auth_type": "manual",
            "authenticated_at": "datetime.utcnow().isoformat()",
            "user_id": user_id,
            **auth_data
        } 