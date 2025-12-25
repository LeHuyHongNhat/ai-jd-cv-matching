"""
RabbitMQ Worker - Main Entry Point

Worker nhận và xử lý messages từ Spring Boot qua RabbitMQ CloudAMQP

Usage:
    python rabbitmq_worker.py

Environment Variables (đặt trong config.env):
    OPENAI_API_KEY: API key của OpenAI
    RABBITMQ_HOST: Host RabbitMQ (default: chameleon.lmq.cloudamqp.com)
    RABBITMQ_USER: Username RabbitMQ (default: abkqvbjm)
    RABBITMQ_PASSWORD: Password RabbitMQ
    RABBITMQ_VHOST: Virtual host (default: abkqvbjm)
"""

import sys
import logging
import signal
from app.rabbitmq.consumer import RabbitMQConsumer

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('rabbitmq_worker.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Global consumer instance
consumer = None


def signal_handler(sig, frame):
    """Handler cho Ctrl+C"""
    logger.info("\nĐã nhận tín hiệu dừng (Ctrl+C)")
    if consumer:
        consumer.stop_consuming()
    sys.exit(0)


def main():
    """Main function"""
    global consumer
    
    try:
        logger.info("="*80)
        logger.info("RabbitMQ Worker - CV-JD Matching Service")
        logger.info("="*80)
        
        # Đăng ký signal handler cho Ctrl+C
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Khởi tạo consumer
        consumer = RabbitMQConsumer()
        
        # Bắt đầu consuming
        consumer.start_consuming()
        
    except KeyboardInterrupt:
        logger.info("\nWorker đã dừng bởi người dùng")
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if consumer:
            consumer.stop_consuming()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
