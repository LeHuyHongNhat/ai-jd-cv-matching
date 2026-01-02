# CV-JD Matching System

Hệ thống so khớp CV và Job Description sử dụng OpenAI GPT-4o-mini và text-embedding-3-small.

## Kiến trúc

- **GPT-4o-mini**: Trích xuất và cấu trúc hóa dữ liệu từ CV/JD
- **text-embedding-3-small**: Tạo vector embeddings cho semantic matching
- **ChromaDB**: Lưu trữ vectors và metadata
- **FastAPI**: REST API để xử lý và so khớp
- **RabbitMQ**: Xử lý messages từ Spring Boot (tùy chọn)

## Cài đặt

1. Clone repository và cài đặt dependencies:

```bash
pip install -r requirements.txt
```

2. Tạo file `config.env` và thêm cấu hình:

```bash
OPENAI_API_KEY=sk-your-api-key-here

# RabbitMQ Configuration (tùy chọn, nếu sử dụng RabbitMQ)
RABBITMQ_HOST=chameleon.lmq.cloudamqp.com
RABBITMQ_USER=your-username
RABBITMQ_PASSWORD=your-password
RABBITMQ_VHOST=your-vhost
```

## Cấu trúc dự án

```
.
├── app/
│   ├── api/
│   │   └── main.py                    # FastAPI endpoints
│   ├── rabbitmq/
│   │   ├── connection.py              # RabbitMQ connection
│   │   ├── consumer.py                # Message consumer
│   │   ├── producer.py                # Message producer
│   │   └── message_handlers.py        # Message handlers
│   └── services/
│       ├── parser_service.py          # Parse PDF/DOCX
│       ├── structuring_service.py     # GPT-4o-mini structuring
│       ├── embedding_service.py       # text-embedding-3-small
│       ├── vector_store.py            # ChromaDB management
│       ├── scoring_service.py         # Public scoring interface
│       └── scoring_service_new.py     # Enhanced 6-category scoring
├── core/
│   ├── config.py                      # Settings và API keys
│   └── schemas.py                     # Pydantic models
├── rabbitmq_worker.py                 # RabbitMQ worker entry point
├── requirements.txt
├── config.env                         # Environment configuration
└── README.md
```

## Sử dụng

### 1. Khởi động FastAPI server:

```bash
uvicorn app.api.main:app --reload
```

### 2. Khởi động RabbitMQ worker (tùy chọn):

```bash
python rabbitmq_worker.py
```

## API Endpoints

### GET `/`

Trả về thông tin API và danh sách endpoints.

### POST `/process/cv`

Upload CV file (PDF hoặc DOCX) để xử lý.

**Request:**

- `file`: File CV (PDF hoặc DOCX)

**Response:**

- `doc_id`: ID của CV đã được lưu
- `structured_data`: Dữ liệu đã được cấu trúc hóa

### POST `/process/jd`

Gửi Job Description text để xử lý.

**Request:**

```json
{
  "text": "Job description text here..."
}
```

**Response:**

- `doc_id`: ID của JD đã được lưu
- `structured_data`: Dữ liệu đã được cấu trúc hóa

### GET `/match/{cv_id}/{jd_id}`

So khớp CV và JD, trả về điểm số chi tiết.

**Response:**

- `total_score`: Điểm tổng hợp (0-1)
- `breakdown`: Điểm chi tiết theo từng tiêu chí

## Hệ thống chấm điểm

Điểm tổng hợp được tính từ 6 thành phần:

1. **Hard Skills (30%)**: Semantic matching của kỹ năng kỹ thuật

   - Programming languages
   - Technologies & frameworks
   - Tools & software
   - Certifications
   - Industry-specific skills

2. **Work Experience (25%)**: Đánh giá kinh nghiệm làm việc

   - Job titles matching
   - Industry matching
   - Years of experience

3. **Responsibilities & Achievements (15%)**: Trách nhiệm và thành tựu

   - Key responsibilities
   - Achievements
   - Project types

4. **Soft Skills (10%)**: Kỹ năng mềm

   - Communication & teamwork
   - Leadership & management
   - Problem solving
   - Adaptability

5. **Education & Training (5%)**: Học vấn và đào tạo

   - Degrees
   - Majors
   - Additional courses

6. **Additional Factors (15%)**: Các yếu tố bổ sung
   - Languages
   - Availability
   - Relocation willingness

## RabbitMQ Integration

Hệ thống hỗ trợ xử lý messages từ Spring Boot qua RabbitMQ:

- **Input Queue**: `cv_processing_queue` - Nhận CV từ Spring Boot
- **Output Queue**: `cv_result_queue` - Gửi kết quả về Spring Boot
- **Exchange**: `internal_exchange` (direct type)

Xem thêm chi tiết trong `docs/RABBITMQ_INTEGRATION.md`.

## Lưu ý

- ChromaDB sẽ tạo thư mục `./chroma_db` để lưu trữ dữ liệu
- File tạm thời sẽ được tự động xóa sau khi xử lý
- Cần có OpenAI API key hợp lệ
- Cấu hình RabbitMQ là tùy chọn, chỉ cần thiết khi sử dụng worker
