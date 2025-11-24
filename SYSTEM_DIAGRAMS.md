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

    subgraph "External Services"
        OAI[OpenAI API<br/>GPT-4o-mini<br/>text-embedding-3-small]
    end

    FE -->|REST/GraphQL| SB
    SB -->|Internal API calls| API

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

**API Endpoints:**

- `POST /process/cv` - Upload và xử lý CV (PDF/DOCX)
- `POST /process/jd` - Xử lý Job Description (text)
- `GET /match/{cv_id}/{jd_id}` - So khớp CV với JD và trả về điểm số

---

## 2. Luồng Xử lý API - Ba Endpoint Chính

### 2.1 POST /process/cv - Xử lý CV

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI<br/>/process/cv
    participant PS as ParserService
    participant SS as StructuringService
    participant ES as EmbeddingService
    participant VS as VectorStoreService
    participant OAI as OpenAI API
    participant DB as ChromaDB

    User->>API: POST /process/cv<br/>(upload PDF/DOCX)

    API->>API: Validate file type
    API->>API: Save to temp file

    API->>PS: parse_file(tmp_file_path)
    PS->>PS: _parse_pdf() or _parse_docx()
    PS->>PS: _clean_text()
    PS-->>API: text_content

    API->>SS: get_structured_data(text_content, StructuredData)
    SS->>SS: Create system_prompt + user_message
    SS->>SS: _dump_prompts(timestamp)
    SS->>OAI: chat.completions.create<br/>(model: gpt-4o-mini, response_format: json_object)
    OAI-->>SS: JSON response
    SS->>SS: _dump_response(timestamp)
    SS-->>API: structured_json

    API->>ES: get_embedding(text_content)
    ES->>OAI: embeddings.create<br/>(model: text-embedding-3-small)
    OAI-->>ES: embedding vector [1536 dims]
    ES-->>API: embedding

    API->>API: Generate cv_id (UUID)

    API->>VS: add_document("cv_collection", cv_id, embedding, structured_json)
    VS->>VS: Sanitize metadata (JSON serialize)
    VS->>DB: collection.add()

    API->>API: Clean temp file
    API-->>User: ProcessResponse<br/>{doc_id: cv_id, structured_data}
```

### 2.2 POST /process/jd - Xử lý Job Description

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI<br/>/process/jd
    participant SS as StructuringService
    participant ES as EmbeddingService
    participant VS as VectorStoreService
    participant OAI as OpenAI API
    participant DB as ChromaDB

    User->>API: POST /process/jd<br/>(text input)

    API->>API: Validate text not empty

    API->>SS: get_structured_data(text_content, StructuredData)
    SS->>SS: Create prompts
    SS->>OAI: chat.completions.create
    OAI-->>SS: structured JSON
    SS-->>API: structured_json

    API->>ES: get_embedding(text_content)
    ES->>OAI: embeddings.create
    OAI-->>ES: embedding vector
    ES-->>API: embedding

    API->>API: Generate jd_id (UUID)

    API->>VS: add_document("jd_collection", jd_id, embedding, structured_json)
    VS->>DB: collection.add()

    API-->>User: ProcessResponse<br/>{doc_id: jd_id, structured_data}
```

### 2.3 GET /match/{cv_id}/{jd_id} - So khớp CV-JD

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI<br/>/match/{cv_id}/{jd_id}
    participant VS as VectorStoreService
    participant SC as ScoringService
    participant ESC as EnhancedScoringService
    participant ES as EmbeddingService
    participant DB as ChromaDB
    participant OAI as OpenAI API

    User->>API: GET /match/{cv_id}/{jd_id}

    API->>VS: get_document_by_id("cv_collection", cv_id)
    VS->>DB: collection.get(ids=[cv_id])
    DB-->>VS: {embedding, metadata}
    VS->>VS: Deserialize JSON metadata
    VS-->>API: cv_doc

    API->>VS: get_document_by_id("jd_collection", jd_id)
    VS->>DB: collection.get(ids=[jd_id])
    DB-->>VS: {embedding, metadata}
    VS-->>API: jd_doc

    API->>API: Prepare cv_data, jd_data

    API->>SC: calculate_match_score(cv_data, jd_data)
    SC->>ESC: calculate_enhanced_match_score()

    ESC->>ESC: _check_new_structure()
    ESC->>ESC: _calculate_detailed_scores()

    Note over ESC: Calculate 6 categories
    ESC->>ESC: _score_hard_skills()
    ESC->>ES: get_embeddings_batch([skills])
    ES->>OAI: embeddings.create (batch)
    OAI-->>ES: embeddings
    ES-->>ESC: embeddings
    ESC->>ESC: cosine_similarity()

    ESC->>ESC: _score_work_experience()
    ESC->>ESC: _score_responsibilities()
    ESC->>ESC: _score_soft_skills()
    ESC->>ESC: _score_education()
    ESC->>ESC: _score_additional_factors()

    ESC->>ESC: Calculate weighted total_score
    ESC->>ESC: _generate_detailed_analysis()
    ESC-->>SC: {total_score, category_scores, weights, analysis}
    SC-->>API: score_result

    API-->>User: ScoreResponse<br/>{total_score, breakdown}
```

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

---

## 7. Data Flow - Từ File Upload đến Matching Result

```mermaid
flowchart TD
    START[User uploads CV PDF/DOCX] --> UPLOAD[FastAPI receives file]

    UPLOAD --> TEMP[Save to temp file]
    TEMP --> PARSE[ParserService.parse_file]

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

    CHROMA --> RESPONSE1[Return ProcessResponse<br/>doc_id + structured_data]

    RESPONSE1 --> MATCH_REQUEST[User requests matching<br/>GET /match/cv_id/jd_id]

    MATCH_REQUEST --> LOAD_CV[Load CV from ChromaDB]
    MATCH_REQUEST --> LOAD_JD[Load JD from ChromaDB]

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
    ANALYSIS --> FINAL[Return ScoreResponse<br/>total_score + breakdown]

    style START fill:#E8F5E9
    style FINAL fill:#C8E6C9
    style GPT fill:#FFF3E0
    style OPENAI_EMB fill:#FFF3E0
    style CHROMA fill:#E1F5FE
```

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
