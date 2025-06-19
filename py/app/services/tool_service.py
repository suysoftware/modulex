"""
Tool Execution Service
"""
import subprocess
import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from functools import lru_cache

from .auth_service import AuthService
from ..config.load_config import get_load_config

# Configure logger for tool service
logger = logging.getLogger(__name__)

class ToolService:
    """Service for executing tools"""
    
    def __init__(self, db: AsyncSession, max_concurrent_executions: int = None):
        self.db = db
        self.auth_service = AuthService(db)
        self.integrations_path = Path("integrations")
        
        # Load configuration based on environment or Azure setup
        self.load_config = get_load_config()
        
        # Use provided value or load from config
        if max_concurrent_executions is None:
            max_concurrent_executions = self.load_config.max_concurrent_executions
            
        # Dynamic semaphore based on expected load
        # For Azure E8ds v5: 25-35 concurrent executions recommended
        self._execution_semaphore = asyncio.Semaphore(max_concurrent_executions)
        
        # Statistics tracking
        self._active_executions = 0
        self._queued_executions = 0
        
        logger.info(f"ToolService initialized with {max_concurrent_executions} concurrent executions")
        logger.info(f"Load config: {os.getenv('LOAD_CONFIG', 'medium')}")
    
    async def execute_tool(self, user_id: str, tool_name: str, action: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool action for a user"""
        if parameters is None:
            parameters = {}
        
        # Check queue size limit
        if self._queued_executions >= self.load_config.max_queue_size:
            return {
                "success": False,
                "error": f"Server busy. Queue limit ({self.load_config.max_queue_size}) exceeded. Please try again later.",
                "tool_name": tool_name,
                "action": action
            }
        
        # Track queued requests for monitoring
        self._queued_executions += 1
        
        try:
            # Get user credentials
            credentials = await self.auth_service.get_user_credentials(user_id, tool_name)
            if not credentials:
                # Try to clean up invalid credentials first
                await self.auth_service.cleanup_invalid_credentials(user_id, tool_name)
                raise ValueError(f"User {user_id} not authenticated for {tool_name}. Please complete authentication.")
            
            # Check if credentials contain OAuth errors (additional safety check)
            if "error" in credentials and "access_token" not in credentials:
                logger.debug(f"Found invalid credentials with error, cleaning up for user {user_id}")
                await self.auth_service.cleanup_invalid_credentials(user_id, tool_name)
                raise ValueError(f"Invalid authentication for {tool_name}. Please re-authenticate.")

            # Find tool script
            tool_script_path = self.integrations_path / tool_name / "main.py"
            if not tool_script_path.exists():
                raise ValueError(f"Tool script not found: {tool_script_path}")
            
            # Limit concurrent executions to prevent resource exhaustion
            async with self._execution_semaphore:
                self._queued_executions -= 1
                self._active_executions += 1
                
                try:
                    # Prepare environment variables (thread-safe: each call gets its own env dict)
                    env = os.environ.copy()
                    env.update(self._prepare_tool_env(credentials))
                    
                    # Prepare execution data
                    execution_data = {
                        "action": action,
                        "parameters": parameters,
                        "user_id": user_id,
                        "user_credentials": credentials  # Pass credentials to all tools
                    }
                    
                    # Execute tool script in separate process (isolated environment)
                    result = await asyncio.create_subprocess_exec(
                        "python", str(tool_script_path),
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env
                    )
                    
                    stdout, stderr = await asyncio.wait_for(
                        result.communicate(input=json.dumps(execution_data).encode()),
                        timeout=self.load_config.request_timeout
                    )
                    
                    if result.returncode == 0:
                        # Success
                        try:
                            output = json.loads(stdout.decode())
                            return {
                                "success": True,
                                "result": output,
                                "tool_name": tool_name,
                                "action": action
                            }
                        except json.JSONDecodeError:
                            return {
                                "success": True,
                                "result": stdout.decode(),
                                "tool_name": tool_name,
                                "action": action
                            }
                    else:
                        # Error
                        return {
                            "success": False,
                            "error": stderr.decode() or stdout.decode(),
                            "tool_name": tool_name,
                            "action": action
                        }
                        
                except asyncio.TimeoutError:
                    return {
                        "success": False,
                        "error": f"Tool execution timed out after {self.load_config.request_timeout}s",
                        "tool_name": tool_name,
                        "action": action
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "tool_name": tool_name,
                        "action": action
                    }
                finally:
                    self._active_executions -= 1
        finally:
            # Ensure queue count is decremented even if early exit
            if self._queued_executions > 0:
                self._queued_executions -= 1
    
    @lru_cache(maxsize=1000)
    def _get_excluded_credential_keys(self) -> frozenset:
        """Cache excluded credential keys for performance"""
        return frozenset(["auth_type", "registered_at"])

    def _prepare_tool_env(self, credentials: Dict[str, Any]) -> Dict[str, str]:
        """Prepare environment variables for tool execution
        
        Optimized for high-concurrency scenarios:
        - Minimal logging with level checks
        - Efficient dictionary operations
        - Cached exclude list
        """
        env = {}
        excluded_keys = self._get_excluded_credential_keys()
        
        # Debug logging only if enabled (prevents I/O overhead)
        debug_enabled = logger.isEnabledFor(logging.DEBUG)
        
        if debug_enabled:
            logger.debug(f"Preparing env for credential keys: {list(credentials.keys())}")
        
        # Add OAuth auth environment variables (most common case first)
        access_token = credentials.get("access_token")
        if access_token:
            env["ACCESS_TOKEN"] = access_token
            if debug_enabled:
                logger.debug("ACCESS_TOKEN configured")
        
        refresh_token = credentials.get("refresh_token")
        if refresh_token:
            env["REFRESH_TOKEN"] = refresh_token
            if debug_enabled:
                logger.debug("REFRESH_TOKEN configured")
        
        # Add other credential fields as environment variables
        # Using dict comprehension for better performance
        env.update({
            key.upper(): value 
            for key, value in credentials.items() 
            if isinstance(value, str) and key not in excluded_keys
        })
        
        if debug_enabled:
            logger.debug(f"Environment prepared with {len(env)} variables")
        
        return env
    
    async def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool information"""
        info_file = self.integrations_path / tool_name / "info.json"
        
        if not info_file.exists():
            return None
        
        try:
            with open(info_file, 'r') as f:
                tool_info = json.load(f)
                return tool_info
        except Exception as e:
            import logging
            logging.error(f"Error loading tool info for {tool_name}: {e}")
            return None
    
    async def list_available_tools(self) -> list:
        """List all available tools"""
        tools = []
        
        if not self.integrations_path.exists():
            return tools
        
        for tool_dir in self.integrations_path.iterdir():
            if tool_dir.is_dir():
                tool_info = await self.get_tool_info(tool_dir.name)
                if tool_info:
                    tools.append(tool_info)
                else:
                    # Basic info if no info.json
                    tools.append({
                        "name": tool_dir.name,
                        "description": f"{tool_dir.name} integration",
                        "actions": []
                    })
        
        return tools
    
    async def get_all_tools(self) -> list:
        """Alias for list_available_tools for compatibility"""
        return await self.list_available_tools()
    
    async def execute_tool_action(self, user_id: str, tool_name: str, action_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool action for a user - alias for execute_tool"""
        return await self.execute_tool(user_id, tool_name, action_name, parameters)
