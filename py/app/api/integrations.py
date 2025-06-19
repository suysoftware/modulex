"""
Integration Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from pydantic import BaseModel

from ..core.database import get_db
from ..core.auth import system_auth_required, AuthResult
from ..services.integration_service import IntegrationService

router = APIRouter(prefix="/integrations", tags=["Integrations"])

# Request/Response Models
class ToolInstallRequest(BaseModel):
    """Request model for installing a tool"""
    tool_name: str
    config_data: Dict[str, str]

class ToolConfigUpdateRequest(BaseModel):
    """Request model for updating tool configuration"""
    config_data: Dict[str, str]

class SyncResponse(BaseModel):
    """Response model for sync operations"""
    success: bool
    message: str
    synced_count: int

@router.get("/available")
async def get_available_tools(
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(system_auth_required)
):
    """Get all available tools that can be installed"""
    integration_service = IntegrationService(db)
    
    try:
        tools = await integration_service.get_available_tools()
        return {
            "success": True,
            "tools": tools,
            "total": len(tools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving available tools: {str(e)}")

@router.get("/installed")
async def get_installed_tools(
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(system_auth_required)
):
    """Get all currently installed tools"""
    integration_service = IntegrationService(db)
    
    try:
        tools = await integration_service.get_installed_tools()
        return {
            "success": True,
            "tools": tools,
            "total": len(tools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving installed tools: {str(e)}")

@router.post("/install")
async def install_tool(
    request: ToolInstallRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(system_auth_required)
):
    """Manually install a tool with configuration"""
    integration_service = IntegrationService(db)
    
    try:
        success = await integration_service.install_tool(
            tool_name=request.tool_name,
            config_data=request.config_data
        )
        
        return {
            "success": success,
            "message": f"Tool '{request.tool_name}' installed successfully",
            "tool_name": request.tool_name
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error installing tool: {str(e)}")

@router.delete("/{tool_name}")
async def uninstall_tool(
    tool_name: str,
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(system_auth_required)
):
    """Uninstall a tool"""
    integration_service = IntegrationService(db)
    
    try:
        success = await integration_service.uninstall_tool(tool_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found or not installed")
        
        return {
            "success": success,
            "message": f"Tool '{tool_name}' uninstalled successfully",
            "tool_name": tool_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uninstalling tool: {str(e)}")

@router.put("/{tool_name}/config")
async def update_tool_config(
    tool_name: str,
    request: ToolConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(system_auth_required)
):
    """Update tool configuration"""
    integration_service = IntegrationService(db)
    
    try:
        success = await integration_service.update_tool_config(
            tool_name=tool_name,
            config_data=request.config_data
        )
        
        return {
            "success": success,
            "message": f"Tool '{tool_name}' configuration updated successfully",
            "tool_name": tool_name
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating tool configuration: {str(e)}")

@router.get("/{tool_name}/config")
async def get_tool_config(
    tool_name: str,
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(system_auth_required)
):
    """Get tool configuration (environment variables)"""
    integration_service = IntegrationService(db)
    
    try:
        config = await integration_service.get_tool_environment(tool_name)
        
        return {
            "success": True,
            "tool_name": tool_name,
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tool configuration: {str(e)}")

@router.post("/sync")
async def sync_tools(
    auto_install: bool = Query(True, description="Auto-install tools from environment"),
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(system_auth_required)
):
    """Manually trigger sync of available tools and auto-install from environment"""
    integration_service = IntegrationService(db)
    
    try:
        # Sync available tools from integrations folder
        synced_count = await integration_service.sync_available_tools()
        
        installed_count = 0
        if auto_install:
            # Auto-install from environment variables
            installed_count = await integration_service.auto_install_from_env()
        
        return {
            "success": True,
            "message": f"Sync completed: {synced_count} tools synced, {installed_count} tools auto-installed",
            "synced_count": synced_count,
            "installed_count": installed_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during sync: {str(e)}")

@router.get("/{tool_name}/schema")
async def get_tool_schema(
    tool_name: str,
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(system_auth_required)
):
    """Get tool schema (available actions and required environment variables)"""
    integration_service = IntegrationService(db)
    
    try:
        # Get from available tools
        tools = await integration_service.get_available_tools()
        tool_schema = next((tool for tool in tools if tool["name"] == tool_name), None)
        
        if not tool_schema:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found in available tools")
        
        return {
            "success": True,
            "tool_name": tool_name,
            "schema": {
                "name": tool_schema["name"],
                "display_name": tool_schema["display_name"],
                "description": tool_schema["description"],
                "author": tool_schema["author"],
                "version": tool_schema["version"],
                "actions": tool_schema["actions"],
                "environment_variables": tool_schema["environment_variables"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tool schema: {str(e)}")

@router.get("/status")
async def get_integration_status(
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(system_auth_required)
):
    """Get integration system status"""
    integration_service = IntegrationService(db)
    
    try:
        available_tools = await integration_service.get_available_tools()
        installed_tools = await integration_service.get_installed_tools()
        
        return {
            "success": True,
            "status": {
                "available_tools_count": len(available_tools),
                "installed_tools_count": len(installed_tools),
                "available_tools": [tool["name"] for tool in available_tools],
                "installed_tools": [tool["name"] for tool in installed_tools],
                "integrations_path": str(integration_service.integrations_path),
                "env_file_path": str(integration_service.env_file_path)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving integration status: {str(e)}") 