"""
Google OAuth Handler - Standard OAuth2 implementation
"""
from .base_oauth_handler import BaseOAuthHandler


class GoogleOAuthHandler(BaseOAuthHandler):
    """Google OAuth2 handler"""
    
    def get_auth_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/auth"
    
    def get_token_url(self) -> str:
        return "https://oauth2.googleapis.com/token"
    
    def get_scopes(self) -> list:
        return ["openid", "email", "profile"] 