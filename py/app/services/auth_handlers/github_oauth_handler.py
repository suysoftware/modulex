"""
GitHub OAuth Handler - Standard OAuth2 implementation
"""
from .base_oauth_handler import BaseOAuthHandler


class GitHubOAuthHandler(BaseOAuthHandler):
    """GitHub OAuth2 handler"""
    
    def get_auth_url(self) -> str:
        return "https://github.com/login/oauth/authorize"
    
    def get_token_url(self) -> str:
        return "https://github.com/login/oauth/access_token"
    
    def get_scopes(self) -> list:
        return ["repo", "user"] 