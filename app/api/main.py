import uuid
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI

from core.config import settings
from core.schemas import StructuredData, ScoreResponse, ProcessResponse, JDInput, ScoreBreakdown
from app.services.parser_service import ParserService
from app.services.structuring_service import StructuringService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.scoring_service import ScoringService

# Khởi tạo FastAPI app
app = FastAPI(
    title="CV-JD Matching API",
    description="API so khớp CV và Job Description sử dụng OpenAI GPT-4o-mini và text-embedding-3-small",
    version="1.0.0"
)

# Khởi tạo OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Khởi tạo các services
parser_service = ParserService()
structuring_service = StructuringService(openai_client)
embedding_service = EmbeddingService(openai_client)
vector_store_service = VectorStoreService()
scoring_service = ScoringService(embedding_service)


@app.get("/")
async def root():
    """Endpoint root"""
    return {
        "message": "CV-JD Matching API",
        "version": "1.0.0",
        "endpoints": {
            "process_cv": "POST /process/cv",
            "process_jd": "POST /process/jd",
            "match": "GET /match/{cv_id}/{jd_id}"
        }
    }


@app.post("/process/cv", response_model=ProcessResponse)
async def process_cv(file: UploadFile = File(...)):
    """
    Xử lý CV: Parse file, trích xuất structured data, tạo embedding và lưu vào vector store
    
    Args:
        file: File CV (PDF hoặc DOCX)
        
    Returns:
        ProcessResponse chứa doc_id và structured_data
    """
    try:
        # Kiểm tra định dạng file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Tên file không được để trống")
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.pdf', '.docx']:
            raise HTTPException(
                status_code=400,
                detail=f"Định dạng file không được hỗ trợ: {file_extension}. Chỉ hỗ trợ .pdf và .docx"
            )
        
        # Lưu file tạm thời
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Bước 1: Parse file để lấy text
            text_content = parser_service.parse_file(tmp_file_path)
            
            # Bước 2: Trích xuất structured data bằng GPT-4o-mini
            structured_json = structuring_service.get_structured_data(
                text_content,
                StructuredData
            )
            
            # Bước 3: Tạo embedding từ text content
            embedding = embedding_service.get_embedding(text_content)
            
            # Bước 4: Tạo CV ID
            cv_id = str(uuid.uuid4())
            
            # Bước 5: Lưu vào vector store
            # Metadata sẽ chứa structured_json
            vector_store_service.add_document(
                collection_name="cv_collection",
                doc_id=cv_id,
                embedding=embedding,
                metadata=structured_json
            )
            
            # Parse structured_json thành StructuredData object
            structured_data = StructuredData(**structured_json)
            
            return ProcessResponse(
                doc_id=cv_id,
                structured_data=structured_data
            )
            
        finally:
            # Xóa file tạm thời
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý CV: {str(e)}")


@app.post("/process/jd", response_model=ProcessResponse)
async def process_jd(jd_input: JDInput):
    """
    Xử lý Job Description: Trích xuất structured data, tạo embedding và lưu vào vector store
    
    Args:
        jd_input: JDInput chứa text của Job Description
        
    Returns:
        ProcessResponse chứa doc_id và structured_data
    """
    try:
        text_content = jd_input.text
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Nội dung Job Description không được để trống")
        
        # Bước 1: Trích xuất structured data bằng GPT-4o-mini
        structured_json = structuring_service.get_structured_data(
            text_content,
            StructuredData
        )
        
        # Bước 2: Tạo embedding từ text content
        embedding = embedding_service.get_embedding(text_content)
        
        # Bước 3: Tạo JD ID
        jd_id = str(uuid.uuid4())
        
        # Bước 4: Lưu vào vector store
        vector_store_service.add_document(
            collection_name="jd_collection",
            doc_id=jd_id,
            embedding=embedding,
            metadata=structured_json
        )
        
        # Parse structured_json thành StructuredData object
        structured_data = StructuredData(**structured_json)
        
        return ProcessResponse(
            doc_id=jd_id,
            structured_data=structured_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý Job Description: {str(e)}")


@app.get("/match/{cv_id}/{jd_id}", response_model=ScoreResponse)
async def match_cv_jd(cv_id: str, jd_id: str):
    """
    So khớp CV và Job Description, trả về điểm số chi tiết
    
    Args:
        cv_id: ID của CV
        jd_id: ID của Job Description
        
    Returns:
        ScoreResponse chứa total_score và breakdown
    """
    try:
        # Lấy dữ liệu từ vector store
        cv_doc = vector_store_service.get_document_by_id("cv_collection", cv_id)
        jd_doc = vector_store_service.get_document_by_id("jd_collection", jd_id)
        
        if not cv_doc:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy CV với ID: {cv_id}")
        
        if not jd_doc:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy Job Description với ID: {jd_id}")
        
        # Chuẩn bị dữ liệu
        cv_data = {
            "embedding": cv_doc["embedding"],
            "structured_json": cv_doc["metadata"]
        }
        
        jd_data = {
            "embedding": jd_doc["embedding"],
            "structured_json": jd_doc["metadata"]
        }
        
        # Tính điểm số
        score_result = scoring_service.calculate_match_score(cv_data, jd_data)
        
        # Tạo response
        breakdown = ScoreBreakdown(**score_result["breakdown"])
        
        return ScoreResponse(
            total_score=score_result["total_score"],
            breakdown=breakdown
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi so khớp CV-JD: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

