"""
RabbitMQ Consumer

Nhận và xử lý messages từ Spring Boot qua RabbitMQ
Thực hiện error handling theo quy trình:
- Thành công: Gửi kết quả -> ACK
- Lỗi dữ liệu (JSON sai): Log lỗi -> ACK (bỏ qua tin nhắn lỗi)
- Lỗi hệ thống (Mất mạng, bug): NACK -> Tin nhắn được re-queue
"""

import json
import logging
import pika
from typing import Callable
from core.config import settings
from .connection import RabbitMQConnection
from .producer import RabbitMQProducer
from .message_handlers import MessageHandlers

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """Consumer nhận messages từ Spring Boot"""
    
    def __init__(self):
        self.connection_manager = RabbitMQConnection()
        self.producer = RabbitMQProducer()
        self.message_handlers = MessageHandlers()
        self.channel = None
        self.is_consuming = False
    
    def start_consuming(self):
        """Bắt đầu consume messages từ queue"""
        try:
            # Connect to RabbitMQ
            logger.info("Starting RabbitMQ Consumer...")
            self.channel = self.connection_manager.connect()
            self.producer.connect()
            
            # Set up consumer
            self.channel.basic_consume(
                queue=settings.RABBITMQ_INPUT_QUEUE,
                on_message_callback=self._on_message_callback,
                auto_ack=False  # Manual ACK
            )
            
            self.is_consuming = True
            logger.info(f"Consumer đang lắng nghe queue: {settings.RABBITMQ_INPUT_QUEUE}")
            logger.info("Đang chờ messages từ Spring Boot... (Ctrl+C để dừng)")
            
            # Start consuming
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("\nĐã nhận tín hiệu dừng...")
            self.stop_consuming()
        except Exception as e:
            logger.error(f"Lỗi khi consume messages: {str(e)}", exc_info=True)
            raise
    
    def _on_message_callback(self, ch, method, properties, body):
        """
        Callback xử lý message
        
        Args:
            ch: Channel
            method: Method info
            properties: Message properties
            body: Message body
        """
        application_id = None
        
        try:
            # Parse JSON để lấy applicationId
            try:
                temp_data = json.loads(body.decode('utf-8'))
                application_id = temp_data.get("applicationId", properties.correlation_id or "unknown")
            except:
                application_id = properties.correlation_id or "unknown"
            
            logger.info(f"\nNhận message mới (applicationId: {application_id})")
            
            # Parse JSON message
            try:
                message_data = json.loads(body.decode('utf-8'))
                logger.info(f"fileUrl: {message_data.get('fileUrl')}, jobTitle: {message_data.get('jobTitle')}")
            except json.JSONDecodeError as e:
                # LỖI DỮ LIỆU (JSON sai) -> ACK để bỏ qua
                logger.error(f"JSON decode error: {str(e)}")
                error_msg = f"Invalid JSON format: {str(e)}"
                
                # Gửi error response
                self.producer.send_error_response(
                    request_id=str(application_id),
                    error_message=error_msg,
                    error_type="DATA_ERROR"
                )
                
                # ACK để bỏ qua message lỗi
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info("ACK - Message JSON lỗi đã được bỏ qua")
                return
            
            # Xử lý message
            try:
                success, response_data, error_type = self.message_handlers.handle_message(message_data)
                
                if success:
                    # THÀNH CÔNG -> Gửi kết quả -> ACK
                    self.producer.send_success_response(
                        request_id=str(application_id),
                        data=response_data
                    )
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info("ACK - Message đã được xử lý thành công")
                    
                else:
                    # CÓ LỖI
                    error_message = response_data.get("error", "Unknown error")
                    
                    if error_type == "DATA_ERROR":
                        # LỖI DỮ LIỆU -> Gửi error response -> ACK
                        self.producer.send_error_response(
                            request_id=str(application_id),
                            error_message=error_message,
                            error_type="DATA_ERROR"
                        )
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        logger.warning(f"ACK - Data error: {error_message}")
                        
                    else:
                        # LỖI HỆ THỐNG -> NACK (re-queue)
                        logger.error(f"System error: {error_message}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                        logger.warning("NACK - Message sẽ được re-queue")
                        
            except Exception as e:
                # LỖI HỆ THỐNG (Code bug, mất mạng) -> NACK
                logger.error(f"System error trong xử lý: {str(e)}", exc_info=True)
                
                try:
                    # Thử gửi error response (nếu có thể)
                    self.producer.send_error_response(
                        request_id=str(application_id),
                        error_message=f"System error: {str(e)}",
                        error_type="SYSTEM_ERROR"
                    )
                except:
                    logger.error("Không thể gửi error response")
                
                # NACK để re-queue message
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                logger.warning("NACK - Message sẽ được re-queue do lỗi hệ thống")
                
        except Exception as e:
            # Lỗi nghiêm trọng trong callback
            logger.error(f"Critical error trong message callback: {str(e)}", exc_info=True)
            
            # NACK message
            try:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                logger.warning("NACK - Message sẽ được re-queue do lỗi nghiêm trọng")
            except:
                logger.error("Không thể NACK message")
    
    def stop_consuming(self):
        """Dừng consume messages"""
        try:
            if self.is_consuming and self.channel:
                logger.info("Đang dừng consumer...")
                self.channel.stop_consuming()
                self.is_consuming = False
            
            # Close connections
            self.connection_manager.close()
            self.producer.close()
            
            logger.info("Consumer đã dừng hoàn toàn")
            
        except Exception as e:
            logger.error(f"Lỗi khi dừng consumer: {str(e)}")
    
    def is_running(self) -> bool:
        """Kiểm tra consumer có đang chạy không"""
        return self.is_consuming and self.connection_manager.is_connected()
