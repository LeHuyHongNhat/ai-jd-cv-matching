# Luồng Hoạt Động của Hệ Thống CV-JD Matching

## 📋 Tổng Quan

Hệ thống CV-JD Matching sử dụng AI để so khớp CV của ứng viên với Job Description (JD), trả về điểm số chi tiết theo 6 tiêu chí.

### Công nghệ sử dụng:
- **GPT-4o-mini**: Trích xuất và cấu trúc hóa dữ liệu từ CV/JD
- **text-embedding-3-small**: Tạo vector embeddings cho semantic matching
- **ChromaDB**: Lưu trữ vectors và metadata
- **FastAPI**: REST API để xử lý và so khớp

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────┐
│                    CV-JD Matching System                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   FastAPI    │      │   Demo CLI   │                    │
│  │   (API)      │      │  (Script)    │                    │
│  └──────┬───────┘      └──────┬───────┘                    │
│         │                     │                              │
│         └──────────┬──────────┘                              │
│                    │                                          │
│         ┌──────────▼──────────┐                              │
│         │   Services Layer    │                              │
│         ├─────────────────────┤                              │
│         │ • ParserService     │                              │
│         │ • StructuringService│                              │
│         │ • EmbeddingService  │                              │
│         │ • VectorStoreService│                              │
│         │ • ScoringService    │                              │
│         └──────────┬──────────┘                              │
│                    │                                          │
│         ┌──────────▼──────────┐                              │
│         │   External APIs     │                              │
│         ├─────────────────────┤                              │
│         │ • OpenAI GPT-4o-mini │                              │
│         │ • OpenAI Embeddings │                              │
│         └──────────┬──────────┘                              │
│                    │                                          │
│         ┌──────────▼──────────┐                              │
│         │   Storage Layer     │                              │
│         ├─────────────────────┤                              │
│         │ • ChromaDB          │                              │
│         │ • io_dump/          │                              │
│         └─────────────────────┘                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Luồng Xử Lý CV

### Bước 1: Nhận Input
```
User uploads CV file (PDF/DOCX)
    ↓
FastAPI endpoint: POST /process/cv
    hoặc
Demo: process_cv(cv_path)
```

### Bước 2: Parse File → Text
```
ParserService.parse_file()
    ↓
Extract text từ PDF/DOCX
    ↓
Clean text (remove extra spaces, normalize)
    ↓
Return: text_content (string)
```

**Code:**
```python
text_content = parser_service.parse_file(cv_file_path)
```

### Bước 3: Trích Xuất Structured Data
```
StructuringService.get_structured_data()
    ↓
1. Lấy JSON schema từ Pydantic model (StructuredData)
    ↓
2. Tạo system prompt với:
   - JSON schema
   - Extraction guidelines (6 categories)
   - Rules và best practices
    ↓
3. Tạo user message với text_content
    ↓
4. Lưu prompt vào io_dump/prompts/
    ↓
5. Gọi OpenAI GPT-4o-mini API:
   - Model: gpt-4o-mini
   - Response format: json_object
   - Temperature: 0.1
    ↓
6. Lưu response vào io_dump/responses/
    ↓
7. Parse JSON response
    ↓
Return: structured_json (dict)
```

**Structured Data bao gồm:**
- `hard_skills`: Programming languages, frameworks, tools, certifications
- `work_experience`: Years, job titles, industries, companies
- `responsibilities_achievements`: Key responsibilities, achievements, projects
- `soft_skills`: Communication, leadership, problem-solving
- `education_training`: Degrees, majors, universities, courses
- `additional_factors`: Languages, availability, relocation

**Code:**
```python
structured_json = structuring_service.get_structured_data(
    text_content,
    StructuredData
)
```

### Bước 4: Tạo Embedding
```
EmbeddingService.get_embedding()
    ↓
Gọi OpenAI Embeddings API:
   - Model: text-embedding-3-small
   - Input: text_content (full text)
    ↓
Return: embedding vector (1536 dimensions)
```

**Code:**
```python
embedding = embedding_service.get_embedding(text_content)
```

### Bước 5: Lưu vào Vector Store
```
VectorStoreService.add_document()
    ↓
1. Tạo UUID cho CV
    ↓
2. Lưu vào ChromaDB:
   - Collection: "cv_collection"
   - doc_id: UUID
   - embedding: vector (1536 dims)
   - metadata: structured_json
    ↓
Return: cv_id
```

**Code:**
```python
cv_id = str(uuid.uuid4())
vector_store_service.add_document(
    collection_name="cv_collection",
    doc_id=cv_id,
    embedding=embedding,
    metadata=structured_json
)
```

### Kết Quả:
- ✅ CV được lưu trong ChromaDB với ID
- ✅ Có thể query và match sau này

---

## 🔄 Luồng Xử Lý JD

Luồng xử lý JD **tương tự** CV, nhưng có một số khác biệt:

### Khác biệt chính:

1. **Input**: 
   - CV: Upload file (PDF/DOCX)
   - JD: Text content (có thể từ file hoặc text trực tiếp)

2. **Collection**: 
   - CV → `cv_collection`
   - JD → `jd_collection`

3. **Extraction Focus**:
   - CV: Extract ALL information
   - JD: Focus on REQUIREMENTS (keywords: "required", "must have", "essential")

### Luồng:
```
1. Parse JD file → text_content
2. Extract structured data (GPT-4o-mini)
3. Create embedding (text-embedding-3-small)
4. Store in ChromaDB (jd_collection)
5. Return jd_id
```

---

## 🎯 Luồng Matching (So Khớp)

### Bước 1: Lấy Dữ Liệu
```
GET /match/{cv_id}/{jd_id}
    ↓
1. Query ChromaDB:
   - Get CV: cv_collection[cv_id]
   - Get JD: jd_collection[jd_id]
    ↓
2. Extract:
   - cv_embedding: vector
   - cv_structured_json: metadata
   - jd_embedding: vector
   - jd_structured_json: metadata
```

### Bước 2: Tính Điểm Matching
```
ScoringService.calculate_match_score()
    ↓
EnhancedScoringService.calculate_enhanced_match_score()
    ↓
Tính điểm cho 6 categories:
```

#### Category 1: Hard Skills (30%)
```
_score_hard_skills()
    ↓
1. Collect skills từ structured_json:
   - programming_languages (weight: 2.0)
   - technologies_frameworks (weight: 1.5)
   - tools_software (weight: 1.0)
   - certifications (weight: 1.2)
   - industry_specific_skills (weight: 1.3)
    ↓
2. Tạo embeddings cho tất cả skills
    ↓
3. Tính cosine similarity matrix
    ↓
4. Weighted average similarity
    ↓
Return: score (0-1)
```

#### Category 2: Work Experience (25%)
```
_score_work_experience()
    ↓
1. Job titles matching (40% weight):
   - Semantic similarity
    ↓
2. Industry matching (30% weight):
   - Exact match sau normalize
    ↓
3. Years of experience (30% weight):
   - CV years / JD required years
   - Max 1.0 if exceeds
    ↓
Return: weighted average score
```

#### Category 3: Responsibilities (15%)
```
_score_responsibilities()
    ↓
1. Key responsibilities (60% weight):
   - Semantic similarity
    ↓
2. Achievements (20% weight):
   - Having achievements = bonus
    ↓
3. Project types (20% weight):
   - Exact match
    ↓
Return: weighted average score
```

#### Category 4: Soft Skills (10%)
```
_score_soft_skills()
    ↓
1. Collect từ categories:
   - communication_teamwork
   - leadership_management
   - problem_solving
   - adaptability
    ↓
2. Semantic similarity matching
    ↓
Return: score
```

#### Category 5: Education (5%)
```
_score_education()
    ↓
1. Degrees (50% weight):
   - Exact match
    ↓
2. Majors (30% weight):
   - Semantic similarity
    ↓
3. Additional courses (20% weight):
   - Having courses = bonus
    ↓
Return: weighted average score
```

#### Category 6: Additional Factors (15%)
```
_score_additional_factors()
    ↓
1. Languages (40% weight):
   - Exact match
    ↓
2. Availability (30% weight):
   - Check immediate availability
    ↓
3. Relocation (30% weight):
   - Match willingness
    ↓
Return: weighted average score
```

### Bước 3: Tính Total Score
```
total_score = sum(
    category_score × category_weight
    for all 6 categories
)

Weights:
- hard_skills: 30%
- work_experience: 25%
- responsibilities: 15%
- soft_skills: 10%
- education: 5%
- additional_factors: 15%
```

### Bước 4: Trả Về Kết Quả
```python
{
    "total_score": 0.5926,
    "breakdown": {
        "hard_skills": 0.6486,
        "work_experience": 0.3693,
        "responsibilities": 0.5251,
        "soft_skills": 0.5984,
        "education": 0.3423,
        "additional_factors": 1.0000
    },
    "category_weights": {...},
    "detailed_analysis": {...}
}
```

---

## 📊 Sơ Đồ Luồng Hoàn Chỉnh

```
┌─────────────────────────────────────────────────────────────┐
│                    CV-JD MATCHING FLOW                      │
└─────────────────────────────────────────────────────────────┘

[INPUT]
    │
    ├─ CV File (PDF/DOCX)
    │   │
    │   ├─► Parse → Text
    │   │
    │   ├─► GPT-4o-mini → Structured Data
    │   │   ├─► Save prompt → io_dump/prompts/
    │   │   └─► Save response → io_dump/responses/
    │   │
    │   ├─► Embedding → Vector (1536 dims)
    │   │
    │   └─► Store → ChromaDB (cv_collection)
    │       └─► Return: cv_id
    │
    └─ JD File/Text
        │
        ├─► Parse → Text (if file)
        │
        ├─► GPT-4o-mini → Structured Data
        │   ├─► Save prompt → io_dump/prompts/
        │   └─► Save response → io_dump/responses/
        │
        ├─► Embedding → Vector (1536 dims)
        │
        └─► Store → ChromaDB (jd_collection)
            └─► Return: jd_id

[MATCHING]
    │
    ├─► Get CV & JD from ChromaDB
    │
    ├─► Calculate Scores (6 categories):
    │   ├─► Hard Skills (30%)
    │   ├─► Work Experience (25%)
    │   ├─► Responsibilities (15%)
    │   ├─► Soft Skills (10%)
    │   ├─► Education (5%)
    │   └─► Additional Factors (15%)
    │
    └─► Calculate Total Score
        └─► Return: ScoreResponse
```

---

## 🔧 Các Services Chi Tiết

### 1. ParserService
**Vai trò**: Parse file PDF/DOCX thành text

**Methods**:
- `parse_file(file_path)`: Parse file và trả về text đã clean

**Dependencies**: 
- `pypdf` (PDF)
- `python-docx` (DOCX)

---

### 2. StructuringService
**Vai trò**: Trích xuất structured data từ text bằng GPT-4o-mini

**Methods**:
- `get_structured_data(text, schema)`: Trả về structured JSON
- `_dump_prompts()`: Lưu prompts
- `_dump_response()`: Lưu responses

**Flow**:
1. Tạo prompt với JSON schema
2. Gọi OpenAI API
3. Parse JSON response
4. Lưu prompts/responses vào io_dump/

**Dependencies**: OpenAI API

---

### 3. EmbeddingService
**Vai trò**: Tạo vector embeddings cho semantic matching

**Methods**:
- `get_embedding(text)`: Tạo embedding cho 1 text
- `get_embeddings_batch(texts)`: Tạo embeddings cho nhiều texts

**Model**: `text-embedding-3-small` (1536 dimensions)

**Dependencies**: OpenAI API

---

### 4. VectorStoreService
**Vai trò**: Lưu trữ và query vectors trong ChromaDB

**Methods**:
- `add_document(collection, doc_id, embedding, metadata)`: Thêm document
- `get_document_by_id(collection, doc_id)`: Lấy document theo ID
- `search_similar(collection, embedding, n_results)`: Tìm documents tương tự

**Collections**:
- `cv_collection`: Lưu CVs
- `jd_collection`: Lưu JDs

**Dependencies**: ChromaDB

---

### 5. ScoringService
**Vai trò**: Tính điểm matching giữa CV và JD

**Methods**:
- `calculate_match_score(cv_data, jd_data)`: Tính tổng điểm và breakdown

**Delegates to**: `EnhancedScoringService`

**Scoring Categories**:
1. Hard Skills (30%)
2. Work Experience (25%)
3. Responsibilities (15%)
4. Soft Skills (10%)
5. Education (5%)
6. Additional Factors (15%)

**Dependencies**: EmbeddingService (cho semantic matching)

---

## 📝 Ví Dụ Luồng Hoàn Chỉnh

### Scenario: Match 1 CV với 1 JD

```
1. User uploads CV: cv_candidate.pdf
   ↓
2. POST /process/cv
   ├─ Parse: "John Doe, Software Engineer, 5 years..."
   ├─ Structure: {hard_skills: ["Python", "FastAPI"], ...}
   ├─ Embedding: [0.1, 0.2, ...] (1536 dims)
   └─ Store: cv_id = "abc-123"
   
3. User uploads JD: jd_software_engineer.docx
   ↓
4. POST /process/jd
   ├─ Parse: "We are looking for..."
   ├─ Structure: {hard_skills: ["Python", "Django"], ...}
   ├─ Embedding: [0.11, 0.21, ...] (1536 dims)
   └─ Store: jd_id = "xyz-789"
   
5. User requests matching
   ↓
6. GET /match/abc-123/xyz-789
   ├─ Get CV & JD from ChromaDB
   ├─ Calculate scores:
   │  ├─ Hard Skills: 0.85 (Python matches)
   │  ├─ Work Experience: 0.70
   │  ├─ Responsibilities: 0.65
   │  ├─ Soft Skills: 0.60
   │  ├─ Education: 0.80
   │  └─ Additional: 0.90
   └─ Total: 0.75 (weighted average)
   
7. Return JSON response với breakdown chi tiết
```

---

## 🎯 Điểm Quan Trọng

### 1. **Tách biệt Processing và Matching**
- Processing: Chỉ làm 1 lần, lưu vào DB
- Matching: Có thể làm nhiều lần, nhanh (không gọi API)

### 2. **Semantic Matching**
- Sử dụng embeddings để tìm similarity, không chỉ exact match
- Ví dụ: "Python" và "Python programming" → high similarity

### 3. **Weighted Scoring**
- Mỗi category có weight riêng
- Total score = weighted sum của tất cả categories

### 4. **Debugging Support**
- Tất cả prompts/responses được lưu vào `io_dump/`
- Dễ dàng kiểm tra và debug

### 5. **Scalability**
- ChromaDB hỗ trợ vector search nhanh
- Có thể match nhiều CVs với 1 JD hiệu quả

---

## 🔍 File Locations

```
GP/
├── app/
│   ├── api/
│   │   └── main.py              # FastAPI endpoints
│   └── services/
│       ├── parser_service.py    # Parse PDF/DOCX
│       ├── structuring_service.py  # GPT-4o-mini extraction
│       ├── embedding_service.py     # Create embeddings
│       ├── vector_store.py         # ChromaDB operations
│       └── scoring_service.py       # Matching scores
├── core/
│   ├── config.py                # Settings
│   └── schemas.py               # Pydantic models
├── io_dump/
│   ├── prompts/                # LLM prompts
│   └── responses/              # LLM responses
├── chroma_db/                  # ChromaDB storage
└── demo_matching.py            # Demo script
```

---

## 📚 Tài Liệu Tham Khảo

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

