from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    APP_NAME: str = "CloudGuard"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    API_V1_STR: str = "/api/v1"
    
    # AWS Config
    AWS_DEFAULT_REGION: str = "ap-south-1"
    AWS_ROLE_SESSION_NAME: str = "cloudguard-security-scan"
    CLOUDGUARD_EXTERNAL_ID: str | None = None
    
    # CORS
    CORS_ORIGINS: List[str] | str = []
    
    # AI Copilot Config
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "openai" # "openai" or "mock"
    AI_API_KEY: str | None = None
    AI_MODEL: str = "gpt-4o-mini"
    AI_BASE_URL: str | None = None
    
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
        
    DATABASE_URL: str = "postgresql+psycopg2://cloudguard:password@localhost:5432/cloudguard"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

settings = Settings()
