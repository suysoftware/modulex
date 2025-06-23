"""
Slack OAuth Handler - Standard OAuth2 implementation
"""
from .base_oauth_handler import BaseOAuthHandler


class SlackOAuthHandler(BaseOAuthHandler):
    """Slack OAuth2 handler"""
    
    def get_auth_url(self) -> str:
        return "https://slack.com/oauth/v2/authorize"
    
    def get_token_url(self) -> str:
        return "https://slack.com/api/oauth.v2.access"
    
    def get_scopes(self) -> list:
        return ["chat:write", "channels:read"] 