## 1. Mục tiêu và phạm vi hệ thống AI

- **Mục tiêu chính**: Cung cấp “AI Matching Backend” như một microservice độc lập phục vụ hệ thống tuyển dụng thông minh GP. Microservice này nhận yêu cầu từ backend chính (Spring Boot), tự động trích xuất, chuẩn hóa và so khớp CV – JD, trả về điểm số có giải thích để frontend hiển thị cho recruiter.
- **Năng lực cốt lõi**:
  - Nhận CV (PDF/DOCX) và JD (text/file) qua các API nội bộ để tạo hồ sơ có cấu trúc theo `core/schemas.py`.
  - Tạo embedding với OpenAI `text-embedding-3-small`, lưu trong ChromaDB (`chroma_db/`) cùng metadata phục vụ tái sử dụng, audit.
  - Tính điểm theo **6 hạng mục** dựa trên `app/services/scoring_service_new.py` (Hard Skills, Work Experience, Responsibilities, Soft Skills, Education, Additional Factors) và sinh phân tích chi tiết.
  - Hỗ trợ Spring Boot trả kết quả về frontend, đồng thời lưu log/prompt/response (`io_dump/`) để audit và fine-tune sau này.
  - Cung cấp bộ công cụ load test (`load_test_*.py`, `load_test_k6.js`, `run_load_test.*`) để đánh giá hiệu năng trước khi tích hợp chính thức.
- **Phạm vi triển khai**:
  - AI backend là một pod/service trong cụm Kubernetes, giao tiếp với Spring Boot qua REST (hoặc gRPC nội bộ) được bảo vệ bằng mTLS/JWT. Frontend chỉ tương tác với Spring Boot.
  - Lưu trữ vector, metadata tại AI backend; Spring Boot chỉ lưu kết quả tổng hợp cần thiết vào database nghiệp vụ.
  - Hệ thống hoạt động theo mô hình microservices: Spring Boot (core), AI backend, các dịch vụ hỗ trợ (auth, analytics…). AI backend phải độc lập scale, log, monitor.

## 2. Lựa chọn công nghệ (ngắn gọn)

- **Ngôn ngữ & Framework**: Python 3.11+, FastAPI (AI backend), Pydantic, Typer CLI, Pytest; Spring Boot 3.x (backend chính), React/Next (frontend).
- **AI/ML**: OpenAI GPT-4o-mini (trích xuất cấu trúc), OpenAI text-embedding-3-small (vector), NumPy + scikit-learn (cosine similarity) trong `scoring_service_new.py`.
- **Dữ liệu & Lưu trữ**: ChromaDB (vector store), thư mục `io_dump/` (prompt/response/log), PostgreSQL hoặc MinIO cho metadata bổ sung, Redis cho cache/rate limit (khuyến nghị).
- **Triển khai & Vận hành**: Docker/Kubernetes, Uvicorn/Gunicorn, GitHub Actions CI/CD, Prometheus + Grafana + Loki + Alertmanager, OpenTelemetry tracing, Spring Cloud Gateway/API Gateway nội bộ.
- **Bảo mật & Cấu hình**: `.env`, `config.env`, Vault/K8s Secret; OAuth2/OIDC do Spring Boot phát hành, xác thực JWT/mTLS giữa microservices; WAF ở lớp gateway.

## 3. Cơ sở lý thuyết và công nghệ sử dụng

### 3.1 Xử lý ngôn ngữ tự nhiên (NLP)

- **Trích xuất cấu trúc với GPT-4o-mini**: System prompt mô tả chuẩn schema; model chạy ở chế độ `response_format=json_object` để đảm bảo dữ liệu thống nhất. Tận dụng few-shot hướng dẫn và temperature thấp (0.1) để duy trì tính xác định.
- **Chuẩn hóa & làm sạch**: Parser loại bỏ ký tự thừa, chuẩn hóa khoảng trắng, tách đoạn để giảm noise trước khi gửi tới LLM.
- **Giải quyết đa ngôn ngữ**: GPT-4o-mini xử lý song ngữ; data schema sử dụng key tiếng Anh để tương thích với downstream code, đảm bảo mapping nhất quán.

### 3.2 Biểu diễn vector & tìm kiếm ngữ nghĩa

- **OpenAI text-embedding-3-small**: Vector 1,536 chiều dùng cho so khớp semantic; lựa chọn vì chi phí thấp, tốc độ cao, đủ chính xác cho matching.
- **Kho vector ChromaDB**: Lưu cặp (id, embedding, metadata). Hai collection chính `cv_collection` và `jd_collection` bảo đảm tách biệt nguồn dữ liệu, thuận tiện cho truy vấn chéo.
- **Tương đồng cosine**: Được ScoringService sử dụng làm thành phần chính của điểm tổng; hỗ trợ chuẩn hóa (min-max) để kết hợp với điểm heuristics.

### 3.3 Phân tích đặc trưng & tính điểm (theo `scoring_service_new.py`)

- **6 hạng mục & trọng số**:
  1. `hard_skills` – **30%**: gom kỹ năng theo nhóm (programming, frameworks, tools, certifications, industry skills) với trọng số nội bộ; dùng embedding batch để tạo ma trận cosine, lấy max similarity cho từng yêu cầu.
  2. `work_experience` – **25%**: kết hợp semantic match job title (40%), match industry (30%) và số năm kinh nghiệm (30%) với cơ chế “đủ thì 1.0, thiếu thì tỷ lệ”.
  3. `responsibilities` – **15%**: so khớp nhiệm vụ chính (60%), thành tích (20%) và loại dự án (20%); nếu CV liệt kê achievements → thưởng thêm.
  4. `soft_skills` – **10%**: gom các nhóm communication, leadership, problem solving, adaptability; fallback 0.5 nếu CV không ghi rõ nhưng JD có yêu cầu.
  5. `education` – **5%**: so khớp bằng cấp, chuyên ngành và khóa học bổ trợ (bonus 0.2 nếu có học thêm).
  6. `additional_factors` – **15%**: ngôn ngữ, khả dụng, willingness to relocate; mỗi yếu tố có trọng số riêng (0.4/0.3/0.3).
- **Công thức**: `total_score = Σ(score_i × weight_i)` với clamp [0,1]; output bao gồm `category_scores`, `category_weights`, `detailed_analysis` (strengths/gaps/recommendations). Lỗi embedding được fallback sang `_simple_match_score` để đảm bảo trả lời nhất quán.
- **Tích hợp**: Spring Boot lưu `category_scores` để FE hiển thị biểu đồ radar, highlight kỹ năng thiếu, gợi ý training.

### 3.4 Kiến trúc dịch vụ

- **Service Layer** (`app/services/`):
  - `parser_service.py`: đọc file (PDF/DOCX), chuẩn hóa text.
  - `structuring_service.py`: chuẩn bị prompt, gọi GPT-4o-mini, lưu log vào `io_dump/`.
  - `embedding_service.py`: wrap gọi model embedding, xử lý retry/batching.
  - `vector_store.py`: thao tác CRUD với ChromaDB.
  - `scoring_service_new.py`: orchestrate matching logic 6 hạng mục, tính điểm và giải thích.
- **API Layer** (`app/api/main.py`): FastAPI router cung cấp endpoint `/process/cv`, `/process/jd`, `/match/{cv_id}/{jd_id}`. Bao gồm upload file, trả ID, và endpoint match.
- **Core Layer** (`core/`): `config.py` đọc biến môi trường; `schemas.py` định nghĩa Pydantic models cho request/response, structured data.

### 3.5 Công cụ hỗ trợ & kiểm thử

- **Load testing**: Scripts `load_test_simple.py`, `load_test_locust.py`, `load_test_k6.js`, `load_test_ab.sh` giúp đánh giá throughput và latency; tài liệu hướng dẫn trong `LOAD_TESTING_README.md` và `QUICK_START_LOAD_TEST.md`.
- **Automation**: `run_load_test.*`, `run_demo.bat`, `run_tests.py` tạo luồng kiểm thử, demo nhanh.
- **Lưu vết**: Thư mục `io_dump/` chứa prompts/responses để debug và audit.

## 4. Phân tích & thiết kế hệ thống (chi tiết)

### 4.1 Kiến trúc tổng thể

```
┌───────────────────────────────────────────────────────────────┐
│                      Intelligent Hiring Platform              │
├───────────────────────────────────────────────────────────────┤
│ Frontend (React/Next)                                         │
│   │ REST/GraphQL                                              │
│   ▼                                                           │
│ Spring Boot Core Backend                                      │
│   • Auth, workflow, notification                              │
│   • API Gateway / BFF                                         │
│   │                                                           │
│   ├─(1) /ai/process/cv|jd   ──┐                                │
│   ├─(2) /ai/match/{cv}{jd}   │ REST internal (mTLS, JWT)      │
│   ▼                         ▼                                │
│ AI Matching Backend (FastAPI microservice)                    │
│   • Parser / Structuring / Embedding / Vector Store / Scoring │
│   • ChromaDB, Redis cache, io_dump logs                       │
│   • Calls OpenAI GPT-4o-mini + text-embedding-3-small         │
│                                                               │
│ Shared services: Observability, Secrets, Kafka/Event Bus      │
└───────────────────────────────────────────────────────────────┘
```

- Spring Boot đóng vai trò orchestrator: nhận yêu cầu từ FE, xác thực người dùng, chuẩn hóa dữ liệu, gọi AI backend và hợp nhất kết quả (kèm business logic) trước khi trả lại FE.
- AI backend độc lập scale; giao tiếp qua TLS nội bộ, rate limit và circuit breaker được cài ở Spring Boot/Spring Cloud Gateway. Các pod AI backend đọc secret OpenAI từ Vault/K8s Secret.
- ChromaDB đặt trong PVC; prompt/response ở `io_dump/` để audit. Event “matching_completed” có thể publish lên Kafka để analytics service xử lý.

### 4.2 Luồng hoạt động chi tiết (kèm sơ đồ)

#### 4.2.1 Tích hợp Spring Boot ↔ AI backend

```
FE ──(upload CV/JD)─> Spring Boot
Spring Boot:
  [1] gọi POST /ai/process/cv  → FastAPI /process/cv
  [2] gọi POST /ai/process/jd  → FastAPI /process/jd
  [3] lưu {cv_id, jd_id} trong DB
  [4] khi cần so khớp → GET /ai/match/{cv_id}/{jd_id}
AI backend trả kết quả → Spring Boot → FE
```

#### 4.2.2 Activity xử lý CV/JD

```
Start
  │
  ▼
Nhận file/text (Spring Boot đã auth, scan virus)
  │
  ▼
ParserService.parse_file() → chuẩn hóa text
  │
  ▼
StructuringService.get_structured_data():
  • Tạo system prompt từ schema Pydantic
  • Gọi GPT-4o-mini (temperature 0.1, response_format=json_object)
  • Lưu prompt/response vào io_dump
  • Validate JSON → structured_json
  │
  ▼
EmbeddingService.get_embedding()  (text-embedding-3-small)
  │
  ▼
VectorStoreService.add_document():
  • Sinh UUID (cv_id/jd_id)
  • Lưu embedding + metadata vào ChromaDB
  • Trả {id, structured_json} về Spring Boot
End
```

#### 4.2.3 Sequence chấm điểm mới (6 hạng mục)

```
Spring Boot           AI Backend              ChromaDB      OpenAI
     │ GET /match/{cv}{jd} │                     │            │
     │────────────────────►│                     │            │
     │                    │──load cv/jd────────►│            │
     │                    │◄─embeddings+meta────│            │
     │                    │  EnhancedScoringService          │
     │                    │  (nếu cần embedding batch) ─────►│
     │                    │                                 ◄│
     │                    │─> tính 6 category + analysis      │
     │                    │→ ghi log (io_dump)                │
     │◄───────────────────│ tổng điểm + breakdown             │
     │ ghi DB + broadcast │
FE ◄─ trả về kết quả từ Spring Boot
```

### 4.3 Thiết kế module

- **API Layer (`app/api/main.py`)**:
  - Endpoint nội bộ: `/health`, `/process/cv`, `/process/jd`, `/match/{cv_id}/{jd_id}`.
  - Middleware: logging theo correlation-id do Spring Boot truyền, CORS đóng, rate limit per service account, JWT validator.
  - Validation: kiểm tra MIME type, kích thước file; sanitize file name; mã lỗi rõ ràng để Spring Boot xử lý.
- **Service Layer (`app/services/`)**:
  - `parser_service.py`: trích text từ PDF/DOCX, normalize (unicode NFC, lowercase optional).
  - `structuring_service.py`: tạo system prompt, user prompt, gọi GPT-4o-mini, lưu trace `io_dump/`.
  - `embedding_service.py`: batch OpenAI embeddings, retry exponential backoff, caching tạm thời.
  - `vector_store.py`: quản lý collection `cv_collection`, `jd_collection`, hỗ trợ upsert, query vector, delete theo TTL.
  - `scoring_service_new.py`: triển khai logic 6 hạng mục, fallback simple match, sinh phân tích.
- **Core Layer (`core/`)**:
  - `config.py`: đọc ENV (OpenAI key, endpoint URL, timeouts, mTLS cert path).
  - `schemas.py`: Pydantic models cho request/response, structured JSON.
- **Edge Integration**:
  - Spring Boot cần map DTO ⇄ schema Pydantic; FE hiển thị breakdown do Spring Boot truyền trả.

### 4.4 Phi chức năng

- **Bảo mật**:
  - Chỉ Spring Boot (đã auth người dùng) mới gọi được AI backend; xác thực JWT + mTLS.
  - Secrets (OpenAI key, DB credentials) lưu trong Vault/K8s Secret; `.env` chỉ dùng local.
  - Prompt/response lưu ở `io_dump/` phải mã hóa ổ đĩa, cấu hình TTL xóa sau N ngày; ẩn data nhạy cảm trong log.
  - Tuân thủ GDPR: hỗ trợ xoá dữ liệu ứng viên theo yêu cầu (delete API).
- **Hiệu năng & khả năng mở rộng**:
  - FastAPI chạy async, kết nối HTTP keep-alive tới OpenAI; autoscale HPA theo CPU/QPS.
  - Cache embedding hoặc structured data theo hash nội dung để tránh gọi lại OpenAI.
  - Batch CLI xử lý khối lượng lớn (import CV/JD) để giảm áp lực runtime API.
  - Các script load test (Locust, k6, ab) mô phỏng traffic 100–500 RPS giúp tinh chỉnh RLIMIT và worker.
- **Quan sát & vận hành**:
  - Metrics: latency từng endpoint, tỉ lệ lỗi OpenAI, queue độ dài when calling embeddings.
  - Tracing: OpenTelemetry gắn trace-id (nhận từ Spring Boot) để theo dõi end-to-end.
  - Alerting: thiết lập ngưỡng cho error rate >2%, thời gian phản hồi >3s, drift điểm trung bình.
  - Backup: snapshot PVC của ChromaDB, đồng bộ lên object storage; logs chuyển sang Loki/ELK.
- **Quy trình phát triển**:
  - GitFlow hoặc trunk-based; CI chạy `pytest`, `ruff`/`black`, unit test scoring và integration mock OpenAI.
  - IaC bằng Helm chart; pipeline CD deploy lên môi trường dev/stage/prod với canary 10% traffic.
  - Review policy: thay đổi `scoring_service_new.py` yêu cầu QA + SME phê duyệt.

### 4.5 Khả năng mở rộng tương lai

- **Ontology nội bộ**: Chuẩn hóa skills/job title theo taxonomy riêng, đồng bộ với Spring Boot để báo cáo thống nhất.
- **Learning Loop**: Thu thập feedback recruiter (qua FE) → cập nhật prompt, trọng số, thậm chí fine-tune model.
- **Explainability nâng cao**: xuất báo cáo PDF/HTML (kèm highlights) gửi cho recruiter hoặc ứng viên.
- **Event-driven**: Publish `matching_completed`, `cv_processed` lên Kafka để BI/analytics tiêu thụ, đồng thời cập nhật dashboard thời gian thực.
- **Hybrid models**: kết hợp scoring rule-based với mô hình học sâu riêng (fine-tune BERT) để tăng độ chính xác khi data đủ lớn.

---

Tài liệu này phản ánh kiến trúc hiện tại của dự án GP dựa trên các thành phần trong repo (`app/`, `core/`, `chroma_db/`, `SYSTEM_FLOW.md`, `scoring_service_new.py`). Khi triển khai thực tế, cần đồng bộ cùng Spring Boot/FE và cập nhật khi thay đổi trọng số, mô hình, chính sách bảo mật hoặc kiến trúc microservices.
