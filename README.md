# CV-JD Matching System

Hệ thống so khớp CV và Job Description sử dụng OpenAI GPT-4o-mini và text-embedding-3-small.

## Kiến trúc

- **GPT-4o-mini**: Trích xuất và cấu trúc hóa dữ liệu từ CV/JD
- **text-embedding-3-small**: Tạo vector embeddings cho semantic matching
- **ChromaDB**: Lưu trữ vectors và metadata
- **FastAPI**: REST API để xử lý và so khớp

## Cài đặt

1. Clone repository và cài đặt dependencies:

```bash
pip install -r requirements.txt
```

2. Tạo file `.env` từ `.env.example` và thêm OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

## Cấu trúc dự án

```
.
├── app/
│   ├── api/
│   │   └── main.py          # FastAPI endpoints
│   └── services/
│       ├── parser_service.py      # Parse PDF/DOCX
│       ├── structuring_service.py # GPT-4o-mini structuring
│       ├── embedding_service.py  # text-embedding-3-small
│       ├── vector_store.py       # ChromaDB management
│       └── scoring_service.py    # Multi-dimensional scoring
├── core/
│   ├── config.py            # Settings và API keys
│   └── schemas.py            # Pydantic models
├── requirements.txt
├── .env.example
└── README.md
```

## Sử dụng

1. Khởi động server:

```bash
uvicorn app.api.main:app --reload
```

2. API Endpoints:

### POST `/process/cv`

Upload CV file (PDF hoặc DOCX) để xử lý.

### POST `/process/jd`

Gửi Job Description text để xử lý.

### GET `/match/{cv_id}/{jd_id}`

So khớp CV và JD, trả về điểm số chi tiết.

## Hệ thống chấm điểm

Điểm tổng hợp được tính từ 4 thành phần:

1. **Overall Semantic Score (40%)**: Cosine similarity của embeddings tổng thể
2. **Skill Match (30%)**: Semantic matching của skills
3. **Job Title Match (20%)**: Exact match của job titles
4. **Education/Cert Match (10%)**: Exact match của bằng cấp và chứng chỉ

## Lưu ý

- ChromaDB sẽ tạo thư mục `./chroma_db` để lưu trữ dữ liệu
- File tạm thời sẽ được tự động xóa sau khi xử lý
- Cần có OpenAI API key hợp lệ
