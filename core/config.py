from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Cấu hình ứng dụng sử dụng Pydantic Settings để tải từ .env"""
    OPENAI_API_KEY: str
    
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = "chameleon.lmq.cloudamqp.com"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_TLS_PORT: int = 5671
    RABBITMQ_USE_TLS: bool = True
    RABBITMQ_USER: str = "abkqvbjm"
    RABBITMQ_PASSWORD: str = "4vwaChdSYTuiz6cPNzyy2FPZ041TVpOX"
    RABBITMQ_VHOST: str = "abkqvbjm"
    
    # RabbitMQ Exchange & Queue Configuration
    RABBITMQ_EXCHANGE: str = "internal_exchange"
    RABBITMQ_EXCHANGE_TYPE: str = "direct"
    
    # Input Queue Configuration (Python nhận từ Spring Boot)
    RABBITMQ_INPUT_QUEUE: str = "cv_processing_queue"
    RABBITMQ_INPUT_ROUTING_KEY: str = "cv_upload_key"
    
    # Output Queue Configuration (Python gửi kết quả về)
    RABBITMQ_OUTPUT_QUEUE: str = "cv_result_queue"
    RABBITMQ_OUTPUT_ROUTING_KEY: str = "cv_result_key"
    
    # Dead Letter Queue
    RABBITMQ_DLQ: str = "cv_processing_dlq"
    
    # RabbitMQ Connection Settings
    RABBITMQ_HEARTBEAT: int = 600
    RABBITMQ_BLOCKED_CONNECTION_TIMEOUT: int = 300
    RABBITMQ_PREFETCH_COUNT: int = 1  # Process 1 message at a time
    
    model_config = ConfigDict(
        env_file="config.env",
        env_file_encoding="utf-8"
    )


# Khởi tạo settings instance
settings = Settings()

