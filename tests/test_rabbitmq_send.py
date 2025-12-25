"""
Test script để gửi test messages tới RabbitMQ

Usage:
    python test_rabbitmq_send.py
"""

import pika
import json
import ssl
import sys
from core.config import settings

def send_test_message(action: str, data: dict, correlation_id: str = "test-123"):
    """Gửi test message tới RabbitMQ"""
    
    try:
        print(f"\n{'='*80}")
        print(f"Gửi test message: {action}")
        print(f"{'='*80}\n")
        
        # Credentials
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD
        )
        
        # Connection parameters with TLS
        if settings.RABBITMQ_USE_TLS:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_TLS_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=credentials,
                ssl_options=pika.SSLOptions(ssl_context)
            )
        else:
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=credentials
            )
        
        # Connect
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Prepare message
        message = {
            "action": action,
            "data": data
        }
        
        message_body = json.dumps(message, ensure_ascii=False)
        
        # Publish
        properties = pika.BasicProperties(
            content_type='application/json',
            delivery_mode=2,
            correlation_id=correlation_id
        )
        
        channel.basic_publish(
            exchange='',
            routing_key=settings.RABBITMQ_REQUEST_QUEUE,
            body=message_body,
            properties=properties
        )
        
        print(f"Đã gửi message với correlation_id: {correlation_id}")
        print(f"\nMessage content:")
        print(json.dumps(message, indent=2, ensure_ascii=False))
        
        connection.close()
        print(f"\n{'='*80}")
        print("Thành công!")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\nLỗi: {str(e)}\n")
        sys.exit(1)


def test_process_jd():
    """Test xử lý Job Description"""
    
    data = {
        "text": """
        Job Title: Senior Python Developer
        
        Requirements:
        - 5+ years of Python development experience
        - Strong knowledge of FastAPI, Django
        - Experience with AWS, Docker, Kubernetes
        - Bachelor's degree in Computer Science
        - Good English communication skills
        
        Responsibilities:
        - Design and implement RESTful APIs
        - Work with cross-functional teams
        - Mentor junior developers
        - Write clean, maintainable code
        """,
        "jd_id": "test-jd-001"
    }
    
    send_test_message("process_jd", data, "test-jd-correlation-001")


def test_invalid_json():
    """Test message với JSON không hợp lệ (để test error handling)"""
    
    print(f"\n{'='*80}")
    print("Test: Gửi invalid message (để test error handling)")
    print(f"{'='*80}\n")
    
    # Gửi message không phải JSON hợp lệ sẽ cần handle ở receiver side
    # Ở đây ta test với action không tồn tại
    data = {
        "invalid_field": "test"
    }
    
    send_test_message("invalid_action", data, "test-invalid-001")


def test_missing_fields():
    """Test message thiếu required fields"""
    
    print(f"\n{'='*80}")
    print("Test: Message thiếu required fields")
    print(f"{'='*80}\n")
    
    # Missing 'text' field cho process_jd
    data = {
        "jd_id": "test-jd-002"
    }
    
    send_test_message("process_jd", data, "test-missing-fields-001")


def main():
    """Main function"""
    
    print("\n" + "="*80)
    print("RabbitMQ Test Script")
    print("="*80)
    print("\nChọn test case:")
    print("1. Test Process JD (thành công)")
    print("2. Test Invalid Action (lỗi dữ liệu)")
    print("3. Test Missing Fields (lỗi dữ liệu)")
    print("4. Chạy tất cả tests")
    print("0. Thoát")
    print()
    
    try:
        choice = input("Nhập lựa chọn (0-4): ").strip()
        
        if choice == "1":
            test_process_jd()
        elif choice == "2":
            test_invalid_json()
        elif choice == "3":
            test_missing_fields()
        elif choice == "4":
            print("\nChạy tất cả test cases...\n")
            test_process_jd()
            input("\nNhấn Enter để tiếp tục...")
            test_invalid_json()
            input("\nNhấn Enter để tiếp tục...")
            test_missing_fields()
            print("\nĐã hoàn thành tất cả tests!")
        elif choice == "0":
            print("Goodbye!")
            return
        else:
            print("Lựa chọn không hợp lệ!")
            
    except KeyboardInterrupt:
        print("\n\nĐã hủy bởi người dùng")
    except Exception as e:
        print(f"\nLỗi: {str(e)}")


if __name__ == "__main__":
    main()
