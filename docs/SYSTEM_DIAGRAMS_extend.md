# Sơ đồ Hệ thống AI Matching Backend

> Tài liệu này chứa các sơ đồ được vẽ dựa trên code thực tế trong folder dự án GP.

---

## 1. Kiến trúc Tổng thể Hệ thống

```mermaid
graph TB
    subgraph "External"
        FE[Frontend React/Next]
        SB[Spring Boot Backend]
    end

    subgraph "AI Matching Backend - FastAPI"
        API[API Layer<br/>app/api/main.py]

        subgraph "Service Layer - app/services/"
            PS[ParserService<br/>parser_service.py]
            SS[StructuringService<br/>structuring_service.py]
            ES[EmbeddingService<br/>embedding_service.py]
            VS[VectorStoreService<br/>vector_store.py]
            SC[ScoringService<br/>scoring_service.py]
            ESC[EnhancedScoringService<br/>scoring_service_new.py]
        end

        subgraph "Core Layer - core/"
            CFG[Config<br/>config.py]
            SCH[Schemas<br/>schemas.py]
        end
    end

    subgraph "Data Storage"
        CHROMA[(ChromaDB<br/>chroma_db/)]
        DUMP[IO Dump<br/>io_dump/prompts/<br/>io_dump/responses/]
    end

    subgraph "Message Queue"
        MQ[RabbitMQ / Kafka<br/>Message Broker]
    end

    subgraph "External Services"
        OAI[OpenAI API<br/>GPT-4o-mini<br/>text-embedding-3-small]
    end

    FE -->|REST/GraphQL| SB
    SB -->|Publish messages| MQ
    MQ -->|Consume messages| API

    API --> PS
    API --> SS
    API --> ES
    API --> VS
    API --> SC

    SC --> ESC
    SC --> ES
    ESC --> ES

    PS -->|parse PDF/DOCX| API
    SS -->|GPT-4o-mini| OAI
    ES -->|text-embedding-3-small| OAI

    VS -->|read/write| CHROMA
    SS -->|log prompts/responses| DUMP

    CFG -.->|config| API
    SCH -.->|data models| API

    style API fill:#4A90E2
    style CHROMA fill:#50C878
    style OAI fill:#FFA500
```

**Message Queue Channels:**

- `cv_processing_queue` - Nhận CV từ Spring Boot để xử lý
- `jd_processing_queue` - Nhận JD từ Spring Boot để xử lý
- `matching_request_queue` - Nhận yêu cầu matching
- `result_notification_queue` - Gửi kết quả về Spring Boot

### Giải thích chi tiết:

**Kiến trúc Microservices với Message Queue:**

- Hệ thống được chia thành 4 tầng chính: **External** (Frontend + Spring Boot), **Message Queue** (RabbitMQ/Kafka), **AI Matching Backend** (Python Background Workers), và **Data Storage** (ChromaDB + IO Dump).
- Spring Boot đóng vai trò là API Gateway nhận request từ Frontend, xác thực người dùng, và publish messages lên queue.
- Python AI chạy dưới dạng **background workers**, tự động consume messages từ queue và xử lý bất đồng bộ.

**AI Matching Backend (Python Background Workers):**

- **Worker Layer** (`app/workers/`): Background workers consume messages từ queue, validate data và orchestrate các services.
- **Message Consumer**: 3 consumers chính:
  - `CVProcessingWorker`: Lắng nghe `cv_processing_queue`
  - `JDProcessingWorker`: Lắng nghe `jd_processing_queue`
  - `MatchingWorker`: Lắng nghe `matching_request_queue`
- **Service Layer**: 6 services độc lập xử lý từng nhiệm vụ cụ thể:
  - `ParserService`: Trích xuất text từ PDF/DOCX bằng pdfplumber và python-docx
  - `StructuringService`: Gọi GPT-4o-mini để chuyển text thô thành structured JSON theo schema
  - `EmbeddingService`: Tạo vector 1536 chiều bằng text-embedding-3-small
  - `VectorStoreService`: Quản lý ChromaDB collections (cv_collection, jd_collection)
  - `ScoringService`: Public interface cho scoring logic
  - `EnhancedScoringService`: Implementation chi tiết của hệ thống chấm điểm 6 hạng mục
- **Core Layer**: Config quản lý biến môi trường (OpenAI API key), Schemas định nghĩa Pydantic models cho validation

**Data Storage:**

- **ChromaDB** (`./chroma_db/`): Vector database lưu embeddings và metadata của CV/JD, persistent trên disk
- **IO Dump** (`./io_dump/`): Lưu prompts/responses từ OpenAI để audit, debug và potential fine-tuning

**Luồng hoạt động (Asynchronous Message-Driven):**

1. **Upload CV/JD**: Spring Boot nhận file/text từ Frontend → Validate → Publish message lên queue (`cv_processing_queue` hoặc `jd_processing_queue`) → Trả về `task_id` ngay lập tức
2. **Background Processing**: Python worker consume message → Parse → Structure → Embed → Lưu ChromaDB → Publish kết quả lên `result_notification_queue`
3. **Notification**: Spring Boot consume kết quả từ queue → Lưu `doc_id` vào database → Notify Frontend qua WebSocket/SSE
4. **Matching Request**: Spring Boot publish matching request lên `matching_request_queue` với `{cv_id, jd_id, task_id}`
5. **Matching Processing**: MatchingWorker consume → Load từ ChromaDB → Tính điểm → Publish kết quả
6. **Result Delivery**: Spring Boot nhận kết quả → Cập nhật DB → Notify Frontend

**Lợi ích của Message Queue Pattern:**

- **Asynchronous**: Frontend không chờ xử lý (5-10s), nhận kết quả qua notification
- **Scalability**: Có thể chạy nhiều workers song song, auto-scale theo queue depth
- **Resilience**: Message không bị mất nếu worker crash, có retry mechanism
- **Decoupling**: Spring Boot và Python AI hoàn toàn độc lập, không phụ thuộc uptime của nhau

**Message Queue Technology:**

- **RabbitMQ** (recommended): AMQP protocol, dễ setup, support priority queues, TTL, dead letter queues
- **Kafka**: High throughput, distributed, event streaming, tốt cho scale lớn
- Message format: JSON với schema `{"task_id": "uuid", "task_type": "process_cv", "payload": {...}, "timestamp": "..."}`

**Bảo mật & Hiệu năng:**

- Messages được encrypt nếu chứa sensitive data (CV content)
- Queue authentication với username/password hoặc TLS certificates
- ChromaDB sử dụng PersistentClient để dữ liệu không bị mất khi restart
- Workers có thể scale độc lập: chạy nhiều instances consume cùng 1 queue (horizontal scaling)
- Dead Letter Queue (DLQ) cho failed messages, retry 3 lần trước khi vào DLQ

---

## 2. Luồng Xử lý API - Ba Endpoint Chính

### 2.1 CV Processing với Message Queue

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant SB as Spring Boot
    participant MQ as Message Queue
    participant Worker as CVProcessingWorker
    participant PS as ParserService
    participant SS as StructuringService
    participant ES as EmbeddingService
    participant VS as VectorStoreService
    participant OAI as OpenAI API
    participant DB as ChromaDB

    User->>FE: Upload CV (PDF/DOCX)
    FE->>SB: POST /api/cv/upload
    SB->>SB: Validate file, save temp
    SB->>SB: Generate task_id (UUID)
    SB->>MQ: Publish message<br/>{task_id, file_path, user_id}
    SB-->>FE: 202 Accepted<br/>{task_id, status: "processing"}

    Note over Worker: Background Worker<br/>continuously polls queue

    MQ->>Worker: Consume message
    Worker->>Worker: Load file from path

    Worker->>PS: parse_file(file_path)
    PS->>PS: _parse_pdf() or _parse_docx()
    PS->>PS: _clean_text()
    PS-->>Worker: text_content

    Worker->>SS: get_structured_data(text_content)
    SS->>OAI: GPT-4o-mini request
    OAI-->>SS: structured JSON
    SS->>SS: Log to io_dump
    SS-->>Worker: structured_json

    Worker->>ES: get_embedding(text_content)
    ES->>OAI: Embedding request
    OAI-->>ES: embedding vector
    ES-->>Worker: embedding

    Worker->>Worker: Generate cv_id (UUID)
    Worker->>VS: add_document("cv_collection", cv_id, ...)
    VS->>DB: collection.add()

    Worker->>MQ: Publish result<br/>{task_id, cv_id, status: "completed"}

    MQ->>SB: Consume result
    SB->>SB: Update DB, save cv_id
    SB->>FE: WebSocket/SSE notification<br/>{task_id, cv_id, status: "completed"}
    FE->>User: Show success notification
```

### 2.2 JD Processing với Message Queue

```mermaid
sequenceDiagram
    actor Recruiter
    participant FE as Frontend
    participant SB as Spring Boot
    participant MQ as Message Queue
    participant Worker as JDProcessingWorker
    participant SS as StructuringService
    participant ES as EmbeddingService
    participant VS as VectorStoreService
    participant OAI as OpenAI API
    participant DB as ChromaDB

    Recruiter->>FE: Paste JD text
    FE->>SB: POST /api/jd/create
    SB->>SB: Validate text, generate task_id
    SB->>MQ: Publish to jd_processing_queue<br/>{task_id, jd_text, recruiter_id}
    SB-->>FE: 202 Accepted<br/>{task_id, status: "processing"}

    MQ->>Worker: Consume message
    Worker->>Worker: Validate text not empty

    Worker->>SS: get_structured_data(jd_text)
    SS->>OAI: GPT-4o-mini request
    OAI-->>SS: structured JSON
    SS-->>Worker: structured_json

    Worker->>ES: get_embedding(jd_text)
    ES->>OAI: Embedding request
    OAI-->>ES: embedding vector
    ES-->>Worker: embedding

    Worker->>Worker: Generate jd_id (UUID)
    Worker->>VS: add_document("jd_collection", jd_id, ...)
    VS->>DB: collection.add()

    Worker->>MQ: Publish result<br/>{task_id, jd_id, status: "completed"}

    MQ->>SB: Consume result
    SB->>SB: Update DB, save jd_id
    SB->>FE: WebSocket notification<br/>{task_id, jd_id}
    FE->>Recruiter: JD ready for matching
```

### 2.3 CV-JD Matching với Message Queue

```mermaid
sequenceDiagram
    actor Recruiter
    participant FE as Frontend
    participant SB as Spring Boot
    participant MQ as Message Queue
    participant Worker as MatchingWorker
    participant VS as VectorStoreService
    participant SC as ScoringService
    participant ESC as EnhancedScoringService
    participant ES as EmbeddingService
    participant DB as ChromaDB
    participant OAI as OpenAI API

    Recruiter->>FE: Request matching CV with JD
    FE->>SB: POST /api/matching/request
    SB->>SB: Validate cv_id, jd_id exist
    SB->>SB: Generate task_id
    SB->>MQ: Publish to matching_request_queue<br/>{task_id, cv_id, jd_id}
    SB-->>FE: 202 Accepted<br/>{task_id, status: "matching"}

    MQ->>Worker: Consume message

    Worker->>VS: get_document_by_id("cv_collection", cv_id)
    VS->>DB: collection.get(ids=[cv_id])
    DB-->>VS: {embedding, metadata}
    VS-->>Worker: cv_doc

    Worker->>VS: get_document_by_id("jd_collection", jd_id)
    VS->>DB: collection.get(ids=[jd_id])
    DB-->>VS: {embedding, metadata}
    VS-->>Worker: jd_doc

    Worker->>SC: calculate_match_score(cv_data, jd_data)
    SC->>ESC: calculate_enhanced_match_score()

    Note over ESC: 6-category scoring
    ESC->>ESC: _score_hard_skills()
    ESC->>ES: get_embeddings_batch([skills])
    ES->>OAI: Batch embeddings
    OAI-->>ES: embeddings
    ESC->>ESC: cosine_similarity()

    ESC->>ESC: _score_work_experience()
    ESC->>ESC: _score_responsibilities()
    ESC->>ESC: _score_soft_skills()
    ESC->>ESC: _score_education()
    ESC->>ESC: _score_additional_factors()

    ESC->>ESC: Weighted sum + analysis
    ESC-->>SC: {total_score, breakdown, analysis}
    SC-->>Worker: score_result

    Worker->>MQ: Publish result<br/>{task_id, total_score, breakdown, status: "completed"}

    MQ->>SB: Consume result
    SB->>SB: Save matching result to DB
    SB->>FE: WebSocket notification<br/>{task_id, score, breakdown}
    FE->>Recruiter: Display matching score<br/>+ radar chart + recommendations
```

### Giải thích chi tiết Message Queue Pattern:

#### 2.1 CV Processing với Background Worker:

**Phase A: Upload & Queue (Spring Boot - Synchronous)**

- Frontend upload CV file → Spring Boot nhận request
- Spring Boot validate file (extension, size, MIME type), scan virus (optional)
- Lưu file vào shared storage (NFS/S3) hoặc temp folder accessible by workers
- Generate `task_id` (UUID) để tracking
- Publish message lên `cv_processing_queue`: `{"task_id": "...", "file_path": "...", "user_id": "...", "timestamp": "..."}`
- Trả về **202 Accepted** ngay lập tức với `task_id` → **Response time < 100ms**
- Frontend polling hoặc lắng nghe WebSocket để nhận notification

**Phase B: Background Processing (Python Worker - Asynchronous)**

- Worker instance (có thể nhiều workers chạy song song) continuously poll queue với `prefetch_count=1`
- Consume message từ `cv_processing_queue`
- ACK message sau khi xử lý xong (hoặc NACK nếu fail để retry)
- Load file từ `file_path` trong message
- `ParserService.parse_file()` gọi `pdfplumber` (PDF) hoặc `python-docx` (DOCX)
- `_clean_text()` normalize whitespace, remove empty lines

**Phase C: AI Processing**

- `StructuringService.get_structured_data()`:
  - Generate system prompt từ Pydantic schema
  - Call GPT-4o-mini với `temperature=0.1`, `response_format=json_object`
  - Extract 6 categories: hard_skills, work_experience, responsibilities, soft_skills, education, additional_factors
  - Log prompt/response vào `io_dump/` với timestamp
- `EmbeddingService.get_embedding()`:
  - Call OpenAI `text-embedding-3-small`
  - Return vector 1536 dimensions

**Phase D: Storage & Result Publishing**

- Generate `cv_id` (UUID)
- `VectorStoreService.add_document()`:
  - Serialize metadata (JSON.dumps cho list/dict)
  - Save to ChromaDB `cv_collection`
  - HNSW indexing tự động
- Publish result message lên `result_notification_queue`:
  ```json
  {
    "task_id": "original_task_id",
    "cv_id": "generated_cv_id",
    "status": "completed",
    "structured_data": {...},
    "timestamp": "...",
    "processing_time_ms": 8500
  }
  ```

**Phase E: Result Delivery (Spring Boot)**

- Spring Boot consume message từ `result_notification_queue`
- Lưu `cv_id` và `structured_data` vào PostgreSQL
- Update task status: `processing` → `completed`
- Send WebSocket/SSE notification tới Frontend: `{task_id, cv_id, status}`
- Frontend hiển thị success notification, load CV details

#### 2.2 JD Processing với Background Worker:

**Luồng tương tự CV Processing:**

1. **Upload**: Recruiter paste JD text → Spring Boot validate → Publish message lên `jd_processing_queue`
2. **Worker**: `JDProcessingWorker` consume message, không cần parse file (đã là text)
3. **AI**: Structure với GPT-4o-mini + Embedding
4. **Storage**: Lưu vào `jd_collection` (tách biệt với CV)
5. **Notification**: Publish result → Spring Boot notify Frontend

**Khác biệt với CV:**

- Không có parsing step (input đã là text)
- Có thể cache JD templates (nhiều CVs match với 1 JD)
- JD thường ít thay đổi → có thể pre-compute embeddings

**Use case**: Recruiter tạo JD mới hoặc import từ website tuyển dụng

#### 2.3 CV-JD Matching với Background Worker:

**Phase 1: Request Initiation (Spring Boot)**

- Recruiter click "Match CV với JD" trên Frontend
- Spring Boot nhận request `{cv_id, jd_id}`
- Validate cả 2 IDs tồn tại trong DB (đã được processed)
- Generate `task_id`, publish lên `matching_request_queue`
- Return **202 Accepted** với `task_id`

**Phase 2: Background Matching (MatchingWorker)**

- Worker consume message từ `matching_request_queue`
- Load CV và JD từ ChromaDB:
  - `VectorStoreService.get_document_by_id("cv_collection", cv_id)`
  - `VectorStoreService.get_document_by_id("jd_collection", jd_id)`
  - Deserialize JSON metadata về Python objects

**Phase 3: Scoring Pipeline**

- `ScoringService.calculate_match_score()` orchestrate toàn bộ logic
- `EnhancedScoringService` tính điểm 6 categories:
  1. **Hard Skills (30%)**: Batch embed all skills → cosine similarity matrix → weighted average
  2. **Work Experience (25%)**: Job title match (40%) + industry (30%) + years (30%)
  3. **Responsibilities (15%)**: Key tasks (60%) + achievements (20%) + projects (20%)
  4. **Soft Skills (10%)**: Semantic match với fallback 0.5
  5. **Education (5%)**: Degrees (50%) + majors (30%) + courses (20%)
  6. **Additional Factors (15%)**: Languages (40%) + availability (30%) + relocation (30%)
- `_generate_detailed_analysis()`: strengths, gaps, recommendations

**Phase 4: Result Publishing**

- Worker publish result message lên `result_notification_queue`:
  ```json
  {
    "task_id": "...",
    "cv_id": "...",
    "jd_id": "...",
    "total_score": 0.745,
    "category_scores": {...},
    "detailed_analysis": {...},
    "status": "completed",
    "processing_time_ms": 3200
  }
  ```

**Phase 5: Result Delivery**

- Spring Boot consume result
- Save matching result vào DB (for history, analytics)
- Send WebSocket notification tới Frontend
- Frontend display:
  - Total score với màu (green >0.8, yellow 0.6-0.8, red <0.6)
  - Radar chart 6 categories
  - Detailed analysis (strengths, gaps, recommendations)
  - Action buttons: "Accept", "Reject", "Interview"

**Performance & Scalability:**

- Matching có thể call OpenAI API để batch embed skills (~1-2s)
- Có thể cache embeddings của common skills (Python, Java, ...) trong Redis
- Multiple MatchingWorkers chạy song song để handle high load
- Average processing time: **2-5 giây** (down from 5-10s synchronous)

#### 2.4 Worker Implementation Details:

**Worker Architecture:**

```python
# app/workers/cv_processing_worker.py
import pika  # RabbitMQ client
# hoặc from kafka import KafkaConsumer  # Kafka client

class CVProcessingWorker:
    def __init__(self):
        self.parser = ParserService()
        self.structuring = StructuringService()
        self.embedding = EmbeddingService()
        self.vector_store = VectorStoreService()

    def start(self):
        # Kết nối message queue
        connection = pika.BlockingConnection(...)
        channel = connection.channel()
        channel.queue_declare(queue='cv_processing_queue', durable=True)
        channel.basic_qos(prefetch_count=1)  # Process 1 message at a time

        # Consume messages
        channel.basic_consume(
            queue='cv_processing_queue',
            on_message_callback=self.process_message
        )

        print("Worker started, waiting for messages...")
        channel.start_consuming()

    def process_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            task_id = message['task_id']
            file_path = message['file_path']

            # Process CV
            text = self.parser.parse_file(file_path)
            structured = self.structuring.get_structured_data(text)
            embedding = self.embedding.get_embedding(text)

            cv_id = str(uuid.uuid4())
            self.vector_store.add_document("cv_collection", cv_id, embedding, structured)

            # Publish result
            self.publish_result({
                'task_id': task_id,
                'cv_id': cv_id,
                'status': 'completed'
            })

            # ACK message (success)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            # NACK message (retry or move to DLQ)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            self.publish_error(task_id, str(e))
```

**Docker Deployment:**

```dockerfile
# Dockerfile.worker
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY core/ ./core/

CMD ["python", "-m", "app.workers.cv_processing_worker"]
```

**Kubernetes Deployment:**

```yaml
# k8s/workers-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cv-processing-worker
spec:
  replicas: 3 # 3 workers chạy song song
  selector:
    matchLabels:
      app: cv-worker
  template:
    metadata:
      labels:
        app: cv-worker
    spec:
      containers:
        - name: worker
          image: ai-matching-worker:latest
          env:
            - name: QUEUE_TYPE
              value: "cv_processing"
            - name: RABBITMQ_URL
              valueFrom:
                secretKeyRef:
                  name: rabbitmq-secret
                  key: url
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: openai-secret
                  key: api_key
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
```

**Auto-scaling:**

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cv-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cv-processing-worker
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: External
      external:
        metric:
          name: rabbitmq_queue_messages_ready
          selector:
            matchLabels:
              queue: cv_processing_queue
        target:
          type: AverageValue
          averageValue: "30" # Scale up nếu >30 messages trong queue
```

**Error Handling & Retry:**

- **Retry Logic**: Failed message được retry 3 lần với exponential backoff (1s, 2s, 4s)
- **Dead Letter Queue (DLQ)**: Sau 3 retries failed → move to `cv_processing_dlq` để manual review
- **Poison Messages**: Messages invalid format → move to DLQ ngay lập tức
- **Timeout**: Nếu worker xử lý >60s → kill process, NACK message để worker khác retry
- **Monitoring**: Track metrics `messages_processed`, `messages_failed`, `processing_time_avg`

#### 2.5 So sánh: Synchronous REST API vs Message Queue

| Aspect              | REST API (Old)               | Message Queue (New)                       |
| ------------------- | ---------------------------- | ----------------------------------------- |
| **Response Time**   | 5-10s (blocking)             | <100ms (202 Accepted)                     |
| **User Experience** | Loading spinner 10s          | Instant response + notification           |
| **Scalability**     | Limited by server threads    | Unlimited workers                         |
| **Fault Tolerance** | Request lost if crash        | Message persisted, retry                  |
| **Load Balancing**  | Round-robin HTTP             | Queue automatically distributes           |
| **Monitoring**      | HTTP status codes            | Queue depth, processing time              |
| **Backpressure**    | HTTP 503 Service Unavailable | Messages queue up, auto-scale             |
| **Cost**            | Keep connections open        | Workers scale down to 0 when idle         |
| **Complexity**      | Simple (1 service call)      | Complex (queue + workers + notifications) |
| **Best For**        | Quick operations (<1s)       | Long-running tasks (>2s)                  |

**When to use Message Queue:**

- ✅ Processing time > 2 seconds
- ✅ Need to scale processing independently
- ✅ Want to retry failed operations
- ✅ Batch processing
- ✅ Decouple services

**When to use REST API:**

- ✅ Real-time response required
- ✅ Processing time < 1 second
- ✅ Simple CRUD operations
- ✅ Client needs immediate result

---

## 2.6 Message Queue Architecture - Worker Pattern

```mermaid
graph TB
    subgraph "Spring Boot API Layer"
        SB1[Spring Boot Instance 1]
        SB2[Spring Boot Instance 2]
        SB3[Spring Boot Instance N]
    end

    subgraph "Message Queue Cluster"
        MQ[RabbitMQ / Kafka Broker]
        Q1[cv_processing_queue]
        Q2[jd_processing_queue]
        Q3[matching_request_queue]
        Q4[result_notification_queue]
        DLQ[Dead Letter Queue]

        MQ --> Q1
        MQ --> Q2
        MQ --> Q3
        MQ --> Q4
        MQ --> DLQ
    end

    subgraph "Python AI Workers Pod 1"
        W1[CVProcessingWorker]
        W2[JDProcessingWorker]
        W3[MatchingWorker]
    end

    subgraph "Python AI Workers Pod 2"
        W4[CVProcessingWorker]
        W5[JDProcessingWorker]
        W6[MatchingWorker]
    end

    subgraph "Python AI Workers Pod N"
        W7[CVProcessingWorker]
        W8[JDProcessingWorker]
        W9[MatchingWorker]
    end

    subgraph "Shared Services"
        CHROMA[(ChromaDB)]
        OAI[OpenAI API]
        REDIS[(Redis Cache)]
    end

    SB1 -->|Publish| Q1
    SB2 -->|Publish| Q2
    SB3 -->|Publish| Q3

    Q1 -->|Consume| W1
    Q1 -->|Consume| W4
    Q1 -->|Consume| W7

    Q2 -->|Consume| W2
    Q2 -->|Consume| W5
    Q2 -->|Consume| W8

    Q3 -->|Consume| W3
    Q3 -->|Consume| W6
    Q3 -->|Consume| W9

    W1 -->|Publish Result| Q4
    W2 -->|Publish Result| Q4
    W3 -->|Publish Result| Q4

    Q4 -->|Consume| SB1
    Q4 -->|Consume| SB2
    Q4 -->|Consume| SB3

    W1 -->|Read/Write| CHROMA
    W1 -->|AI Calls| OAI
    W1 -->|Cache| REDIS

    W3 -->|Read/Write| CHROMA
    W3 -->|AI Calls| OAI
    W3 -->|Cache| REDIS

    Q1 -.->|Failed Messages| DLQ
    Q2 -.->|Failed Messages| DLQ
    Q3 -.->|Failed Messages| DLQ

    style MQ fill:#FFB6C1
    style Q1 fill:#FFE4B5
    style Q2 fill:#FFE4B5
    style Q3 fill:#FFE4B5
    style Q4 fill:#98FB98
    style DLQ fill:#FF6B6B
    style W1 fill:#87CEEB
    style W4 fill:#87CEEB
    style W7 fill:#87CEEB
```

### Giải thích Worker Pattern:

**Load Distribution:**

- Mỗi queue có thể có **multiple consumers** (workers)
- Messages được distribute **round-robin** hoặc **fair dispatch** (worker nào rảnh nhận message)
- `prefetch_count=1` đảm bảo worker chỉ xử lý 1 message tại 1 thời điểm

**Fault Tolerance:**

- Nếu Worker 1 crash giữa chừng → message được re-deliver cho Worker 4 hoặc Worker 7
- Messages được **persist to disk** (durable queues) → không mất khi broker restart
- ACK/NACK mechanism đảm bảo **at-least-once delivery**

**Auto-scaling:**

- Kubernetes HPA monitor queue depth
- Nếu `cv_processing_queue` có >100 messages → scale up thêm pods
- Nếu queue empty trong 5 phút → scale down về min replicas (2)

**Isolation:**

- Mỗi worker type (CV, JD, Matching) chạy trong separate process/container
- Crash ở CVWorker không ảnh hưởng MatchingWorker
- Có thể scale từng loại worker độc lập (nhiều CVWorker hơn JDWorker)

**Dead Letter Queue:**

- Messages failed sau 3 retries → move to DLQ
- Admin dashboard để review, manual reprocess, hoặc investigate lỗi
- Không block main queue processing

---

## 3. Cấu trúc Data Schema (core/schemas.py)

```mermaid
classDiagram
    class StructuredData {
        +str full_name
        +str email
        +str phone
        +HardSkills hard_skills
        +WorkExperience work_experience
        +ResponsibilitiesAchievements responsibilities_achievements
        +SoftSkills soft_skills
        +EducationTraining education_training
        +AdditionalFactors additional_factors
        +List~str~ skills (legacy)
        +List~str~ job_titles (legacy)
        +List~str~ degrees (legacy)
    }

    class HardSkills {
        +List~str~ programming_languages
        +List~str~ technologies_frameworks
        +List~str~ tools_software
        +List~str~ certifications
        +List~str~ industry_specific_skills
    }

    class WorkExperience {
        +float total_years
        +List~str~ job_titles
        +List~str~ industries
        +List~str~ companies
        +List~str~ company_sizes
    }

    class ResponsibilitiesAchievements {
        +List~str~ key_responsibilities
        +List~str~ achievements
        +List~str~ project_types
    }

    class SoftSkills {
        +List~str~ communication_teamwork
        +List~str~ leadership_management
        +List~str~ problem_solving
        +List~str~ adaptability
    }

    class EducationTraining {
        +List~str~ degrees
        +List~str~ majors
        +List~str~ universities
        +List~str~ additional_courses
    }

    class AdditionalFactors {
        +List~str~ languages
        +str availability
        +bool relocation_willingness
        +bool travel_willingness
        +str expected_salary
    }

    class ProcessResponse {
        +str doc_id
        +StructuredData structured_data
    }

    class ScoreResponse {
        +float total_score
        +ScoreBreakdown breakdown
    }

    class ScoreBreakdown {
        +float overall_semantic
        +float skill_match
        +float job_title_match
        +float education_cert_match
    }

    StructuredData *-- HardSkills
    StructuredData *-- WorkExperience
    StructuredData *-- ResponsibilitiesAchievements
    StructuredData *-- SoftSkills
    StructuredData *-- EducationTraining
    StructuredData *-- AdditionalFactors

    ProcessResponse *-- StructuredData
    ScoreResponse *-- ScoreBreakdown
```

### Giải thích chi tiết:

**StructuredData - Schema chính (lines 133-183 trong schemas.py):**

- Đây là Pydantic model chính định nghĩa cấu trúc dữ liệu cho cả CV và JD
- Được chia thành **6 categories** tương ứng với hệ thống chấm điểm:
  1. `HardSkills` (30% weight): Technical skills chia thành 5 nhóm con
  2. `WorkExperience` (25% weight): Kinh nghiệm làm việc, job titles, industries
  3. `ResponsibilitiesAchievements` (15% weight): Nhiệm vụ, thành tích
  4. `SoftSkills` (10% weight): 4 nhóm soft skills
  5. `EducationTraining` (5% weight): Học vấn, chuyên ngành
  6. `AdditionalFactors` (15% weight): Ngôn ngữ, availability, relocation
- **Legacy fields** (skills, job_titles, degrees) được giữ lại để backward compatibility

**HardSkills - Category quan trọng nhất (lines 5-26):**

- `programming_languages`: Python, Java, C++, JavaScript, ...
- `technologies_frameworks`: React, Django, TensorFlow, Docker, Kubernetes, ...
- `tools_software`: Git, Jira, VS Code, Figma, ...
- `certifications`: AWS Certified, PMP, CKA, ...
- `industry_specific_skills`: Real-time systems, HIPAA compliance, Financial modeling, ...

**Tại sao chia nhỏ thành 5 sub-categories?**

- Áp dụng **weighted scoring** (lines 138-144 trong scoring_service_new.py): programming_languages (2.0), frameworks (1.5), tools (1.0), certs (1.2), industry (1.3)
- Core skills (programming) quan trọng hơn supporting tools
- Certifications cho thấy commitment và formal training

**WorkExperience - Đánh giá kinh nghiệm (lines 29-51):**

- `total_years`: Số năm kinh nghiệm (float để xử lý "2.5 years")
- `job_titles`: Software Engineer, Senior Data Scientist, Product Manager, ...
- `industries`: Fintech, Healthcare, E-commerce, ...
- `companies`: Google, startup XYZ, ...
- `company_sizes`: Startup (<50), SME (50-500), Enterprise (>500)

**ResponsibilitiesAchievements - Đánh giá chi tiết công việc (lines 53-67):**

- `key_responsibilities`: "Led team of 5 engineers", "Designed microservices architecture", ...
- `achievements`: "Reduced latency by 40%", "Increased user engagement 2x", ...
- `project_types`: Web applications, Mobile apps, Data pipelines, ML models, ...

**SoftSkills - Skills khó đo lường (lines 69-87):**

- Thường không được ghi rõ trong CV nên có **fallback score 0.5** (line 268 trong scoring_service_new.py)
- Chia thành 4 nhóm để semantic matching chính xác hơn
- Ví dụ: "Team player", "Excellent communication" → `communication_teamwork`

**EducationTraining - Nền tảng học thuật (lines 89-107):**

- `degrees`: Bachelor, Master, PhD, ...
- `majors`: Computer Science, Data Science, Software Engineering, ...
- `universities`: MIT, Stanford, PTIT, ...
- `additional_courses`: Coursera certificates, bootcamps → **bonus 20%** (line 292 trong scoring_service_new.py)

**AdditionalFactors - Yếu tố phụ trợ (lines 109-131):**

- `languages`: ["English: Fluent", "Vietnamese: Native", "Japanese: Basic"]
- `availability`: "Immediate", "1 month notice", "2 months"
- `relocation_willingness`: True/False → quan trọng nếu JD yêu cầu
- `expected_salary`: Optional, để tham khảo (không ảnh hưởng matching score)

**API Response Models:**

- `ProcessResponse`: Trả về sau khi process CV/JD, chứa `doc_id` (UUID) và `structured_data`
- `ScoreResponse`: Trả về sau matching, chứa `total_score` (0-1) và `breakdown` (điểm từng category)
- `ScoreBreakdown`: Legacy structure, hiện tại sử dụng dict với 6 keys (hard_skills, work_experience, ...)

**Validation với Pydantic:**

- Tự động validate types (str, List[str], float, bool)
- `Field(default_factory=list)` để empty list nếu không có data
- `Optional[...]` cho nullable fields
- Model có thể serialize/deserialize JSON dễ dàng với `.model_dump()` và `.model_validate()`

---

## 4. Hệ thống Chấm điểm 6 Hạng mục (scoring_service_new.py)

```mermaid
graph TB
    subgraph "EnhancedScoringService"
        START[calculate_enhanced_match_score]

        START --> CHECK[_check_new_structure]
        CHECK --> CALC[_calculate_detailed_scores]

        subgraph "6 Categories with Weights"
            CALC --> HS[_score_hard_skills<br/>Weight: 30%]
            CALC --> WE[_score_work_experience<br/>Weight: 25%]
            CALC --> RS[_score_responsibilities<br/>Weight: 15%]
            CALC --> SS[_score_soft_skills<br/>Weight: 10%]
            CALC --> ED[_score_education<br/>Weight: 5%]
            CALC --> AF[_score_additional_factors<br/>Weight: 15%]
        end

        HS --> TOTAL[Calculate total_score]
        WE --> TOTAL
        RS --> TOTAL
        SS --> TOTAL
        ED --> TOTAL
        AF --> TOTAL

        TOTAL --> ANALYSIS[_generate_detailed_analysis]
        ANALYSIS --> RESULT[Return Result]
    end

    subgraph "Scoring Logic Details"
        HS --> HS1[Group skills by category<br/>programming, frameworks, tools, certs]
        HS1 --> HS2[Apply internal weights<br/>2.0, 1.5, 1.0, 1.2, 1.3]
        HS2 --> HS3[Batch embeddings]
        HS3 --> HS4[Cosine similarity matrix]
        HS4 --> HS5[Max similarity per JD skill]
        HS5 --> HS6[Weighted average]

        WE --> WE1[Job title match: 40%]
        WE --> WE2[Industry match: 30%]
        WE --> WE3[Years of experience: 30%<br/>Proportional if less]

        RS --> RS1[Key responsibilities: 60%]
        RS --> RS2[Achievements bonus: 20%]
        RS --> RS3[Project types: 20%]

        SS --> SS1[Communication/Teamwork]
        SS --> SS2[Leadership/Management]
        SS --> SS3[Problem Solving]
        SS --> SS4[Adaptability]
        SS --> SS5[Fallback 0.5 if CV empty but JD requires]

        ED --> ED1[Degrees: 50%]
        ED --> ED2[Majors: 30%]
        ED --> ED3[Additional courses bonus: 20%]

        AF --> AF1[Languages: 40%]
        AF --> AF2[Availability: 30%]
        AF --> AF3[Relocation willingness: 30%]
    end

    style HS fill:#FF6B6B
    style WE fill:#4ECDC4
    style RS fill:#45B7D1
    style SS fill:#96CEB4
    style ED fill:#FFEAA7
    style AF fill:#DFE6E9
    style TOTAL fill:#6C5CE7
```

### Giải thích chi tiết:

**EnhancedScoringService - Core Scoring Engine (lines 11-398 trong scoring_service_new.py):**

**Trọng số 6 categories (lines 32-39):**

```python
{
    "hard_skills": 0.30,          # 30% - Quan trọng nhất
    "work_experience": 0.25,       # 25% - Kinh nghiệm thực tế
    "responsibilities": 0.15,      # 15% - Chi tiết công việc
    "soft_skills": 0.10,           # 10% - Khó đo lường
    "education": 0.05,             # 5% - Nền tảng
    "additional_factors": 0.15     # 15% - Logistics factors
}
```

Tổng = 100%, đảm bảo final score trong khoảng [0, 1]

**Pipeline chấm điểm (lines 41-76):**

1. `_check_new_structure()`: Verify data có đủ 6 categories, throw error nếu thiếu
2. `_calculate_detailed_scores()`: Gọi 6 scoring methods song song
3. Weighted sum: `Σ(score_i × weight_i)`
4. `_generate_detailed_analysis()`: Phân tích strengths/gaps/recommendations

**Hard Skills Scoring - Chi tiết nhất (lines 124-179):**

- **Internal weights**: programming (2.0), frameworks (1.5), tools (1.0), certs (1.2), industry (1.3)
- **Batch embeddings**: Gọi OpenAI 1 lần cho tất cả skills (lines 153-159) → tối ưu performance
- **Cosine similarity matrix**: JD skills × CV skills
- **Max matching**: Mỗi JD skill lấy CV skill giống nhất (line 168)
- **Weighted average**: Nhân với internal weights, chia cho tổng weights
- **Fallback**: Nếu embedding fails → `_simple_match_score` (exact string matching, lines 353-364)

**Work Experience Scoring - 3 thành phần (lines 181-214):**

- **Job titles (40%)**: Semantic match với `_semantic_list_match()` (lines 187-190)
  - "Software Engineer" vs "Senior SWE" → similarity ~0.85
- **Industry (30%)**: Simple match (Fintech = Fintech) (lines 193-197)
- **Years (30%)**: Proportional scoring (lines 200-206)
  - CV: 3 years, JD requires: 5 years → score = 3/5 = 0.6
  - CV: 7 years, JD requires: 5 years → score = min(1.0, 7/5) = 1.0

**Responsibilities Scoring - Đánh giá công việc (lines 216-246):**

- **Key responsibilities (60%)**: Semantic match các nhiệm vụ chính
- **Achievements (20%)**: Bonus nếu CV có achievements dù JD không yêu cầu → điểm 1.0
- **Project types (20%)**: Simple match loại dự án

**Soft Skills Scoring - Fallback logic (lines 248-269):**

- Gom 4 categories thành 1 list
- Semantic match giữa CV và JD
- **Fallback 0.5**: Nếu CV không ghi soft skills nhưng JD yêu cầu → không cho 0.0 (quá harsh)

**Education Scoring - Thấp nhất (lines 271-298):**

- **Degrees (50%)**: Bachelor, Master, PhD → simple match
- **Majors (30%)**: Computer Science vs Software Engineering → semantic match
- **Additional courses (20%)**: Nếu có thêm khóa học → bonus 1.0 × 0.2 = 0.2 điểm

**Additional Factors Scoring - Logistics (lines 300-330):**

- **Languages (40%)**: Match required languages
- **Availability (30%)**: "Immediate" > "1 month" → score 1.0 vs 0.7
- **Relocation (30%)**: Boolean match (JD requires = CV willing → 1.0)

**Detailed Analysis Generation (lines 366-397):**

- **Strengths**: Số lượng technical skills, có achievements, ...
- **Gaps**: Missing skills (lấy 5 skills đầu tiên)
- **Recommendations**: "Consider acquiring: Docker, Kubernetes, CI/CD"

**Performance & Robustness:**

- Try-except ở mỗi scoring method
- Fallback sang simple matching nếu embedding fails
- Batch embeddings giảm số lần gọi OpenAI API
- Response time: 2-5 giây (phụ thuộc số skills cần embed)

---

## 5. Chi tiết Logic Chấm điểm Hard Skills

```mermaid
flowchart TD
    START[Start _score_hard_skills] --> COLLECT[Collect skills from 5 categories]

    COLLECT --> CAT1[Programming Languages<br/>Weight: 2.0]
    COLLECT --> CAT2[Technologies/Frameworks<br/>Weight: 1.5]
    COLLECT --> CAT3[Tools/Software<br/>Weight: 1.0]
    COLLECT --> CAT4[Certifications<br/>Weight: 1.2]
    COLLECT --> CAT5[Industry Skills<br/>Weight: 1.3]

    CAT1 --> CHECK_JD{JD skills empty?}
    CAT2 --> CHECK_JD
    CAT3 --> CHECK_JD
    CAT4 --> CHECK_JD
    CAT5 --> CHECK_JD

    CHECK_JD -->|Yes| RETURN1[Return 1.0]
    CHECK_JD -->|No| CHECK_CV{CV skills empty?}

    CHECK_CV -->|Yes| RETURN0[Return 0.0]
    CHECK_CV -->|No| BATCH[get_embeddings_batch<br/>all CV + JD skills]

    BATCH --> SPLIT[Split embeddings:<br/>cv_embeddings, jd_embeddings]
    SPLIT --> COSINE[cosine_similarity<br/>jd_embeddings vs cv_embeddings]

    COSINE --> MATRIX[Similarity Matrix<br/>jd_skills × cv_skills]
    MATRIX --> MAX[Get max similarity<br/>for each JD skill]

    MAX --> WEIGHT[Multiply by JD skill weights]
    WEIGHT --> SUM[Sum weighted similarities /<br/>Sum of weights]

    SUM --> CLAMP["Clamp to range 0.0 - 1.0"]
    CLAMP --> RETURN[Return score]

    BATCH -.->|Exception| FALLBACK[_simple_match_score<br/>Exact string matching]
    FALLBACK --> RETURN
```

### Giải thích chi tiết:

**Luồng xử lý \_score_hard_skills() - Method phức tạp nhất (lines 124-179 trong scoring_service_new.py):**

**Step 1: Collect & Weight Skills (lines 128-145)**

```python
skill_categories = [
    ("programming_languages", 2.0),      # Core skills - weight cao nhất
    ("technologies_frameworks", 1.5),    # Frameworks quan trọng
    ("tools_software", 1.0),             # Tools ít quan trọng hơn
    ("certifications", 1.2),             # Certifications shows commitment
    ("industry_specific_skills", 1.3)    # Domain knowledge
]
```

- Mỗi skill được gán weight dựa trên importance
- Ví dụ: Python (2.0) quan trọng hơn Git (1.0)

**Step 2: Edge Cases (lines 146-149)**

- Nếu JD không yêu cầu skills → return 1.0 (perfect match)
- Nếu CV không có skills nhưng JD yêu cầu → return 0.0 (no match)

**Step 3: Batch Embeddings (lines 153-162)**

```python
all_skills = cv_skill_names + jd_skill_names
embeddings = self.embedding_service.get_embeddings_batch(all_skills)
```

- Gộp tất cả skills thành 1 list
- Gọi OpenAI API **1 lần duy nhất** (thay vì N lần) → tiết kiệm thời gian và chi phí
- Ví dụ: ["Python", "Java", "React", "Docker", ...] → [[emb1], [emb2], [emb3], [emb4], ...]

**Step 4: Split Embeddings (line 161-162)**

```python
cv_embeddings = embeddings[:len(cv_skill_names)]   # First N embeddings
jd_embeddings = embeddings[len(cv_skill_names):]   # Remaining embeddings
```

**Step 5: Cosine Similarity Matrix (line 165)**

```python
similarity_matrix = cosine_similarity(jd_embeddings, cv_embeddings)
```

- Matrix kích thước: `(num_jd_skills × num_cv_skills)`
- Ví dụ:

```
              Python  Java  React  Docker
Django        0.65    0.32  0.15   0.10
FastAPI       0.72    0.28  0.18   0.12
PostgreSQL    0.35    0.30  0.10   0.45
```

**Step 6: Max Similarity Per JD Skill (line 168)**

```python
max_similarities = np.max(similarity_matrix, axis=1)
```

- Mỗi JD skill lấy CV skill match nhất
- Django → Python (0.65), FastAPI → Python (0.72), PostgreSQL → Docker (0.45)

**Step 7: Weighted Average (lines 169-172)**

```python
weighted_similarities = max_similarities * jd_weights
score = sum(weighted_similarities) / sum(jd_weights)
```

- Nhân với weights: Django (2.0), FastAPI (1.5), PostgreSQL (1.0)
- Tính weighted average
- Clamp vào [0.0, 1.0]

**Step 8: Exception Handling (lines 174-179)**

- Nếu OpenAI API fails (network error, rate limit, ...)
- Fallback sang `_simple_match_score`: exact string matching (lowercase)
- Đảm bảo hệ thống luôn trả về kết quả

**Ví dụ thực tế:**

**CV Skills:**

- Python (weight 2.0)
- Django (weight 1.5)
- PostgreSQL (weight 1.0)
- Git (weight 1.0)

**JD Requirements:**

- Python (weight 2.0)
- FastAPI (weight 1.5)
- Redis (weight 1.3)
- Docker (weight 1.0)

**Matching:**

1. Python → Python: similarity = 1.0 (exact)
2. FastAPI → Django: similarity = 0.75 (similar frameworks)
3. Redis → PostgreSQL: similarity = 0.60 (both databases)
4. Docker → Git: similarity = 0.30 (both dev tools but different)

**Score Calculation:**

```
weighted_sum = (1.0×2.0 + 0.75×1.5 + 0.60×1.3 + 0.30×1.0) = 4.205
total_weight = (2.0 + 1.5 + 1.3 + 1.0) = 5.8
final_score = 4.205 / 5.8 = 0.725 (72.5%)
```

**Tại sao không dùng simple exact matching?**

- "FastAPI" vs "Fast API" → exact match fails
- "Kubernetes" vs "K8s" → exact match fails
- Semantic similarity giải quyết typos, abbreviations, synonyms

---

## 6. Service Dependencies

```mermaid
graph LR
    subgraph "API Layer"
        MAIN[main.py]
    end

    subgraph "Services"
        PS[ParserService]
        SS[StructuringService]
        ES[EmbeddingService]
        VS[VectorStoreService]
        SC[ScoringService]
        ESC[EnhancedScoringService]
    end

    subgraph "Core"
        CFG[config.py]
        SCH[schemas.py]
    end

    subgraph "External"
        OAI_CLIENT[OpenAI Client]
        CHROMA[ChromaDB Client]
    end

    MAIN --> PS
    MAIN --> SS
    MAIN --> ES
    MAIN --> VS
    MAIN --> SC

    SS --> OAI_CLIENT
    ES --> OAI_CLIENT

    SC --> ESC
    SC --> ES
    ESC --> ES

    VS --> CHROMA

    MAIN --> CFG
    MAIN --> SCH
    SS --> SCH

    CFG -.->|settings.OPENAI_API_KEY| OAI_CLIENT

    style MAIN fill:#4A90E2
    style OAI_CLIENT fill:#FFA500
    style CHROMA fill:#50C878
```

### Giải thích chi tiết:

**Dependency Injection Pattern:**

- `main.py` khởi tạo tất cả services với dependencies (lines 23-31)
- `OpenAI Client` được inject vào `StructuringService` và `EmbeddingService`
- `ChromaDB Client` được khởi tạo trong `VectorStoreService.__init__()`
- Services độc lập, dễ test với mocking

**Service Orchestration:**

- `main.py` (API Layer) orchestrate workflow: parse → structure → embed → store
- Mỗi service có single responsibility:
  - `ParserService`: File I/O only
  - `StructuringService`: OpenAI GPT-4o-mini calls only
  - `EmbeddingService`: OpenAI embeddings calls only
  - `VectorStoreService`: ChromaDB operations only
  - `ScoringService`: Public interface
  - `EnhancedScoringService`: Scoring logic implementation

**Scoring Service Hierarchy:**

- `ScoringService` là wrapper (lines 7-37 trong scoring_service.py)
- Delegate sang `EnhancedScoringService` cho actual logic
- Tách biệt public API và implementation → dễ thay đổi scoring algorithm

**Config Management:**

- `config.py` sử dụng Pydantic Settings (lines 6-13 trong config.py)
- Load từ `config.env` file
- `settings.OPENAI_API_KEY` được inject vào OpenAI client
- Environment variables: `OPENAI_API_KEY` (required)

**Schema Usage:**

- `schemas.py` định nghĩa Pydantic models
- `StructuringService` sử dụng schema để generate prompt (line 33 trong structuring_service.py)
- API endpoints sử dụng schema cho request/response validation

**External Dependencies:**

- **OpenAI Client**: Shared giữa StructuringService và EmbeddingService để reuse connection pooling
- **ChromaDB Client**: PersistentClient với `./chroma_db/` path, auto-persist data

**Tại sao tách services?**

- **Testability**: Mock từng service riêng biệt
- **Maintainability**: Thay đổi 1 service không ảnh hưởng services khác
- **Scalability**: Có thể tách services thành separate microservices nếu cần
- **Reusability**: `EmbeddingService` được dùng bởi cả API và ScoringService

---

## 7. Data Flow - Message Queue Pattern (End-to-End)

```mermaid
flowchart TD
    START[User uploads CV PDF/DOCX] --> UPLOAD[Spring Boot receives file]

    UPLOAD --> VALIDATE[Validate & Save to storage]
    VALIDATE --> TASK[Generate task_id]
    TASK --> PUBLISH[Publish message to queue]
    PUBLISH --> RETURN[Return 202 Accepted + task_id]

    RETURN --> WORKER_POLL[Worker polls queue]
    WORKER_POLL --> CONSUME[Consume message]
    CONSUME --> PARSE[ParserService.parse_file]

    PARSE --> PDF{File type?}
    PDF -->|PDF| PARSE_PDF[pdfplumber.open<br/>extract_text per page]
    PDF -->|DOCX| PARSE_DOCX[python-docx Document<br/>extract paragraphs]

    PARSE_PDF --> CLEAN[_clean_text<br/>Remove extra whitespace]
    PARSE_DOCX --> CLEAN

    CLEAN --> TEXT[Raw text content]
    TEXT --> STRUCT[StructuringService.get_structured_data]

    STRUCT --> PROMPT[Generate system_prompt<br/>+ user_message from schema]
    PROMPT --> GPT[OpenAI GPT-4o-mini<br/>response_format: json_object<br/>temperature: 0.1]

    GPT --> JSON[Structured JSON]
    JSON --> DUMP1[Save to io_dump/prompts/<br/>io_dump/responses/]

    TEXT --> EMBED[EmbeddingService.get_embedding]
    EMBED --> OPENAI_EMB[OpenAI text-embedding-3-small]
    OPENAI_EMB --> VECTOR[1536-dim vector]

    JSON --> UUID[Generate UUID cv_id]
    VECTOR --> UUID
    UUID --> STORE[VectorStoreService.add_document]

    STORE --> SANITIZE[Sanitize metadata<br/>JSON serialize lists/dicts]
    SANITIZE --> CHROMA[ChromaDB cv_collection.add<br/>embedding + metadata]

    CHROMA --> PUBLISH_RESULT[Publish result to<br/>result_notification_queue]
    PUBLISH_RESULT --> SB_CONSUME[Spring Boot consumes result]
    SB_CONSUME --> SAVE_DB[Save cv_id to database]
    SAVE_DB --> NOTIFY[WebSocket notification to Frontend]

    NOTIFY --> MATCH_REQUEST[User requests matching]
    MATCH_REQUEST --> PUBLISH_MATCH[Publish to matching_request_queue]
    PUBLISH_MATCH --> WORKER_MATCH[MatchingWorker consumes]

    WORKER_MATCH --> LOAD_CV[Load CV from ChromaDB]
    WORKER_MATCH --> LOAD_JD[Load JD from ChromaDB]

    LOAD_CV --> SCORING[ScoringService.calculate_match_score]
    LOAD_JD --> SCORING

    SCORING --> ENHANCED[EnhancedScoringService<br/>6-category scoring]

    ENHANCED --> SCORE1[_score_hard_skills 30%]
    ENHANCED --> SCORE2[_score_work_experience 25%]
    ENHANCED --> SCORE3[_score_responsibilities 15%]
    ENHANCED --> SCORE4[_score_soft_skills 10%]
    ENHANCED --> SCORE5[_score_education 5%]
    ENHANCED --> SCORE6[_score_additional_factors 15%]

    SCORE1 --> WEIGHTED[Weighted sum]
    SCORE2 --> WEIGHTED
    SCORE3 --> WEIGHTED
    SCORE4 --> WEIGHTED
    SCORE5 --> WEIGHTED
    SCORE6 --> WEIGHTED

    WEIGHTED --> ANALYSIS[Generate detailed_analysis<br/>strengths, gaps, recommendations]
    ANALYSIS --> PUBLISH_MATCH_RESULT[Publish match result to queue]
    PUBLISH_MATCH_RESULT --> SB_CONSUME_MATCH[Spring Boot consumes match result]
    SB_CONSUME_MATCH --> SAVE_MATCH[Save matching result to DB]
    SAVE_MATCH --> NOTIFY_MATCH[WebSocket notification with score]
    NOTIFY_MATCH --> FINAL[Frontend displays result<br/>Radar chart + recommendations]

    style START fill:#E8F5E9
    style FINAL fill:#C8E6C9
    style GPT fill:#FFF3E0
    style OPENAI_EMB fill:#FFF3E0
    style CHROMA fill:#E1F5FE
    style PUBLISH fill:#FFB6C1
    style WORKER_POLL fill:#87CEEB
    style PUBLISH_RESULT fill:#98FB98
    style NOTIFY fill:#FFD700
```

### Giải thích chi tiết:

**Complete Pipeline - Từ File đến Matching Score:**

**Phase 1: Upload & Queue Submission (Synchronous - Spring Boot)**

1. User upload CV file qua Frontend
2. Spring Boot validate file (type, size, MIME, virus scan)
3. Save file to shared storage (NFS mount / S3) accessible by workers
4. Generate `task_id` (UUID) for tracking
5. Publish message to `cv_processing_queue`: `{"task_id": "...", "file_path": "...", "user_id": "..."}`
6. **Return 202 Accepted immediately** (response time <100ms)
7. Frontend shows "Processing..." state, lắng nghe WebSocket cho notification

**Phase 2: Worker Polling & Message Consumption (Asynchronous - Python Worker)**

8. CVProcessingWorker continuously polls `cv_processing_queue` với `prefetch_count=1`
9. Worker consumes message, extract `task_id`, `file_path`
10. Load file từ shared storage
11. `ParserService.parse_file()`: pdfplumber/python-docx extract text
12. `_clean_text()` normalize whitespace

**Phase 3: AI Processing (Async - Worker + OpenAI)**

13. `StructuringService.get_structured_data()`:
    - Generate prompt từ Pydantic schema
    - Call GPT-4o-mini (`temperature=0.1`, `response_format=json_object`)
    - Extract 6 categories
    - Log to `io_dump/` với timestamp
14. `EmbeddingService.get_embedding()`:
    - Call OpenAI `text-embedding-3-small`
    - Return 1536-dim vector

**Phase 4: Storage & Result Publishing (Async - Worker)**

15. Generate `cv_id` (UUID)
16. `VectorStoreService.add_document()`:
    - Sanitize metadata (JSON serialize)
    - Save to ChromaDB `cv_collection`
17. Publish result message to `result_notification_queue`:
    ```json
    {
      "task_id": "...",
      "cv_id": "...",
      "status": "completed",
      "processing_time_ms": 8500
    }
    ```
18. ACK original message (processing success)

**Phase 5: Result Delivery (Async - Spring Boot)**

19. Spring Boot consumes message từ `result_notification_queue`
20. Save `cv_id` và metadata vào PostgreSQL
21. Update task status table: `task_id` → `completed`
22. **Send WebSocket/SSE notification** tới Frontend: `{task_id, cv_id, status: "completed"}`
23. Frontend hides loading, shows "CV processed successfully", enables matching button

**Phase 6: Matching Request (Async - Same Pattern)**

24. User click "Match with JD" → Spring Boot publish to `matching_request_queue`
25. Return 202 Accepted với `match_task_id`
26. MatchingWorker consumes, loads CV/JD từ ChromaDB
27. 6-category scoring (as detailed in section 4)

**Phase 7: Scoring Execution (Async - MatchingWorker)**

28. EnhancedScoringService tính điểm 6 categories:
    - Hard Skills (30%): Batch embed, cosine similarity matrix
    - Work Experience (25%): Job title + industry + years
    - Responsibilities (15%): Tasks + achievements + projects
    - Soft Skills (10%): Semantic match với fallback
    - Education (5%): Degrees + majors + courses
    - Additional Factors (15%): Languages + availability
29. Weighted sum: `Σ(score_i × weight_i)`
30. Generate detailed_analysis: strengths, gaps, recommendations

**Phase 8: Match Result Publishing (Async - Worker)**

31. Publish to `result_notification_queue`:
    ```json
    {
      "match_task_id": "...",
      "total_score": 0.745,
      "category_scores": {...},
      "detailed_analysis": {...},
      "status": "completed"
    }
    ```
32. ACK matching request message

**Phase 9: Final Delivery (Async - Spring Boot → Frontend)**

33. Spring Boot consumes match result
34. Save to database (matching_results table)
35. Send WebSocket notification với full result
36. Frontend displays:
    - Total score với color coding
    - Radar chart 6 categories
    - Detailed recommendations
    - Action buttons (Accept/Reject/Interview)

**Benefits of Message Queue Pattern:**

- **User Experience**: Frontend response <100ms vs 10s blocking
- **Scalability**: Workers auto-scale 2→10 instances based on queue depth
- **Reliability**: Messages persist, auto-retry 3 times, DLQ for failed
- **Throughput**: Xử lý 100+ CVs đồng thời (vs 10-20 synchronous)
- **Cost Optimization**: Workers scale down to 0 when idle (serverless pattern)

**Performance Comparison:**

| Metric            | Synchronous REST | Async Message Queue       |
| ----------------- | ---------------- | ------------------------- |
| API Response Time | 5-10 seconds     | <100ms (202)              |
| Processing Time   | 5-10 seconds     | 5-10 seconds (background) |
| Max Concurrent    | 20-50 (threads)  | 1000+ (workers)           |
| User Waiting      | Yes (blocking)   | No (notification)         |
| Retry on Fail     | Manual           | Automatic (3x)            |

**Error Handling with Message Queue:**

- **Transient Errors** (network timeout): Auto-retry với exponential backoff
- **Permanent Errors** (invalid file): Move to DLQ sau 3 retries
- **Worker Crash**: Message re-delivered tới worker khác
- **Queue Overflow**: Backpressure signal → scale up workers
- **Monitoring**: Prometheus metrics `queue_depth`, `processing_time`, `error_rate`

---

## 8. ChromaDB Storage Structure

```mermaid
graph TB
    subgraph "ChromaDB - ./chroma_db/"
        CLIENT[PersistentClient]

        subgraph "cv_collection"
            CV1[Document 1]
            CV2[Document 2]
            CV3[Document ...]
        end

        subgraph "jd_collection"
            JD1[Document 1]
            JD2[Document 2]
            JD3[Document ...]
        end

        CLIENT --> cv_collection
        CLIENT --> jd_collection
    end

    subgraph "Document Structure"
        DOC[Document]
        ID[id: UUID string]
        EMB[embedding: List~float~ 1536 dims]
        META[metadata: Dict]

        DOC --> ID
        DOC --> EMB
        DOC --> META

        subgraph "Metadata Fields (JSON serialized)"
            FULL[full_name: str]
            EMAIL[email: str]
            PHONE[phone: str]
            HS[hard_skills: JSON str]
            WE[work_experience: JSON str]
            RA[responsibilities_achievements: JSON str]
            SS[soft_skills: JSON str]
            ET[education_training: JSON str]
            AF[additional_factors: JSON str]
        end

        META --> FULL
        META --> EMAIL
        META --> PHONE
        META --> HS
        META --> WE
        META --> RA
        META --> SS
        META --> ET
        META --> AF
    end

    style cv_collection fill:#BBDEFB
    style jd_collection fill:#C8E6C9
```

### Giải thích chi tiết:

**ChromaDB Architecture (lines 10-21 trong vector_store.py):**

**PersistentClient Configuration:**

```python
self.client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=ChromaSettings(anonymized_telemetry=False)
)
```

- Data persist trên disk, không bị mất khi restart service
- SQLite database (`chroma.sqlite3`) lưu metadata
- HNSW index files lưu embeddings cho fast similarity search

**Two Collections:**

- **cv_collection**: Chứa tất cả CV documents
- **jd_collection**: Chứa tất cả JD documents
- Tách biệt để query và manage dễ dàng

**Document Structure:**

1. **id**: UUID string (cv_id hoặc jd_id)
   - Generated bởi Python `uuid.uuid4()`
   - Unique identifier cho mỗi document
2. **embedding**: List[float] với 1536 dimensions
   - OpenAI text-embedding-3-small output
   - Dùng cho similarity search (nếu cần top-k similar CVs/JDs)
   - Lưu dưới dạng binary trong HNSW index
3. **metadata**: Dict chứa structured data
   - **Constraint**: ChromaDB chỉ chấp nhận scalar types (str, int, float, bool)
   - **Solution**: JSON.dumps() cho nested structures (lines 48-58 trong vector_store.py)

**Metadata Serialization (lines 48-58):**

```python
for key, value in metadata.items():
    if isinstance(value, (list, dict)):
        sanitized_metadata[key] = json.dumps(value, ensure_ascii=False)
    elif value is None:
        continue  # Skip None values
    else:
        sanitized_metadata[key] = value
```

**Metadata Fields:**

- `full_name`, `email`, `phone`: Lưu trực tiếp (str)
- `hard_skills`, `work_experience`, ...: JSON string
  - Ví dụ: `'{"programming_languages": ["Python", "Java"], ...}'`

**Retrieval & Deserialization (lines 86-100):**

```python
for key, value in raw_metadata.items():
    if isinstance(value, str):
        try:
            deserialized_metadata[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            deserialized_metadata[key] = value  # Keep as string
```

- Tự động detect JSON strings và parse về dict/list
- Fallback sang plain string nếu không phải JSON

**Storage on Disk:**

```
chroma_db/
├── chroma.sqlite3                  # Metadata database
├── {collection-uuid}/
│   ├── data_level0.bin             # HNSW index
│   ├── header.bin
│   ├── length.bin
│   └── link_lists.bin
```

**Query Operations:**

- `get_document_by_id()`: O(1) lookup by UUID
- `query()`: Vector similarity search với HNSW
- `collection.count()`: Số documents trong collection

**Why ChromaDB?**

- **Lightweight**: Không cần separate vector DB server (như Milvus, Pinecone)
- **Persistent**: Data saved locally
- **Fast**: HNSW index cho nearest neighbor search
- **Python-native**: Dễ integrate với FastAPI

**Scalability:**

- Hiện tại: Single-node ChromaDB (đủ cho <100K documents)
- Tương lai: Có thể migrate sang Chroma Server Mode hoặc Pinecone/Weaviate cho distributed setup

---

## 9. IO Dump Structure - Audit Trail

```mermaid
graph TB
    subgraph "io_dump/ Directory"
        subgraph "prompts/"
            P1[prompt_20251120_015516_123591.json]
            P2[prompt_20251120_015533_107918.json]
            P3[prompt_YYYYMMDD_HHMMSS_microsec.json]
        end

        subgraph "responses/"
            R1[response_20251120_015516_123591.json]
            R2[response_20251120_015533_107918.json]
            R3[response_YYYYMMDD_HHMMSS_microsec.json]
        end

        README[README.md]
    end

    P1 -.->|Same timestamp| R1
    P2 -.->|Same timestamp| R2
    P3 -.->|Same timestamp| R3

    subgraph "Prompt File Content"
        PROMPT_CONTENT["{<br/>  system_prompt: str,<br/>  user_message: str,<br/>  json_schema: dict<br/>}"]
    end

    subgraph "Response File Content"
        RESPONSE_CONTENT["{<br/>  model: 'gpt-4o-mini',<br/>  content: str (JSON),<br/>  usage: {<br/>    prompt_tokens,<br/>    completion_tokens,<br/>    total_tokens<br/>  },<br/>  finish_reason: str<br/>}"]
    end

    P1 --> PROMPT_CONTENT
    R1 --> RESPONSE_CONTENT

    style prompts/ fill:#FFF9C4
    style responses/ fill:#C5E1A5
```

### Giải thích chi tiết:

**Purpose của IO Dump - Audit Trail & Debugging (lines 146-180 trong structuring_service.py):**

**Timestamp Format:**

- `YYYYMMDD_HHMMSS_microsec`: `20251120_015516_123591`
- Microseconds đảm bảo uniqueness ngay cả khi xử lý nhiều requests đồng thời
- Same timestamp cho prompt và response để dễ trace

**Prompt File Structure (lines 103-107):**

```json
{
  "system_prompt": "You are an expert in extracting...",
  "user_message": "Please analyze and extract...",
  "json_schema": {
    "properties": {...},
    "required": [...],
    ...
  }
}
```

- `system_prompt`: Toàn bộ instructions cho GPT-4o-mini
- `user_message`: Text content cần extract
- `json_schema`: Pydantic schema converted to JSON để trace

**Response File Structure (lines 125-134):**

```json
{
  "model": "gpt-4o-mini",
  "content": "{\"full_name\": \"...\", \"hard_skills\": {...}}",
  "usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 850,
    "total_tokens": 2100
  },
  "finish_reason": "stop"
}
```

- `model`: Actual model used (may differ if fallback)
- `content`: Raw JSON string response
- `usage`: Token consumption → cost tracking
- `finish_reason`: "stop" (normal), "length" (truncated), "content_filter"

**Use Cases:**

1. **Debugging:**

   - Nếu structured JSON không đúng → xem prompt có clear không
   - Nếu thiếu fields → kiểm tra user_message có đủ thông tin không

2. **Audit & Compliance:**

   - Trace lại tất cả LLM calls cho regulatory requirements
   - Verify không có PII leakage trong prompts

3. **Fine-tuning Dataset:**

   - Collect prompt-response pairs
   - Filter high-quality examples
   - Fine-tune custom model để giảm dependency vào OpenAI

4. **Cost Analysis:**

   - Tổng tokens consumed per day/month
   - Average tokens per CV/JD
   - Optimize prompt để giảm tokens

5. **Performance Monitoring:**
   - Nếu response chậm → check token count có quá lớn không
   - A/B test different prompts

**Auto-cleanup Strategy:**

- Hiện tại: Files tích lũy vô hạn
- Recommended: Cron job xóa files >30 ngày hoặc archive lên S3
- Encryption: Nếu chứa sensitive data → encrypt at rest

**File Sizes:**

- Prompt: ~5-10 KB (schema lớn)
- Response: ~3-8 KB (structured JSON)
- 1000 requests = ~8-18 MB

**Implementation Notes (lines 146-180):**

- Try-except around file writes → không block main flow nếu disk full
- `ensure_ascii=False` → support Unicode (Vietnamese, Chinese names)
- `indent=2` → human-readable JSON

---

## 10. Error Handling Flow

```mermaid
flowchart TD
    START[API Request] --> TRY{Try}

    TRY --> VALIDATE[Validate Input]
    VALIDATE -->|Invalid| HTTP400[HTTPException 400<br/>Bad Request]
    VALIDATE -->|Valid| PROCESS[Process Request]

    PROCESS --> SERVICE[Call Services]
    SERVICE -->|Parser Error| CATCH_PARSER[Catch: file format, missing file]
    SERVICE -->|Structuring Error| CATCH_STRUCT[Catch: OpenAI API error, JSON parse]
    SERVICE -->|Embedding Error| CATCH_EMBED[Catch: OpenAI API error]
    SERVICE -->|VectorStore Error| CATCH_VS[Catch: ChromaDB error]
    SERVICE -->|Scoring Error| CATCH_SCORE[Catch: calculation error]

    CATCH_PARSER --> HTTP500[HTTPException 500<br/>Internal Server Error]
    CATCH_STRUCT --> HTTP500
    CATCH_EMBED --> HTTP500
    CATCH_VS --> HTTP500
    CATCH_SCORE --> HTTP500

    SERVICE -->|Success| RESPONSE[Return Response]

    HTTP400 --> CLIENT[Return to Client]
    HTTP500 --> CLIENT
    RESPONSE --> CLIENT

    subgraph "Scoring Fallback"
        CATCH_SCORE -.->|Embedding fails| FALLBACK[_simple_match_score<br/>String matching]
        FALLBACK -.-> RESPONSE
    end

    subgraph "Resource Cleanup"
        PROCESS -.->|Finally| CLEANUP[Delete temp files<br/>Close connections]
    end

    style HTTP400 fill:#FFCDD2
    style HTTP500 fill:#EF9A9A
    style RESPONSE fill:#C8E6C9
    style FALLBACK fill:#FFF59D
```

### Giải thích chi tiết:

**Error Handling Strategy - Defensive Programming:**

**Level 1: Input Validation (lines 60-69, 136 trong main.py)**

- **HTTP 400 Bad Request**:
  - Empty filename
  - Invalid file extension (not .pdf or .docx)
  - Empty JD text
  - File size quá lớn (có thể thêm)
- Return immediately với descriptive error message

**Level 2: Service-level Errors (lines 115-118, 166-169, 217-220)**

```python
try:
    # Process logic
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý: {str(e)}")
```

- **Parser Errors**: File corrupt, unsupported format
- **Structuring Errors**: OpenAI API timeout, rate limit, JSON parse fails
- **Embedding Errors**: OpenAI API errors
- **VectorStore Errors**: ChromaDB connection, disk full
- **Scoring Errors**: Division by zero, missing data

**Level 3: Graceful Fallbacks (lines 174-179 trong scoring_service_new.py)**

```python
try:
    # Batch embeddings + cosine similarity
    return semantic_score
except Exception:
    # Fallback to simple string matching
    return self._simple_match_score(cv_list, jd_list)
```

- **Hard Skills**: Semantic match fails → simple exact match
- **Soft Skills**: CV empty → fallback score 0.5
- Đảm bảo luôn trả về valid score [0, 1]

**Level 4: Resource Cleanup (lines 110-113 trong main.py)**

```python
finally:
    if os.path.exists(tmp_file_path):
        os.remove(tmp_file_path)
```

- Delete temp files ngay cả khi error
- Prevent disk space leak

**Error Response Format:**

```json
{
  "detail": "Lỗi khi xử lý CV: JSON parsing failed at line 42"
}
```

- Spring Boot có thể parse và display user-friendly message

**Logging Strategy:**

- Hiện tại: Chưa có structured logging
- Recommended:
  - `structlog` hoặc `python-json-logger`
  - Log levels: INFO (normal), WARNING (fallback used), ERROR (failed)
  - Correlation ID từ Spring Boot để trace end-to-end

**Retry Logic:**

- Hiện tại: Không có retry
- Recommended:
  - `tenacity` library cho OpenAI API calls
  - Exponential backoff: 1s, 2s, 4s
  - Max 3 retries
  - Retry on: RateLimitError, Timeout

**Circuit Breaker:**

- Nếu OpenAI API down → stop calling, return cached results hoặc error ngay
- Prevent cascading failures

**Monitoring & Alerting:**

- Track error rates per endpoint
- Alert if error rate > 5% trong 5 phút
- Alert if OpenAI API latency > 10s

**Example Error Scenarios:**

1. **Corrupt PDF**:

   - pdfplumber throws error → caught in try-except → HTTP 500
   - User sees: "Không thể đọc file PDF, vui lòng thử file khác"

2. **OpenAI Rate Limit**:

   - OpenAI returns 429 → caught → HTTP 500
   - User sees: "Hệ thống đang bận, vui lòng thử lại sau"

3. **Missing Skills Data**:

   - CV has no hard_skills → scoring returns 0.0 (not error)
   - Still return valid ScoreResponse

4. **ChromaDB Connection Loss**:
   - Collection.get() fails → caught → HTTP 500
   - User sees: "Không thể load dữ liệu, vui lòng thử lại"

---

## 11. Matching Score Calculation - Detailed Formula

```mermaid
graph TB
    START[Start Scoring] --> LOAD[Load CV & JD structured_json]

    LOAD --> CAT[Calculate 6 Categories]

    CAT --> HS[Hard Skills Score<br/>30% weight]
    CAT --> WE[Work Experience Score<br/>25% weight]
    CAT --> RS[Responsibilities Score<br/>15% weight]
    CAT --> SS[Soft Skills Score<br/>10% weight]
    CAT --> ED[Education Score<br/>5% weight]
    CAT --> AF[Additional Factors Score<br/>15% weight]

    HS --> FORMULA["Total Score Formula:<br/>Sum of weighted scores"]
    WE --> FORMULA
    RS --> FORMULA
    SS --> FORMULA
    ED --> FORMULA
    AF --> FORMULA

    FORMULA --> CALC["total_score =<br/>HS*0.30 + WE*0.25 + RS*0.15 +<br/>SS*0.10 + ED*0.05 + AF*0.15"]

    CALC --> ROUND[Round to 4 decimals]
    ROUND --> RESULT[Return Result]

    subgraph "Result Structure"
        RESULT --> TOTAL[total_score: float]
        RESULT --> BREAKDOWN[category_scores: dict]
        RESULT --> WEIGHTS[category_weights: dict]
        RESULT --> ANALYSIS[detailed_analysis: dict]

        BREAKDOWN --> BS1[hard_skills: float]
        BREAKDOWN --> BS2[work_experience: float]
        BREAKDOWN --> BS3[responsibilities: float]
        BREAKDOWN --> BS4[soft_skills: float]
        BREAKDOWN --> BS5[education: float]
        BREAKDOWN --> BS6[additional_factors: float]

        ANALYSIS --> STRENGTHS[strengths: List~str~]
        ANALYSIS --> GAPS[gaps: List~str~]
        ANALYSIS --> RECS[recommendations: List~str~]
    end

    style FORMULA fill:#6C5CE7
    style CALC fill:#A29BFE
    style RESULT fill:#74B9FF
```

### Giải thích chi tiết:

**Matching Score Formula - Weighted Sum Approach (lines 64-75 trong scoring_service_new.py):**

**Step 1: Calculate Individual Scores**
Mỗi category trả về score trong khoảng [0.0, 1.0]:

```python
scores = {
    "hard_skills": 0.85,          # 85% match
    "work_experience": 0.70,      # 70% match
    "responsibilities": 0.60,     # 60% match
    "soft_skills": 0.50,          # 50% match (fallback)
    "education": 0.80,            # 80% match
    "additional_factors": 0.90    # 90% match
}
```

**Step 2: Apply Weights**

```python
weights = {
    "hard_skills": 0.30,          # 30%
    "work_experience": 0.25,      # 25%
    "responsibilities": 0.15,     # 15%
    "soft_skills": 0.10,          # 10%
    "education": 0.05,            # 5%
    "additional_factors": 0.15    # 15%
}
# Total = 1.0 (100%)
```

**Step 3: Weighted Sum**

```python
total_score = sum(scores[cat] * weights[cat] for cat in weights)
            = 0.85*0.30 + 0.70*0.25 + 0.60*0.15 + 0.50*0.10 + 0.80*0.05 + 0.90*0.15
            = 0.255 + 0.175 + 0.09 + 0.05 + 0.04 + 0.135
            = 0.745
```

**Step 4: Round to 4 Decimals**

```python
total_score = round(0.7450, 4) = 0.7450
```

**Result Structure:**

**1. total_score (float):**

- Range: [0.0, 1.0]
- Interpretation:
  - 0.9 - 1.0: Excellent match (>90%)
  - 0.8 - 0.9: Very good match (80-90%)
  - 0.7 - 0.8: Good match (70-80%)
  - 0.6 - 0.7: Fair match (60-70%)
  - < 0.6: Poor match (<60%)

**2. category_scores (dict):**

```json
{
  "hard_skills": 0.85,
  "work_experience": 0.7,
  "responsibilities": 0.6,
  "soft_skills": 0.5,
  "education": 0.8,
  "additional_factors": 0.9
}
```

- Frontend hiển thị radar chart với 6 axes
- Highlight categories có điểm thấp (< 0.6) bằng màu đỏ

**3. category_weights (dict):**

```json
{
  "hard_skills": 0.3,
  "work_experience": 0.25,
  "responsibilities": 0.15,
  "soft_skills": 0.1,
  "education": 0.05,
  "additional_factors": 0.15
}
```

- Frontend hiển thị để recruiter biết tầm quan trọng từng category
- Có thể customize weights theo từng job role (future feature)

**4. detailed_analysis (dict):**

```json
{
  "strengths": [
    "Possesses 12 technical skills",
    "Strong educational background",
    "Willing to relocate"
  ],
  "gaps": [
    "Missing skills: Docker, Kubernetes, Terraform, CI/CD, Microservices"
  ],
  "recommendations": ["Consider acquiring: Docker, Kubernetes, CI/CD"]
}
```

- Tự động generate từ CV vs JD comparison
- Giúp recruiter đưa ra quyết định và feedback cho candidate

**Why Weighted Sum?**

- **Simple**: Dễ hiểu, dễ explain cho stakeholders
- **Transparent**: Biết chính xác mỗi category đóng góp bao nhiêu
- **Tunable**: Có thể điều chỉnh weights theo feedback
- **Fair**: Không có category nào bị ignore hoàn toàn

**Alternative Approaches (not implemented):**

- **Machine Learning**: Train model trên historical data (CV, JD, hiring outcome)
  - Pros: Có thể học patterns phức tạp
  - Cons: Cần data, black box, khó explain
- **Fuzzy Logic**: Membership functions cho từng category

  - Pros: Handle uncertainty tốt
  - Cons: Phức tạp, khó tune

- **AHP (Analytic Hierarchy Process)**: Pairwise comparison cho weights
  - Pros: Rigorous methodology
  - Cons: Overkill cho use case này

**Customization Potential:**

- Recruiter có thể adjust weights theo job role:
  - Senior role: Tăng work_experience, giảm education
  - Junior role: Tăng education, giảm work_experience
  - Technical lead: Tăng soft_skills (leadership)
- Store custom weights trong JD metadata

**Validation:**

- Total score luôn trong [0.0, 1.0] vì weights sum to 1.0 và scores clamped [0, 1]
- Không có NaN hoặc Inf vì có fallback scores và zero-division checks

---

## Ghi chú

- Tất cả sơ đồ được vẽ dựa trên code thực tế trong folder `d:\Python Projects\GP`
- Các file tham chiếu:
  - `app/api/main.py` - API endpoints
  - `app/services/*.py` - Service implementations
  - `core/schemas.py` - Data models
  - `core/config.py` - Configuration
- Không có thông tin bịa đặt, tất cả đều dựa trên implementation hiện tại
- Trọng số chấm điểm: Hard Skills 30%, Work Experience 25%, Responsibilities 15%, Soft Skills 10%, Education 5%, Additional Factors 15%
