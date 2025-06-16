"""
Load-based configuration for different user scenarios
"""
import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class LoadConfig:
    """Configuration for different load scenarios"""
    
    # Basic configuration
    max_concurrent_executions: int
    request_timeout: float
    max_queue_size: int
    
    # Rate limiting per user
    user_requests_per_minute: int
    user_burst_limit: int
    
    # System monitoring thresholds
    cpu_threshold: float  # 0.0 - 1.0
    memory_threshold: float  # 0.0 - 1.0

# Predefined configurations for different scales
LOAD_CONFIGS: Dict[str, LoadConfig] = {
    "small": LoadConfig(
        max_concurrent_executions=10,
        request_timeout=30.0,
        max_queue_size=50,
        user_requests_per_minute=10,
        user_burst_limit=5,
        cpu_threshold=0.7,
        memory_threshold=0.8
    ),
    
    "medium": LoadConfig(
        max_concurrent_executions=50,
        request_timeout=30.0,
        max_queue_size=200,
        user_requests_per_minute=20,
        user_burst_limit=10,
        cpu_threshold=0.8,
        memory_threshold=0.85
    ),
    
    "large": LoadConfig(
        max_concurrent_executions=100,
        request_timeout=45.0,
        max_queue_size=500,
        user_requests_per_minute=30,
        user_burst_limit=15,
        cpu_threshold=0.85,
        memory_threshold=0.9
    ),
    
    "enterprise": LoadConfig(
        max_concurrent_executions=200,
        request_timeout=60.0,
        max_queue_size=1000,
        user_requests_per_minute=50,
        user_burst_limit=25,
        cpu_threshold=0.9,
        memory_threshold=0.95
    ),
    
    # Custom configuration for Azure E8ds v5 (8 vCPU, 64GB RAM)
    "azure_e8ds_v5": LoadConfig(
        max_concurrent_executions=25,  # Optimal for 8 vCPUs
        request_timeout=35.0,
        max_queue_size=300,  # 500 active users buffer
        user_requests_per_minute=25,
        user_burst_limit=12,
        cpu_threshold=0.75,  # Conservative for stability
        memory_threshold=0.8   # RAM is abundant, focus on CPU
    ),
    
    # Aggressive configuration for peak loads
    "azure_e8ds_v5_peak": LoadConfig(
        max_concurrent_executions=35,  # Push the limits
        request_timeout=40.0,
        max_queue_size=500,
        user_requests_per_minute=35,
        user_burst_limit=18,
        cpu_threshold=0.85,
        memory_threshold=0.85
    )
}

def get_load_config() -> LoadConfig:
    """Get load configuration based on environment"""
    config_name = os.getenv("LOAD_CONFIG", "medium")  # Default to medium
    
    if config_name in LOAD_CONFIGS:
        return LOAD_CONFIGS[config_name]
    else:
        # Custom configuration from environment variables
        return LoadConfig(
            max_concurrent_executions=int(os.getenv("MAX_CONCURRENT_EXECUTIONS", "50")),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", "30.0")),
            max_queue_size=int(os.getenv("MAX_QUEUE_SIZE", "200")),
            user_requests_per_minute=int(os.getenv("USER_REQUESTS_PER_MINUTE", "20")),
            user_burst_limit=int(os.getenv("USER_BURST_LIMIT", "10")),
            cpu_threshold=float(os.getenv("CPU_THRESHOLD", "0.8")),
            memory_threshold=float(os.getenv("MEMORY_THRESHOLD", "0.85"))
        )

# Usage examples for different scenarios :

# 10,000 users, 500 active → Use "large" or "enterprise"
# 1,000 users, 50 active → Use "medium" 
# 100 users, 10 active → Use "small" 