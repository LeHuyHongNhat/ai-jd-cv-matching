# Cấu trúc Dự án - CV-JD Matching System

## Tổng quan cấu trúc

```
GP/
├── app/                              # Lớp ứng dụng - Logic nghiệp vụ chính
│   ├── api/
│   │   └── main.py                   # API FastAPI
│   │
│   ├── rabbitmq/                     # Tích hợp RabbitMQ với Spring Boot
│   │   ├── connection.py             # Quản lý kết nối CloudAMQP (TLS)
│   │   ├── consumer.py               # Nhận tin nhắn từ Spring Boot
│   │   ├── producer.py               # Gửi kết quả về Spring Boot
│   │   └── message_handlers.py       # Xử lý logic nghiệp vụ
│   │
│   └── services/                     # Các dịch vụ nghiệp vụ
│       ├── parser_service.py         # Phân tích CV từ PDF/DOCX thành văn bản
│       ├── structuring_service.py    # Trích xuất dữ liệu có cấu trúc (GPT-4o-mini)
│       ├── embedding_service.py      # Tạo embedding vector (text-embedding-3-small)
│       ├── scoring_service.py        # Tính điểm cơ bản
│       └── scoring_service_new.py    # Tính điểm nâng cao theo 6 tiêu chí
│
├── core/                             # Lớp cấu hình & Schema
│   ├── config.py                     # Cấu hình (OpenAI, RabbitMQ, biến môi trường)
│   └── schemas.py                    # Mô hình dữ liệu Pydantic
│
├── input/                            # Dữ liệu mẫu
│   ├── cvs/                          # File CV mẫu (PDF)
│   └── jds/                          # File mô tả công việc mẫu (DOCX)
│
├── chroma_db/                        # Lưu trữ vector ChromaDB (tự động tạo)
├── io_dump/                          # Debug logs của OpenAI API
│
├── config.env                        # Biến môi trường (API keys, thông tin RabbitMQ)
├── requirements.txt                  # Thư viện Python cần thiết
│
└── rabbitmq_worker.py                # Điểm khởi chạy chính của RabbitMQ Worker
```

---

## Các thành phần chính

### Điểm khởi chạy

| File                 | Mô tả                                            | Cách chạy                   |
| -------------------- | ------------------------------------------------ | --------------------------- |
| `rabbitmq_worker.py` | Worker nhận tin nhắn từ Spring Boot qua RabbitMQ | `python rabbitmq_worker.py` |

### Cấu hình hệ thống

| File              | Mô tả                                  |
| ----------------- | -------------------------------------- |
| `config.env`      | Khóa API, thông tin đăng nhập RabbitMQ |
| `core/config.py`  | Nạp cấu hình từ biến môi trường        |
| `core/schemas.py` | Định nghĩa mô hình dữ liệu và xác thực |

### Tích hợp RabbitMQ (Spring Boot - Python)

| File                               | Trách nhiệm                                   |
| ---------------------------------- | --------------------------------------------- |
| `app/rabbitmq/connection.py`       | Quản lý kết nối với CloudAMQP (hỗ trợ TLS)    |
| `app/rabbitmq/consumer.py`         | Nhận tin nhắn từ hàng đợi cv_processing_queue |
| `app/rabbitmq/producer.py`         | Gửi kết quả vào hàng đợi cv_result_queue      |
| `app/rabbitmq/message_handlers.py` | Tải CV, phân tích, trích xuất và tính điểm    |

### Dịch vụ xử lý AI

| File                                  | Trách nhiệm                                     |
| ------------------------------------- | ----------------------------------------------- |
| `app/services/parser_service.py`      | Chuyển đổi PDF/DOCX thành văn bản               |
| `app/services/structuring_service.py` | Trích xuất dữ liệu có cấu trúc bằng GPT-4o-mini |
| `app/services/embedding_service.py`   | Tạo vector embedding từ văn bản                 |
| `app/services/scoring_service_new.py` | Tính điểm matching theo 6 tiêu chí              |

---

## Luồng xử lý

### Luồng xử lý RabbitMQ Worker

```
┌─────────────────────────────────────────────────────────────┐
│  1. Spring Boot gửi tin nhắn vào cv_processing_queue        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. rabbitmq_worker.py nhận tin nhắn                        │
│     - consumer.py lắng nghe hàng đợi                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. message_handlers.py xử lý                               │
│     a. Tải CV từ URL                                        │
│     b. Phân tích CV thành văn bản                           │
│     c. Trích xuất dữ liệu có cấu trúc                       │
│     d. Tạo embedding vectors                                │
│     e. Tính 6 điểm matching                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. producer.py gửi kết quả vào cv_result_queue            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Spring Boot nhận kết quả từ cv_result_queue            │
└─────────────────────────────────────────────────────────────┘
```

---

## Kiến trúc phân lớp

### Lớp ứng dụng (`app/`)

- **RabbitMQ**: Tích hợp hàng đợi tin nhắn với Spring Boot
- **Dịch vụ**: Xử lý AI (phân tích, trích xuất, embedding, chấm điểm)

### Lớp lõi (`core/`)

- **Cấu hình**: Thiết lập, biến môi trường
- **Schema**: Mô hình dữ liệu và xác thực (Pydantic)

### Lớp dữ liệu

- **ChromaDB**: Lưu trữ vector embeddings
- **I/O Dump**: Nhật ký debug các lời gọi OpenAI API

---

## Hướng dẫn triển khai

### Bước 1: Cài đặt thư viện phụ thuộc

```bash
pip install -r requirements.txt
```

### Bước 2: Cấu hình biến môi trường

Tạo file `config.env` và điền thông tin:

- `OPENAI_API_KEY`: Khóa API của OpenAI
- `RABBITMQ_*`: Thông tin đăng nhập CloudAMQP

### Bước 3: Khởi chạy RabbitMQ Worker

```bash
python rabbitmq_worker.py
```

Worker sẽ lắng nghe hàng đợi `cv_processing_queue` và xử lý tin nhắn từ Spring Boot.

---

## Lưu ý quan trọng

1. File **config.env** chứa khóa API và thông tin bảo mật - KHÔNG được commit lên Git
2. Thư mục **chroma_db/** chứa vector embeddings - Tự động tạo khi chạy
3. Thư mục **io_dump/** chứa nhật ký gọi OpenAI API - Dùng để gỡ lỗi
4. Cần cài đặt đầy đủ thư viện trong **requirements.txt** trước khi chạy

---

Cập nhật: 2025-12-17  
Tác giả: Lê Huy Hồng Nhật
