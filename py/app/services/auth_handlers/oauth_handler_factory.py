"""
OAuth Handler Factory - Factory pattern for managing OAuth handlers
"""
from typing import Dict, Type, Optional
from .base_oauth_handler import BaseOAuthHandler
from .github_oauth_handler import GitHubOAuthHandler
from .reddit_oauth_handler import RedditOAuthHandler
from .google_oauth_handler import GoogleOAuthHandler
from .slack_oauth_handler import SlackOAuthHandler


class OAuthHandlerFactory:
    """Factory for creating OAuth handlers"""
    
    # Registry of available handlers
    _handlers: Dict[str, Type[BaseOAuthHandler]] = {
        "github": GitHubOAuthHandler,
        "reddit": RedditOAuthHandler,
        "google": GoogleOAuthHandler,
        "slack": SlackOAuthHandler,
    }
    
    @classmethod
    def register_handler(cls, provider_name: str, handler_class: Type[BaseOAuthHandler]):
        """Register a new OAuth handler"""
        cls._handlers[provider_name] = handler_class
    
    @classmethod
    def get_handler(cls, provider_name: str, client_id: str, client_secret: str) -> Optional[BaseOAuthHandler]:
        """Get an OAuth handler instance for the given provider"""
        handler_class = cls._handlers.get(provider_name.lower())
        
        if handler_class is None:
            raise ValueError(f"No OAuth handler found for provider: {provider_name}")
        
        return handler_class(client_id, client_secret)
    
    @classmethod
    def is_supported(cls, provider_name: str) -> bool:
        """Check if a provider is supported"""
        return provider_name.lower() in cls._handlers
    
    @classmethod
    def get_supported_providers(cls) -> list:
        """Get list of supported providers"""
        return list(cls._handlers.keys())
    
    @classmethod
    def get_provider_config(cls, provider_name: str) -> Dict[str, any]:
        """Get basic configuration for a provider (without credentials)"""
        if not cls.is_supported(provider_name):
            raise ValueError(f"Unsupported provider: {provider_name}")
        
        # Create a dummy instance to get URLs and scopes
        dummy_handler = cls._handlers[provider_name.lower()]("dummy", "dummy")
        
        return {
            "auth_url": dummy_handler.get_auth_url(),
            "token_url": dummy_handler.get_token_url(),
            "scopes": dummy_handler.get_scopes()
        } 