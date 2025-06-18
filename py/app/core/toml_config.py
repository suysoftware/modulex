"""
TOML Configuration Loader for ModuleX

Simple loader that only reads the auth provider setting from TOML files.
"""

import os
import toml
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TOMLConfig:
    """Simple TOML Configuration loader for auth provider only"""
    
    def __init__(self):
        self.default_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "modulex.toml"
        )
        
    def get_auth_provider(self) -> str:
        """Get the authentication provider setting from TOML config"""
        # Default value
        auth_provider = "default"
        
        # Try to load from default config first
        if os.path.exists(self.default_config_path):
            try:
                config = toml.load(self.default_config_path)
                auth_provider = config.get("auth", {}).get("provider", "default")
            except Exception as e:
                logger.warning(f"Error loading default config: {e}")
        
        # Try to load from custom config if specified
        custom_config_path = os.getenv("MODULEX_CONFIG_PATH")
        if custom_config_path and os.path.exists(custom_config_path):
            try:
                config = toml.load(custom_config_path)
                auth_provider = config.get("auth", {}).get("provider", auth_provider)
            except Exception as e:
                logger.warning(f"Error loading custom config: {e}")
        
        return auth_provider

# Global instance
toml_config = TOMLConfig() 