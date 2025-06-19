"""
TOML Configuration Loader for ModuleX

Simple loader that only reads the auth provider setting from TOML files.
Supports custom config path via MODULEX_CONFIG_PATH environment variable.
"""

import os
import toml
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TOMLConfig:
    """Simple TOML Configuration loader for auth provider only"""
    
    def __init__(self):
        self.default_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "modulex.toml"
        )
        self._config_info: Optional[Dict[str, Any]] = None
        self._loaded_config_path: Optional[str] = None
        
    def _determine_config_path(self) -> tuple[str, str]:
        """
        Determine which config file to use
        
        Returns:
            tuple: (config_path, config_type)
            config_type: 'default' or 'custom'
        """
        custom_config_path = os.getenv("MODULEX_CONFIG_PATH")
        
        # Check if MODULEX_CONFIG_PATH is set and not empty
        if custom_config_path and custom_config_path.strip():
            custom_config_path = custom_config_path.strip()
            
            if os.path.exists(custom_config_path):
                if custom_config_path.endswith('.toml'):
                    logger.info(f"Using custom config: {custom_config_path}")
                    return custom_config_path, "custom"
                else:
                    logger.warning(f"MODULEX_CONFIG_PATH file is not a .toml file: {custom_config_path}")
            else:
                logger.warning(f"MODULEX_CONFIG_PATH file does not exist: {custom_config_path}")
        
        # Fallback to default config
        if os.path.exists(self.default_config_path):
            logger.info(f"Using default config: {self.default_config_path}")
            return self.default_config_path, "default"
        else:
            logger.warning(f"Default config file not found: {self.default_config_path}")
            return self.default_config_path, "default"  # Return path anyway for error handling
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get information about configuration paths and status"""
        custom_config_path = os.getenv("MODULEX_CONFIG_PATH")
        config_path, config_type = self._determine_config_path()
        
        return {
            "environment_variable": {
                "MODULEX_CONFIG_PATH": custom_config_path,
                "is_set": bool(custom_config_path and custom_config_path.strip()),
                "is_empty": not bool(custom_config_path and custom_config_path.strip())
            },
            "default_config": {
                "path": self.default_config_path,
                "exists": os.path.exists(self.default_config_path)
            },
            "custom_config": {
                "path": custom_config_path,
                "exists": os.path.exists(custom_config_path) if custom_config_path else False,
                "is_toml": custom_config_path.endswith('.toml') if custom_config_path else False
            },
            "active_config": {
                "path": config_path,
                "type": config_type,
                "exists": os.path.exists(config_path)
            }
        }
    
    def get_auth_provider(self) -> str:
        """Get the authentication provider setting from TOML config"""
        # Default value
        auth_provider = "default"
        
        # Determine which config to use
        config_path, config_type = self._determine_config_path()
        self._loaded_config_path = config_path
        
        if os.path.exists(config_path):
            try:
                config = toml.load(config_path)
                auth_provider = config.get("auth", {}).get("provider", "default")
                logger.info(f"Loaded auth provider '{auth_provider}' from {config_type} config: {config_path}")
            except Exception as e:
                logger.error(f"Error loading {config_type} config from {config_path}: {e}")
        else:
            logger.error(f"Config file does not exist: {config_path}")
        
        return auth_provider
    
    def reload(self) -> None:
        """Reload configuration from files"""
        logger.info("Reloading TOML configuration...")
        self._config_info = None
        self._loaded_config_path = None
        # get_auth_provider will re-determine the config path
    
    def get_loaded_config_path(self) -> Optional[str]:
        """Get the path of the currently loaded config file"""
        return self._loaded_config_path

# Global instance
toml_config = TOMLConfig() 