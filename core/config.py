from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Cấu hình ứng dụng sử dụng Pydantic Settings để tải từ .env"""
    OPENAI_API_KEY: str
    
    model_config = ConfigDict(
        env_file="config.env",
        env_file_encoding="utf-8"
    )


# Khởi tạo settings instance
settings = Settings()

