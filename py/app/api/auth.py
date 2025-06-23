"""
Authentication API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from pydantic import BaseModel

from ..core.database import get_db
from ..services.auth_service import AuthService
from ..core.auth import user_auth_required, system_auth_required, AuthResult

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Separate router for callback endpoints (no API key required)
callback_router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_success_html(tool_name: str) -> str:
    """Generate success HTML page"""
    tool_display_names = {
        "github": "GitHub",
        "google": "Google",
        "slack": "Slack",
        "gitlab": "GitLab",
        "bitbucket": "Bitbucket"
    }
    
    display_name = tool_display_names.get(tool_name, tool_name.title())
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Authentication Successful - ModuleX</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                min-height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            
            .container {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                padding: 40px;
                max-width: 500px;
                width: 100%;
                text-align: center;
                animation: slideUp 0.6s ease-out;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .success-icon {{
                width: 80px;
                height: 80px;
                background: #10B981;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
                animation: checkmark 0.6s ease-in-out 0.3s both;
            }}
            
            @keyframes checkmark {{
                0% {{
                    transform: scale(0);
                }}
                50% {{
                    transform: scale(1.2);
                }}
                100% {{
                    transform: scale(1);
                }}
            }}
            
            .checkmark {{
                width: 32px;
                height: 32px;
                color: white;
            }}
            
            .title {{
                font-size: 28px;
                font-weight: 700;
                color: #1F2937;
                margin-bottom: 12px;
            }}
            
            .subtitle {{
                font-size: 16px;
                color: #6B7280;
                margin-bottom: 32px;
                line-height: 1.5;
            }}
            
            .tool-info {{
                background: #F3F4F6;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 32px;
            }}
            
            .tool-name {{
                font-size: 18px;
                font-weight: 600;
                color: #374151;
                margin-bottom: 8px;
            }}
            
            .tool-status {{
                font-size: 14px;
                color: #059669;
                font-weight: 500;
            }}
            
            .close-button {{
                background: #6366F1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 32px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }}
            
            .close-button:hover {{
                background: #5B21B6;
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
            }}
            
            .footer {{
                margin-top: 24px;
                font-size: 12px;
                color: #9CA3AF;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">
                <svg class="checkmark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
            </div>
            
            <h1 class="title">Authentication Successful!</h1>
            <p class="subtitle">
                You have successfully connected your {display_name} account to ModuleX.
                You can now close this window and return to your application.
            </p>
            
            <div class="tool-info">
                <div class="tool-name">{display_name}</div>
                <div class="tool-status">✓ Successfully Connected</div>
            </div>
            
            <button class="close-button" onclick="window.close()">
                Close Window
            </button>
            
            <div class="footer">
                Powered by ModuleX • Authentication System
            </div>
        </div>
        
        <script>
            // Auto-close after 10 seconds if user doesn't close manually
            setTimeout(() => {{
                if (window.opener) {{
                    window.close();
                }}
            }}, 10000);
        </script>
    </body>
    </html>
    """


def get_error_html(tool_name: str, error_message: str) -> str:
    """Generate error HTML page"""
    tool_display_names = {
        "github": "GitHub",
        "google": "Google", 
        "slack": "Slack",
        "gitlab": "GitLab",
        "bitbucket": "Bitbucket"
    }
    
    display_name = tool_display_names.get(tool_name, tool_name.title())
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Authentication Failed - ModuleX</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                min-height: 100vh;
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            
            .container {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                padding: 40px;
                max-width: 500px;
                width: 100%;
                text-align: center;
                animation: slideUp 0.6s ease-out;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .error-icon {{
                width: 80px;
                height: 80px;
                background: #EF4444;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
                animation: shake 0.6s ease-in-out 0.3s both;
            }}
            
            @keyframes shake {{
                0%, 100% {{ transform: translateX(0); }}
                25% {{ transform: translateX(-4px); }}
                75% {{ transform: translateX(4px); }}
            }}
            
            .x-mark {{
                width: 32px;
                height: 32px;
                color: white;
            }}
            
            .title {{
                font-size: 28px;
                font-weight: 700;
                color: #1F2937;
                margin-bottom: 12px;
            }}
            
            .subtitle {{
                font-size: 16px;
                color: #6B7280;
                margin-bottom: 32px;
                line-height: 1.5;
            }}
            
            .tool-info {{
                background: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 32px;
            }}
            
            .tool-name {{
                font-size: 18px;
                font-weight: 600;
                color: #374151;
                margin-bottom: 8px;
            }}
            
            .tool-status {{
                font-size: 14px;
                color: #DC2626;
                font-weight: 500;
                margin-bottom: 12px;
            }}
            
            .error-details {{
                font-size: 12px;
                color: #7F1D1D;
                background: #FEE2E2;
                padding: 8px 12px;
                border-radius: 6px;
                font-family: monospace;
                word-break: break-word;
            }}
            
            .action-buttons {{
                display: flex;
                gap: 12px;
                justify-content: center;
                flex-wrap: wrap;
            }}
            
            .retry-button {{
                background: #059669;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                text-decoration: none;
                display: inline-block;
            }}
            
            .retry-button:hover {{
                background: #047857;
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(5, 150, 105, 0.4);
            }}
            
            .close-button {{
                background: #6B7280;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }}
            
            .close-button:hover {{
                background: #4B5563;
                transform: translateY(-2px);
            }}
            
            .footer {{
                margin-top: 24px;
                font-size: 12px;
                color: #9CA3AF;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">
                <svg class="x-mark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </div>
            
            <h1 class="title">Authentication Failed</h1>
            <p class="subtitle">
                We couldn't connect your {display_name} account to ModuleX.
                Please try again or contact support if the problem persists.
            </p>
            
            <div class="tool-info">
                <div class="tool-name">{display_name}</div>
                <div class="tool-status">✗ Connection Failed</div>
                <div class="error-details">{error_message}</div>
            </div>
            
            <div class="action-buttons">
                <a href="javascript:history.back()" class="retry-button">Try Again</a>
                <button class="close-button" onclick="window.close()">Close Window</button>
            </div>
            
            <div class="footer">
                Powered by ModuleX • Authentication System
            </div>
        </div>
    </body>
    </html>
    """


class ManualAuthRequest(BaseModel):
    """Manual authentication request for any tool"""
    tool_name: str
    credentials: Dict[str, Any]  # Flexible credentials structure


class ToolActiveStatusRequest(BaseModel):
    """Request model for setting tool active status"""
    is_active: bool


class ActionDisabledStatusRequest(BaseModel):
    """Request model for setting action disabled status"""
    is_disabled: bool


@router.get("/url/{tool_name}")
async def get_auth_url(
    tool_name: str,
    user: AuthResult = Depends(user_auth_required),
    user_id: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get OAuth authorization URL for a tool or handle manual auth"""
    auth_service = AuthService(db)
    
    # Get effective user_id: for X-API-KEY use parameter, for tokens use authenticated user_id
    effective_user_id = user_id if user.auth_method == "x_api_key" else user.user_id
    
    try:
        # Check the auth_type of the tool
        auth_type = await auth_service.get_tool_auth_type(tool_name)
        
        if auth_type == "manual":
            # Handle manual authentication (r2r style)
            result = await auth_service.handle_manual_auth_url(effective_user_id, tool_name)
            return result
        elif auth_type == "api_key":
            # Handle form-based authentication (n8n style)
            result = await auth_service.handle_form_auth_url(effective_user_id, tool_name)
            return result
        else:
            # Handle OAuth2 authentication (existing flow)
            auth_url, state = await auth_service.generate_auth_url(effective_user_id, tool_name)
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
    user_id: str = Query(None, description="User ID (required when using X-API-KEY)"),
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(user_auth_required)
):
    """Register credentials manually for any tool (no OAuth flow needed)"""
    auth_service = AuthService(db)
    
    # Get effective user_id: for X-API-KEY use parameter, for tokens use authenticated user_id
    effective_user_id = user_id if user.auth_method == "x_api_key" else user.user_id
    
    # user_id is only required when using X-API-KEY
    if user.auth_method == "x_api_key" and not user_id:
        raise HTTPException(status_code=400, detail="user_id is required when using X-API-KEY")
    
    if not effective_user_id:
        raise HTTPException(status_code=400, detail="user_id could not be determined")
    
    try:
        success = await auth_service.register_manual_auth(
            user_id=effective_user_id,
            tool_name=request.tool_name,
            credentials=request.credentials
        )
        
        if success:
            return {
                "success": True,
                "message": f"Manual credentials successfully registered for {request.tool_name}",
                "user_id": effective_user_id,
                "tool_name": request.tool_name
            }
        else:
            raise HTTPException(status_code=400, detail="Manual credential registration failed")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@callback_router.get("/callback/{tool_name}", response_class=HTMLResponse)
async def auth_callback(
    tool_name: str,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback - Returns beautiful HTML page"""
    auth_service = AuthService(db)
    
    try:
        # Handle traditional OAuth callback
        success = await auth_service.handle_callback(tool_name, code, state)
        if success:
            return HTMLResponse(content=get_success_html(tool_name), status_code=200)
        else:
            return HTMLResponse(content=get_error_html(tool_name, "Authentication process failed"), status_code=400)
    except ValueError as e:
        return HTMLResponse(content=get_error_html(tool_name, str(e)), status_code=400)
    except Exception as e:
        return HTMLResponse(content=get_error_html(tool_name, f"Internal error: {str(e)}"), status_code=500)


@callback_router.get("/callback/form/{tool_name}", response_class=HTMLResponse)
async def form_auth_callback(
    tool_name: str,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle form-based auth success callback - Returns beautiful HTML page"""
    try:
        # For form-based auth, credentials were already saved in form submit
        # Just return success page
        return HTMLResponse(content=get_success_html(tool_name), status_code=200)
    except Exception as e:
        return HTMLResponse(content=get_error_html(tool_name, f"Internal error: {str(e)}"), status_code=500)


@callback_router.get("/form/{tool_name}", response_class=HTMLResponse)
async def auth_form(
    tool_name: str,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Show authentication form for tools that require manual credential input"""
    auth_service = AuthService(db)
    
    try:
        form_html = await auth_service.generate_auth_form(user_id, tool_name)
        return HTMLResponse(content=form_html, status_code=200)
    except ValueError as e:
        return HTMLResponse(content=get_error_html(tool_name, str(e)), status_code=400)
    except Exception as e:
        return HTMLResponse(content=get_error_html(tool_name, f"Internal error: {str(e)}"), status_code=500)


@callback_router.post("/form/{tool_name}", response_class=HTMLResponse)
async def handle_auth_form_submit(
    tool_name: str,
    user_id: str = Query(...),
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle form submission for tools that require manual credential input"""
    from fastapi import Request
    
    auth_service = AuthService(db)
    
    try:
        # Get form data
        form_data = await request.form()
        credentials = {}
        for key, value in form_data.items():
            if key != "user_id":  # Exclude user_id from credentials
                credentials[key] = value
        
        # Save credentials using manual auth method
        success = await auth_service.register_manual_auth(
            user_id=user_id,
            tool_name=tool_name,
            credentials=credentials
        )
        
        if success:
            return HTMLResponse(
                content=get_success_html(tool_name),
                status_code=200
            )
        else:
            return HTMLResponse(
                content=get_error_html(tool_name, "Failed to save credentials"),
                status_code=400
            )
            
    except ValueError as e:
        return HTMLResponse(content=get_error_html(tool_name, str(e)), status_code=400)
    except Exception as e:
        return HTMLResponse(content=get_error_html(tool_name, f"Internal error: {str(e)}"), status_code=500)


@router.get("/tools")
async def get_user_tools(
    user_id: str = Query(None, description="User ID (required when using X-API-KEY)"),
    detail: bool = Query(False, description="Return detailed tool information"),
    db: AsyncSession = Depends(get_db),
    user: AuthResult = Depends(user_auth_required)
):
    """Get all available tools with user authentication and active status"""
    auth_service = AuthService(db)
    
    # Get effective user_id: for X-API-KEY use parameter, for tokens use authenticated user_id
    effective_user_id = user_id if user.auth_method == "x_api_key" else user.user_id
    
    # user_id is only required when using X-API-KEY
    if user.auth_method == "x_api_key" and not user_id:
        raise HTTPException(status_code=400, detail="user_id is required when using X-API-KEY")
    
    if not effective_user_id:
        raise HTTPException(status_code=400, detail="user_id could not be determined")
    
    try:
        tools = await auth_service.get_all_tools_with_user_status(effective_user_id, detail)
        
        return {
            "tools": tools,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tools: {str(e)}")


@router.put("/tools/{tool_name}/status")
async def set_tool_active_status(
    tool_name: str = Path(..., description="Tool name"),
    user_id: str = Query(None, description="User ID (required when using X-API-KEY)"),
    request: ToolActiveStatusRequest = ...,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthResult = Depends(user_auth_required)
):
    """Set the active status of a user's authenticated tool"""
    auth_service = AuthService(db)
    
    # Get effective user_id: for X-API-KEY use parameter, for tokens use authenticated user_id
    effective_user_id = user_id if auth_user.auth_method == "x_api_key" else auth_user.user_id
    
    # user_id is only required when using X-API-KEY
    if auth_user.auth_method == "x_api_key" and not user_id:
        raise HTTPException(status_code=400, detail="user_id is required when using X-API-KEY")
    
    if not effective_user_id:
        raise HTTPException(status_code=400, detail="user_id could not be determined")
    
    try:
        success = await auth_service.set_tool_active_status(effective_user_id, tool_name, request.is_active)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Tool {tool_name} not found or not authenticated for user {effective_user_id}"
            )
        
        return {
            "success": True,
            "message": f"Tool {tool_name} {'activated' if request.is_active else 'deactivated'} successfully",
            "user_id": effective_user_id,
            "tool_name": tool_name,
            "is_active": request.is_active
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating tool status: {str(e)}")


@router.put("/tools/{tool_name}/actions/{action_name}/status")
async def set_action_disabled_status(
    tool_name: str = Path(..., description="Tool name"),
    action_name: str = Path(..., description="Action name"),
    user_id: str = Query(None, description="User ID (required when using X-API-KEY)"),
    request: ActionDisabledStatusRequest = ...,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthResult = Depends(user_auth_required)
):
    """Enable or disable a specific action for a user's tool"""
    auth_service = AuthService(db)
    
    # Get effective user_id: for X-API-KEY use parameter, for tokens use authenticated user_id
    effective_user_id = user_id if auth_user.auth_method == "x_api_key" else auth_user.user_id
    
    # user_id is only required when using X-API-KEY
    if auth_user.auth_method == "x_api_key" and not user_id:
        raise HTTPException(status_code=400, detail="user_id is required when using X-API-KEY")
    
    if not effective_user_id:
        raise HTTPException(status_code=400, detail="user_id could not be determined")
    
    try:
        success = await auth_service.set_action_disabled_status(
            effective_user_id, tool_name, action_name, request.is_disabled
        )
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Tool {tool_name} not found or not authenticated for user {effective_user_id}"
            )
        
        return {
            "success": True,
            "message": f"Action '{action_name}' for tool '{tool_name}' {'disabled' if request.is_disabled else 'enabled'} successfully",
            "user_id": effective_user_id,
            "tool_name": tool_name,
            "action_name": action_name,
            "is_disabled": request.is_disabled
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating action status: {str(e)}")


@router.delete("/tools/{tool_name}")
async def disconnect_tool(
    tool_name: str = Path(..., description="Tool name"),
    user_id: str = Query(None, description="User ID (required when using X-API-KEY)"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthResult = Depends(user_auth_required)
):
    """Disconnect user from a tool by deleting the authentication record"""
    auth_service = AuthService(db)
    
    # Get effective user_id: for X-API-KEY use parameter, for tokens use authenticated user_id
    effective_user_id = user_id if auth_user.auth_method == "x_api_key" else auth_user.user_id
    
    # user_id is only required when using X-API-KEY
    if auth_user.auth_method == "x_api_key" and not user_id:
        raise HTTPException(status_code=400, detail="user_id is required when using X-API-KEY")
    
    if not effective_user_id:
        raise HTTPException(status_code=400, detail="user_id could not be determined")
    
    try:
        success = await auth_service.disconnect_tool(effective_user_id, tool_name)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Tool {tool_name} not found for user {effective_user_id}"
            )
        
        return {
            "success": True,
            "message": f"Successfully disconnected from {tool_name}",
            "user_id": effective_user_id,
            "tool_name": tool_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting from tool: {str(e)}") 