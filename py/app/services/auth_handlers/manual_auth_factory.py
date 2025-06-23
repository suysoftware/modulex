"""
Manual Auth Handler Factory - Creates manual authentication handlers
"""
from typing import Dict, Type
from .manual_auth_handler import BaseManualAuthHandler
from .r2r_manual_auth_handler import R2RManualAuthHandler
from .form_manual_auth_handler import FormManualAuthHandler


class ManualAuthHandlerFactory:
    """Factory for creating manual auth handlers"""
    
    _handlers: Dict[str, Type[BaseManualAuthHandler]] = {
        "r2r": R2RManualAuthHandler,
        "n8n": FormManualAuthHandler,
    }
    
    @classmethod
    def get_handler(cls, tool_name: str) -> BaseManualAuthHandler:
        """Get manual auth handler for tool"""
        if tool_name not in cls._handlers:
            raise ValueError(f"Manual auth handler not supported for tool: {tool_name}")
        
        handler_class = cls._handlers[tool_name]
        
        # Special handling for form-based tools that need tool_name
        if handler_class == FormManualAuthHandler:
            return handler_class(tool_name)
        
        return handler_class()
    
    @classmethod
    def register_handler(cls, tool_name: str, handler_class: Type[BaseManualAuthHandler]):
        """Register a new manual auth handler"""
        cls._handlers[tool_name] = handler_class
    
    @classmethod
    def get_supported_tools(cls):
        """Get list of supported manual auth tools"""
        return list(cls._handlers.keys()) 