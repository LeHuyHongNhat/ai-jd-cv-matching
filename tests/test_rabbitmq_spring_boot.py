"""
Test script để gửi test messages tới RabbitMQ theo format Spring Boot

Usage:
    python test_rabbitmq_spring_boot.py
"""

import pika
import json
import ssl
import sys
from datetime import datetime
from core.config import settings


def send_cv_processing_request(
    request_id: str,
    candidate_id: int,
    job_id: int,
    cv_content: str,
    job_requirements: str
):
    """
    Gửi CV processing request theo format Spring Boot
    
    Args:
        request_id: Unique request ID
        candidate_id: ID của ứng viên
        job_id: ID của công việc
        cv_content: Nội dung CV (text)
        job_requirements: Yêu cầu công việc (text)
    """
    try:
        print(f"\n{'='*80}")
        print(f"Gửi CV Processing Request")
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
        
        # Prepare message theo format Spring Boot
        message = {
            "requestId": request_id,
            "candidateId": candidate_id,
            "jobId": job_id,
            "cvContent": cv_content,
            "jobRequirements": job_requirements,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        message_body = json.dumps(message, ensure_ascii=False)
        
        # Publish
        properties = pika.BasicProperties(
            content_type='application/json',
            delivery_mode=2,
            correlation_id=request_id
        )
        
        channel.basic_publish(
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key=settings.RABBITMQ_INPUT_ROUTING_KEY,
            body=message_body,
            properties=properties
        )
        
        print(f"Đã gửi message với requestId: {request_id}")
        print(f"\nMessage content:")
        print(json.dumps(message, indent=2, ensure_ascii=False))
        
        connection.close()
        print(f"\n{'='*80}")
        print("Thành công!")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\nLỗi: {str(e)}\n")
        sys.exit(1)


def test_python_developer():
    """Test với Python Developer CV"""
    
    cv_content = """
    NGUYỄN VĂN A
    Senior Python Developer
    Email: nguyenvana@email.com | Phone: 0901234567
    
    KINH NGHIỆM LÀM VIỆC:
    - 5 năm kinh nghiệm phát triển Python
    - Thành thạo FastAPI, Django, Flask
    - Có kinh nghiệm với AWS, Docker, Kubernetes
    - Làm việc với PostgreSQL, MongoDB, Redis
    - CI/CD với Jenkins, GitLab CI
    
    HỌC VẤN:
    - Cử nhân Khoa học Máy tính, Đại học Bách Khoa Hà Nội
    - GPA: 3.5/4.0
    
    KỸ NĂNG:
    - Ngôn ngữ: Python, JavaScript, SQL
    - Framework: FastAPI, Django, React
    - Database: PostgreSQL, MongoDB, Redis
    - Cloud: AWS (EC2, S3, Lambda, RDS)
    - DevOps: Docker, Kubernetes, CI/CD
    - Tiếng Anh: TOEIC 850
    
    DỰ ÁN NỔI BẬT:
    - Xây dựng RESTful API cho hệ thống e-commerce (500K users)
    - Phát triển microservices cho fintech startup
    - Tối ưu hóa performance, giảm 60% response time
    """
    
    job_requirements = """
    VỊ TRÍ: Senior Python Developer
    
    YÊU CẦU:
    - 3+ năm kinh nghiệm phát triển Python
    - Thành thạo FastAPI hoặc Django
    - Có kinh nghiệm với AWS cloud services
    - Biết về Docker và Kubernetes
    - Kinh nghiệm làm việc với database (PostgreSQL, MongoDB)
    - Good English communication skills
    
    ƯU TIÊN:
    - Có kinh nghiệm với microservices architecture
    - Biết về CI/CD pipelines
    - Có kinh nghiệm với Redis caching
    - Đã làm việc trong môi trường agile
    
    QUYỀN LỢI:
    - Lương: 25-35 triệu VND
    - Full benefits package
    - Remote working flexibility
    """
    
    send_cv_processing_request(
        request_id="req_test_001",
        candidate_id=101,
        job_id=55,
        cv_content=cv_content,
        job_requirements=job_requirements
    )


def test_java_developer():
    """Test với Java Developer CV (không match lắm)"""
    
    cv_content = """
    TRẦN THỊ B
    Java Backend Developer
    Email: tranthib@email.com | Phone: 0912345678
    
    KINH NGHIỆM:
    - 4 năm kinh nghiệm Java Spring Boot
    - Thành thạo Spring Framework, Spring MVC
    - Có kinh nghiệm với microservices
    - Oracle Database, MySQL
    
    KỸ NĂNG:
    - Java, Spring Boot, Spring Cloud
    - Oracle, MySQL, JPA/Hibernate
    - Maven, Gradle
    - Basic Docker knowledge
    
    HỌC VẤN:
    - Cử nhân CNTT, ĐH Công Nghệ
    """
    
    job_requirements = """
    VỊ TRÍ: Senior Python Developer
    
    YÊU CẦU:
    - 3+ năm kinh nghiệm Python
    - FastAPI, Django
    - AWS, Docker, Kubernetes
    - PostgreSQL, MongoDB
    """
    
    send_cv_processing_request(
        request_id="req_test_002",
        candidate_id=102,
        job_id=55,
        cv_content=cv_content,
        job_requirements=job_requirements
    )


def test_missing_fields():
    """Test với message thiếu fields"""
    
    print(f"\n{'='*80}")
    print("Test: Message thiếu required fields")
    print(f"{'='*80}\n")
    
    try:
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD
        )
        
        if settings.RABBITMQ_USE_TLS:
            ssl_context = ssl.create_default_context()
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
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Message thiếu cvContent
        message = {
            "requestId": "req_test_003",
            "candidateId": 103,
            "jobId": 55,
            "jobRequirements": "Some requirements..."
            # Missing cvContent
        }
        
        channel.basic_publish(
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key=settings.RABBITMQ_INPUT_ROUTING_KEY,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                content_type='application/json',
                delivery_mode=2,
                correlation_id="req_test_003"
            )
        )
        
        print("Đã gửi message thiếu fields")
        connection.close()
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")


def main():
    """Main function"""
    
    print("\n" + "="*80)
    print("RabbitMQ Test Script - Spring Boot Format")
    print("="*80)
    print("\nChọn test case:")
    print("1. Test Python Developer (high match)")
    print("2. Test Java Developer (low match)")
    print("3. Test Missing Fields (error case)")
    print("4. Chạy tất cả tests")
    print("0. Thoát")
    print()
    
    try:
        choice = input("Nhập lựa chọn (0-4): ").strip()
        
        if choice == "1":
            test_python_developer()
        elif choice == "2":
            test_java_developer()
        elif choice == "3":
            test_missing_fields()
        elif choice == "4":
            print("\nChạy tất cả test cases...\n")
            test_python_developer()
            input("\nNhấn Enter để tiếp tục...")
            test_java_developer()
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
