#!/usr/bin/env python3
"""
GitHub Integration - Main Script
"""
import json
import sys
import os
import requests
from typing import Dict, Any


def get_auth_headers() -> Dict[str, str]:
    """Get GitHub API authentication headers"""
    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        raise ValueError("ACCESS_TOKEN not found in environment")
    
    return {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }


def list_repositories(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """List user's repositories"""
    headers = get_auth_headers()
    per_page = parameters.get("per_page", 30)
    
    response = requests.get(
        f"https://api.github.com/user/repos?per_page={per_page}",
        headers=headers
    )
    response.raise_for_status()
    
    repos = response.json()
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
    
    response = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json=data
    )
    response.raise_for_status()
    
    repo = response.json()
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
    
    response = requests.get("https://api.github.com/user", headers=headers)
    response.raise_for_status()
    
    user = response.json()
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
        
        # Execute action
        if action == "list_repositories":
            result = list_repositories(parameters)
        elif action == "create_repository":
            result = create_repository(parameters)
        elif action == "get_user_info":
            result = get_user_info(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
        
        # Return result
        print(json.dumps(result))
        
    except Exception as e:
        # Return error
        error_result = {
            "error": str(e),
            "type": type(e).__name__
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main() 