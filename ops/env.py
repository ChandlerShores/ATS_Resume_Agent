"""Environment variable validation using Pydantic Settings.

This module ensures all required environment variables are present and valid
before the application starts. This prevents runtime errors and improves security.
"""

import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings validated from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # === Core Settings ===
    node_env: str = Field(default="development", description="Environment: development, production, test")
    
    # === API Configuration ===
    host: str = Field(default="127.0.0.1", description="API host binding (use 0.0.0.0 for Docker)")
    port: int = Field(default=8000, ge=1024, le=65535, description="API port")
    api_title: str = Field(default="ATS Resume Bullet Revisor API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    
    # === CORS Configuration ===
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # === LLM API Keys (at least one required) ===
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    
    # === LLM Configuration ===
    default_llm_provider: str = Field(default="openai", description="Default LLM provider: openai or anthropic")
    default_model: str = Field(default="gpt-4o-mini", description="Default model name")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="LLM temperature")
    llm_max_tokens: int = Field(default=2000, ge=1, le=100000, description="Max tokens per LLM request")
    llm_timeout: int = Field(default=60, ge=1, le=300, description="LLM request timeout (seconds)")
    
    # === Rate Limiting ===
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=10, ge=1, description="Requests per minute")
    
    # === Redis (Optional) ===
    redis_enabled: bool = Field(default=False, description="Enable Redis for caching/rate limiting")
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_password: Optional[str] = Field(None, description="Redis password")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    
    # === Job Board Scraping ===
    scraping_enabled: bool = Field(default=True, description="Enable job board scraping")
    scraping_timeout: int = Field(default=10, ge=1, le=60, description="Scraping timeout (seconds)")
    scraping_user_agent: str = Field(
        default="Mozilla/5.0 (compatible; ATS-Resume-Agent/1.0)",
        description="User agent for web scraping"
    )
    
    # === Storage ===
    cache_dir: str = Field(default="./out/cache", description="Cache directory path")
    job_cache_dir: str = Field(default="./out/job_cache", description="Job cache directory path")
    output_dir: str = Field(default="./out", description="Output directory path")
    
    # === Logging ===
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARN, ERROR")
    log_format: str = Field(default="json", description="Log format: json or text")
    
    # === Security ===
    enable_cors: bool = Field(default=True, description="Enable CORS middleware")
    enable_security_headers: bool = Field(default=True, description="Enable security headers")
    allowed_file_types: str = Field(
        default=".pdf,.docx,.txt",
        description="Comma-separated allowed file extensions for uploads"
    )
    max_upload_size_mb: int = Field(default=10, ge=1, le=100, description="Max upload size in MB")
    
    @field_validator("node_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        """Validate environment."""
        allowed = {"development", "production", "test"}
        if v.lower() not in allowed:
            raise ValueError(f"node_env must be one of {allowed}")
        return v.lower()
    
    @field_validator("default_llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider."""
        allowed = {"openai", "anthropic"}
        if v.lower() not in allowed:
            raise ValueError(f"default_llm_provider must be one of {allowed}")
        return v.lower()
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v.upper()
    
    def get_allowed_origins_list(self) -> list[str]:
        """Parse allowed origins from comma-separated string."""
        if not self.allowed_origins:
            return []
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    def get_llm_api_key(self, provider: Optional[str] = None) -> str:
        """Get API key for specified provider or default."""
        provider = provider or self.default_llm_provider
        
        if provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            return self.openai_api_key
        elif provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            return self.anthropic_api_key
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.node_env == "production"
    
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.node_env == "development"


# Global settings instance (singleton)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience: Load settings at module import for validation
try:
    settings = get_settings()
except Exception as e:
    print(f"❌ Environment validation failed: {e}")
    print("Please check your .env file and ensure all required variables are set.")
    raise

