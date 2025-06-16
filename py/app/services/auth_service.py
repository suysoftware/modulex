"""
Authentication Service - Simplified
"""
import secrets
import httpx
import json
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from ..models.user import User, UserToolAuth
from ..core.config import settings
from ..core.encryption import encrypt_credentials, decrypt_credentials
from ..core.database import redis_client


class AuthService:
    """Simple authentication service"""
    
    # OAuth configurations
    OAUTH_CONFIGS = {
        "github": {
            "auth_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scopes": ["repo", "user"],
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
        },
        "google": {
            "auth_url": "https://accounts.google.com/o/oauth2/auth", 
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": ["openid", "email", "profile"],
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
        },
        "slack": {
            "auth_url": "https://slack.com/oauth/v2/authorize",
            "token_url": "https://slack.com/api/oauth.v2.access",
            "scopes": ["chat:write", "channels:read"],
            "client_id": settings.SLACK_CLIENT_ID,
            "client_secret": settings.SLACK_CLIENT_SECRET,
        }
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis = redis_client
        self.oauth_state_prefix = "oauth_state:"  # Redis key prefix for namespacing
        self.oauth_state_ttl = 600  # 10 minutes TTL for security
    
    async def register_manual_auth(self, user_id: str, tool_name: str, credentials: Dict[str, Any]) -> bool:
        """Register credentials manually for any tool (no OAuth flow needed)"""
        try:
            # Prepare credentials data
            credentials_data = {
                **credentials,  # User provided credentials
                "auth_type": "manual",
                "registered_at": datetime.utcnow().isoformat()
            }
            
            # Get or create user
            user = await self.get_or_create_user(user_id)
            
            # Save credentials using existing method
            await self._save_credentials(user, tool_name, credentials_data)
            
            print(f"✅ DEBUG: Manual auth registered for user_id={user_id}, tool_name={tool_name}")
            return True
            
        except Exception as e:
            print(f"💥 DEBUG: Manual auth failed for user_id={user_id}, tool_name={tool_name}: {str(e)}")
            raise ValueError(f"Manual auth registration failed: {str(e)}")
    
    async def get_or_create_user(self, external_id: str) -> User:
        """Get or create user by external ID"""
        result = await self.db.execute(
            select(User).where(User.external_id == external_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(external_id=external_id)
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def generate_auth_url(self, user_id: str, tool_name: str) -> Tuple[str, str]:
        """Generate OAuth authorization URL"""
        if tool_name not in self.OAUTH_CONFIGS:
            raise ValueError(f"Tool {tool_name} not supported")
        
        config = self.OAUTH_CONFIGS[tool_name]
        state = secrets.token_urlsafe(32)
        
        # Store state in Redis with TTL for security
        state_data = {
            "user_id": user_id,
            "tool_name": tool_name,
            "created_at": datetime.utcnow().isoformat()
        }
        
        redis_key = f"{self.oauth_state_prefix}{state}"
        await self.redis.setex(
            redis_key, 
            self.oauth_state_ttl,  # 10 minutes TTL
            json.dumps(state_data)
        )
        
        # Build redirect URI
        redirect_uri = f"{settings.BASE_URL}/auth/callback/{tool_name}"
        
        # Build authorization URL
        scopes_str = " ".join(config["scopes"])
        auth_url = (
            f"{config['auth_url']}"
            f"?client_id={config['client_id']}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes_str}"
            f"&state={state}"
            f"&response_type=code"
        )
        
        return auth_url, state
    
    async def handle_callback(self, tool_name: str, code: str, state: str) -> bool:
        """Handle OAuth callback"""
        # Validate state from Redis
        redis_key = f"{self.oauth_state_prefix}{state}"
        
        # Get and delete state atomically (single operation)
        state_json = await self.redis.get(redis_key)
        if not state_json:
            raise ValueError("Invalid state")
        
        # Parse state data
        try:
            state_data = json.loads(state_json)
        except json.JSONDecodeError:
            raise ValueError("Invalid state format")
        
        # Validate tool name matches
        if state_data.get("tool_name") != tool_name:
            raise ValueError("Tool name mismatch")
        
        user_id = state_data["user_id"]
        
        # Exchange code for token
        config = self.OAUTH_CONFIGS[tool_name]
        token_data = await self._exchange_code_for_token(tool_name, code)
        
        # Save credentials
        user = await self.get_or_create_user(user_id)
        await self._save_credentials(user, tool_name, token_data)
        
        # Clean up state from Redis (delete after successful use)
        await self.redis.delete(redis_key)
        
        return True
    
    async def _exchange_code_for_token(self, tool_name: str, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        config = self.OAUTH_CONFIGS[tool_name]
        redirect_uri = f"{settings.BASE_URL}/auth/callback/{tool_name}"
        
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(config["token_url"], data=data, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            
            # Check if response contains an error instead of access token
            if "error" in token_data:
                error_msg = f"OAuth error: {token_data.get('error')} - {token_data.get('error_description', 'No description')}"
                print(f"💥 DEBUG: OAuth token exchange failed: {error_msg}")
                raise ValueError(error_msg)
            
            # Verify that we got an access token
            if "access_token" not in token_data:
                print(f"💥 DEBUG: No access_token in response: {list(token_data.keys())}")
                raise ValueError("No access_token received from OAuth provider")
                
            print(f"✅ DEBUG: OAuth token exchange successful, got keys: {list(token_data.keys())}")
            return token_data
    
    async def _save_credentials(self, user: User, tool_name: str, token_data: Dict[str, Any]):
        """Save encrypted credentials to database"""
        # Check if auth record exists
        result = await self.db.execute(
            select(UserToolAuth).where(
                UserToolAuth.user_id == user.id,
                UserToolAuth.tool_name == tool_name
            )
        )
        auth_record = result.scalar_one_or_none()
        
        # Encrypt credentials
        encrypted_creds = encrypt_credentials(user.id, token_data)
        
        if auth_record:
            # Update existing
            auth_record.encrypted_credentials = encrypted_creds
            auth_record.is_authenticated = True
            auth_record.last_auth_at = datetime.utcnow()
            auth_record.updated_at = datetime.utcnow()
            
            # Set expiration if provided
            if token_data.get("expires_in"):
                auth_record.auth_expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        else:
            # Create new
            auth_record = UserToolAuth(
                user_id=user.id,
                tool_name=tool_name,
                encrypted_credentials=encrypted_creds,
                is_authenticated=True,
                last_auth_at=datetime.utcnow()
            )
            
            if token_data.get("expires_in"):
                auth_record.auth_expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            
            self.db.add(auth_record)
        
        await self.db.commit()
    
    async def get_user_credentials(self, user_id: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get decrypted user credentials"""
        user = await self.get_or_create_user(user_id)
        
        result = await self.db.execute(
            select(UserToolAuth).where(
                UserToolAuth.user_id == user.id,
                UserToolAuth.tool_name == tool_name,
                UserToolAuth.is_authenticated == True,
                UserToolAuth.is_active == True
            )
        )
        auth_record = result.scalar_one_or_none()
        
        if not auth_record:
            print(f"❌ DEBUG: No active auth record found for user_id={user_id}, tool_name={tool_name}")
            return None
        
        print(f"✅ DEBUG: Active auth record found for user_id={user_id}, tool_name={tool_name}")
        
        try:
            decrypted_creds = decrypt_credentials(user.id, auth_record.encrypted_credentials)
            print(f"🔓 DEBUG: Successfully decrypted credentials, keys: {list(decrypted_creds.keys())}")
            return decrypted_creds
        except Exception as e:
            print(f"💥 DEBUG: Failed to decrypt credentials: {e}")
            return None
    
    async def get_user_tools(self, user_id: str) -> list:
        """Get user's authenticated tools"""
        user = await self.get_or_create_user(user_id)
        
        result = await self.db.execute(
            select(UserToolAuth).where(
                UserToolAuth.user_id == user.id,
                UserToolAuth.is_authenticated == True
            )
        )
        auth_records = result.scalars().all()
        
        tools = []
        for record in auth_records:
            tools.append({
                "tool_name": record.tool_name,
                "is_active": record.is_active,
                "disabled_actions": record.disabled_actions or [],
                "last_auth_at": record.last_auth_at,
                "last_used_at": record.last_used_at,
                "expires_at": record.auth_expires_at
            })
        
        return tools

    async def get_user_active_tools(self, user_id: str) -> list:
        """Get user's authenticated and active tools only"""
        user = await self.get_or_create_user(user_id)
        
        result = await self.db.execute(
            select(UserToolAuth).where(
                UserToolAuth.user_id == user.id,
                UserToolAuth.is_authenticated == True,
                UserToolAuth.is_active == True
            )
        )
        auth_records = result.scalars().all()
        
        tools = []
        for record in auth_records:
            tools.append({
                "tool_name": record.tool_name,
                "is_active": record.is_active,
                "disabled_actions": record.disabled_actions or [],
                "last_auth_at": record.last_auth_at,
                "last_used_at": record.last_used_at,
                "expires_at": record.auth_expires_at
            })
        
        return tools

    async def set_tool_active_status(self, user_id: str, tool_name: str, is_active: bool) -> bool:
        """Set the active status of a user's authenticated tool"""
        user = await self.get_or_create_user(user_id)
        
        result = await self.db.execute(
            select(UserToolAuth).where(
                UserToolAuth.user_id == user.id,
                UserToolAuth.tool_name == tool_name,
                UserToolAuth.is_authenticated == True
            )
        )
        auth_record = result.scalar_one_or_none()
        
        if not auth_record:
            return False
        
        auth_record.is_active = is_active
        auth_record.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return True

    async def set_action_disabled_status(self, user_id: str, tool_name: str, action_name: str, is_disabled: bool) -> bool:
        """Enable or disable a specific action for a user's tool"""
        from sqlalchemy.orm.attributes import flag_modified
        
        user = await self.get_or_create_user(user_id)
        
        result = await self.db.execute(
            select(UserToolAuth).where(
                UserToolAuth.user_id == user.id,
                UserToolAuth.tool_name == tool_name,
                UserToolAuth.is_authenticated == True
            )
        )
        auth_record = result.scalar_one_or_none()
        
        if not auth_record:
            return False
        
        # Initialize disabled_actions if None - create a new list to avoid mutation issues
        disabled_actions = list(auth_record.disabled_actions or [])
        
        if is_disabled:
            # Add action to disabled list if not already there
            if action_name not in disabled_actions:
                disabled_actions.append(action_name)
        else:
            # Remove action from disabled list if it exists
            if action_name in disabled_actions:
                disabled_actions.remove(action_name)
        
        # Assign the new list and explicitly mark as modified
        auth_record.disabled_actions = disabled_actions
        flag_modified(auth_record, 'disabled_actions')
        auth_record.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return True

    async def cleanup_expired_states(self):
        """Clean up expired OAuth states (Redis TTL handles this automatically)"""
        # Redis TTL automatically cleans up expired keys
        # This method is for manual cleanup if needed
        pattern = f"{self.oauth_state_prefix}*"
        keys = await self.redis.keys(pattern)
        
        if keys:
            # Get all state data to check expiration manually if needed
            values = await self.redis.mget(keys)
            expired_keys = []
            
            for i, value in enumerate(values):
                if value:
                    try:
                        state_data = json.loads(value)
                        created_at = datetime.fromisoformat(state_data["created_at"])
                        if (datetime.utcnow() - created_at).total_seconds() > self.oauth_state_ttl:
                            expired_keys.append(keys[i])
                    except:
                        expired_keys.append(keys[i])
            
            if expired_keys:
                await self.redis.delete(*expired_keys)
        
        return len(expired_keys) if 'expired_keys' in locals() else 0

    async def cleanup_invalid_credentials(self, user_id: str, tool_name: str) -> bool:
        """Clean up invalid credentials that contain OAuth errors"""
        user = await self.get_or_create_user(user_id)
        
        result = await self.db.execute(
            select(UserToolAuth).where(
                UserToolAuth.user_id == user.id,
                UserToolAuth.tool_name == tool_name
            )
        )
        auth_record = result.scalar_one_or_none()
        
        if not auth_record:
            return False
        
        try:
            # Try to decrypt and check if it contains an error
            decrypted_creds = decrypt_credentials(user.id, auth_record.encrypted_credentials)
            if "error" in decrypted_creds and "access_token" not in decrypted_creds:
                print(f"🧹 DEBUG: Cleaning up invalid credentials for user_id={user_id}, tool_name={tool_name}")
                # Mark as not authenticated but don't delete the record
                auth_record.is_authenticated = False
                auth_record.updated_at = datetime.utcnow()
                await self.db.commit()
                return True
        except Exception as e:
            print(f"💥 DEBUG: Error checking credentials for cleanup: {e}")
        
        return False

    async def get_all_tools_with_user_status(self, user_id: str, detail: bool = False):
        """Get all available tools with user authentication and active status"""
        # Import here to avoid circular import
        from ..services.tool_service import ToolService
        tool_service = ToolService(self.db)
        
        # Get all available tools
        available_tools = await tool_service.list_available_tools()
        
        # Get user's authenticated tools
        user = await self.get_or_create_user(user_id)
        result = await self.db.execute(
            select(UserToolAuth).where(
                UserToolAuth.user_id == user.id
            )
        )
        user_auth_records = {record.tool_name: record for record in result.scalars().all()}
        
        tools_with_status = []
        
        for tool in available_tools:
            tool_name = tool["name"]
            auth_record = user_auth_records.get(tool_name)
            
            # Determine authentication and active status
            is_authenticated = auth_record is not None and auth_record.is_authenticated
            is_active = is_authenticated and auth_record.is_active if auth_record else False
            disabled_actions = auth_record.disabled_actions if auth_record else []
            
            # Prepare actions with is_active status
            actions_with_status = []
            if tool.get("actions"):
                for action in tool["actions"]:
                    action_is_active = is_active and action["name"] not in (disabled_actions or [])
                    actions_with_status.append({
                        "name": action["name"],
                        "description": action.get("description", ""),
                        "is_active": action_is_active
                    })
            
            # Build tool response based on detail level
            tool_response = {
                "name": tool["name"],
                "display_name": tool.get("display_name", tool["name"]),
                "is_authenticated": is_authenticated,
                "is_active": is_active,
                "health_status": True,  # TODO: Implement actual health check
                "actions": actions_with_status
            }
            
            # Add detailed information if requested
            if detail:
                tool_response.update({
                    "description": tool.get("description", ""),
                    "version": tool.get("version", "1.0.0"),
                    "author": tool.get("author", "Unknown"),
                    "requires_auth": tool.get("requires_auth", True),
                    "auth_type": tool.get("auth_type", "oauth2")
                })
            
            tools_with_status.append(tool_response)
        
        return tools_with_status 