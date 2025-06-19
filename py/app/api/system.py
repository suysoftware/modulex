"""
System API Endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import sys
from pathlib import Path

from ..core.database import get_db
from ..core.x_api_key_auth import verify_system_api_key

router = APIRouter(prefix="/system", tags=["System"])


async def run_migrations(raise_on_error: bool = True):
    """Run database migrations"""
    try:
        print("🔄 Running database migrations...")
        
        # Import and run the migration
        import os
        
        # Add migrations directory to path
        migrations_path = Path(__file__).parent.parent.parent / "migrations"
        sys.path.insert(0, str(migrations_path))
        
        # Import and run migration
        from add_is_active_column import run_migration
        await run_migration()
        
        print("✅ Database migrations completed")
        
    except Exception as e:
        print(f"⚠️ Migration warning: {str(e)}")
        # Don't fail startup if migration fails, but re-raise for API endpoints
        if raise_on_error:
            raise


async def run_migrations_for_startup():
    """Run migrations during startup - don't fail if migration fails"""
    await run_migrations(raise_on_error=False)


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring and deployment"""
    return {
        "status": "healthy", 
        "service": "ModuleX",
        "version": "0.1.2"
    }


@router.get("/config")
async def get_system_config(
    _: bool = Depends(verify_system_api_key)
):
    """Get system configuration - Protected by X-API-KEY"""
    from ..core.toml_config import toml_config
    
    config_info = toml_config.get_config_info()
    
    return {
        "success": True,
        "auth_provider": toml_config.get_auth_provider(),
        "config_info": config_info,
        "loaded_config_path": toml_config.get_loaded_config_path(),
        "message": "System configuration retrieved successfully"
    }


@router.post("/config/reload")
async def reload_system_config(
    _: bool = Depends(verify_system_api_key)
):
    """Reload TOML configuration - Protected by X-API-KEY"""
    try:
        from ..core.toml_config import toml_config
        toml_config.reload()
        
        return {
            "success": True,
            "auth_provider": toml_config.get_auth_provider(),
            "message": "Configuration reloaded successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to reload configuration"
        }


@router.post("/database/update")
async def update_database(
    _: bool = Depends(verify_system_api_key)
):
    """Update database schema (run migrations) - Protected by X-API-KEY"""
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


@router.post("/database/rollback")
async def rollback_database(
    _: bool = Depends(verify_system_api_key)
):
    """Rollback database schema changes - Protected by X-API-KEY"""
    try:
        # Add migrations directory to path
        migrations_path = Path(__file__).parent.parent.parent / "migrations"
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