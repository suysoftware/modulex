"""
ModuleX - Simplified Version
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings
from .core.database import create_tables
from .api import auth, tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    # Startup
    await create_tables()
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="ModuleX - Simplified",
    description="Simple tool authentication and execution server",
    version="0.1.0",
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
app.include_router(tools.router)
app.include_router(tools.router_direct)  # Add the direct execution router


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ModuleX - Simplified Version",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "auth": {
                "get_auth_url": "/auth/url/{tool_name}?user_id=YOUR_USER_ID",
                "callback": "/auth/callback/{tool_name}",
                "list_user_tools": "/auth/tools?user_id=YOUR_USER_ID"
            },
            "tools": {
                "list_tools": "/tools/",
                "get_tool_info": "/tools/{tool_name}",
                "execute_tool": "/tools/{tool_name}/execute?user_id=YOUR_USER_ID"
            },
            "openai_integration": {
                "get_user_openai_tools": "/tools/openai/users/{user_id}/openai-tools",
                "execute_tool_direct": "/tools/direct/{tool_name_action}/execute?user_id=YOUR_USER_ID"
            }
        },
        "vercel_ai_sdk_usage": {
            "description": "For Vercel AI SDK integration",
            "get_tools": "GET /tools/openai/users/{USER_ID}/openai-tools",
            "execute_tool": "POST /tools/direct/{toolName_action}/execute?user_id={USER_ID}",
            "note": "Tool names in execution should be in format: toolname_action (e.g., github_list_repositories)"
        }
    }


@app.get("/health/")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "service": "ModuleX"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,  # Different port to avoid conflict
        reload=True
    ) 