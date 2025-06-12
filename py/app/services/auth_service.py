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
                UserToolAuth.is_authenticated == True
            )
        )
        auth_record = result.scalar_one_or_none()
        
        if not auth_record:
            print(f"❌ DEBUG: No auth record found for user_id={user_id}, tool_name={tool_name}")
            return None
        
        print(f"✅ DEBUG: Auth record found for user_id={user_id}, tool_name={tool_name}")
        
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
                "last_auth_at": record.last_auth_at,
                "last_used_at": record.last_used_at,
                "expires_at": record.auth_expires_at
            })
        
        return tools
    
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