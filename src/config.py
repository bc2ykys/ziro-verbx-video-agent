from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # VerbX
    verbx_api_key: str = Field(default="", alias="VERBX_API_KEY")
    verbx_base_url: str = Field(default="https://api.verbxeco.com/v1", alias="VERBX_BASE_URL")

    # External vision (optional)
    external_vision_api_key: Optional[str] = Field(default=None, alias="EXTERNAL_VISION_API_KEY")
    external_vision_endpoint: Optional[str] = Field(default=None, alias="EXTERNAL_VISION_ENDPOINT")

    # Database
    database_url: str = Field(default="sqlite:///./agent.db", alias="DATABASE_URL")

    # Server
    port: int = Field(default=8501, alias="PORT")
    host: str = Field(default="0.0.0.0", alias="HOST")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()