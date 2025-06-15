# ModuleX API Documentation

## Overview
ModuleX is a simple tool authentication and execution server that supports OAuth2 authentication and tool execution for various integrations.

**Base URL:** `http://localhost:8000`  
**Version:** `0.1.2`  
**Total Endpoints:** `14`

## Endpoint Summary

| Category | Count | Description |
|----------|--------|-------------|
| **Main App** | 2 | Root and health check endpoints |
| **Authentication** | 7 | OAuth flows, manual auth, tool and action management |
| **Tools** | 5 | Tool listing, execution, and OpenAI integration |
| **Total** | **14** | All available endpoints |

---

## 🏠 Main Application Endpoints

### 1. Root Endpoint
- **Method:** `GET`
- **Path:** `/`
- **Description:** Welcome endpoint with basic API information
- **Authentication:** None required

**Response Example:**
```json
{
  "message": "ModuleX - Simplified Version",
  "version": "0.1.2",
  "docs": "/docs",
  "endpoints": {
    "auth": {
      "get_auth_url": "/auth/url/{tool_name}?user_id=YOUR_USER_ID",
      "callback": "/auth/callback/{tool_name}",
      "list_user_tools": "/auth/tools?user_id=YOUR_USER_ID"
    },
    "tools": {
      "list_tools": "/tools/",
      "get_tool_info": "/tools/{tool_name}",
      "execute_tool": "/tools/{tool_name}/execute?user_id=YOUR_USER_ID",
      "get_user_openai_tools": "/tools/openai/users/{user_id}/openai-tools"
    }
  }
}
```

### 2. Health Check
- **Method:** `GET`
- **Path:** `/health/`
- **Description:** Health check endpoint for monitoring and deployment
- **Authentication:** None required

**Response Example:**
```json
{
  "status": "healthy",
  "service": "ModuleX"
}
```

---

## 🔐 Authentication Endpoints

### 1. Get OAuth Authorization URL
- **Method:** `GET`
- **Path:** `/auth/url/{tool_name}`
- **Description:** Generate OAuth authorization URL for a specific tool
- **Authentication:** None required

**Path Parameters:**
- `tool_name` (string): Name of the tool (e.g., "github", "google", "slack")

**Query Parameters:**
- `user_id` (string, required): User identifier

**Request Example:**
```bash
GET /auth/url/github?user_id=user123
```

**Response Example:**
```json
{
  "auth_url": "https://github.com/login/oauth/authorize?client_id=...",
  "state": "random_state_token",
  "tool_name": "github"
}
```

### 2. Manual Authentication
- **Method:** `POST`
- **Path:** `/auth/manual`
- **Description:** Register credentials manually without OAuth flow
- **Authentication:** None required

**Request Body:**
```json
{
  "user_id": "user123",
  "tool_name": "github",
  "credentials": {
    "api_key": "your_api_key",
    "secret": "your_secret"
  }
}
```

**Response Example:**
```json
{
  "success": true,
  "message": "Manual credentials successfully registered for github",
  "user_id": "user123",
  "tool_name": "github"
}
```

### 3. OAuth Callback
- **Method:** `GET`
- **Path:** `/auth/callback/{tool_name}`
- **Description:** Handle OAuth callback after user authorization
- **Authentication:** None required (internal use)

**Path Parameters:**
- `tool_name` (string): Name of the tool

**Query Parameters:**
- `code` (string, required): Authorization code from OAuth provider
- `state` (string, required): State token for security

**Request Example:**
```bash
GET /auth/callback/github?code=auth_code&state=state_token
```

**Response Example:**
```json
{
  "success": true,
  "message": "Successfully authenticated with github"
}
```

### 4. Get All Tools with User Status
- **Method:** `GET`
- **Path:** `/auth/tools`
- **Description:** Get all available tools with user authentication and active status
- **Authentication:** User ID required

**Query Parameters:**
- `user_id` (string, required): User identifier
- `detail` (boolean, optional): Return detailed tool information (default: false)

**Request Example (Basic):**
```bash
GET /auth/tools?user_id=user123
```

**Basic Response Example:**
```json
{
  "user_id": "user123",
  "tools": [
    {
      "name": "github",
      "display_name": "GitHub",
      "is_authenticated": true,
      "is_active": true,
      "health_status": true,
      "actions": [
        {
          "name": "list_repositories",
          "description": "List user's GitHub repositories",
          "is_active": true
        },
        {
          "name": "create_repository",
          "description": "Create a new GitHub repository",
          "is_active": false
        }
      ]
    },
    {
      "name": "slack",
      "display_name": "Slack",
      "is_authenticated": false,
      "is_active": false,
      "health_status": true,
      "actions": [
        {
          "name": "send_message",
          "description": "Send a message to Slack",
          "is_active": false
        }
      ]
    }
  ],
  "total": 2,
  "detail": false
}
```

**Request Example (Detailed):**
```bash
GET /auth/tools?user_id=user123&detail=true
```

**Detailed Response Example:**
```json
{
  "user_id": "user123",
  "tools": [
    {
      "name": "github",
      "display_name": "GitHub",
      "description": "GitHub repository and user management",
      "is_authenticated": true,
      "is_active": true,
      "health_status": true,
      "version": "1.0.0",
      "author": "ModuleX",
      "requires_auth": true,
      "auth_type": "oauth2",
      "actions": [
        {
          "name": "list_repositories",
          "description": "List user's GitHub repositories",
          "is_active": true
        },
        {
          "name": "create_repository",
          "description": "Create a new GitHub repository",
          "is_active": false
        }
      ]
    }
  ],
  "total": 1,
  "detail": true
}
```

### 5. Set Tool Active Status
- **Method:** `PUT`
- **Path:** `/auth/users/{user_id}/tools/{tool_name}/status`
- **Description:** Enable or disable a user's authenticated tool
- **Authentication:** User ownership required

**Path Parameters:**
- `user_id` (string): User identifier
- `tool_name` (string): Tool name to modify

**Request Body:**
```json
{
  "is_active": false
}
```

**Response Example:**
```json
{
  "success": true,
  "message": "Tool github deactivated successfully",
  "user_id": "user123",
  "tool_name": "github",
  "is_active": false
}
```

### 6. Set Action Disabled Status
- **Method:** `PUT`
- **Path:** `/auth/users/{user_id}/tools/{tool_name}/actions/{action_name}/status`
- **Description:** Enable or disable a specific action for a user's tool
- **Authentication:** User ownership required

**Path Parameters:**
- `user_id` (string): User identifier
- `tool_name` (string): Tool name
- `action_name` (string): Action name to modify

**Request Body:**
```json
{
  "is_disabled": true
}
```

**Response Example:**
```json
{
  "success": true,
  "message": "Action 'create_repository' for tool 'github' disabled successfully",
  "user_id": "user123",
  "tool_name": "github",
  "action_name": "create_repository",
  "is_disabled": true
}
```

---

## 🛠️ Tools Endpoints

### 1. List Available Tools
- **Method:** `GET`
- **Path:** `/tools/`
- **Description:** List all available tools in the system
- **Authentication:** None required

**Response Example:**
```json
{
  "tools": [
    {
      "name": "github",
      "display_name": "GitHub",
      "description": "GitHub repository and user management",
      "version": "1.0.0",
      "requires_auth": true,
      "auth_type": "oauth2",
      "actions": [
        {
          "name": "list_repositories",
          "description": "List user's GitHub repositories",
          "parameters": {
            "per_page": {
              "type": "integer",
              "description": "Number of repositories per page",
              "default": 30,
              "optional": true
            }
          }
        }
      ]
    }
  ],
  "total": 1
}
```

### 2. Get Tool Information
- **Method:** `GET`
- **Path:** `/tools/{tool_name}`
- **Description:** Get detailed information about a specific tool
- **Authentication:** None required

**Path Parameters:**
- `tool_name` (string): Name of the tool

**Request Example:**
```bash
GET /tools/github
```

**Response Example:**
```json
{
  "name": "github",
  "display_name": "GitHub",
  "description": "GitHub repository and user management",
  "version": "1.0.0",
  "requires_auth": true,
  "auth_type": "oauth2",
  "actions": [
    {
      "name": "list_repositories",
      "description": "List user's GitHub repositories",
      "parameters": {
        "per_page": {
          "type": "integer",
          "description": "Number of repositories per page",
          "default": 30,
          "optional": true
        }
      }
    }
  ]
}
```

### 3. Execute Tool Action
- **Method:** `POST`
- **Path:** `/tools/{tool_name}/execute`
- **Description:** Execute a specific action on a tool for a user
- **Authentication:** User must be authenticated with the tool and action must be enabled

**Path Parameters:**
- `tool_name` (string): Name of the tool to execute

**Query Parameters:**
- `user_id` (string, required): User identifier

**Request Body (Legacy Format):**
```json
{
  "action": "list_repositories",
  "parameters": {
    "per_page": 10
  }
}
```

**Request Body (New Format):**
```json
{
  "parameters": {
    "action": "list_repositories",
    "per_page": 10
  }
}
```

**Success Response Example:**
```json
{
  "success": true,
  "tool_name": "github",
  "action": "list_repositories",
  "result": [
    {
      "name": "my-repo",
      "full_name": "user/my-repo",
      "private": false,
      "description": "My repository description"
    }
  ],
  "execution_time": 1.23
}
```

**Disabled Action Response Example:**
```json
{
  "success": false,
  "error": "Action 'create_repository' is disabled for tool 'github'. Please enable it first.",
  "tool_name": "github",
  "action": "create_repository"
}
```

### 4. Get OpenAI Tools (Vercel AI SDK)
- **Method:** `GET`
- **Path:** `/tools/openai/users/{user_id}/openai-tools`
- **Description:** Get user's active tools with enabled actions in OpenAI function format for Vercel AI SDK
- **Authentication:** User ID required

**Path Parameters:**
- `user_id` (string): User identifier

**Request Example:**
```bash
GET /tools/openai/users/user123/openai-tools
```

**Response Example:**
```json
[
  {
    "type": "function",
    "function": {
      "name": "github_list_repositories",
      "description": "List user's GitHub repositories",
      "parameters": {
        "type": "object",
        "properties": {
          "per_page": {
            "type": "integer",
            "description": "Number of repositories per page"
          }
        },
        "required": []
      }
    },
    "metadata": {
      "tool_key": "github",
      "action": "list_repositories"
    }
  }
]
```

**Note:** Only enabled actions from active tools are returned. Disabled actions are filtered out automatically.

### 5. Get User Tools (Tools Module)
- **Method:** `GET`
- **Path:** `/tools/users/{user_id}/tools`
- **Description:** Get user's authenticated tools from the tools module
- **Authentication:** User ID required

**Path Parameters:**
- `user_id` (string): User identifier

**Query Parameters:**
- `active_only` (boolean, optional): Return only active tools (default: false)

**Request Example:**
```bash
GET /tools/users/user123/tools?active_only=true
```

**Response Example:**
```json
{
  "user_id": "user123",
  "tools": [
    {
      "tool_name": "github",
      "is_active": true,
      "disabled_actions": ["create_repository"],
      "last_auth_at": "2024-01-15T10:30:00Z",
      "last_used_at": "2024-01-15T11:00:00Z",
      "expires_at": null
    }
  ],
  "total": 1,
  "active_only": true
}
```

---

## 🔧 Usage Examples

### Complete OAuth Flow
```bash
# 1. Get authorization URL
GET /auth/url/github?user_id=user123

# 2. User visits the auth_url and authorizes
# 3. OAuth provider redirects to callback (automatic)
GET /auth/callback/github?code=...&state=...

# 4. Check all tools with user status
GET /auth/tools?user_id=user123

# 5. Execute tool action
POST /tools/github/execute?user_id=user123
{
  "action": "list_repositories",
  "parameters": {"per_page": 5}
}
```

### Tool and Action Management Flow
```bash
# 1. List available tools
GET /tools/

# 2. Get specific tool info
GET /tools/github

# 3. Check all tools with user status (basic)
GET /auth/tools?user_id=user123

# 4. Check all tools with detailed info
GET /auth/tools?user_id=user123&detail=true

# 5. Disable a specific action
PUT /auth/users/user123/tools/github/actions/create_repository/status
{"is_disabled": true}

# 6. Check tools again to see action status
GET /auth/tools?user_id=user123

# 7. Try to execute disabled action (will fail)
POST /tools/github/execute?user_id=user123
{"action": "create_repository", "parameters": {"name": "test"}}

# 8. Check OpenAI tools (disabled actions won't appear)
GET /tools/openai/users/user123/openai-tools

# 9. Re-enable the action
PUT /auth/users/user123/tools/github/actions/create_repository/status
{"is_disabled": false}

# 10. Deactivate entire tool
PUT /auth/users/user123/tools/github/status
{"is_active": false}
```

### Manual Authentication Flow
```bash
# 1. Register credentials manually
POST /auth/manual
{
  "user_id": "user123",
  "tool_name": "custom_api",
  "credentials": {
    "api_key": "your_api_key",
    "base_url": "https://api.example.com"
  }
}

# 2. Check tool status
GET /auth/tools?user_id=user123&detail=true

# 3. Execute tool action
POST /tools/custom_api/execute?user_id=user123
{
  "action": "get_data",
  "parameters": {"limit": 10}
}

# 4. Disable specific actions if needed
PUT /auth/users/user123/tools/custom_api/actions/delete_data/status
{"is_disabled": true}
```

---

## 📋 Error Responses

### Common Error Formats
```json
{
  "detail": "Error description"
}
```

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (validation errors, missing parameters)
- `404` - Not Found (tool not found, user not authenticated)
- `500` - Internal Server Error (server-side errors)

### Authentication Errors
- `Tool {tool_name} not found or not authenticated for user {user_id}`
- `User {user_id} not authenticated for {tool_name}. Please complete authentication.`
- `Invalid authentication for {tool_name}. Please re-authenticate.`

### Action Management Errors
- `Action '{action_name}' is disabled for tool '{tool_name}'. Please enable it first.`
- `Tool {tool_name} not found or not authenticated for user {user_id}`

---

## 🔐 Security Notes

1. **OAuth State:** OAuth flows use secure state tokens with 10-minute TTL
2. **Credential Encryption:** All user credentials are encrypted before storage
3. **Active Tools:** Only active tools can be executed and appear in OpenAI format
4. **Action Control:** Users can disable specific actions within tools for fine-grained control
5. **User Isolation:** Users can only access their own tools and data

---

## 🚀 Integration Guide

### For Vercel AI SDK
```javascript
// Get user's active tools with enabled actions
const response = await fetch(`/tools/openai/users/${userId}/openai-tools`);
const tools = await response.json();

// Use tools in Vercel AI SDK (only enabled actions will be available)
const { generateText } = await openai.chat.completions.create({
  model: "gpt-4",
  messages: [{ role: "user", content: "List my repositories" }],
  tools: tools
});
```

### For Custom Integrations
```javascript
// List available tools
const tools = await fetch('/tools/').then(r => r.json());

// Authenticate user with a tool
const authUrl = await fetch(`/auth/url/github?user_id=${userId}`)
  .then(r => r.json());

// Redirect user to authUrl.auth_url
window.location.href = authUrl.auth_url;

// After authentication, check all tools with user status
const userTools = await fetch(`/auth/tools?user_id=${userId}&detail=true`)
  .then(r => r.json());

// Manage action permissions
await fetch(`/auth/users/${userId}/tools/github/actions/create_repository/status`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ is_disabled: true })
});

// Execute tool actions (only enabled actions will work)
const result = await fetch(`/tools/github/execute?user_id=${userId}`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    action: 'list_repositories',
    parameters: { per_page: 10 }
  })
});
```

---

## 🎯 Action Management Features

### Granular Control
- **Tool Level:** Enable/disable entire tools
- **Action Level:** Enable/disable specific actions within tools
- **User Specific:** Each user has their own action preferences

### Use Cases
- **Security:** Disable potentially dangerous actions like "delete_repository"
- **Workflow Control:** Only enable actions needed for specific tasks
- **Permission Management:** Fine-tune what AI can do with user's tools
- **Testing:** Disable actions in development/testing environments

### Best Practices
1. **Start Restrictive:** Disable potentially harmful actions by default
2. **User Education:** Inform users about action capabilities before enabling
3. **Audit Trail:** Monitor which actions are being enabled/disabled
4. **Gradual Rollout:** Enable new actions gradually based on user feedback

---

## 📊 Tool Status Understanding

### Tool States
- **Not Authenticated:** User hasn't connected the tool yet
- **Authenticated but Inactive:** User connected but disabled the tool
- **Authenticated and Active:** Tool is ready to use

### Action States
- **Active:** Action can be executed
- **Inactive:** Action is disabled (either tool is inactive or action is specifically disabled)

### Health Status
- **True:** Tool is functioning properly (currently always true)
- **False:** Tool has health issues (to be implemented) 