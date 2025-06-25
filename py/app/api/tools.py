"""
Tools API Endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from pydantic import BaseModel
import json

from ..core.database import get_db
from ..services.tool_service import ToolService
from ..services.integration_service import IntegrationService
from ..services.auth_service import AuthService
from ..core.auth import user_auth_required, AuthResult


class ToolExecutionRequest(BaseModel):
    """Tool execution request"""
    action: str
    parameters: Optional[Dict[str, Any]] = None

# Also support legacy format
class LegacyToolExecutionRequest(BaseModel):
    """Legacy tool execution request"""
    parameters: Dict[str, Any]

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
    
    print(f"🚀 DEBUG [API]: Received request for tool '{tool_name}'")
    print(f"👤 DEBUG [API]: User auth method: {user.auth_method}, user_id param: {user_id}")
    print(f"📦 DEBUG [API]: Request body - action: {request.action}, parameters: {request.parameters}")
    
    # Get effective user_id: for X-API-KEY use parameter, for tokens use authenticated user_id
    effective_user_id = user_id if user.auth_method == "x_api_key" else user.user_id
    
    print(f"🎯 DEBUG [API]: Effective user_id: {effective_user_id}")
    
    if not effective_user_id:
        print(f"❌ DEBUG [API]: No effective user_id found")
        raise HTTPException(status_code=400, detail="user_id is required")
    
    tool_service = ToolService(db)
    
    try:
        print(f"⚡ DEBUG [API]: Starting tool execution: {tool_name}/{request.action}")
        result = await tool_service.execute_tool_action(
            user_id=effective_user_id,
            tool_name=tool_name,
            action_name=request.action,
            parameters=request.parameters or {}
        )
        print(f"✅ DEBUG [API]: Tool execution completed successfully")
        return result
    except Exception as e:
        print(f"💥 DEBUG [API]: Tool execution failed: {str(e)}")
        print(f"🔍 DEBUG [API]: Exception type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


@router.post("/{tool_name}/debug-execute")
async def debug_execute_tool(
    tool_name: str,
    request_obj: Request,
    user: AuthResult = Depends(user_auth_required),
    user_id: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to see raw request body"""
    
    print(f"🔍 DEBUG [RAW]: Received debug request for tool '{tool_name}'")
    print(f"👤 DEBUG [RAW]: User auth method: {user.auth_method}, user_id param: {user_id}")
    
    try:
        # Get raw body
        raw_body = await request_obj.body()
        print(f"📦 DEBUG [RAW]: Raw request body: {raw_body}")
        
        # Try to parse as JSON
        try:
            parsed_body = json.loads(raw_body)
            print(f"📊 DEBUG [RAW]: Parsed JSON: {parsed_body}")
        except json.JSONDecodeError as e:
            print(f"❌ DEBUG [RAW]: JSON parse error: {e}")
            return {"error": "Invalid JSON", "raw_body": raw_body.decode()}
        
        # Get effective user_id
        effective_user_id = user_id if user.auth_method == "x_api_key" else user.user_id
        print(f"🎯 DEBUG [RAW]: Effective user_id: {effective_user_id}")
        
        # Try to extract action and parameters from different formats
        action = None
        parameters = {}
        
        if "action" in parsed_body:
            # Legacy format: {"action": "...", "parameters": {...}}
            action = parsed_body.get("action")
            parameters = parsed_body.get("parameters", {})
            print(f"📝 DEBUG [RAW]: Legacy format detected - action: {action}, params: {parameters}")
        elif "parameters" in parsed_body and "action" in parsed_body.get("parameters", {}):
            # New format: {"parameters": {"action": "...", ...}}
            parameters = parsed_body["parameters"]
            action = parameters.pop("action", None)  # Remove action from parameters
            print(f"📝 DEBUG [RAW]: New format detected - action: {action}, params: {parameters}")
        else:
            print(f"❌ DEBUG [RAW]: Unknown request format")
            return {"error": "Unknown request format", "parsed_body": parsed_body}
        
        if not action:
            return {"error": "No action found in request", "parsed_body": parsed_body}
        
        # Execute the tool
        tool_service = ToolService(db)
        
        print(f"⚡ DEBUG [RAW]: Starting tool execution: {tool_name}/{action}")
        result = await tool_service.execute_tool_action(
            user_id=effective_user_id,
            tool_name=tool_name,
            action_name=action,
            parameters=parameters
        )
        print(f"✅ DEBUG [RAW]: Tool execution completed successfully")
        return result
        
    except Exception as e:
        print(f"💥 DEBUG [RAW]: Debug execution failed: {str(e)}")
        print(f"🔍 DEBUG [RAW]: Exception type: {type(e).__name__}")
        return {"error": str(e), "type": type(e).__name__}


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


