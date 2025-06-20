"""
ModuleX - Simplified Version
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings, verify_api_key, get_api_key_info
from .core.database import create_tables
from .api import auth, tools, system, integrations
from .api.system import run_migrations_for_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    # Startup
    await create_tables()
    await run_migrations_for_startup()  # Run migrations after table creation
    
    # Sync integrations on startup
    try:
        from .core.database import AsyncSessionLocal
        from .services.integration_service import IntegrationService
        
        async with AsyncSessionLocal() as db:
            integration_service = IntegrationService(db)
            
            # Sync available tools from integrations folder
            synced_count = await integration_service.sync_available_tools()
            print(f"🔄 Synced {synced_count} available tools")
            
            # Auto-install tools from environment
            installed_count = await integration_service.auto_install_from_env()
            print(f"🚀 Auto-installed {installed_count} tools from environment")
            
    except Exception as e:
        print(f"⚠️ Warning: Integration sync failed during startup: {str(e)}")
    
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="ModuleX - Simplified",
    description="Simple tool authentication and execution server",
    version="0.1.2",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(auth.callback_router)  # Callback endpoints without API key
app.include_router(tools.router)
app.include_router(system.router)
app.include_router(integrations.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ModuleX - Simplified Version",
        "version": "0.1.2",
        "docs": "/docs",
        "api_key_info": get_api_key_info(),
        "endpoints": {
            "auth": {
                "get_auth_url": "/auth/url/{tool_name}?user_id=YOUR_USER_ID",
                "callback": "/auth/callback/{tool_name}",
                "list_user_tools": "/auth/tools?user_id=YOUR_USER_ID",
                "set_tool_status": "/auth/tools/{tool_name}/status?user_id=YOUR_USER_ID",
                "set_action_status": "/auth/tools/{tool_name}/actions/{action_name}/status?user_id=YOUR_USER_ID",
                "disconnect_tool": "/auth/tools/{tool_name}?user_id=YOUR_USER_ID"
            },
            "tools": {
                "list_tools": "/tools/",
                "get_tool_info": "/tools/{tool_name}",
                "execute_tool": "/tools/{tool_name}/execute?user_id=YOUR_USER_ID",
                "get_user_openai_tools": "/tools/openai-tools?user_id=YOUR_USER_ID"
            },
            "system": {
                "health": "/system/health",
                "config": "/system/config",
                "config_reload": "/system/config/reload",
                "database_update": "/system/database/update",
                "database_rollback": "/system/database/rollback"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,  # Different port to avoid conflict
        reload=True
    ) 