# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml for dependencies
COPY pyproject.toml .
COPY user_requirements.txt .

# Install Python dependencies from pyproject.toml
RUN pip install --no-cache-dir .

# Install user requirements if file has content (not just comments/empty lines)
RUN if [ -s user_requirements.txt ] && [ "$(grep -v '^#' user_requirements.txt | grep -v '^$' | wc -l)" -gt 0 ]; then \
        echo "Installing user requirements..." && \
        pip install --no-cache-dir -r user_requirements.txt; \
    else \
        echo "No user requirements to install."; \
    fi

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' --shell /bin/bash user && \
    chown -R user:user /app
USER user

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 