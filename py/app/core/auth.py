"""
Authentication Module for ModuleX

Professional authentication system using Strategy Pattern:
- UserAuthenticator: For user endpoints requiring user_id
- SystemAuthenticator: For system/admin endpoints  
- Clean separation of concerns and single responsibility principle
"""

import os
import httpx
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, Depends, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .toml_config import toml_config

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
        is_system_user: bool = False
    ):
        self.user_id = user_id
        self.auth_method = auth_method  # "x_api_key", "custom_token", "supabase_token"
        self.additional_data = additional_data or {}
        self.is_system_user = is_system_user

class BaseAuthenticator(ABC):
    """Base authenticator interface following Strategy Pattern"""
    
    def __init__(self):
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
    
    @abstractmethod
    async def authenticate(
        self,
        x_api_key: Optional[str] = None,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
        user_id: Optional[str] = None
    ) -> AuthResult:
        """Authenticate request and return result"""
        pass
    
    def _validate_headers(self, x_api_key: Optional[str], credentials: Optional[HTTPAuthorizationCredentials]):
        """Common header validation"""
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
    
    def _verify_x_api_key(self, x_api_key: str) -> bool:
        """Common X-API-KEY verification"""
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
        
        return True
    
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
                    additional_data=user_data,
                    is_system_user=False
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
                additional_data=user_data,
                is_system_user=False
            )
            
        except Exception as e:
            logger.error(f"Supabase auth error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase token validation failed"
            )

class UserAuthenticator(BaseAuthenticator):
    """Authenticator for user endpoints - requires user_id for X-API-KEY"""
    
    async def authenticate(
        self,
        x_api_key: Optional[str] = None,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
        user_id: Optional[str] = None
    ) -> AuthResult:
        """Authenticate user request"""
        self._validate_headers(x_api_key, credentials)
        provider = toml_config.get_auth_provider()
        
        # Handle X-API-KEY authentication
        if x_api_key:
            self._verify_x_api_key(x_api_key)
            
            # User endpoints require user_id parameter
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="user_id parameter required for user endpoints when using X-API-KEY"
                )
            
            return AuthResult(
                user_id=user_id,
                auth_method="x_api_key",
                additional_data={"provider": provider},
                is_system_user=False
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

class SystemAuthenticator(BaseAuthenticator):
    """Authenticator for system endpoints - X-API-KEY only, user_id optional"""
    
    async def authenticate(
        self,
        x_api_key: Optional[str] = None,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
        user_id: Optional[str] = None
    ) -> AuthResult:
        """Authenticate system request"""
        # System endpoints only accept X-API-KEY
        if credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System endpoints only accept X-API-KEY authentication"
            )
        
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-API-KEY header required for system endpoints"
            )
        
        self._verify_x_api_key(x_api_key)
        provider = toml_config.get_auth_provider()
        
        return AuthResult(
            user_id=user_id or "system_admin",
            auth_method="x_api_key",
            additional_data={"provider": provider},
            is_system_user=True
        )

# Global authenticator instances
user_authenticator = UserAuthenticator()
system_authenticator = SystemAuthenticator()

# Clean, professional authentication dependencies
async def user_auth_required(
    x_api_key: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_id: Optional[str] = None
) -> AuthResult:
    """
    Authentication dependency for user endpoints (tools, auth, etc.)
    Uses UserAuthenticator strategy
    """
    return await user_authenticator.authenticate(
        x_api_key=x_api_key,
        credentials=credentials,
        user_id=user_id
    )

async def system_auth_required(
    x_api_key: Optional[str] = Header(None),
    user_id: Optional[str] = None
) -> AuthResult:
    """
    Authentication dependency for system endpoints (config, health, etc.)
    Uses SystemAuthenticator strategy
    """
    return await system_authenticator.authenticate(
        x_api_key=x_api_key,
        credentials=None,
        user_id=user_id
    )

# Backward compatibility alias
auth_required = lambda endpoint_requires_user_id=True: user_auth_required if endpoint_requires_user_id else system_auth_required 