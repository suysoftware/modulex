"""
Authentication API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from pydantic import BaseModel

from ..core.database import get_db
from ..services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


class ManualAuthRequest(BaseModel):
    """Manual authentication request for any tool"""
    user_id: str
    tool_name: str
    credentials: Dict[str, Any]  # Flexible credentials structure


class ToolActiveStatusRequest(BaseModel):
    """Request model for setting tool active status"""
    is_active: bool


@router.get("/url/{tool_name}")
async def get_auth_url(
    tool_name: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get OAuth authorization URL for a tool"""
    auth_service = AuthService(db)
    
    try:
        auth_url, state = await auth_service.generate_auth_url(user_id, tool_name)
        return {
            "auth_url": auth_url,
            "state": state,
            "tool_name": tool_name
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/manual")
async def register_manual_auth(
    request: ManualAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register credentials manually for any tool (no OAuth flow needed)"""
    auth_service = AuthService(db)
    
    try:
        success = await auth_service.register_manual_auth(
            user_id=request.user_id,
            tool_name=request.tool_name,
            credentials=request.credentials
        )
        
        if success:
            return {
                "success": True,
                "message": f"Manual credentials successfully registered for {request.tool_name}",
                "user_id": request.user_id,
                "tool_name": request.tool_name
            }
        else:
            raise HTTPException(status_code=400, detail="Manual credential registration failed")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/callback/{tool_name}")
async def auth_callback(
    tool_name: str,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback"""
    auth_service = AuthService(db)
    
    try:
        success = await auth_service.handle_callback(tool_name, code, state)
        if success:
            return {"success": True, "message": f"Successfully authenticated with {tool_name}"}
        else:
            raise HTTPException(status_code=400, detail="Authentication failed")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/tools")
async def get_user_tools(
    user_id: str = Query(..., description="User ID"),
    active_only: bool = Query(False, description="Return only active tools"),
    db: AsyncSession = Depends(get_db)
):
    """Get user's authenticated tools"""
    auth_service = AuthService(db)
    
    try:
        if active_only:
            tools = await auth_service.get_user_active_tools(user_id)
        else:
            tools = await auth_service.get_user_tools(user_id)
        
        return {
            "user_id": user_id,
            "tools": tools,
            "total": len(tools),
            "active_only": active_only
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tools: {str(e)}")


@router.put("/users/{user_id}/tools/{tool_name}/status")
async def set_tool_active_status(
    user_id: str = Path(..., description="User ID"),
    tool_name: str = Path(..., description="Tool name"),
    request: ToolActiveStatusRequest = ...,
    db: AsyncSession = Depends(get_db)
):
    """Set the active status of a user's authenticated tool"""
    auth_service = AuthService(db)
    
    try:
        success = await auth_service.set_tool_active_status(user_id, tool_name, request.is_active)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Tool {tool_name} not found or not authenticated for user {user_id}"
            )
        
        return {
            "success": True,
            "message": f"Tool {tool_name} {'activated' if request.is_active else 'deactivated'} successfully",
            "user_id": user_id,
            "tool_name": tool_name,
            "is_active": request.is_active
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating tool status: {str(e)}") 