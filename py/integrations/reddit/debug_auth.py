#!/usr/bin/env python3
"""
Reddit OAuth2 Authentication Debug Script
"""
import os
import json
import requests
from typing import Dict, Any, Optional

def test_reddit_credentials(user_credentials: Dict[str, Any] = None) -> Dict[str, Any]:
    """Test Reddit API credentials"""
    
    # Get credentials
    if user_credentials and user_credentials.get("auth_type") == "manual":
        client_id = user_credentials.get("client_id")
        client_secret = user_credentials.get("client_secret")
        access_token = user_credentials.get("access_token")
        refresh_token = user_credentials.get("refresh_token")
    else:
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        access_token = user_credentials.get("access_token") if user_credentials else None
        refresh_token = user_credentials.get("refresh_token") if user_credentials else None

    result = {
        "client_id_exists": bool(client_id),
        "client_secret_exists": bool(client_secret),
        "access_token_exists": bool(access_token),
        "refresh_token_exists": bool(refresh_token)
    }
    
    print("🔍 Reddit Credentials Check:")
    print(f"  Client ID: {'✅' if result['client_id_exists'] else '❌'}")
    print(f"  Client Secret: {'✅' if result['client_secret_exists'] else '❌'}")
    print(f"  Access Token: {'✅' if result['access_token_exists'] else '❌'}")
    print(f"  Refresh Token: {'✅' if result['refresh_token_exists'] else '❌'}")
    
    # Test API call if access token exists
    if access_token:
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "ModuleX Reddit Integration/1.0"
            }
            
            response = requests.get("https://oauth.reddit.com/api/v1/me", headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                result["api_test"] = "success"
                result["user_name"] = user_data.get("name")
                print(f"✅ API Test: Success - User: {user_data.get('name')}")
            else:
                result["api_test"] = "failed"
                result["status_code"] = response.status_code
                result["error"] = response.text
                print(f"❌ API Test: Failed - Status: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except Exception as e:
            result["api_test"] = "error"
            result["exception"] = str(e)
            print(f"💥 API Test: Exception - {str(e)}")
    else:
        result["api_test"] = "no_token"
        print("⚠️ API Test: Skipped - No access token")
    
    return result

def refresh_access_token(refresh_token: str, client_id: str, client_secret: str) -> Dict[str, Any]:
    """Refresh Reddit access token"""
    
    if not all([refresh_token, client_id, client_secret]):
        return {"error": "Missing required parameters for token refresh"}
    
    try:
        # Reddit token refresh endpoint
        token_url = "https://www.reddit.com/api/v1/access_token"
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        auth = (client_id, client_secret)
        headers = {"User-Agent": "ModuleX Reddit Integration/1.0"}
        
        response = requests.post(token_url, data=data, auth=auth, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Token Refresh: Success")
            print(f"   New Access Token: {token_data.get('access_token', 'N/A')[:20]}...")
            return token_data
        else:
            print(f"❌ Token Refresh: Failed - Status: {response.status_code}")
            print(f"   Error: {response.text}")
            return {"error": f"Token refresh failed: {response.status_code}"}
            
    except Exception as e:
        print(f"💥 Token Refresh: Exception - {str(e)}")
        return {"error": f"Token refresh exception: {str(e)}"}

if __name__ == "__main__":
    print("🔧 Reddit OAuth2 Debug Tool")
    print("=" * 50)
    
    # Test with environment credentials
    print("\n1. Testing Environment Credentials:")
    env_result = test_reddit_credentials()
    
    # Test token refresh if refresh token available
    if env_result.get("refresh_token_exists") and env_result.get("api_test") == "failed":
        print("\n2. Attempting Token Refresh:")
        refresh_result = refresh_access_token(
            refresh_token=os.getenv("REDDIT_REFRESH_TOKEN", ""),
            client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET", "")
        )
        
        if "access_token" in refresh_result:
            print("\n3. Testing with Refreshed Token:")
            test_creds = {
                "access_token": refresh_result["access_token"],
                "refresh_token": refresh_result.get("refresh_token")
            }
            test_reddit_credentials(test_creds)
    
    print("\n" + "=" * 50)
    print("Debug completed!") 