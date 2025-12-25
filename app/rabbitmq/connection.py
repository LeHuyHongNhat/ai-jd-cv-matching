"""
RabbitMQ Connection Manager

Quản lý kết nối đến RabbitMQ CloudAMQP với TLS support
"""

import pika
import ssl
import logging
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQConnection:
    """Quản lý kết nối RabbitMQ với CloudAMQP"""
    
    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        
    def connect(self) -> pika.channel.Channel:
        """
        Tạo kết nối đến RabbitMQ CloudAMQP
        
        Returns:
            pika.channel.Channel: Channel để giao tiếp với RabbitMQ
        """
        try:
            # Cấu hình credentials
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD
            )
            
            # Cấu hình connection parameters
            if settings.RABBITMQ_USE_TLS:
                # Sử dụng TLS/SSL
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                
                parameters = pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_TLS_PORT,
                    virtual_host=settings.RABBITMQ_VHOST,
                    credentials=credentials,
                    ssl_options=pika.SSLOptions(ssl_context),
                    heartbeat=settings.RABBITMQ_HEARTBEAT,
                    blocked_connection_timeout=settings.RABBITMQ_BLOCKED_CONNECTION_TIMEOUT
                )
            else:
                # Không sử dụng TLS
                parameters = pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                    virtual_host=settings.RABBITMQ_VHOST,
                    credentials=credentials,
                    heartbeat=settings.RABBITMQ_HEARTBEAT,
                    blocked_connection_timeout=settings.RABBITMQ_BLOCKED_CONNECTION_TIMEOUT
                )
            
            # Tạo connection
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queues
            self._declare_queues()
            
            # Set QoS (Quality of Service) - prefetch count
            self.channel.basic_qos(prefetch_count=settings.RABBITMQ_PREFETCH_COUNT)
            
            logger.info(f"Đã kết nối thành công đến RabbitMQ tại {settings.RABBITMQ_HOST}")
            return self.channel
            
        except Exception as e:
            logger.error(f"Lỗi kết nối RabbitMQ: {str(e)}")
            raise
    
    def _declare_queues(self):
        """Bind queues với exchange (Spring Boot đã tạo queues và exchange rồi)"""
        if not self.channel:
            raise RuntimeError("Channel chưa được khởi tạo")
        
        # NOTE: Spring Boot đã tạo exchange và queues
        # Python worker CHỈ bind queues với exchange, KHÔNG tạo mới
        logger.info(f"Sử dụng exchange: {settings.RABBITMQ_EXCHANGE}")
        
        # Bind Input Queue với Exchange (queue đã được Spring Boot tạo)
        try:
            self.channel.queue_bind(
                queue=settings.RABBITMQ_INPUT_QUEUE,
                exchange=settings.RABBITMQ_EXCHANGE,
                routing_key=settings.RABBITMQ_INPUT_ROUTING_KEY
            )
            logger.info(f"Đã bind Input Queue: {settings.RABBITMQ_INPUT_QUEUE} -> {settings.RABBITMQ_INPUT_ROUTING_KEY}")
        except Exception as e:
            logger.warning(f"Không thể bind Input Queue (có thể đã bind rồi): {str(e)}")
        
        # Bind Output Queue với Exchange (queue đã được Spring Boot tạo)
        try:
            self.channel.queue_bind(
                queue=settings.RABBITMQ_OUTPUT_QUEUE,
                exchange=settings.RABBITMQ_EXCHANGE,
                routing_key=settings.RABBITMQ_OUTPUT_ROUTING_KEY
            )
            logger.info(f"Đã bind Output Queue: {settings.RABBITMQ_OUTPUT_QUEUE} -> {settings.RABBITMQ_OUTPUT_ROUTING_KEY}")
        except Exception as e:
            logger.warning(f"Không thể bind Output Queue (có thể đã bind rồi): {str(e)}")
        
        logger.info("Sẵn sàng lắng nghe messages từ Spring Boot")
    
    def close(self):
        """Đóng kết nối RabbitMQ"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("Đã đóng kết nối RabbitMQ")
        except Exception as e:
            logger.error(f"Lỗi khi đóng kết nối: {str(e)}")
    
    def is_connected(self) -> bool:
        """Kiểm tra trạng thái kết nối"""
        return self.connection is not None and self.connection.is_open
    
    def reconnect(self):
        """Thử kết nối lại"""
        logger.info("Đang thử kết nối lại RabbitMQ...")
        self.close()
        return self.connect()
