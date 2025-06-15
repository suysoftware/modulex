#!/usr/bin/env python3
"""
Database Migration: Add is_active and disabled_actions columns to user_tool_auths table

This migration adds the is_active and disabled_actions columns to existing installations.
Run this after updating the code to ensure database compatibility.
"""
import asyncio
import asyncpg
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def run_migration():
    """Run the migration to add is_active and disabled_actions columns"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/modulex")
    
    print("🔄 Running migration: Add is_active and disabled_actions columns to user_tool_auths")
    print(f"📋 Database URL: {database_url}")
    
    try:
        # Create async engine
        engine = create_async_engine(database_url, echo=True)
        
        async with engine.begin() as conn:
            # Check if is_active column already exists
            check_is_active_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_tool_auths' 
                AND column_name = 'is_active'
            """)
            
            result = await conn.execute(check_is_active_query)
            is_active_exists = result.fetchone()
            
            # Check if disabled_actions column already exists
            check_disabled_actions_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_tool_auths' 
                AND column_name = 'disabled_actions'
            """)
            
            result = await conn.execute(check_disabled_actions_query)
            disabled_actions_exists = result.fetchone()
            
            updates_made = []
            
            # Add is_active column if it doesn't exist
            if not is_active_exists:
                print("➕ Adding 'is_active' column...")
                add_is_active_query = text("""
                    ALTER TABLE user_tool_auths 
                    ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL
                """)
                await conn.execute(add_is_active_query)
                updates_made.append("is_active")
            else:
                print("✅ Column 'is_active' already exists.")
            
            # Add disabled_actions column if it doesn't exist
            if not disabled_actions_exists:
                print("➕ Adding 'disabled_actions' column...")
                add_disabled_actions_query = text("""
                    ALTER TABLE user_tool_auths 
                    ADD COLUMN disabled_actions JSON DEFAULT '[]'
                """)
                await conn.execute(add_disabled_actions_query)
                updates_made.append("disabled_actions")
            else:
                print("✅ Column 'disabled_actions' already exists.")
            
            # Update existing records
            if updates_made:
                update_query_parts = []
                if "is_active" in updates_made:
                    update_query_parts.append("is_active = TRUE")
                if "disabled_actions" in updates_made:
                    update_query_parts.append("disabled_actions = '[]'")
                
                if update_query_parts:
                    update_existing_query = text(f"""
                        UPDATE user_tool_auths 
                        SET {', '.join(update_query_parts)}
                        WHERE {' OR '.join([f"{col} IS NULL" for col in updates_made])}
                    """)
                    
                    result = await conn.execute(update_existing_query)
                    updated_rows = result.rowcount
                    
                    print(f"📊 Updated {updated_rows} existing records")
            
            if updates_made:
                print(f"✅ Migration completed successfully! Added columns: {', '.join(updates_made)}")
            else:
                print("✅ All columns already exist. No migration needed.")
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        await engine.dispose()

async def rollback_migration():
    """Rollback the migration (remove is_active and disabled_actions columns)"""
    
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/modulex")
    
    print("⏪ Rolling back migration: Remove is_active and disabled_actions columns")
    print(f"📋 Database URL: {database_url}")
    
    try:
        engine = create_async_engine(database_url, echo=True)
        
        async with engine.begin() as conn:
            # Check which columns exist
            check_columns_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_tool_auths' 
                AND column_name IN ('is_active', 'disabled_actions')
            """)
            
            result = await conn.execute(check_columns_query)
            existing_columns = [row[0] for row in result.fetchall()]
            
            if not existing_columns:
                print("✅ Columns don't exist. Nothing to rollback.")
                return
            
            # Remove existing columns
            for column in existing_columns:
                print(f"➖ Removing '{column}' column...")
                remove_column_query = text(f"""
                    ALTER TABLE user_tool_auths 
                    DROP COLUMN {column}
                """)
                await conn.execute(remove_column_query)
            
            print(f"✅ Rollback completed successfully! Removed columns: {', '.join(existing_columns)}")
            
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