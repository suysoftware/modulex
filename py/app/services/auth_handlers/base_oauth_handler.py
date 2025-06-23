"""
Base OAuth Handler - Abstract base class for all OAuth providers
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import httpx


class BaseOAuthHandler(ABC):
    """Abstract base class for OAuth handlers"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
    
    @abstractmethod
    def get_auth_url(self) -> str:
        """Get the OAuth authorization URL for this provider"""
        pass
    
    @abstractmethod
    def get_token_url(self) -> str:
        """Get the token exchange URL for this provider"""
        pass
    
    @abstractmethod
    def get_scopes(self) -> list:
        """Get the required scopes for this provider"""
        pass
    
    def build_auth_url(self, redirect_uri: str, state: str) -> str:
        """Build the complete authorization URL"""
        scopes_str = " ".join(self.get_scopes())
        return (
            f"{self.get_auth_url()}"
            f"?client_id={self.client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes_str}"
            f"&state={state}"
            f"&response_type=code"
        )
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        Can be overridden by providers with special requirements
        """
        data = self.prepare_token_request_data(code, redirect_uri)
        headers = self.prepare_token_request_headers()
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.get_token_url(), data=data, headers=headers)
                return await self.process_token_response(response)
                
            except httpx.HTTPStatusError as e:
                raise ValueError(f"HTTP {e.response.status_code}: {e.response.text}")
    
    def prepare_token_request_data(self, code: str, redirect_uri: str) -> Dict[str, str]:
        """Prepare the data for token request (can be overridden)"""
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
    
    def prepare_token_request_headers(self) -> Dict[str, str]:
        """Prepare headers for token request (can be overridden)"""
        return {"Accept": "application/json"}
    
    async def process_token_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Process the token response (can be overridden)"""
        response.raise_for_status()
        token_data = response.json()
        
        # Check if response contains an error
        if "error" in token_data:
            error_msg = f"OAuth error: {token_data.get('error')} - {token_data.get('error_description', 'No description')}"
            raise ValueError(error_msg)
        
        # Verify that we got an access token
        if "access_token" not in token_data:
            raise ValueError("No access_token received from OAuth provider")
        
        return token_data
    
    def get_provider_name(self) -> str:
        """Get the provider name (derived from class name)"""
        return self.__class__.__name__.lower().replace('oauthhandler', '') 