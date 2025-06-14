# 🚀 ModuleX

**The Ultimate MCP Server Management & Tool Authentication Platform**

ModuleX is a powerful, production-ready platform for managing Model Context Protocol (MCP) servers and handling OAuth authentication for various tools and services. Built with modern Python and FastAPI, it provides a unified interface for integrating and executing tools securely across different platforms.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com/)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-suysoftware%2Fmodulex-blue.svg)](https://hub.docker.com/r/suysoftware/modulex)

## ✨ Features

### 🔐 **Robust Authentication**
- **OAuth 2.0 Support**: Seamless integration with GitHub, and other OAuth providers
- **API Key Management**: Support for API key-based authentication
- **User Session Management**: Secure token storage and validation
- **Multi-Provider Support**: Easily extensible to new authentication providers

### 🛠️ **Tool Integration**
- **GitHub Integration**: Repository management, user info, and more
- **R2R (RAG to Riches)**: Production-ready retrieval-augmented generation system
- **Plugin Architecture**: Easy addition of new tools and services
- **Standardized API**: Consistent interface across all integrated tools

### 🏗️ **Enterprise-Ready Architecture**
- **FastAPI Backend**: High-performance async Python framework
- **PostgreSQL Database**: Reliable data persistence with async support
- **Redis Caching**: Fast session and data caching
- **Docker Compose**: Complete containerized deployment
- **Monitoring Stack**: Prometheus + Grafana for metrics and dashboards

### 🔌 **MCP Compatibility**
- **OpenAI Integration**: Compatible with Vercel AI SDK
- **Standardized Tool Format**: Following MCP specifications
- **Real-time Execution**: Fast tool execution with proper error handling
- **Extensible Framework**: Easy to add new MCP-compatible tools

## 🚀 Quick Start

### 🐳 Docker Hub (One-Click Deployment)

**The fastest way to get ModuleX running!**

1. **Pull and run the latest image**
```bash
docker run -d \
  --name modulex \
  -p 8000:8000 \
  -e DATABASE_URL="sqlite:///app/data/modulex.db" \
  -e REDIS_URL="redis://redis:6379" \
  -v modulex_data:/app/data \
  suysoftware/modulex:latest
```

2. **Or with docker-compose (recommended)**
```yaml
version: '3.8'
services:
  modulex:
    image: suysoftware/modulex:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/modulex
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: modulex
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

3. **Access your ModuleX instance**
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health/

### 🏷️ Available Docker Tags

- `suysoftware/modulex:latest` - Latest stable release
- `suysoftware/modulex:dev` - Development version
- `suysoftware/modulex:v0.1.0` - Specific version tags

### Prerequisites
- Docker
- PostgreSQL (optional, can use SQLite)
- Redis (optional, for caching)

### 🐳 Docker Deployment (Full Stack)

1. **Clone the repository**
```bash
git clone https://github.com/suysoftware/modulex.git
cd modulex
```

2. **Configure environment variables**
```bash
cp docker/env/modulex.env.example docker/env/modulex.env
# Edit the configuration file with your settings
```

3. **Start the complete stack**
```bash
cd docker
docker-compose up -d
```

4. **Access the services**
- **API Documentation**: http://localhost:8000/docs
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Prometheus Metrics**: http://localhost:9090
- **pgAdmin**: http://localhost:5050 (admin@admin.com/admin)

### 🐍 Local Development

1. **Install dependencies**
```bash
cd py
pip install -e .[dev]
```

2. **Set up environment variables**
```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/modulex"
export REDIS_URL="redis://localhost:6379"
```

3. **Run the application**
```bash
python -m app.main
```

## 📚 API Usage

### Authentication Flow

1. **Get OAuth URL**
```bash
curl "http://localhost:8000/auth/url/github?user_id=your_user_id"
```

2. **Handle Callback** (automatic)
The OAuth provider will redirect to `/auth/callback/github` with the authorization code.

3. **List Authenticated Tools**
```bash
curl "http://localhost:8000/auth/tools?user_id=your_user_id"
```

### Tool Execution

1. **List Available Tools**
```bash
curl "http://localhost:8000/tools/"
```

2. **Get Tool Information**
```bash
curl "http://localhost:8000/tools/github"
```

3. **Execute Tool Action**
```bash
curl -X POST "http://localhost:8000/tools/github/execute?user_id=your_user_id" \
  -H "Content-Type: application/json" \
  -d '{"per_page": 10, "action": "list_repositories"}'
```

### OpenAI/Vercel AI SDK Integration

1. **Get OpenAI-Compatible Tools**
```bash
curl "http://localhost:8000/tools/openai/users/your_user_id/openai-tools"
```

2. **Execute Tool (OpenAI Format)**
```bash
curl -X POST "http://localhost:8000/tools/github/execute?user_id=your_user_id" \
  -H "Content-Type: application/json" \
  -d '{"per_page": 10, "action": "list_repositories"}'
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `DEBUG` | Enable debug mode | `false` |
| `ALLOWED_HOSTS` | CORS allowed hosts | `*` |
| `SECRET_KEY` | JWT secret key | Auto-generated |

### Adding New Tools

1. **Create tool directory**
```bash
mkdir integrations/your_tool
```

2. **Create info.json**
```json
{
  "name": "your_tool",
  "display_name": "Your Tool",
  "description": "Tool description",
  "version": "1.0.0",
  "requires_auth": true,
  "auth_type": "oauth2",
  "actions": [
    {
      "name": "action_name",
      "description": "Action description",
      "parameters": {
        "param1": {
          "type": "string",
          "description": "Parameter description",
          "required": true
        }
      }
    }
  ]
}
```

3. **Implement the tool logic**
```python
# integrations/your_tool/main.py
async def execute_action(action: str, params: dict, auth_data: dict):
    # Your implementation here
    pass
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│   PostgreSQL    │────│      Redis      │
│   (Port 8000)   │    │   (Port 5432)   │    │   (Port 6379)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ├── Auth Service (OAuth 2.0)
         ├── Tool Service (Execution)
         └── Integration Layer
              ├── GitHub
              ├── R2R
              └── Custom Tools...

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │────│     Grafana     │────│     pgAdmin     │
│   (Port 9090)   │    │   (Port 3000)   │    │   (Port 5050)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Development

### Running Tests
```bash
cd py
pytest tests/
```

### Code Quality
```bash
# Format code
black app/

# Lint code
ruff check app/

# Type checking
mypy app/
```

### Adding Dependencies
```bash
# Add to pyproject.toml, then:
pip install -e .[dev]
```

## 📊 Monitoring

ModuleX includes a complete monitoring stack:

- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and visualization
- **PostgreSQL Exporter**: Database metrics
- **Application Metrics**: Custom FastAPI metrics

Access Grafana at http://localhost:3000 with `admin/admin` to view:
- API request metrics
- Database performance
- Authentication success rates
- Tool execution statistics

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 **Documentation**: [modulex.readthedocs.io](https://modulex.readthedocs.io/)
- 🐛 **Issues**: [GitHub Issues](https://github.com/suysoftware/modulex/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/suysoftware/modulex/discussions)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the amazing framework
- [Model Context Protocol](https://github.com/modelcontextprotocol) for the standards
- [R2R](https://r2r-docs.sciphi.ai/) for the RAG system integration
- All our contributors and the open-source community

---

**Made with ❤️ by the ModuleX Team**
