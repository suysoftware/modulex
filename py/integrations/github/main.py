#!/usr/bin/env python3
"""
GitHub Integration - Main Script
"""
import json
import sys
import os
import requests
from typing import Dict, Any


def debug_print(message: str):
    """Print debug messages to stderr to avoid interfering with JSON output"""
    print(message, file=sys.stderr)


def get_auth_headers() -> Dict[str, str]:
    """Get GitHub API authentication headers"""
    access_token = os.getenv("ACCESS_TOKEN")
    debug_print(f"🔑 DEBUG [GitHub]: ACCESS_TOKEN from env: {'Found' if access_token else 'Not found'}")
    if access_token:
        debug_print(f"🔑 DEBUG [GitHub]: ACCESS_TOKEN length: {len(access_token)}, starts with: {access_token[:10]}...")
    
    if not access_token:
        debug_print(f"❌ DEBUG [GitHub]: ACCESS_TOKEN not found in environment variables")
        debug_print(f"🌍 DEBUG [GitHub]: Available env vars: {list(os.environ.keys())}")
        raise ValueError("ACCESS_TOKEN not found in environment")
    
    return {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }


def list_repositories(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """List user's repositories"""
    headers = get_auth_headers()
    per_page = parameters.get("per_page", 30)
    
    debug_print(f"📡 DEBUG [GitHub]: Making request to list repositories with per_page={per_page}")
    debug_print(f"🔐 DEBUG [GitHub]: Using Authorization header: {headers['Authorization'][:20]}...")
    
    response = requests.get(
        f"https://api.github.com/user/repos?per_page={per_page}",
        headers=headers
    )
    
    debug_print(f"📊 DEBUG [GitHub]: API Response status code: {response.status_code}")
    if response.status_code != 200:
        debug_print(f"❌ DEBUG [GitHub]: API Error response: {response.text}")
    
    response.raise_for_status()
    
    repos = response.json()
    debug_print(f"✅ DEBUG [GitHub]: Successfully retrieved {len(repos)} repositories")
    return {
        "repositories": [
            {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo["description"],
                "private": repo["private"],
                "url": repo["html_url"],
                "clone_url": repo["clone_url"]
            }
            for repo in repos
        ],
        "total": len(repos)
    }


def create_repository(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new repository"""
    headers = get_auth_headers()
    
    name = parameters.get("name")
    if not name:
        raise ValueError("Repository name is required")
    
    data = {
        "name": name,
        "description": parameters.get("description", ""),
        "private": parameters.get("private", False)
    }
    
    debug_print(f"📡 DEBUG [GitHub]: Making request to create repository '{name}'")
    debug_print(f"🔐 DEBUG [GitHub]: Using Authorization header: {headers['Authorization'][:20]}...")
    debug_print(f"📦 DEBUG [GitHub]: Repository data: {data}")
    
    response = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json=data
    )
    
    debug_print(f"📊 DEBUG [GitHub]: API Response status code: {response.status_code}")
    if response.status_code != 201:
        debug_print(f"❌ DEBUG [GitHub]: API Error response: {response.text}")
    
    response.raise_for_status()
    
    repo = response.json()
    debug_print(f"✅ DEBUG [GitHub]: Successfully created repository '{repo['name']}'")
    return {
        "repository": {
            "name": repo["name"],
            "full_name": repo["full_name"],
            "description": repo["description"],
            "private": repo["private"],
            "url": repo["html_url"],
            "clone_url": repo["clone_url"]
        }
    }


def get_user_info(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Get user information"""
    headers = get_auth_headers()
    
    debug_print(f"📡 DEBUG [GitHub]: Making request to get user info")
    debug_print(f"🔐 DEBUG [GitHub]: Using Authorization header: {headers['Authorization'][:20]}...")
    
    response = requests.get("https://api.github.com/user", headers=headers)
    
    debug_print(f"📊 DEBUG [GitHub]: API Response status code: {response.status_code}")
    if response.status_code != 200:
        debug_print(f"❌ DEBUG [GitHub]: API Error response: {response.text}")
    
    response.raise_for_status()
    
    user = response.json()
    debug_print(f"✅ DEBUG [GitHub]: Successfully retrieved user info for '{user.get('login', 'unknown')}'")
    return {
        "user": {
            "login": user["login"],
            "name": user["name"],
            "email": user["email"],
            "bio": user["bio"],
            "location": user["location"],
            "public_repos": user["public_repos"],
            "followers": user["followers"],
            "following": user["following"]
        }
    }


def main():
    """Main execution function"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        action = input_data.get("action")
        parameters = input_data.get("parameters", {})
        
        debug_print(f"🚀 DEBUG [GitHub]: Starting execution of action '{action}' with parameters: {parameters}")
        
        # Execute action
        if action == "list_repositories":
            result = list_repositories(parameters)
        elif action == "create_repository":
            result = create_repository(parameters)
        elif action == "get_user_info":
            result = get_user_info(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
        
        debug_print(f"🎉 DEBUG [GitHub]: Action '{action}' completed successfully")
        
        # Return result (to stdout)
        print(json.dumps(result))
        
    except Exception as e:
        debug_print(f"💥 DEBUG [GitHub]: Action failed with error: {str(e)}")
        debug_print(f"🔍 DEBUG [GitHub]: Error type: {type(e).__name__}")
        
        # Return error (to stdout)
        error_result = {
            "error": str(e),
            "type": type(e).__name__
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main() 