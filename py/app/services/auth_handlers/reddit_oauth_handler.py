"""
Reddit OAuth Handler - OAuth2 with Basic Auth requirements
"""
import base64
from typing import Dict
from .base_oauth_handler import BaseOAuthHandler


class RedditOAuthHandler(BaseOAuthHandler):
    """Reddit OAuth2 handler with Basic Auth for token exchange"""
    
    def get_auth_url(self) -> str:
        return "https://www.reddit.com/api/v1/authorize"
    
    def get_token_url(self) -> str:
        return "https://www.reddit.com/api/v1/access_token"
    
    def get_scopes(self) -> list:
        return ["identity", "read", "submit", "vote", "save"]
    
    def prepare_token_request_data(self, code: str, redirect_uri: str) -> Dict[str, str]:
        """Reddit doesn't need client_id/client_secret in body when using Basic Auth"""
        return {
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
    
    def prepare_token_request_headers(self) -> Dict[str, str]:
        """Reddit requires Basic Auth for token exchange"""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        return {
            "Authorization": f"Basic {auth_bytes}",
            "User-Agent": "ModuleX/1.0",
            "Accept": "application/json"
        } 