"""
ModuleX - Simplified Version
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings, verify_api_key, get_api_key_info
from .core.database import create_tables
from .api import auth, tools


async def run_migrations():
    """Run database migrations on startup"""
    try:
        print("🔄 Running database migrations...")
        
        # Import and run the migration
        import sys
        import os
        from pathlib import Path
        
        # Add migrations directory to path
        migrations_path = Path(__file__).parent.parent / "migrations"
        sys.path.insert(0, str(migrations_path))
        
        # Import and run migration
        from add_is_active_column import run_migration
        await run_migration()
        
        print("✅ Database migrations completed")
        
    except Exception as e:
        print(f"⚠️ Migration warning: {str(e)}")
        # Don't fail startup if migration fails
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    # Startup
    await create_tables()
    await run_migrations()  # Run migrations after table creation
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
app.include_router(tools.router)


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
                "list_user_tools": "/auth/tools?user_id=YOUR_USER_ID"
            },
            "tools": {
                "list_tools": "/tools/",
                "get_tool_info": "/tools/{tool_name}",
                "execute_tool": "/tools/{tool_name}/execute?user_id=YOUR_USER_ID",
                "get_user_openai_tools": "/tools/openai/users/{user_id}/openai-tools"
            },
            "admin": {
                "database_update": "/admin/database/update",
                "database_rollback": "/admin/database/rollback"
            }
        }
    }


@app.get("/health/")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "service": "ModuleX"}


@app.post("/admin/database/update")
async def update_database(
    _: bool = Depends(verify_api_key)
):
    """Update database schema (run migrations) - Protected by API key"""
    try:
        await run_migrations()
        return {
            "success": True, 
            "message": "Database updated successfully",
            "operation": "migration"
        }
    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "operation": "migration"
        }


@app.post("/admin/database/rollback")
async def rollback_database(
    _: bool = Depends(verify_api_key)
):
    """Rollback database schema changes - Protected by API key"""
    try:
        import sys
        from pathlib import Path
        
        # Add migrations directory to path
        migrations_path = Path(__file__).parent.parent / "migrations"
        sys.path.insert(0, str(migrations_path))
        
        # Import and run rollback
        from add_is_active_column import rollback_migration
        await rollback_migration()
        
        return {
            "success": True, 
            "message": "Database rollback completed successfully",
            "operation": "rollback"
        }
    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "operation": "rollback"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,  # Different port to avoid conflict
        reload=True
    ) 