"""
Authentication Module for ModuleX

Supports 3 authentication providers based on TOML config:
1. default - X-API-KEY + user_id parameter required
2. custom - X-API-KEY + user_id OR Authorization with custom endpoint verification
3. supabase - X-API-KEY + user_id OR Authorization with Supabase verification

IMPORTANT: User cannot send both X-API-KEY and Authorization headers simultaneously.
"""

import os
import httpx
import logging
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, Depends, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .toml_config import toml_config
from .x_api_key_auth import verify_x_api_key

logger = logging.getLogger(__name__)

# Security instance for Authorization Bearer tokens
security = HTTPBearer(auto_error=False)

class AuthResult:
    """Authentication result containing user info"""
    def __init__(
        self, 
        user_id: str, 
        auth_method: str, 
        additional_data: Optional[Dict] = None,
        requires_user_id_param: bool = False
    ):
        self.user_id = user_id
        self.auth_method = auth_method  # "x_api_key", "custom_token", "supabase_token"
        self.additional_data = additional_data or {}
        self.requires_user_id_param = requires_user_id_param

class AuthHandler:
    """Main authentication handler based on TOML provider setting"""
    
    def __init__(self):
        # Initialize Supabase client (lazy loading)
        self._supabase_client = None
    
    def _get_supabase_client(self):
        """Get Supabase client (lazy initialization)"""
        if self._supabase_client is None:
            try:
                from supabase import create_client
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_ANON_KEY")
                
                if not supabase_url or not supabase_key:
                    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
                
                self._supabase_client = create_client(supabase_url, supabase_key)
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Supabase SDK not installed"
                )
        return self._supabase_client
    
    async def authenticate(
        self,
        x_api_key: Optional[str] = None,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
        user_id: Optional[str] = None,
        endpoint_requires_user_id: bool = True
    ) -> AuthResult:
        """
        Main authentication method
        
        Args:
            x_api_key: X-API-KEY header value
            credentials: Authorization Bearer token
            user_id: user_id parameter from request
            endpoint_requires_user_id: Whether this endpoint requires user_id parameter
            
        Returns:
            AuthResult: Authentication result with user info
        """
        # Check that user doesn't send both headers
        if x_api_key and credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot use both X-API-KEY and Authorization headers simultaneously"
            )
        
        if not x_api_key and not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Either X-API-KEY or Authorization header is required"
            )
        
        provider = toml_config.get_auth_provider()
        
        # Handle X-API-KEY authentication (available for all providers)
        if x_api_key:
            return await self._authenticate_with_x_api_key(
                x_api_key, user_id, endpoint_requires_user_id, provider
            )
        
        # Handle Authorization Bearer authentication
        if credentials:
            if provider == "default":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Authorization Bearer tokens not supported with 'default' provider. Use X-API-KEY instead."
                )
            elif provider == "custom":
                return await self._authenticate_custom_token(credentials)
            elif provider == "supabase":
                return await self._authenticate_supabase_token(credentials)
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unknown auth provider: {provider}"
                )
    
    async def _authenticate_with_x_api_key(
        self, 
        x_api_key: str, 
        user_id: Optional[str], 
        endpoint_requires_user_id: bool,
        provider: str
    ) -> AuthResult:
        """Authenticate using X-API-KEY (works with all providers)"""
        
        # Verify X-API-KEY against MODULEX_API_KEY
        modulex_api_key = os.getenv("MODULEX_API_KEY")
        if not modulex_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MODULEX_API_KEY not configured"
            )
        
        if x_api_key != modulex_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid X-API-KEY"
            )
        
        # Check user_id parameter requirement
        if endpoint_requires_user_id and not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id parameter required when using X-API-KEY"
            )
        
        return AuthResult(
            user_id=user_id or "admin_user",
            auth_method="x_api_key",
            additional_data={"provider": provider},
            requires_user_id_param=endpoint_requires_user_id
        )
    
    async def _authenticate_custom_token(self, credentials: HTTPAuthorizationCredentials) -> AuthResult:
        """Authenticate using custom token verification endpoint"""
        
        custom_endpoint = os.getenv("CUSTOM_AUTH_TOKEN_VERIFICATION_ENDPOINT")
        if not custom_endpoint:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CUSTOM_AUTH_TOKEN_VERIFICATION_ENDPOINT not configured"
            )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    custom_endpoint,
                    headers={"Authorization": f"Bearer {credentials.credentials}"},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Custom token verification failed"
                    )
                
                user_data = response.json()
                user_id = user_data.get("user_id")
                
                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token: no user_id returned from verification endpoint"
                    )
                
                return AuthResult(
                    user_id=str(user_id),
                    auth_method="custom_token",
                    additional_data=user_data
                )
                
        except httpx.RequestError as e:
            logger.error(f"Custom auth endpoint error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Custom authentication service unavailable"
            )
    
    async def _authenticate_supabase_token(self, credentials: HTTPAuthorizationCredentials) -> AuthResult:
        """Authenticate using Supabase token verification"""
        
        try:
            supabase = self._get_supabase_client()
            
            # Verify token with Supabase
            response = supabase.auth.get_user(credentials.credentials)
            
            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Supabase token"
                )
            
            user_data = {
                "user_id": response.user.id,
                "email": response.user.email,
                "email_confirmed_at": str(response.user.email_confirmed_at) if response.user.email_confirmed_at else None,
                "created_at": str(response.user.created_at) if response.user.created_at else None,
            }
            
            return AuthResult(
                user_id=response.user.id,
                auth_method="supabase_token",
                additional_data=user_data
            )
            
        except Exception as e:
            logger.error(f"Supabase auth error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase token validation failed"
            )

# Global auth handler
auth_handler = AuthHandler()

async def get_current_user(
    x_api_key: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_id: Optional[str] = None,
    endpoint_requires_user_id: bool = True
) -> AuthResult:
    """
    FastAPI dependency to get current authenticated user
    
    Usage in endpoints:
        # For endpoints that require user_id parameter:
        @router.get("/tools")
        async def get_tools(
            user: AuthResult = Depends(get_current_user), 
            user_id: str = Query(None)
        ):
            effective_user_id = user_id if user.auth_method == "x_api_key" else user.user_id
        
        # For endpoints that don't require user_id parameter:
        @router.get("/health")  
        async def health_check(
            user: AuthResult = Depends(lambda: get_current_user(endpoint_requires_user_id=False))
        ):
            pass
    """
    return await auth_handler.authenticate(
        x_api_key=x_api_key,
        credentials=credentials, 
        user_id=user_id,
        endpoint_requires_user_id=endpoint_requires_user_id
    )

# Convenience functions for specific use cases
def auth_required(endpoint_requires_user_id: bool = True):
    """
    Decorator-style function to create auth dependency
    
    Usage:
        @router.get("/tools")
        async def get_tools(
            user: AuthResult = Depends(auth_required(endpoint_requires_user_id=True)),
            user_id: str = Query(None)
        ):
            pass
    """
    async def _auth_dependency(
        x_api_key: Optional[str] = Header(None),
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        user_id: Optional[str] = None
    ) -> AuthResult:
        return await auth_handler.authenticate(
            x_api_key=x_api_key,
            credentials=credentials,
            user_id=user_id,
            endpoint_requires_user_id=endpoint_requires_user_id
        )
    
    return _auth_dependency 