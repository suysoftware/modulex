"""
Tools API Endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from pydantic import BaseModel

from ..core.database import get_db
from ..services.tool_service import ToolService
from ..services.integration_service import IntegrationService
from ..services.auth_service import AuthService
from ..core.auth import user_auth_required, AuthResult


class ToolExecutionRequest(BaseModel):
    """Tool execution request"""
    action: str
    parameters: Optional[Dict[str, Any]] = None

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.post("/{tool_name}/execute")
async def execute_tool(
    tool_name: str,
    request: ToolExecutionRequest,
    user: AuthResult = Depends(user_auth_required),
    user_id: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Execute a tool action - Auth required with user_id"""
    
    # Get effective user_id: for X-API-KEY use parameter, for tokens use authenticated user_id
    effective_user_id = user_id if user.auth_method == "x_api_key" else user.user_id
    
    if not effective_user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    tool_service = ToolService(db)
    
    try:
        result = await tool_service.execute_tool_action(
            user_id=effective_user_id,
            tool_name=tool_name,
            action_name=request.action,
            parameters=request.parameters or {}
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


@router.get("/openai-tools")
async def get_user_openai_tools(
    user: AuthResult = Depends(user_auth_required),
    user_id: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get user's authenticated and active tools in OpenAI tools format"""
    
    # Get effective user_id: for X-API-KEY use parameter, for tokens use authenticated user_id
    effective_user_id = user_id if user.auth_method == "x_api_key" else user.user_id
    
    if not effective_user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    auth_service = AuthService(db)
    tool_service = ToolService(db)
    
    try:
        # Get user's authenticated and active tools only
        user_tools = await auth_service.get_user_active_tools(effective_user_id)
        
        if not user_tools:
            import logging
            logging.info(f"No active tools found for user_id={effective_user_id}")
        
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
        logging.error(f"Error retrieving OpenAI tools for user {effective_user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving OpenAI tools: {str(e)}")


