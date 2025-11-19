# Hướng dẫn Test

## Cấu trúc Tests

```
tests/
├── __init__.py
├── conftest.py          # Pytest configuration và fixtures
├── test_data.py         # Sample data cho testing
├── test_services.py      # Unit tests cho các services
├── test_api.py          # API endpoint tests
└── test_integration.py  # Integration tests cho toàn bộ workflow
```

## Thiết lập Environment Variables

### Để chạy tests với OpenAI API key thật:

1. Tạo file `config.env` hoặc `.env` trong thư mục gốc:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

2. File này sẽ tự động được load khi chạy tests

3. **Lưu ý**: Nếu không có API key hoặc để trống, tests sẽ sử dụng mock values và test `test_real_api_call` sẽ bị skip

## Chạy Tests

### Chạy tất cả tests:

```bash
pytest tests/ -v
```

hoặc:

```bash
python run_tests.py
```

### Chạy tests cụ thể:

```bash
# Chỉ test services
pytest tests/test_services.py -v

# Chỉ test API
pytest tests/test_api.py -v

# Chỉ test integration
pytest tests/test_integration.py -v

# Chạy test với real API (cần API key trong config.env)
pytest tests/test_integration.py::TestEndToEnd::test_real_api_call -v
```

### Chạy test với coverage:

```bash
pytest tests/ --cov=app --cov=core --cov-report=html
```

## Test Categories

### 1. Unit Tests (test_services.py)

- **TestParserService**: Test parse PDF/DOCX và dọn dẹp text
- **TestStructuringService**: Test trích xuất structured data với GPT-4o-mini
- **TestEmbeddingService**: Test tạo embeddings
- **TestVectorStoreService**: Test lưu trữ và truy xuất từ ChromaDB
- **TestScoringService**: Test các phương thức tính điểm

### 2. API Tests (test_api.py)

- **TestRootEndpoint**: Test root endpoint
- **TestProcessCV**: Test POST /process/cv
- **TestProcessJD**: Test POST /process/jd
- **TestMatchCVJD**: Test GET /match/{cv_id}/{jd_id}

### 3. Integration Tests (test_integration.py)

- **TestFullWorkflow**: Test toàn bộ workflow từ upload CV -> process JD -> match
- **TestEndToEnd**: Test với real API (cần OpenAI API key thật trong config.env/.env)

## Troubleshooting

### Test bị skip mặc dù có API key trong config.env

1. Kiểm tra file `config.env` hoặc `.env` có trong thư mục gốc không
2. Đảm bảo format đúng: `OPENAI_API_KEY=sk-...` (không có dấu ngoặc kép)
3. Chạy lại tests: `pytest tests/ -v`

### Lỗi PermissionError với ChromaDB trên Windows

Đây là vấn đề phổ biến trên Windows khi ChromaDB chưa đóng connection đúng cách. Test đã được sửa để xử lý vấn đề này.

### WARNING về Pydantic

Đã được sửa bằng cách sử dụng `model_config = ConfigDict()` thay vì `class Config` (Pydantic V2).

## Lưu ý

1. **Mocking**: Hầu hết tests sử dụng mocking để tránh gọi OpenAI API thật, tiết kiệm chi phí
2. **OpenAI API Key**: Tests mặc định sử dụng mock. Để test với API thật, set `OPENAI_API_KEY` trong `config.env` hoặc `.env`
3. **ChromaDB**: Tests sử dụng temporary directories để tránh ảnh hưởng đến dữ liệu thật

## Sample Test Output

```
tests/test_services.py::TestParserService::test_clean_text PASSED
tests/test_services.py::TestEmbeddingService::test_get_embedding PASSED
tests/test_api.py::TestProcessCV::test_process_cv_success PASSED
tests/test_integration.py::TestFullWorkflow::test_full_workflow_cv_jd_matching PASSED

✅ Tất cả tests đã pass!
```
