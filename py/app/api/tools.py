"""
Tool API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from ..core.database import get_db
from ..services.tool_service import ToolService
from ..services.auth_service import AuthService
from ..core.config import verify_api_key

router = APIRouter(prefix="/tools", tags=["Tools"])


class ToolExecutionRequest(BaseModel):
    action: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class OpenAIToolExecutionRequest(BaseModel):
    """Request model for direct tool execution (OpenAI/Vercel AI SDK format)"""
    parameters: Optional[Dict[str, Any]] = None


@router.get("/")
async def list_tools(db: AsyncSession = Depends(get_db), _: bool = Depends(verify_api_key)):
    """List all available tools"""
    tool_service = ToolService(db)
    
    try:
        tools = await tool_service.list_available_tools()
        return {
            "tools": tools,
            "total": len(tools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tools: {str(e)}")


@router.get("/{tool_name}")
async def get_tool_info(tool_name: str, db: AsyncSession = Depends(get_db), _: bool = Depends(verify_api_key)):
    """Get information about a specific tool"""
    tool_service = ToolService(db)
    
    tool_info = await tool_service.get_tool_info(tool_name)
    if not tool_info:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    
    return tool_info


@router.post("/{tool_name}/execute")
async def execute_tool(
    tool_name: str,
    request: ToolExecutionRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """Execute a tool action (supports both legacy and new formats)"""
    tool_service = ToolService(db)
    
    try:
        # Handle different request formats
        if hasattr(request, 'action') and request.action:
            # Legacy format: action is directly in the request
            action = request.action
            parameters = request.parameters or {}
        elif hasattr(request, 'parameters') and request.parameters and 'action' in request.parameters:
            # New format: action is inside parameters
            parameters = request.parameters.copy()
            action = parameters.pop('action')
        else:
            raise ValueError("Missing action parameter")
        
        result = await tool_service.execute_tool(
            user_id=user_id,
            tool_name=tool_name,
            action=action,
            parameters=parameters
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution error: {str(e)}")


# New endpoints for OpenAI/Vercel AI SDK compatibility
@router.get("/openai-tools")
async def get_user_openai_tools(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """Get user's authenticated and active tools in OpenAI tools format for Vercel AI SDK"""
    auth_service = AuthService(db)
    tool_service = ToolService(db)
    
    try:
        # Get user's authenticated and active tools only
        user_tools = await auth_service.get_user_active_tools(user_id)
        
        if not user_tools:
            # Log for debugging but return empty list (not an error)
            import logging
            logging.info(f"No active tools found for user_id={user_id}")
        
        openai_tools = []
        
        for user_tool in user_tools:
            tool_name = user_tool["tool_name"]
            disabled_actions = user_tool.get("disabled_actions", [])
            tool_info = await tool_service.get_tool_info(tool_name)
            
            if tool_info and tool_info.get("actions"):
                for action in tool_info["actions"]:
                    # Skip disabled actions
                    if action['name'] in disabled_actions:
                        continue
                    
                    # Convert each enabled action to OpenAI tool format
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": f"{tool_name}_{action['name']}",
                            "description": action.get("description", f"{action['name']} action for {tool_name}"),
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        "metadata": {
                            "tool_key": tool_name,
                            "action": action['name']
                        }
                    }
                    
                    # Convert action parameters to OpenAI function parameters format
                    if action.get("parameters"):
                        for param_name, param_info in action["parameters"].items():
                            openai_tool["function"]["parameters"]["properties"][param_name] = {
                                "type": param_info.get("type", "string"),
                                "description": param_info.get("description", f"{param_name} parameter")
                            }
                            
                            # Add to required list if parameter is required
                            if param_info.get("required", False):
                                openai_tool["function"]["parameters"]["required"].append(param_name)
                    
                    openai_tools.append(openai_tool)
        
        return openai_tools
        
    except Exception as e:
        import logging
        logging.error(f"Error retrieving OpenAI tools for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving OpenAI tools: {str(e)}")