"""Application settings for ASO Agent Service."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
from typing import Optional, Literal
from enum import Enum


class DatabaseType(str, Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MONGO = "mongo"


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Service configuration
    HOST: str = Field(default="0.0.0.0", description="Service host")
    PORT: int = Field(default=8080, description="Service port")
    AUTH_SECRET: Optional[SecretStr] = Field(default=None, description="API authentication secret")
    
    # Database configuration
    DATABASE_TYPE: DatabaseType = Field(default=DatabaseType.SQLITE, description="Database type")
    SQLITE_DB_PATH: str = Field(default="data/aso_agent.db", description="SQLite database path")
    
    # LLM configuration
    OPENAI_API_KEY: Optional[SecretStr] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[SecretStr] = Field(default=None, description="Anthropic API key")
    DEFAULT_MODEL: str = Field(default="gpt-4o-mini", description="Default LLM model")
    
    # ASO-specific configuration
    SENSOR_TOWER_API_KEY: Optional[SecretStr] = Field(default=None, description="Sensor Tower API key")
    ASO_MOBILE_API_KEY: Optional[SecretStr] = Field(default=None, description="ASO Mobile API key")
    ASO_EMAIL: Optional[str] = Field(default=None, description="ASO Mobile email")
    ASO_PASSWORD: Optional[SecretStr] = Field(default=None, description="ASO Mobile password")
    ASO_APP_NAME: Optional[str] = Field(default=None, description="Default ASO app name")
    BROWSER_CAT_API_KEY: Optional[SecretStr] = Field(default=None, description="BrowserCat API key")
    
    # Analysis defaults
    DEFAULT_MARKET_THRESHOLD: int = Field(default=50000, description="Default market size threshold")
    DEFAULT_KEYWORDS_PER_IDEA: int = Field(default=20, description="Default keywords per app idea")
    DEFAULT_MAX_APPS: int = Field(default=20, description="Default max apps per keyword")
    
    # Monitoring
    LANGCHAIN_TRACING_V2: bool = Field(default=False, description="Enable LangSmith tracing")
    LANGCHAIN_API_KEY: Optional[SecretStr] = Field(default=None, description="LangSmith API key")
    LANGCHAIN_PROJECT: str = Field(default="aso-agent-service", description="LangSmith project name")
    
    @property
    def available_models(self) -> list[str]:
        """Get list of available LLM models based on API keys."""
        models = []
        if self.OPENAI_API_KEY:
            models.extend(["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
        if self.ANTHROPIC_API_KEY:
            models.extend(["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"])
        return models or ["gpt-4o-mini"]  # Fallback


# Global settings instance
settings = Settings()