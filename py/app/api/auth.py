"""
Authentication API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..core.database import get_db
from ..services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    db: AsyncSession = Depends(get_db)
):
    """Get user's authenticated tools"""
    auth_service = AuthService(db)
    
    try:
        tools = await auth_service.get_user_tools(user_id)
        return {
            "user_id": user_id,
            "tools": tools,
            "total": len(tools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tools: {str(e)}") 