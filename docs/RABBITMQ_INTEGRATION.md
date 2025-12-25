# Tích hợp RabbitMQ với Spring Boot

Tài liệu hướng dẫn tích hợp Python Worker với Spring Boot qua RabbitMQ CloudAMQP.

---

## 1. Kiến trúc hệ thống

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Frontend   │─────▶│  Spring Boot     │◀────▶│   RabbitMQ      │
│             │      │  Backend         │      │  CloudAMQP      │
└─────────────┘      └──────────────────┘      └─────────────────┘
                                                         │
                                                         │ Exchange:
                                                         │ internal_exchange
                                                         │
                                    ┌────────────────────┴────────────────────┐
                                    │                                         │
                              cv_upload_key                            cv_result_key
                                    │                                         │
                                    ▼                                         ▼
                          ┌──────────────────┐                    ┌──────────────────┐
                          │ cv_processing_   │                    │  cv_result_      │
                          │     queue        │                    │     queue        │
                          └──────────────────┘                    └──────────────────┘
                                    │                                         ▲
                                    │                                         │
                                    ▼                                         │
                          ┌─────────────────────────────────────────────────┐
                          │         Python Worker                            │
                          │  - Parse & Extract CV/JD                        │
                          │  - Create Embeddings (OpenAI)                   │
                          │  - Calculate Match Score                         │
                          └─────────────────────────────────────────────────┘
```

---

## 2. Cấu trúc RabbitMQ

### 2.1 Exchange Configuration

```yaml
Exchange Name: internal_exchange
Exchange Type: direct
Durable: true
```

### 2.2 Queue Configuration

| Queue Name            | Routing Key     | Mô tả                                 | Durable |
| --------------------- | --------------- | ------------------------------------- | ------- |
| `cv_processing_queue` | `cv_upload_key` | Input queue - Python nhận requests    | Yes     |
| `cv_result_queue`     | `cv_result_key` | Output queue - Python gửi results     | Yes     |
| `cv_processing_dlq`   | (auto)          | Dead Letter Queue cho failed messages | Yes     |

---

## 3. Message Format

### 3.1 Input Message (Spring Boot → Python)

**Queue:** `cv_processing_queue`  
**Routing Key:** `cv_upload_key`

```json
{
  "requestId": "req_123456789",
  "candidateId": 101,
  "jobId": 55,
  "cvContent": "Nội dung text trích xuất từ CV...",
  "jobRequirements": "Yêu cầu kỹ năng Java, Spring Boot...",
  "timestamp": "2025-12-16T20:30:00Z"
}
```

**Field Descriptions:**

| Field             | Type              | Required | Mô tả                                  |
| ----------------- | ----------------- | -------- | -------------------------------------- |
| `requestId`       | String            | Yes      | Unique ID để track request             |
| `candidateId`     | Integer           | Yes      | ID của ứng viên                        |
| `jobId`           | Integer           | Yes      | ID của công việc                       |
| `cvContent`       | String            | Yes      | Nội dung CV đã được extract thành text |
| `jobRequirements` | String            | Yes      | Yêu cầu công việc                      |
| `timestamp`       | String (ISO 8601) | Yes      | Thời gian gửi request                  |

### 3.2 Output Message (Python → Spring Boot)

**Queue:** `cv_result_queue`  
**Routing Key:** `cv_result_key`

#### Success Response:

```json
{
  "requestId": "req_123456789",
  "success": true,
  "data": {
    "requestId": "req_123456789",
    "candidateId": 101,
    "jobId": 55,
    "matchScore": 85.5,
    "breakdown": {
      "overallSemantic": 0.82,
      "skillMatch": 0.90,
      "jobTitleMatch": 0.85,
      "educationCertMatch": 0.75
    },
    "cvStructuredData": {
      "full_name": "Nguyễn Văn A",
      "email": "nguyenvana@email.com",
      "hard_skills": {
        "programming_languages": ["Python", "JavaScript"],
        "technologies_frameworks": ["FastAPI", "Django", "React"]
      },
      "work_experience": {
        "total_years": 5.0,
        "job_titles": ["Senior Python Developer"]
      }
    },
    "jdStructuredData": { ... }
  },
  "error": null,
  "timestamp": "2025-12-16T20:30:15Z"
}
```

#### Error Response:

```json
{
  "requestId": "req_123456789",
  "success": false,
  "data": {
    "error_type": "DATA_ERROR",
    "error_message": "Missing required field: cvContent"
  },
  "error": "Missing required field: cvContent",
  "timestamp": "2025-12-16T20:30:15Z"
}
```

**Error Types:**

- `DATA_ERROR`: Lỗi dữ liệu đầu vào (JSON sai, thiếu field, format không hợp lệ)
- `SYSTEM_ERROR`: Lỗi hệ thống (mất mạng, OpenAI timeout, code bug)

---

## 4. Cài đặt & Chạy Python Worker

### 4.1 Requirements

```bash
pip install -r requirements.txt
```

Dependencies chính:

- `pika==1.3.2` - RabbitMQ client
- `openai==1.12.0` - OpenAI API
- `chromadb==0.4.22` - Vector database

### 4.2 Configuration

Tạo file `config.env`:

```env
# OpenAI
OPENAI_API_KEY=sk-your-api-key

# RabbitMQ CloudAMQP
RABBITMQ_HOST=chameleon.lmq.cloudamqp.com
RABBITMQ_PORT=5672
RABBITMQ_TLS_PORT=5671
RABBITMQ_USE_TLS=True
RABBITMQ_USER=abkqvbjm
RABBITMQ_PASSWORD=4vwaChdSYTuiz6cPNzyy2FPZ041TVpOX
RABBITMQ_VHOST=abkqvbjm

# Exchange & Queues
RABBITMQ_EXCHANGE=internal_exchange
RABBITMQ_INPUT_QUEUE=cv_processing_queue
RABBITMQ_INPUT_ROUTING_KEY=cv_upload_key
RABBITMQ_OUTPUT_QUEUE=cv_result_queue
RABBITMQ_OUTPUT_ROUTING_KEY=cv_result_key
```

### 4.3 Chạy Worker

```bash
python rabbitmq_worker.py
```

**Output:**

```
================================================================================
RabbitMQ Worker - CV-JD Matching Service
================================================================================
MessageHandlers đã được khởi tạo
Starting RabbitMQ Consumer...
Đã kết nối thành công đến RabbitMQ tại chameleon.lmq.cloudamqp.com
Đã declare và bind queues:
  - Input: cv_processing_queue (routing_key: cv_upload_key)
  - Output: cv_result_queue (routing_key: cv_result_key)
  - DLQ: cv_processing_dlq
Consumer đang lắng nghe queue: cv_processing_queue
Đang chờ messages từ Spring Boot... (Ctrl+C để dừng)
```

---

## 5. Testing

### 5.1 Test với Python Script

```bash
python test_rabbitmq_spring_boot.py
```

Script cung cấp các test cases:

1. Python Developer (high match)
2. Java Developer (low match)
3. Missing Fields (error case)

### 5.2 Test từ Spring Boot

```java
@Service
public class CVProcessingService {

    @Autowired
    private RabbitTemplate rabbitTemplate;

    public void processCVMatching(Long candidateId, Long jobId,
                                  String cvContent, String jobRequirements) {

        Map<String, Object> message = new HashMap<>();
        message.put("requestId", "req_" + UUID.randomUUID().toString());
        message.put("candidateId", candidateId);
        message.put("jobId", jobId);
        message.put("cvContent", cvContent);
        message.put("jobRequirements", jobRequirements);
        message.put("timestamp", Instant.now().toString());

        rabbitTemplate.convertAndSend(
            "internal_exchange",
            "cv_upload_key",
            message
        );
    }
}
```

### 5.3 Nhận kết quả từ Python

```java
@Service
public class ResultConsumer {

    @RabbitListener(queues = "cv_result_queue")
    public void handleResult(Map<String, Object> message) {
        String requestId = (String) message.get("requestId");
        Boolean success = (Boolean) message.get("success");

        if (success) {
            Map<String, Object> data = (Map<String, Object>) message.get("data");
            Double matchScore = (Double) data.get("matchScore");

            log.info("Match score: {}", matchScore);
            // Process result...
        } else {
            String error = (String) message.get("error");
            log.error("Processing failed: {}", error);
        }
    }
}
```

---

## 6. Error Handling

### 6.1 Quy trình xử lý

```
┌─────────────────────────────────────────────────────────┐
│                   Nhận Message                           │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │  Parse JSON    │
         └────────┬───────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
    ▼                           ▼
┌──────────┐              ┌──────────┐
│ SUCCESS  │              │  ERROR   │
└────┬─────┘              └────┬─────┘
     │                         │
     ▼                         ▼
┌──────────┐         ┌──────────────────┐
│ Process  │         │  DATA_ERROR?     │
│ Message  │         └────┬─────────┬───┘
└────┬─────┘              │         │
     │                    │         │
     ▼                    ▼         ▼
┌──────────┐         ┌─────┐   ┌──────┐
│Send      │         │ ACK │   │NACK  │
│Response  │         │Skip │   │Retry │
└────┬─────┘         └─────┘   └──────┘
     │
     ▼
  ┌─────┐
  │ ACK │
  └─────┘
```

### 6.2 Error Types

| Error Type       | Behavior           | Spring Boot Action                                   |
| ---------------- | ------------------ | ---------------------------------------------------- |
| **DATA_ERROR**   | ACK (skip message) | Nhận error response, log và thông báo user           |
| **SYSTEM_ERROR** | NACK (retry)       | Message được retry tự động, nếu fail nhiều lần → DLQ |

### 6.3 Dead Letter Queue (DLQ)

Messages fail nhiều lần sẽ chuyển sang `cv_processing_dlq`:

- Monitor DLQ trong CloudAMQP console
- Manual review và xử lý
- Có thể replay messages nếu cần

---

## 7. Monitoring & Logs

### 7.1 Worker Logs

```
2025-12-16 21:35:22 - INFO - Nhận message mới (requestId: req_123456789)
2025-12-16 21:35:22 - INFO - candidateId: 101, jobId: 55
2025-12-16 21:35:22 - INFO - Xử lý matching cho candidateId=101, jobId=55
2025-12-16 21:35:22 - INFO - Bước 1: Trích xuất thông tin từ CV...
2025-12-16 21:35:25 - INFO - Bước 2: Trích xuất thông tin từ Job Requirements...
2025-12-16 21:35:28 - INFO - Bước 3: Tạo embeddings...
2025-12-16 21:35:30 - INFO - Bước 4: Tính điểm matching...
2025-12-16 21:35:31 - INFO - Hoàn thành matching: score=85.50
2025-12-16 21:35:31 - INFO - Đã gửi response cho requestId: req_123456789
2025-12-16 21:35:31 - INFO - ACK - Message đã được xử lý thành công
```

### 7.2 CloudAMQP Monitoring

Truy cập: https://customer.cloudamqp.com/

**Theo dõi:**

- Queue depth
- Message rates (publish/deliver/ack)
- Consumer status
- Error rates
- DLQ messages

---

## 8. Performance

### 8.1 Processing Time

| Bước                       | Thời gian trung bình |
| -------------------------- | -------------------- |
| Parse JSON                 | ~5ms                 |
| Extract CV structured data | ~3s                  |
| Extract JD structured data | ~2s                  |
| Create embeddings          | ~1s                  |
| Calculate match score      | ~100ms               |
| **Total**                  | **~6-7s**            |

### 8.2 Scaling

Để tăng throughput:

1. Chạy nhiều worker instances
2. Tăng `RABBITMQ_PREFETCH_COUNT`
3. Sử dụng batch processing nếu có thể

---

## 9. Troubleshooting

### Lỗi kết nối RabbitMQ

```
Lỗi kết nối RabbitMQ: connection refused
```

**Giải pháp:**

- Kiểm tra credentials trong `config.env`
- Verify CloudAMQP instance status
- Check firewall/network

### Messages không được xử lý

**Kiểm tra:**

1. Worker có đang chạy?
2. Queue names và routing keys đúng?
3. Check logs cho errors
4. Xem DLQ có messages không?

### OpenAI API timeout

```
System error: OpenAI API timeout
```

**Behavior:**

- Message được NACK và retry
- Nếu vẫn timeout → chuyển DLQ

---

## 10. Contact & Support

- **Issues**: Tạo issue trên GitHub
- **Documentation**: Xem `SYSTEM_ARCHITECTURE.md`

---

**Chúc bạn tích hợp thành công!**
