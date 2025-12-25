# Hướng dẫn chạy Demo CV-JD Matching

## Chuẩn bị

1. Đảm bảo đã cài đặt dependencies:

```bash
pip install -r requirements.txt
```

2. Đảm bảo có file `config.env` với OpenAI API key:

```env
OPENAI_API_KEY=sk-your-api-key-here
```

## Cách 1: Demo với nhiều CV

Chạy với folder chứa nhiều CV (PDF/DOCX) và 1 JD:

```bash
python demo_matching.py <đường_dẫn_folder_CV> <đường_dẫn_file_JD>
```

**Ví dụ:**

```bash
python demo_matching.py ./sample_cvs ./job_description.docx
```

### Output:

- Hiển thị chi tiết từng bước xử lý cho mỗi CV
- Hiển thị chi tiết từng bước xử lý JD
- Hiển thị kết quả matching cho từng CV
- Hiển thị ranking tất cả CVs theo điểm số
- Lưu kết quả ra file JSON: `matching_results_YYYYMMDD_HHMMSS.json`

## Cách 2: Demo đơn giản (1 CV + 1 JD)

Chạy với 1 CV và 1 JD:

```bash
python demo_simple.py <đường_dẫn_CV> <đường_dẫn_JD>
```

**Ví dụ:**

```bash
python demo_simple.py ./cv_candidate.pdf ./job_description.docx
```

## Output mẫu

```
================================================================================
CV-JD MATCHING SYSTEM DEMO
================================================================================

[INIT] Khởi tạo các services...
✓ OpenAI client initialized
✓ Parser service initialized
✓ Structuring service initialized
✓ Embedding service initialized
✓ Vector store service initialized
✓ Scoring service initialized

================================================================================
[PROCESS JD] job_description.docx
================================================================================

[STEP 1] Parsing file...
✓ Extracted 1234 characters

--- Text Preview (first 500 chars) ---
Job Description
Position: Senior Software Engineer
...

[STEP 2] Extracting structured data with GPT-4o-mini...
✓ Structured data extracted

--- Structured Data ---
{
  "skills": ["Python", "FastAPI", "React", ...],
  "job_titles": ["Senior Software Engineer"],
  ...
}

[STEP 3] Creating embedding with text-embedding-3-small...
✓ Embedding created (dimension: 1536)

[STEP 4] Storing in vector database...
✓ Stored with ID: jd_job_description_20250102_123456

================================================================================
[PROCESS CV] cv_candidate.pdf
================================================================================

[STEP 1] Parsing file...
✓ Extracted 2345 characters

--- Text Preview (first 500 chars) ---
John Doe
Email: john@example.com
...

[STEP 2] Extracting structured data with GPT-4o-mini...
✓ Structured data extracted

--- Structured Data ---
{
  "full_name": "John Doe",
  "skills": ["Python", "JavaScript", "Docker", ...],
  ...
}

[STEP 3] Creating embedding with text-embedding-3-small...
✓ Embedding created (dimension: 1536)

[STEP 4] Storing in vector database...
✓ Stored with ID: cv_candidate_20250102_123456

================================================================================
[MATCHING] cv_candidate.pdf <-> job_description.docx
================================================================================

[STEP 1] Retrieving data from vector store...
✓ Data retrieved

[STEP 2] Calculating matching scores...

--- MATCHING RESULTS ---
Total Score: 0.8542 (85.42%)

Score Breakdown:
  • Overall Semantic Similarity: 0.8234 (Weight: 40%)
  • Skill Match:                 0.9123 (Weight: 30%)
  • Job Title Match:             0.8000 (Weight: 20%)
  • Education/Cert Match:        0.9000 (Weight: 10%)

--- DETAILED COMPARISON ---

Skills:
  CV has: 15 skills
  JD requires: 10 skills
  CV Skills: Python, JavaScript, TypeScript, React, FastAPI, ...
  JD Skills: Python, FastAPI, PostgreSQL, React, Docker, ...

================================================================================
SUMMARY
================================================================================
Total CVs processed: 1
Total matches: 1
Duration: 15.34 seconds

✓ Results saved to: matching_results_20250102_123456.json

================================================================================
DEMO COMPLETED!
================================================================================
```

## Cấu trúc file kết quả JSON

File `matching_results_YYYYMMDD_HHMMSS.json` chứa:

```json
{
  "timestamp": "20250102_123456",
  "total_matches": 3,
  "results": [
    {
      "cv_name": "candidate1.pdf",
      "cv_id": "cv_candidate1_20250102_123456",
      "jd_name": "job_description.docx",
      "jd_id": "jd_job_description_20250102_123456",
      "total_score": 0.8542,
      "breakdown": {
        "overall_semantic": 0.8234,
        "skill_match": 0.9123,
        "job_title_match": 0.8000,
        "education_cert_match": 0.9000
      },
      "cv_structured": {
        "full_name": "John Doe",
        "skills": [...],
        ...
      },
      "jd_structured": {
        "skills": [...],
        ...
      }
    },
    ...
  ]
}
```

## Lưu ý

1. **Chi phí API**: Mỗi CV và JD sẽ gọi OpenAI API:

   - 1 lần GPT-4o-mini để trích xuất structured data
   - 1 lần text-embedding-3-small để tạo embedding
   - Thêm các lần gọi embedding cho skill matching

2. **Thời gian xử lý**: Phụ thuộc vào:

   - Số lượng CV
   - Độ dài văn bản
   - Tốc độ API OpenAI

3. **Database**: Dữ liệu sẽ được lưu trong `./demo_chroma_db/`

4. **Định dạng file**: Hỗ trợ PDF và DOCX

## Troubleshooting

### Lỗi "OpenAI API key not found"

- Kiểm tra file `config.env` có tồn tại và có đúng API key

### Lỗi "File not found"

- Kiểm tra đường dẫn file/folder có đúng không
- Sử dụng đường dẫn tuyệt đối nếu cần

### Lỗi parse file

- Đảm bảo file PDF/DOCX không bị hỏng
- Đảm bảo file có nội dung text (không phải scan image)
