#!/usr/bin/env python3
"""
N8N Integration - Main Script
"""
import json
import sys
import os
import requests
from typing import Dict, Any, Optional


def get_n8n_credentials(user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Get n8n credentials from user data, preferring user-specific credentials."""
    if user_credentials:
        return {
            "base_url": user_credentials.get("base_url") or user_credentials.get("N8N_BASE_URL"),
            "api_key": user_credentials.get("api_key") or user_credentials.get("N8N_API_KEY")
        }
    else:
        # Fallback to environment variables if no user credentials provided
        return {
            "base_url": os.getenv("N8N_BASE_URL"),
            "api_key": os.getenv("N8N_API_KEY")
        }


def get_n8n_client(base_url: str, api_key: str):
    """Initialize n8n client with credentials."""
    if not base_url or not api_key:
        raise ValueError("N8N base URL and API key are required")
    
    # Remove trailing slash if present
    base_url = base_url.rstrip('/')
    
    return {
        "base_url": base_url,
        "api_key": api_key
    }


def make_n8n_request(client: Dict[str, str], endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make HTTP request to n8n API."""
    url = f"{client['base_url']}/api/v1{endpoint}"
    headers = {
        "X-N8N-API-KEY": client["api_key"],
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        error_message = f"N8N API error: {response.text}" if 'response' in locals() else str(e)
        raise ValueError(error_message)
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to connect to n8n: {str(e)}")


def test_connection(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Test connection to n8n instance."""
    try:
        # Get credentials
        credentials = get_n8n_credentials(user_credentials)
        base_url = credentials.get("base_url")
        api_key = credentials.get("api_key")
        
        if not base_url or not api_key:
            raise ValueError("N8N base URL and API key are required. Please provide them via user_credentials or environment variables")
        
        # Create client and test connection
        client = get_n8n_client(base_url, api_key)
        
        # Test connection by listing workflows
        make_n8n_request(client, "/workflows")
        
        return {
            "success": True,
            "message": f"Successfully connected to n8n at {base_url}",
            "connection_details": {
                "url": base_url,
                "status": "connected"
            }
        }
        
    except Exception as e:
        raise ValueError(f"Failed to test n8n connection: {str(e)}")


def list_workflows(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """List all workflows from n8n."""
    try:
        # Get credentials
        credentials = get_n8n_credentials(user_credentials)
        base_url = credentials.get("base_url")
        api_key = credentials.get("api_key")
        
        if not base_url or not api_key:
            raise ValueError("N8N base URL and API key are required. Please provide them via user_credentials or environment variables")
        
        client = get_n8n_client(base_url, api_key)
        
        # List workflows
        workflows_response = make_n8n_request(client, "/workflows")
        
        # Format response
        workflows = workflows_response.get("data", [])
        formatted_workflows = []
        
        for wf in workflows:
            formatted_workflows.append({
                "id": wf.get("id"),
                "name": wf.get("name"),
                "active": wf.get("active"),
                "created": wf.get("createdAt"),
                "updated": wf.get("updatedAt"),
                "tags": wf.get("tags", [])
            })
        
        return {
            "success": True,
            "workflows": formatted_workflows,
            "total": len(formatted_workflows)
        }
        
    except Exception as e:
        raise ValueError(f"Failed to list workflows: {str(e)}")


def create_workflow(parameters: Dict[str, Any], user_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a new workflow in n8n."""
    try:
        name = parameters.get("name")
        nodes = parameters.get("nodes", [])
        connections = parameters.get("connections", {})
        
        if not name:
            raise ValueError("name parameter is required")
        
        # Get credentials
        credentials = get_n8n_credentials(user_credentials)
        base_url = credentials.get("base_url")
        api_key = credentials.get("api_key")
        
        if not base_url or not api_key:
            raise ValueError("N8N base URL and API key are required. Please provide them via user_credentials or environment variables")
        
        client = get_n8n_client(base_url, api_key)
        
        # Prepare workflow data
        workflow_data = {
            "name": name,
            "nodes": nodes,
            "connections": connections,
            "active": False,  # Default to inactive for safety
            "settings": {
                "saveManualExecutions": True,
                "saveExecutionProgress": True
            }
        }
        
        # Create workflow
        workflow = make_n8n_request(client, "/workflows", "POST", workflow_data)
        
        return {
            "success": True,
            "message": f"Successfully created workflow: {name}",
            "workflow": {
                "id": workflow.get("id"),
                "name": workflow.get("name"),
                "active": workflow.get("active"),
                "created": workflow.get("createdAt"),
                "updated": workflow.get("updatedAt")
            }
        }
        
    except Exception as e:
        raise ValueError(f"Failed to create workflow: {str(e)}")


def main():
    """Main execution function"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        action = input_data.get("action")
        parameters = input_data.get("parameters", {})
        user_credentials = input_data.get("user_credentials")
        
        # Execute action based on action name
        if action == "test_connection":
            result = test_connection(parameters, user_credentials)
        elif action == "list_workflows":
            result = list_workflows(parameters, user_credentials)
        elif action == "create_workflow":
            result = create_workflow(parameters, user_credentials)
        else:
            raise ValueError(f"Unknown action: {action}")
        
        # Return result
        print(json.dumps(result))
        
    except Exception as e:
        # Return error in standardized format
        error_result = {
            "error": str(e),
            "type": type(e).__name__
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
