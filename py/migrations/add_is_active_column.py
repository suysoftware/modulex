#!/usr/bin/env python3
"""
Database Migration: Add is_active column to user_tool_auths table

This migration adds the is_active column to existing installations.
Run this after updating the code to ensure database compatibility.
"""
import asyncio
import asyncpg
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def run_migration():
    """Run the migration to add is_active column"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/modulex")
    
    print("🔄 Running migration: Add is_active column to user_tool_auths")
    print(f"📋 Database URL: {database_url}")
    
    try:
        # Create async engine
        engine = create_async_engine(database_url, echo=True)
        
        async with engine.begin() as conn:
            # Check if column already exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_tool_auths' 
                AND column_name = 'is_active'
            """)
            
            result = await conn.execute(check_column_query)
            column_exists = result.fetchone()
            
            if column_exists:
                print("✅ Column 'is_active' already exists. Skipping migration.")
                return
            
            print("➕ Adding 'is_active' column...")
            
            # Add the column with default value TRUE
            add_column_query = text("""
                ALTER TABLE user_tool_auths 
                ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL
            """)
            
            await conn.execute(add_column_query)
            
            # Update existing records to be active by default
            update_existing_query = text("""
                UPDATE user_tool_auths 
                SET is_active = TRUE 
                WHERE is_active IS NULL
            """)
            
            result = await conn.execute(update_existing_query)
            updated_rows = result.rowcount
            
            print(f"✅ Migration completed successfully!")
            print(f"📊 Updated {updated_rows} existing records to be active by default")
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        await engine.dispose()

async def rollback_migration():
    """Rollback the migration (remove is_active column)"""
    
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/modulex")
    
    print("⏪ Rolling back migration: Remove is_active column")
    print(f"📋 Database URL: {database_url}")
    
    try:
        engine = create_async_engine(database_url, echo=True)
        
        async with engine.begin() as conn:
            # Check if column exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_tool_auths' 
                AND column_name = 'is_active'
            """)
            
            result = await conn.execute(check_column_query)
            column_exists = result.fetchone()
            
            if not column_exists:
                print("✅ Column 'is_active' doesn't exist. Nothing to rollback.")
                return
            
            print("➖ Removing 'is_active' column...")
            
            # Remove the column
            remove_column_query = text("""
                ALTER TABLE user_tool_auths 
                DROP COLUMN is_active
            """)
            
            await conn.execute(remove_column_query)
            print("✅ Rollback completed successfully!")
            
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback_migration())
    else:
        asyncio.run(run_migration()) 