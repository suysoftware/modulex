"""
Integration Service for Dynamic Tool Management
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from ..models.integration import AvailableTool, InstalledTool, InstalledToolVariable
from ..core.encryption import encrypt_tool_variable, decrypt_tool_variable

logger = logging.getLogger(__name__)

class IntegrationService:
    """Service for managing dynamic tool integrations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.integrations_path = Path("integrations")
        self.env_file_path = Path("docker/env/modulex.env")
    
    async def sync_available_tools(self) -> int:
        """Sync available tools from integrations folder to database"""
        logger.info("🔄 Syncing available tools from integrations folder...")
        
        if not self.integrations_path.exists():
            logger.warning(f"Integrations path not found: {self.integrations_path}")
            return 0
        
        synced_count = 0
        available_tools_data = []
        
        # Scan integrations folder
        for tool_dir in self.integrations_path.iterdir():
            if not tool_dir.is_dir():
                continue
                
            info_file = tool_dir / "info.json"
            if not info_file.exists():
                logger.warning(f"No info.json found for tool: {tool_dir.name}")
                continue
            
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    tool_info = json.load(f)
                
                # Validate required fields
                if not all(key in tool_info for key in ["name", "display_name"]):
                    logger.error(f"Invalid info.json for tool {tool_dir.name}: missing required fields")
                    continue
                
                # Prepare actions data
                actions = []
                for action in tool_info.get("actions", []):
                    if "name" in action:
                        actions.append({
                            "name": action["name"],
                            "description": action.get("description", "")
                        })
                
                # Prepare environment variables data
                env_vars = []
                for env_var in tool_info.get("setup_environment_variables", []):
                    if "name" in env_var:
                        env_vars.append({
                            "name": env_var["name"],
                            "description": env_var.get("description", ""),
                            "sample_format": env_var.get("sample_format", "")
                        })
                
                tool_data = {
                    "name": tool_info["name"],
                    "display_name": tool_info["display_name"],
                    "description": tool_info.get("description", ""),
                    "author": tool_info.get("author", ""),
                    "version": tool_info.get("version", "1.0.0"),
                    "actions": actions,
                    "environment_variables": env_vars
                }
                
                available_tools_data.append(tool_data)
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error processing tool {tool_dir.name}: {str(e)}")
                continue
        
        # Upsert to database
        if available_tools_data:
            for tool_data in available_tools_data:
                stmt = insert(AvailableTool).values(**tool_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['name'],
                    set_={
                        'display_name': stmt.excluded.display_name,
                        'description': stmt.excluded.description,
                        'author': stmt.excluded.author,
                        'version': stmt.excluded.version,
                        'actions': stmt.excluded.actions,
                        'environment_variables': stmt.excluded.environment_variables,
                        'updated_at': stmt.excluded.updated_at
                    }
                )
                await self.db.execute(stmt)
            
            await self.db.commit()
        
        logger.info(f"✅ Synced {synced_count} available tools to database")
        return synced_count
    
    async def auto_install_from_env(self) -> int:
        """Auto-install tools from modulex.env file"""
        logger.info("🔄 Auto-installing tools from environment variables...")
        
        if not self.env_file_path.exists():
            logger.warning(f"Environment file not found: {self.env_file_path}")
            return 0
        
        # Read environment file
        env_vars = self._read_env_file()
        if not env_vars:
            logger.info("No environment variables found")
            return 0
        
        # Get available tools from database
        result = await self.db.execute(select(AvailableTool))
        available_tools = {tool.name: tool for tool in result.scalars().all()}
        
        installed_count = 0
        
        for tool_name, tool in available_tools.items():
            # Check if tool has required env variables in the env file
            required_env_vars = {var["name"] for var in tool.environment_variables}
            found_env_vars = {key: value for key, value in env_vars.items() 
                            if key in required_env_vars and value.strip()}
            
            if not found_env_vars:
                continue  # No env vars found for this tool
            
            logger.info(f"Found environment variables for {tool_name}: {list(found_env_vars.keys())}")
            
            # Check if tool is already installed
            result = await self.db.execute(
                select(InstalledTool).where(InstalledTool.name == tool_name)
            )
            existing_tool = result.scalar_one_or_none()
            
            if existing_tool:
                # Tool already installed, just update environment variables
                await self._update_tool_environment(tool_name, found_env_vars)
                logger.info(f"Updated environment variables for existing tool: {tool_name}")
            else:
                # Install new tool
                await self._install_tool_from_available(tool, found_env_vars)
                installed_count += 1
                logger.info(f"Auto-installed tool: {tool_name}")
        
        await self.db.commit()
        logger.info(f"✅ Auto-installed {installed_count} tools from environment")
        return installed_count
    
    def _read_env_file(self) -> Dict[str, str]:
        """Read environment variables from modulex.env file"""
        env_vars = {}
        
        try:
            with open(self.env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if value:  # Only store non-empty values
                            env_vars[key] = value
                            
        except Exception as e:
            logger.error(f"Error reading environment file: {str(e)}")
            
        return env_vars
    
    async def _install_tool_from_available(self, available_tool: AvailableTool, env_vars: Dict[str, str]):
        """Install a tool from available tools with given environment variables"""
        # All actions enabled by default
        enabled_actions = available_tool.actions
        disabled_actions = []
        
        # Create installed tool record
        installed_tool = InstalledTool(
            name=available_tool.name,
            display_name=available_tool.display_name,
            author=available_tool.author,
            version=available_tool.version,
            enabled_actions=enabled_actions,
            disabled_actions=disabled_actions
        )
        
        self.db.add(installed_tool)
        await self.db.flush()  # Get the ID
        
        # Save environment variables
        await self._save_tool_environment(available_tool.name, env_vars)
    
    async def _update_tool_environment(self, tool_name: str, env_vars: Dict[str, str]):
        """Update environment variables for an existing tool"""
        await self._save_tool_environment(tool_name, env_vars)
    
    async def _save_tool_environment(self, tool_name: str, env_vars: Dict[str, str]):
        """Save encrypted environment variables for a tool"""
        for key, value in env_vars.items():
            encrypted_value = encrypt_tool_variable(tool_name, value)
            
            # Upsert environment variable
            stmt = insert(InstalledToolVariable).values(
                name=tool_name,
                variable_key=key,
                variable_value=encrypted_value
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['name', 'variable_key'],
                set_={
                    'variable_value': stmt.excluded.variable_value,
                    'updated_at': stmt.excluded.updated_at
                }
            )
            await self.db.execute(stmt)
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools"""
        result = await self.db.execute(select(AvailableTool))
        tools = result.scalars().all()
        
        return [
            {
                "id": tool.id,
                "name": tool.name,
                "display_name": tool.display_name,
                "description": tool.description,
                "author": tool.author,
                "version": tool.version,
                "actions": tool.actions,
                "environment_variables": tool.environment_variables,
                "created_at": tool.created_at.isoformat() if tool.created_at else None,
                "updated_at": tool.updated_at.isoformat() if tool.updated_at else None
            }
            for tool in tools
        ]
    
    async def get_available_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific available tool by name"""
        result = await self.db.execute(
            select(AvailableTool).where(AvailableTool.name == tool_name)
        )
        tool = result.scalar_one_or_none()
        
        if not tool:
            return None
        
        return {
            "id": tool.id,
            "name": tool.name,
            "display_name": tool.display_name,
            "description": tool.description,
            "author": tool.author,
            "version": tool.version,
            "actions": tool.actions,
            "environment_variables": tool.environment_variables,
            "created_at": tool.created_at.isoformat() if tool.created_at else None,
            "updated_at": tool.updated_at.isoformat() if tool.updated_at else None
        }
    
    async def get_installed_tools(self) -> List[Dict[str, Any]]:
        """Get all installed tools"""
        result = await self.db.execute(select(InstalledTool))
        tools = result.scalars().all()
        
        return [
            {
                "id": tool.id,
                "name": tool.name,
                "display_name": tool.display_name,
                "author": tool.author,
                "version": tool.version,
                "enabled_actions": tool.enabled_actions,
                "disabled_actions": tool.disabled_actions,
                "installed_at": tool.installed_at.isoformat() if tool.installed_at else None,
                "updated_at": tool.updated_at.isoformat() if tool.updated_at else None
            }
            for tool in tools
        ]
    
    async def install_tool(self, tool_name: str, config_data: Dict[str, str]) -> bool:
        """Manually install a tool with given configuration"""
        # Get available tool
        result = await self.db.execute(
            select(AvailableTool).where(AvailableTool.name == tool_name)
        )
        available_tool = result.scalar_one_or_none()
        
        if not available_tool:
            raise ValueError(f"Tool '{tool_name}' not found in available tools")
        
        # Check if already installed
        result = await self.db.execute(
            select(InstalledTool).where(InstalledTool.name == tool_name)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"Tool '{tool_name}' is already installed")
        
        # Install the tool
        await self._install_tool_from_available(available_tool, config_data)
        await self.db.commit()
        
        logger.info(f"Manually installed tool: {tool_name}")
        return True
    
    async def uninstall_tool(self, tool_name: str) -> bool:
        """Uninstall a tool"""
        # Remove from installed tools
        result = await self.db.execute(
            delete(InstalledTool).where(InstalledTool.name == tool_name)
        )
        
        if result.rowcount == 0:
            return False
        
        # Remove environment variables
        await self.db.execute(
            delete(InstalledToolVariable).where(InstalledToolVariable.name == tool_name)
        )
        
        await self.db.commit()
        logger.info(f"Uninstalled tool: {tool_name}")
        return True
    
    async def get_tool_environment(self, tool_name: str) -> Dict[str, str]:
        """Get decrypted environment variables for a tool"""
        result = await self.db.execute(
            select(InstalledToolVariable).where(InstalledToolVariable.name == tool_name)
        )
        variables = result.scalars().all()
        
        env_vars = {}
        for var in variables:
            try:
                decrypted_value = decrypt_tool_variable(tool_name, var.variable_value)
                env_vars[var.variable_key] = decrypted_value
            except Exception as e:
                logger.error(f"Error decrypting variable {var.variable_key} for tool {tool_name}: {str(e)}")
                
        return env_vars
    
    async def update_tool_config(self, tool_name: str, config_data: Dict[str, str]) -> bool:
        """Update tool configuration"""
        # Check if tool is installed
        result = await self.db.execute(
            select(InstalledTool).where(InstalledTool.name == tool_name)
        )
        if not result.scalar_one_or_none():
            raise ValueError(f"Tool '{tool_name}' is not installed")
        
        # Update environment variables
        await self._save_tool_environment(tool_name, config_data)
        await self.db.commit()
        
        logger.info(f"Updated configuration for tool: {tool_name}")
        return True 