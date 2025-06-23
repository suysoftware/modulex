"""
Authentication Service with OAuth2 and Manual Auth Support
"""
import secrets
import httpx
import json
import jwt
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from ..models.user import User, UserToolAuth
from ..core.config import settings
from ..core.encryption import encrypt_credentials, decrypt_credentials
from ..core.database import redis_client
from .auth_handlers.oauth_handler_factory import OAuthHandlerFactory
from .auth_handlers.manual_auth_factory import ManualAuthHandlerFactory
from .integration_service import IntegrationService


class AuthService:
    """Simple authentication service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis = redis_client
        self.oauth_state_prefix = "oauth_state:"  # Redis key prefix for namespacing
        self.oauth_state_ttl = 600  # 10 minutes TTL for security
        self.integration_service = IntegrationService()
    
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
        # Check if tool is supported by our handler factory
        if not OAuthHandlerFactory.is_supported(tool_name):
            raise ValueError(f"Tool {tool_name} not supported")
        
        # Get credentials and create handler
        client_id, client_secret = self._get_oauth_credentials(tool_name)
        handler = OAuthHandlerFactory.get_handler(tool_name, client_id, client_secret)
        
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
        
        # Build redirect URI and authorization URL using handler
        redirect_uri = f"{settings.BASE_URL}/auth/callback/{tool_name}"
        auth_url = handler.build_auth_url(redirect_uri, state)
        
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
        
        # Exchange code for token using handler
        client_id, client_secret = self._get_oauth_credentials(tool_name)
        handler = OAuthHandlerFactory.get_handler(tool_name, client_id, client_secret)
        redirect_uri = f"{settings.BASE_URL}/auth/callback/{tool_name}"
        token_data = await handler.exchange_code_for_token(code, redirect_uri)
        
        # Save credentials
        user = await self.get_or_create_user(user_id)
        await self._save_credentials(user, tool_name, token_data)
        
        # Clean up state from Redis (delete after successful use)
        await self.redis.delete(redis_key)
        
        return True
    
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

    async def disconnect_tool(self, user_id: str, tool_name: str) -> bool:
        """Disconnect user from a tool by deleting the auth record"""
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
        
        # Delete the auth record completely
        await self.db.delete(auth_record)
        await self.db.commit()
        
        print(f"🔌 DEBUG: Disconnected user_id={user_id} from tool_name={tool_name}")
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

    async def get_tool_auth_type(self, tool_name: str) -> Optional[str]:
        """Get the auth_type for a tool by reading its info.json file"""
        try:
            from pathlib import Path
            info_file = Path("integrations") / tool_name / "info.json"
            
            if not info_file.exists():
                return None
            
            with open(info_file, 'r') as f:
                tool_info = json.load(f)
                return tool_info.get("auth_type")
        except Exception as e:
            print(f"💥 DEBUG: Error reading tool info for {tool_name}: {e}")
            return None

    async def handle_manual_auth_url(self, user_id: str, tool_name: str) -> Dict[str, Any]:
        """Handle auth URL request for manual auth tools"""
        # Check if tool is supported by manual auth factory
        if not ManualAuthHandlerFactory.is_supported(tool_name):
            raise ValueError(f"Tool {tool_name} not supported for manual auth")
        
        # Get configuration and create handler
        config = self._get_manual_auth_config(tool_name)
        handler = ManualAuthHandlerFactory.get_handler(tool_name, **config)
        
        try:
            # Get auth URL from handler
            auth_url = await handler.get_auth_url(user_id)
            
            # Make GET request to auth_url
            async with httpx.AsyncClient() as client:
                response = await client.get(auth_url)
                response.raise_for_status()
                
                # Get response data
                if response.headers.get("content-type", "").startswith("application/json"):
                    auth_data = response.json()
                else:
                    # If not JSON, treat as text response
                    auth_data = {"response": response.text}
                
                # Process auth response using handler
                credentials = await handler.process_auth_response(auth_data, user_id)
                
                # Save credentials
                user = await self.get_or_create_user(user_id)
                await self._save_credentials(user, tool_name, credentials)
                
                return {
                    "success": True,
                    "message": f"Manual authentication completed for {tool_name}",
                    "tool_name": tool_name,
                    "user_id": user_id
                }
                    
        except httpx.RequestError as e:
            raise ValueError(f"Failed to connect to auth URL: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Auth URL returned error: {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Manual auth failed: {str(e)}")

    async def handle_manual_callback(self, tool_name: str, user_id: str, auth_data: Dict[str, Any]) -> bool:
        """Handle manual authentication callback"""
        try:
            # Prepare credentials data similar to OAuth flow
            credentials_data = {
                "auth_type": "manual",
                "authenticated_at": datetime.utcnow().isoformat(),
                "user_id": user_id  # Store user_id for reference
            }
            
            # Process the auth_data response
            if isinstance(auth_data, dict):
                # Handle access_token response format
                if "access_token" in auth_data:
                    credentials_data["access_token"] = auth_data["access_token"]
                    print(f"🔑 DEBUG: Found access_token in manual auth response")
                
                # Include all other response data
                for key, value in auth_data.items():
                    if key not in credentials_data:  # Don't override existing keys
                        credentials_data[key] = value
            else:
                # If auth_data is not a dict, store it as raw response
                credentials_data["raw_response"] = auth_data
            
            print(f"🔐 DEBUG: Prepared credentials for encryption, keys: {list(credentials_data.keys())}")
            
            # Get or create user
            user = await self.get_or_create_user(user_id)
            
            # Save credentials using existing method (this encrypts the data)
            await self._save_credentials(user, tool_name, credentials_data)
            
            print(f"✅ DEBUG: Manual auth callback completed and encrypted for user_id={user_id}, tool_name={tool_name}")
            return True
            
        except Exception as e:
            print(f"💥 DEBUG: Manual auth callback failed for user_id={user_id}, tool_name={tool_name}: {str(e)}")
            return False

    async def handle_form_auth_url(self, user_id: str, tool_name: str) -> Dict[str, Any]:
        """Handle auth URL request for form-based auth tools (like n8n)"""
        try:
            # Generate form URL
            form_url = f"{settings.BASE_URL}/auth/form/{tool_name}?user_id={user_id}"
            
            return {
                "auth_url": form_url,
                "tool_name": tool_name,
                "user_id": user_id,
                "auth_type": "form"
            }
            
        except Exception as e:
            raise ValueError(f"Form auth URL generation failed: {str(e)}")

    async def generate_auth_form(self, user_id: str, tool_name: str) -> str:
        """Generate authentication form HTML for form-based tools"""
        try:
            # Get tool info to determine required fields
            tool_info = await self.get_tool_info(tool_name)
            if not tool_info:
                raise ValueError(f"Tool {tool_name} not found")
            
            # Get environment variables that are required
            env_vars = tool_info.get("environment_variables", [])
            required_fields = []
            
            for env_var in env_vars:
                field_info = {
                    "name": env_var["name"],
                    "description": env_var.get("description", env_var["name"]),
                    "required": env_var.get("required", True),
                    "type": "password" if "password" in env_var["name"].lower() or "key" in env_var["name"].lower() or "secret" in env_var["name"].lower() else "text"
                }
                required_fields.append(field_info)
            
            # Generate form HTML
            form_html = self._generate_form_html(tool_name, user_id, required_fields)
            return form_html
            
        except Exception as e:
            raise ValueError(f"Form generation failed: {str(e)}")

    async def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool information from info.json file"""
        try:
            from pathlib import Path
            import json
            
            info_file = Path("integrations") / tool_name / "info.json"
            
            if not info_file.exists():
                return None
            
            with open(info_file, 'r') as f:
                tool_info = json.load(f)
                return tool_info
        except Exception as e:
            print(f"💥 DEBUG: Error reading tool info for {tool_name}: {e}")
            return None

    def _generate_form_html(self, tool_name: str, user_id: str, required_fields: list) -> str:
        """Generate beautiful form HTML"""
        tool_display_names = {
            "n8n": "N8N Workflow Automation",
            "api_key": "API Key Authentication",
        }
        
        display_name = tool_display_names.get(tool_name, tool_name.title())
        
        # Generate form fields
        form_fields = ""
        for field in required_fields:
            field_name = field["name"]
            field_type = field["type"]
            field_desc = field["description"]
            is_required = field["required"]
            
            form_fields += f"""
                <div class="form-group">
                    <label for="{field_name}" class="form-label">
                        {field_desc}
                        {' <span class="required">*</span>' if is_required else ''}
                    </label>
                    <input 
                        type="{field_type}" 
                        id="{field_name}" 
                        name="{field_name}" 
                        class="form-input" 
                        placeholder="Enter your {field_desc.lower()}"
                        {'required' if is_required else ''}
                    />
                </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Connect {display_name} - ModuleX</title>
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
                
                .header {{
                    text-align: center;
                    margin-bottom: 32px;
                }}
                
                .tool-icon {{
                    width: 64px;
                    height: 64px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 12px;
                    margin: 0 auto 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 28px;
                    font-weight: bold;
                }}
                
                .title {{
                    font-size: 24px;
                    font-weight: 700;
                    color: #1f2937;
                    margin-bottom: 8px;
                }}
                
                .subtitle {{
                    color: #6b7280;
                    font-size: 14px;
                    line-height: 1.5;
                }}
                
                .form-group {{
                    margin-bottom: 20px;
                }}
                
                .form-label {{
                    display: block;
                    font-weight: 600;
                    color: #374151;
                    margin-bottom: 8px;
                    font-size: 14px;
                }}
                
                .required {{
                    color: #ef4444;
                }}
                
                .form-input {{
                    width: 100%;
                    padding: 12px 16px;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    font-size: 14px;
                    transition: all 0.2s ease;
                    background: #f9fafb;
                }}
                
                .form-input:focus {{
                    outline: none;
                    border-color: #667eea;
                    background: white;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }}
                
                .submit-button {{
                    width: 100%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 14px 20px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    margin-top: 8px;
                }}
                
                .submit-button:hover {{
                    transform: translateY(-1px);
                    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
                }}
                
                .submit-button:active {{
                    transform: translateY(0);
                }}
                
                .footer {{
                    text-align: center;
                    margin-top: 24px;
                    font-size: 12px;
                    color: #9CA3AF;
                }}
                
                .error-message {{
                    background: #fee2e2;
                    color: #dc2626;
                    padding: 12px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    font-size: 14px;
                    display: none;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="tool-icon">
                        {display_name[0]}
                    </div>
                    <h1 class="title">Connect {display_name}</h1>
                    <p class="subtitle">
                        Enter your {display_name} credentials to connect your account with ModuleX.
                        This information will be securely encrypted and stored.
                    </p>
                </div>
                
                <div id="error-message" class="error-message"></div>
                
                <form id="auth-form" action="/auth/form/{tool_name}?user_id={user_id}" method="POST">
                    {form_fields}
                    
                    <button type="submit" class="submit-button">
                        Connect {display_name}
                    </button>
                </form>
                
                <div class="footer">
                    Powered by ModuleX • Secure Authentication System
                </div>
            </div>
            
            <script>
                document.getElementById('auth-form').addEventListener('submit', async function(e) {{
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    const errorDiv = document.getElementById('error-message');
                    
                    try {{
                        const response = await fetch(this.action, {{
                            method: 'POST',
                            body: formData
                        }});
                        
                        if (response.ok) {{
                            // Success - show success page or redirect to callback
                            window.location.href = '/auth/callback/form/{tool_name}?user_id={user_id}';
                        }} else {{
                            const errorText = await response.text();
                            errorDiv.textContent = 'Authentication failed. Please check your credentials.';
                            errorDiv.style.display = 'block';
                        }}
                    }} catch (error) {{
                        errorDiv.textContent = 'Connection error. Please try again.';
                        errorDiv.style.display = 'block';
                    }}
                }});
            </script>
        </body>
        </html>
        """

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

    async def initiate_auth(self, user_id: str, tool_name: str) -> Dict[str, Any]:
        """Initiate authentication flow for a tool"""
        try:
            # Get tool info to determine auth type
            tool_info = await self.integration_service.get_integration_info(tool_name)
            auth_type = tool_info.get("auth_type", "oauth2")
            
            if auth_type == "oauth2":
                return await self._initiate_oauth(user_id, tool_name)
            elif auth_type == "manual":
                return await self._initiate_manual_auth(user_id, tool_name)
            else:
                raise ValueError(f"Unsupported auth type: {auth_type}")
                
        except Exception as e:
            return {"error": str(e)}
    
    async def _initiate_oauth(self, user_id: str, tool_name: str) -> Dict[str, Any]:
        """Initiate OAuth2 flow"""
        try:
            handler = OAuthHandlerFactory.get_handler(tool_name)
            
            state_token = self._generate_state_token(user_id, tool_name)
            auth_url = await handler.get_auth_url(state_token)
            
            return {
                "auth_url": auth_url,
                "state": state_token,
                "message": f"Redirecting to {tool_name} for authorization..."
            }
            
        except Exception as e:
            return {"error": f"OAuth initiation failed: {str(e)}"}
    
    async def _initiate_manual_auth(self, user_id: str, tool_name: str) -> Dict[str, Any]:
        """Initiate manual authentication flow"""
        try:
            handler = ManualAuthHandlerFactory.get_handler(tool_name)
            auth_url = await handler.get_auth_url(user_id)
            
            return {
                "auth_url": auth_url,
                "message": f"Please visit the URL to configure {tool_name} authentication"
            }
            
        except Exception as e:
            return {"error": f"Manual auth initiation failed: {str(e)}"}
    
    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle OAuth2 callback"""
        try:
            # Decode state token
            state_data = self._decode_state_token(state)
            user_id = state_data["user_id"]
            tool_name = state_data["tool_name"]
            
            # Get handler and exchange code for token
            handler = OAuthHandlerFactory.get_handler(tool_name)
            credentials = await handler.exchange_code_for_token(code, state)
            
            # Store credentials
            await self._store_credentials(user_id, tool_name, credentials)
            
            return {
                "success": True,
                "message": f"{tool_name} authentication successful"
            }
            
        except Exception as e:
            return {"error": f"OAuth callback failed: {str(e)}"}
    
    async def handle_manual_auth(self, user_id: str, tool_name: str, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manual authentication submission"""
        try:
            handler = ManualAuthHandlerFactory.get_handler(tool_name)
            credentials = await handler.process_auth_response(auth_data, user_id)
            
            # Store credentials
            await self._store_credentials(user_id, tool_name, credentials)
            
            return {
                "success": True,
                "message": f"{tool_name} authentication successful"
            }
            
        except Exception as e:
            return {"error": f"Manual auth failed: {str(e)}"}
    
    def _generate_state_token(self, user_id: str, tool_name: str) -> str:
        """Generate JWT state token for OAuth2"""
        payload = {
            "user_id": user_id,
            "tool_name": tool_name,
            "timestamp": datetime.utcnow().isoformat(),
            "exp": datetime.utcnow() + timedelta(minutes=10)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    def _decode_state_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate state token"""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise ValueError("State token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid state token")
    
    async def _store_credentials(self, user_id: str, tool_name: str, credentials: Dict[str, Any]):
        """Store authentication credentials"""
        # Implementation depends on your database setup
        # This is a placeholder
        print(f"Storing credentials for user {user_id}, tool {tool_name}")
        print(f"Credentials: {credentials}")
    
    async def get_credentials(self, user_id: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get stored credentials for a user and tool"""
        # Implementation depends on your database setup
        # This is a placeholder
        return None
    
    async def revoke_credentials(self, user_id: str, tool_name: str) -> bool:
        """Revoke stored credentials"""
        # Implementation depends on your database setup
        # This is a placeholder
        return True

    def _get_oauth_credentials(self, tool_name: str) -> Tuple[str, str]:
        """Get OAuth credentials for a tool from settings"""
        credentials_map = {
            "github": (settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET),
            "reddit": (settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET),
            "google": (settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET),
            "slack": (settings.SLACK_CLIENT_ID, settings.SLACK_CLIENT_SECRET),
        }
        
        if tool_name not in credentials_map:
            raise ValueError(f"No credentials configured for tool: {tool_name}")
        
        client_id, client_secret = credentials_map[tool_name]
        if not client_id or not client_secret:
            raise ValueError(f"Missing credentials for tool: {tool_name}")
        
        return client_id, client_secret
    
    def _get_manual_auth_config(self, tool_name: str) -> Dict[str, str]:
        """Get manual auth configuration for a tool"""
        if tool_name == "r2r":
            return {
                "auth_url": settings.R2R_AUTH_URL
            }
        else:
            raise ValueError(f"No manual auth configuration for tool: {tool_name}")

    def _generate_form_html(self, tool_name: str, user_id: str, required_fields: list) -> str:
        """Generate beautiful form HTML"""
        tool_display_names = {
            "n8n": "N8N Workflow Automation",
            "api_key": "API Key Authentication",
        }
        
        display_name = tool_display_names.get(tool_name, tool_name.title())
        
        # Generate form fields
        form_fields = ""
        for field in required_fields:
            field_name = field["name"]
            field_type = field["type"]
            field_desc = field["description"]
            is_required = field["required"]
            
            form_fields += f"""
                <div class="form-group">
                    <label for="{field_name}" class="form-label">
                        {field_desc}
                        {' <span class="required">*</span>' if is_required else ''}
                    </label>
                    <input 
                        type="{field_type}" 
                        id="{field_name}" 
                        name="{field_name}" 
                        class="form-input" 
                        placeholder="Enter your {field_desc.lower()}"
                        {'required' if is_required else ''}
                    />
                </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Connect {display_name} - ModuleX</title>
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
                
                .header {{
                    text-align: center;
                    margin-bottom: 32px;
                }}
                
                .tool-icon {{
                    width: 64px;
                    height: 64px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 12px;
                    margin: 0 auto 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 28px;
                    font-weight: bold;
                }}
                
                .title {{
                    font-size: 24px;
                    font-weight: 700;
                    color: #1f2937;
                    margin-bottom: 8px;
                }}
                
                .subtitle {{
                    color: #6b7280;
                    font-size: 14px;
                    line-height: 1.5;
                }}
                
                .form-group {{
                    margin-bottom: 20px;
                }}
                
                .form-label {{
                    display: block;
                    font-weight: 600;
                    color: #374151;
                    margin-bottom: 8px;
                    font-size: 14px;
                }}
                
                .required {{
                    color: #ef4444;
                }}
                
                .form-input {{
                    width: 100%;
                    padding: 12px 16px;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    font-size: 14px;
                    transition: all 0.2s ease;
                    background: #f9fafb;
                }}
                
                .form-input:focus {{
                    outline: none;
                    border-color: #667eea;
                    background: white;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }}
                
                .submit-button {{
                    width: 100%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 14px 20px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    margin-top: 8px;
                }}
                
                .submit-button:hover {{
                    transform: translateY(-1px);
                    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
                }}
                
                .submit-button:active {{
                    transform: translateY(0);
                }}
                
                .footer {{
                    text-align: center;
                    margin-top: 24px;
                    font-size: 12px;
                    color: #9CA3AF;
                }}
                
                .error-message {{
                    background: #fee2e2;
                    color: #dc2626;
                    padding: 12px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    font-size: 14px;
                    display: none;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="tool-icon">
                        {display_name[0]}
                    </div>
                    <h1 class="title">Connect {display_name}</h1>
                    <p class="subtitle">
                        Enter your {display_name} credentials to connect your account with ModuleX.
                        This information will be securely encrypted and stored.
                    </p>
                </div>
                
                <div id="error-message" class="error-message"></div>
                
                <form id="auth-form" action="/auth/form/{tool_name}?user_id={user_id}" method="POST">
                    {form_fields}
                    
                    <button type="submit" class="submit-button">
                        Connect {display_name}
                    </button>
                </form>
                
                <div class="footer">
                    Powered by ModuleX • Secure Authentication System
                </div>
            </div>
            
            <script>
                document.getElementById('auth-form').addEventListener('submit', async function(e) {{
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    const errorDiv = document.getElementById('error-message');
                    
                    try {{
                        const response = await fetch(this.action, {{
                            method: 'POST',
                            body: formData
                        }});
                        
                        if (response.ok) {{
                            // Success - show success page or redirect to callback
                            window.location.href = '/auth/callback/form/{tool_name}?user_id={user_id}';
                        }} else {{
                            const errorText = await response.text();
                            errorDiv.textContent = 'Authentication failed. Please check your credentials.';
                            errorDiv.style.display = 'block';
                        }}
                    }} catch (error) {{
                        errorDiv.textContent = 'Connection error. Please try again.';
                        errorDiv.style.display = 'block';
                    }}
                }});
            </script>
        </body>
        </html>
        """ 