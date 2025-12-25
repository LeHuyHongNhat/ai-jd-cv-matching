# Tích hợp RabbitMQ với Spring Boot

Hệ thống tích hợp RabbitMQ để kết nối FastAPI service với Spring Boot backend thông qua CloudAMQP.

---

## 📋 Mục lục

1. [Tổng quan](#tổng-quan)
2. [Kiến trúc](#kiến-trúc)
3. [Cài đặt](#cài-đặt)
4. [Cấu hình](#cấu-hình)
5. [Chạy Worker](#chạy-worker)
6. [Message Format](#message-format)
7. [Error Handling](#error-handling)
8. [Testing](#testing)
9. [Monitoring](#monitoring)

---

## Tổng quan

Hệ thống sử dụng RabbitMQ (CloudAMQP) làm message broker để giao tiếp giữa:

- **Spring Boot Backend**: Gửi requests
- **FastAPI Worker**: Xử lý CV/JD và trả về kết quả

### Thông tin kết nối RabbitMQ

```
Region:   AWS ap-northeast-1
Cluster:  chameleon.lmq.cloudamqp.com
Host:     chameleon-01.lmq.cloudamqp.com
User:     your-rabbitmq-user
VHost:    your-rabbitmq-user
Ports:    5672 (AMQP), 5671 (AMQP+TLS)
URL:      amqps://your-rabbitmq-user:****@chameleon.lmq.cloudamqp.com/your-rabbitmq-user
```

---

## Kiến trúc

```mermaid
graph LR
    subgraph "Spring Boot Backend"
        SB[Spring Boot API]
        P[Producer]
        C[Consumer]
    end

    subgraph "RabbitMQ CloudAMQP"
        Q1[Request Queue<br/>cv_jd_requests]
        Q2[Response Queue<br/>cv_jd_responses]
        DLQ[Dead Letter Queue<br/>cv_jd_requests_dlq]
    end

    subgraph "FastAPI Worker"
        W[RabbitMQ Worker]
        H[Message Handlers]
        S[Services]
    end

    SB --> P
    P --> Q1
    Q1 --> W
    W --> H
    H --> S
    S --> W
    W --> Q2
    Q2 --> C
    C --> SB

    Q1 -.->|NACK| DLQ

    style Q1 fill:#FFE5B4
    style Q2 fill:#B4E5FF
    style DLQ fill:#FFB4B4
```

### Luồng xử lý

1. **Spring Boot** gửi request message → **Request Queue**
2. **FastAPI Worker** nhận message từ Request Queue
3. Worker xử lý message (parse CV, extract data, matching...)
4. Worker gửi response → **Response Queue**
5. **Spring Boot** nhận response từ Response Queue
6. Worker gửi **ACK/NACK** cho RabbitMQ

---

## Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

Thư viện RabbitMQ đã được thêm vào `requirements.txt`:

```
pika==1.3.2  # Python RabbitMQ client
```

### 2. Cấu trúc thư mục

```
app/
├── rabbitmq/
│   ├── __init__.py              # Package init
│   ├── connection.py            # Quản lý kết nối RabbitMQ
│   ├── producer.py              # Gửi response về Spring Boot
│   ├── consumer.py              # Nhận và xử lý messages
│   └── message_handlers.py      # Handlers cho các loại messages
rabbitmq_worker.py               # Main worker script
README_RABBITMQ.md               # Tài liệu này
```

---

## Cấu hình

### File `config.env`

Tạo file `config.env` trong thư mục gốc:

```env
# OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key

# RabbitMQ Configuration (CloudAMQP)
RABBITMQ_HOST=chameleon.lmq.cloudamqp.com
RABBITMQ_PORT=5672
RABBITMQ_TLS_PORT=5671
RABBITMQ_USE_TLS=True
RABBITMQ_USER=your-rabbitmq-user
RABBITMQ_PASSWORD=your-rabbitmq-password
RABBITMQ_VHOST=your-rabbitmq-user

# Queue Names
RABBITMQ_REQUEST_QUEUE=cv_jd_requests
RABBITMQ_RESPONSE_QUEUE=cv_jd_responses
RABBITMQ_DLQ=cv_jd_requests_dlq

# Connection Settings
RABBITMQ_HEARTBEAT=600
RABBITMQ_BLOCKED_CONNECTION_TIMEOUT=300
RABBITMQ_PREFETCH_COUNT=1
```

### Cấu hình trong code

File `core/config.py` đã được cập nhật với RabbitMQ settings:

```python
class Settings(BaseSettings):
    OPENAI_API_KEY: str

    # RabbitMQ Configuration
    RABBITMQ_HOST: str = "chameleon.lmq.cloudamqp.com"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USE_TLS: bool = True
    # ... (xem file để biết chi tiết)
```

---

## Chạy Worker

### Chạy trực tiếp

```bash
python rabbitmq_worker.py
```

### Output mẫu

```
================================================================================
🚀 RabbitMQ Worker - CV-JD Matching Service
================================================================================
2025-12-16 10:00:00 - connection - INFO - ✅ Đã kết nối thành công đến RabbitMQ tại chameleon.lmq.cloudamqp.com
2025-12-16 10:00:00 - connection - INFO - ✅ Đã declare queues: cv_jd_requests, cv_jd_responses, cv_jd_requests_dlq
2025-12-16 10:00:00 - consumer - INFO - ✅ Consumer đang lắng nghe queue: cv_jd_requests
2025-12-16 10:00:00 - consumer - INFO - ⏳ Đang chờ messages... (Ctrl+C để dừng)

📨 Nhận message mới (correlation_id: 12345)
📋 Action: process_cv
📄 Parsing CV file: cv_example.pdf
🤖 Extracting structured data from CV
🔢 Creating embedding for CV
💾 Saving CV to vector store with ID: abc-123
✅ Successfully processed CV: abc-123
✅ Đã gửi response cho correlation_id: 12345, success: True
✅ ACK - Message đã được xử lý thành công
```

### Dừng Worker

Nhấn `Ctrl+C` để dừng worker gracefully.

---

## Message Format

### 1. Process CV

**Request từ Spring Boot:**

```json
{
  "action": "process_cv",
  "data": {
    "file_name": "john_doe_cv.pdf",
    "file_content": "base64_encoded_pdf_content...",
    "cv_id": "optional-custom-cv-id"
  }
}
```

**Response:**

```json
{
  "correlation_id": "request-tracking-id",
  "success": true,
  "data": {
    "cv_id": "abc-123-def",
    "file_name": "john_doe_cv.pdf",
    "structured_data": {
      "full_name": "John Doe",
      "email": "john@example.com",
      "hard_skills": {
        "programming_languages": ["Python", "Java"],
        "technologies_frameworks": ["FastAPI", "Spring Boot"]
      },
      "work_experience": {
        "total_years": 5.0,
        "job_titles": ["Software Engineer", "Senior Developer"]
      }
    }
  },
  "error": null
}
```

### 2. Process JD

**Request:**

```json
{
  "action": "process_jd",
  "data": {
    "text": "We are looking for a Senior Python Developer...",
    "jd_id": "optional-custom-jd-id"
  }
}
```

**Response:**

```json
{
  "correlation_id": "request-tracking-id",
  "success": true,
  "data": {
    "jd_id": "xyz-456-abc",
    "structured_data": {
      "hard_skills": {
        "programming_languages": ["Python"],
        "technologies_frameworks": ["Django", "FastAPI"]
      },
      "work_experience": {
        "total_years": 5.0
      }
    }
  },
  "error": null
}
```

### 3. Match CV-JD

**Request:**

```json
{
  "action": "match_cv_jd",
  "data": {
    "cv_id": "abc-123-def",
    "jd_id": "xyz-456-abc"
  }
}
```

**Response:**

```json
{
  "correlation_id": "request-tracking-id",
  "success": true,
  "data": {
    "cv_id": "abc-123-def",
    "jd_id": "xyz-456-abc",
    "total_score": 85.5,
    "breakdown": {
      "overall_semantic": 0.82,
      "skill_match": 0.9,
      "job_title_match": 0.85,
      "education_cert_match": 0.75
    }
  },
  "error": null
}
```

---

## Error Handling

### Quy trình xử lý lỗi

Hệ thống xử lý lỗi theo 3 trường hợp:

#### 1. ✅ Thành công

```
Xử lý message → Gửi response → Gửi ACK → Message bị xóa khỏi queue
```

#### 2. ⚠️ Lỗi dữ liệu (DATA_ERROR)

```
Ví dụ: JSON sai, thiếu field bắt buộc, file format không hỗ trợ

→ Log lỗi → Gửi error response → Gửi ACK → Message bị xóa (bỏ qua)
```

**Error Response:**

```json
{
  "correlation_id": "request-id",
  "success": false,
  "data": {
    "error_type": "DATA_ERROR",
    "error_message": "Invalid JSON format"
  },
  "error": "Invalid JSON format"
}
```

#### 3. ❌ Lỗi hệ thống (SYSTEM_ERROR)

```
Ví dụ: Mất mạng, database down, code bug, OpenAI API timeout

→ Log lỗi → (Gửi error response nếu có thể) → Gửi NACK → Message được re-queue
```

**Behavior:**

- Message sẽ được RabbitMQ tự động gửi lại sau một khoảng thời gian
- Nếu retry nhiều lần vẫn thất bại → Message chuyển sang **Dead Letter Queue (DLQ)**

### Error Types

| Error Type     | Ví dụ                                            | Xử lý           |
| -------------- | ------------------------------------------------ | --------------- |
| `DATA_ERROR`   | JSON invalid, Missing fields, Unsupported format | ACK (bỏ qua)    |
| `SYSTEM_ERROR` | Network timeout, DB connection, Code exception   | NACK (re-queue) |

### Dead Letter Queue (DLQ)

Messages fail nhiều lần sẽ được chuyển sang DLQ:

- Queue name: `cv_jd_requests_dlq`
- Cần manual review và xử lý các messages trong DLQ
- Xem DLQ trong CloudAMQP Management Console

---

## Testing

### 1. Test với Python script

Tạo file `test_rabbitmq.py`:

```python
import pika
import json
import base64

# Kết nối
credentials = pika.PlainCredentials('your-rabbitmq-user', 'your-rabbitmq-password')
parameters = pika.ConnectionParameters(
    host='chameleon.lmq.cloudamqp.com',
    port=5672,
    virtual_host='your-rabbitmq-user',
    credentials=credentials
)

connection = pika.BlockingConnection(parameters)
channel = connection.channel()

# Test message
message = {
    "action": "process_jd",
    "data": {
        "text": "Senior Python Developer needed. 5+ years experience."
    }
}

# Gửi message
channel.basic_publish(
    exchange='',
    routing_key='cv_jd_requests',
    body=json.dumps(message),
    properties=pika.BasicProperties(
        delivery_mode=2,
        correlation_id='test-123'
    )
)

print("✅ Đã gửi test message")
connection.close()
```

### 2. Test từ Spring Boot

```java
@Service
public class RabbitMQProducerService {

    @Autowired
    private RabbitTemplate rabbitTemplate;

    public void sendProcessCVRequest(String fileName, byte[] fileContent) {
        Map<String, Object> message = new HashMap<>();
        message.put("action", "process_cv");

        Map<String, Object> data = new HashMap<>();
        data.put("file_name", fileName);
        data.put("file_content", Base64.getEncoder().encodeToString(fileContent));
        message.put("data", data);

        rabbitTemplate.convertAndSend("cv_jd_requests", message);
    }
}
```

---

## Monitoring

### 1. CloudAMQP Management Console

Truy cập: https://customer.cloudamqp.com/

**Theo dõi:**

- Queue depth (số messages đang chờ)
- Message rates (publish/deliver/ack)
- Connection status
- Consumer status
- Dead letter queue messages

### 2. Log files

Worker ghi log vào:

- Console (stdout)
- File: `rabbitmq_worker.log`

**Log levels:**

- `INFO`: Hoạt động bình thường
- `WARNING`: Cảnh báo (data errors)
- `ERROR`: Lỗi nghiêm trọng (system errors)

### 3. Health Check

Kiểm tra worker đang chạy:

```bash
# Linux/Mac
ps aux | grep rabbitmq_worker

# Windows
tasklist | findstr python
```

---

## Troubleshooting

### Lỗi kết nối RabbitMQ

```
❌ Lỗi kết nối RabbitMQ: connection refused
```

**Giải pháp:**

- Kiểm tra network/firewall
- Verify credentials trong `config.env`
- Kiểm tra CloudAMQP instance status

### Messages không được xử lý

**Kiểm tra:**

1. Worker có đang chạy không?
2. Queue name đúng chưa?
3. Xem log file để tìm lỗi
4. Kiểm tra DLQ có messages không

### OpenAI API timeout

```
❌ System error: OpenAI API timeout
```

**Behavior:**

- Message sẽ được NACK và re-queue
- Worker sẽ retry message sau một khoảng thời gian
- Nếu vẫn timeout → chuyển sang DLQ

---

## Best Practices

### 1. Production Deployment

- Chạy nhiều worker instances (scaling)
- Sử dụng process manager (systemd, supervisor, PM2)
- Monitor queue depth và processing time
- Set up alerts cho DLQ depth

### 2. Performance

- Tăng `RABBITMQ_PREFETCH_COUNT` nếu cần xử lý parallel
- Optimize OpenAI API calls (batching nếu có thể)
- Cache ChromaDB queries

### 3. Security

- Không commit `config.env` vào git
- Rotate RabbitMQ password định kỳ
- Sử dụng TLS (đã enable mặc định)

### 4. Error Recovery

- Monitor DLQ thường xuyên
- Setup replay mechanism cho failed messages
- Log chi tiết để debug

---

## Liên hệ & Hỗ trợ

- **Issues**: Tạo issue trên GitHub repository
- **Documentation**: Xem thêm `SYSTEM_ARCHITECTURE.md`

---

**Chúc bạn tích hợp thành công! 🚀**
