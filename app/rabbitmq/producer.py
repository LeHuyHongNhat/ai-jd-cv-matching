"""
RabbitMQ Producer

Gửi kết quả xử lý từ FastAPI service về Spring Boot qua RabbitMQ
"""

import json
import logging
import pika
from typing import Dict, Any
from core.config import settings
from .connection import RabbitMQConnection

logger = logging.getLogger(__name__)


class RabbitMQProducer:
    """Producer để gửi kết quả về Spring Boot"""
    
    def __init__(self):
        self.connection_manager = RabbitMQConnection()
        self.channel = None
    
    def connect(self):
        """Kết nối đến RabbitMQ"""
        self.channel = self.connection_manager.connect()
    
    def send_response(self, request_id: str, response_data: Dict[str, Any], 
                     success: bool = True, error_message: str = None):
        """
        Gửi response về Spring Boot qua cv_result_queue
        
        Args:
            request_id: Request ID từ Spring Boot
            response_data: Dữ liệu response (dict)
            success: Trạng thái xử lý (True/False)
            error_message: Message lỗi nếu có
        """
        try:
            if not self.channel or not self.connection_manager.is_connected():
                logger.warning("Kết nối bị mất, đang kết nối lại...")
                self.connect()
            
            # Tạo response message theo format của Spring Boot
            import datetime
            message = {
                "applicationId": request_id,  # request_id chứa applicationId
                "success": success,
                "data": response_data if success else None,
                "error": error_message if not success else None,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
            
            # Convert to JSON
            message_body = json.dumps(message, ensure_ascii=False)
            
            # Publish message với properties
            properties = pika.BasicProperties(
                content_type='application/json',
                delivery_mode=2,  # Persistent message
                correlation_id=request_id
            )
            
            self.channel.basic_publish(
                exchange=settings.RABBITMQ_EXCHANGE,
                routing_key=settings.RABBITMQ_OUTPUT_ROUTING_KEY,
                body=message_body,
                properties=properties
            )
            
            logger.info(f"Đã gửi response cho applicationId: {request_id}, success: {success}")
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi response: {str(e)}")
            # Thử reconnect và gửi lại
            try:
                self.connect()
                self.channel.basic_publish(
                    exchange='',
                    routing_key=settings.RABBITMQ_RESPONSE_QUEUE,
                    body=message_body,
                    properties=properties
                )
                logger.info(f"Đã gửi lại response sau khi reconnect")
            except Exception as retry_error:
                logger.error(f"Không thể gửi response sau khi retry: {str(retry_error)}")
                raise
    
    def send_success_response(self, request_id: str, data: Dict[str, Any]):
        """
        Gửi response thành công
        
        Args:
            request_id: Application ID từ Spring Boot
            data: Dữ liệu kết quả
        """
        self.send_response(request_id, data, success=True)
    
    def send_error_response(self, request_id: str, error_message: str, 
                           error_type: str = "SYSTEM_ERROR"):
        """
        Gửi response lỗi
        
        Args:
            request_id: Application ID từ Spring Boot
            error_message: Message lỗi
            error_type: Loại lỗi (DATA_ERROR, SYSTEM_ERROR)
        """
        error_data = {
            "error_type": error_type,
            "error_message": error_message
        }
        self.send_response(request_id, error_data, success=False, error_message=error_message)
    
    def send_direct_response(self, response_data: Dict[str, Any]):
        """
        Gửi response đã được format sẵn từ message_handlers
        (response_data đã có đầy đủ structure: applicationId, isSuccess, version, timestamp, error, data)
        
        Args:
            response_data: Dữ liệu response đã được format đầy đủ
        """
        try:
            if not self.channel or not self.connection_manager.is_connected():
                logger.warning("Kết nối bị mất, đang kết nối lại...")
                self.connect()
            
            # Convert to JSON
            message_body = json.dumps(response_data, ensure_ascii=False)
            
            # Publish message với properties
            request_id = str(response_data.get("applicationId", "unknown"))
            properties = pika.BasicProperties(
                content_type='application/json',
                delivery_mode=2,  # Persistent message
                correlation_id=request_id
            )
            
            self.channel.basic_publish(
                exchange=settings.RABBITMQ_EXCHANGE,
                routing_key=settings.RABBITMQ_OUTPUT_ROUTING_KEY,
                body=message_body,
                properties=properties
            )
            
            is_success = response_data.get("isSuccess", False)
            logger.info(f"Đã gửi response cho applicationId: {request_id}, isSuccess: {is_success}")
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi direct response: {str(e)}")
            # Thử reconnect và gửi lại
            try:
                self.connect()
                self.channel.basic_publish(
                    exchange=settings.RABBITMQ_EXCHANGE,
                    routing_key=settings.RABBITMQ_OUTPUT_ROUTING_KEY,
                    body=message_body,
                    properties=properties
                )
                logger.info(f"Đã gửi lại response sau khi reconnect")
            except Exception as retry_error:
                logger.error(f"Không thể gửi response sau khi retry: {str(retry_error)}")
                raise
    
    def close(self):
        """Đóng kết nối"""
        self.connection_manager.close()
