"""Integration tests - Test toàn bộ workflow"""
import pytest
import json
import tempfile
import os
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock

from app.api.main import app
from tests.test_data import SAMPLE_CV_TEXT, SAMPLE_JD_TEXT


@pytest.fixture
def client():
    """Tạo test client"""
    return TestClient(app)


@pytest.fixture
def mock_openai_all():
    """Mock toàn bộ OpenAI API calls"""
    with patch('app.api.main.OpenAI') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        
        # Mock embedding response
        def create_embedding_response(text):
            # Tạo embedding giả dựa trên text length để có consistency
            base_embedding = [0.1] * 100
            if isinstance(text, list):
                return MagicMock(data=[MagicMock(embedding=base_embedding) for _ in text])
            else:
                mock_data = MagicMock()
                mock_data.embedding = base_embedding
                return MagicMock(data=[mock_data])
        
        mock_client.embeddings.create.side_effect = lambda **kwargs: create_embedding_response(
            kwargs.get('input', '')
        )
        
        # Mock chat completion response
        def create_chat_response(prompt_text):
            # Trả về structured data dựa trên nội dung
            if "CV" in prompt_text or "curriculum" in prompt_text.lower() or "nguyễn" in prompt_text.lower():
                structured = {
                    "full_name": "Nguyễn Văn A",
                    "email": "nguyenvana@email.com",
                    "phone": "0123456789",
                    "skills": ["Python", "JavaScript", "TypeScript", "FastAPI", "React"],
                    "job_titles": ["Software Engineer"],
                    "degrees": ["Cử nhân Công nghệ Thông tin"],
                    "certifications": ["AWS Certified Solutions Architect"]
                }
            else:
                structured = {
                    "skills": ["Python", "FastAPI", "PostgreSQL", "React"],
                    "job_titles": ["Senior Software Engineer"],
                    "degrees": ["Cử nhân Công nghệ Thông tin"],
                    "certifications": ["AWS"]
                }
            
            mock_choice = MagicMock()
            mock_choice.message.content = json.dumps(structured)
            return MagicMock(choices=[mock_choice])
        
        mock_client.chat.completions.create.side_effect = lambda **kwargs: create_chat_response(
            kwargs.get('messages', [{}])[-1].get('content', '')
        )
        
        yield mock_client


class TestFullWorkflow:
    """Test toàn bộ workflow từ đầu đến cuối"""
    
    @patch('app.api.main.parser_service')
    @patch('app.api.main.structuring_service')
    @patch('app.api.main.embedding_service')
    @patch('app.api.main.vector_store_service')
    @patch('app.api.main.scoring_service')
    def test_full_workflow_cv_jd_matching(self, mock_scoring, mock_vector_store,
                                           mock_embedding, mock_structuring, 
                                           mock_parser, client, mock_openai_all):
        """Test workflow đầy đủ: Upload CV -> Process JD -> Match"""
        
        # Setup mocks
        mock_parser.parse_file.return_value = SAMPLE_CV_TEXT
        mock_structuring.get_structured_data.return_value = {
            "full_name": "Nguyễn Văn A",
            "skills": ["Python", "JavaScript"],
            "job_titles": ["Software Engineer"],
            "degrees": ["Cử nhân CNTT"],
            "certifications": []
        }
        mock_embedding.get_embedding.return_value = [0.1] * 100
        mock_vector_store.add_document = Mock()
        
        cv_id = str(uuid.uuid4())
        jd_id = str(uuid.uuid4())
        
        # Mock get_document_by_id để trả về dữ liệu khi match
        def mock_get_doc(collection_name, doc_id):
            if collection_name == "cv_collection" and doc_id == cv_id:
                return {
                    "embedding": [0.1] * 100,
                    "metadata": {
                        "skills": ["Python", "JavaScript"],
                        "job_titles": ["Software Engineer"],
                        "degrees": ["Cử nhân CNTT"],
                        "certifications": []
                    }
                }
            elif collection_name == "jd_collection" and doc_id == jd_id:
                return {
                    "embedding": [0.11] * 100,
                    "metadata": {
                        "skills": ["Python", "FastAPI"],
                        "job_titles": ["Senior Software Engineer"],
                        "degrees": ["Cử nhân CNTT"],
                        "certifications": []
                    }
                }
            return None
        
        mock_vector_store.get_document_by_id.side_effect = mock_get_doc
        
        # Mock scoring
        mock_scoring.calculate_match_score.return_value = {
            "total_score": 0.85,
            "breakdown": {
                "overall_semantic": 0.8,
                "skill_match": 0.9,
                "job_title_match": 0.7,
                "education_cert_match": 1.0
            }
        }
        
        # Bước 1: Upload và process CV
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"fake pdf content for testing")
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, "rb") as f:
                cv_response = client.post(
                    "/process/cv",
                    files={"file": ("test_cv.pdf", f, "application/pdf")}
                )
            
            assert cv_response.status_code == 200
            cv_data = cv_response.json()
            assert "doc_id" in cv_data
            assert "structured_data" in cv_data
            
            # Lưu cv_id để dùng sau
            cv_id = cv_data["doc_id"]
            
        finally:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
        
        # Bước 2: Process JD
        jd_response = client.post(
            "/process/jd",
            json={"text": SAMPLE_JD_TEXT}
        )
        
        assert jd_response.status_code == 200
        jd_data = jd_response.json()
        assert "doc_id" in jd_data
        
        # Lưu jd_id để dùng sau
        jd_id = jd_data["doc_id"]
        
        # Update mock để sử dụng IDs thực tế
        mock_vector_store.get_document_by_id.side_effect = mock_get_doc
        
        # Bước 3: Match CV và JD
        match_response = client.get(f"/match/{cv_id}/{jd_id}")
        
        assert match_response.status_code == 200
        match_data = match_response.json()
        
        assert "total_score" in match_data
        assert "breakdown" in match_data
        assert 0.0 <= match_data["total_score"] <= 1.0
        
        breakdown = match_data["breakdown"]
        assert "overall_semantic" in breakdown
        assert "skill_match" in breakdown
        assert "job_title_match" in breakdown
        assert "education_cert_match" in breakdown
        
        print(f"\n✅ Integration test passed!")
        print(f"CV ID: {cv_id}")
        print(f"JD ID: {jd_id}")
        print(f"Total Score: {match_data['total_score']:.4f}")
        print(f"Breakdown: {json.dumps(breakdown, indent=2)}")


class TestEndToEnd:
    """End-to-end tests với real services (cần OpenAI API key)"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY") or 
        os.getenv("OPENAI_API_KEY", "").strip() == "" or
        os.getenv("OPENAI_API_KEY") == "test-key-for-mocking",
        reason="Cần OpenAI API key thật để chạy end-to-end test (set OPENAI_API_KEY trong config.env hoặc .env)"
    )
    def test_real_api_call(self, client):
        """Test với OpenAI API thật (chỉ chạy khi có API key)"""
        # Test này sẽ chỉ chạy khi có OPENAI_API_KEY thật từ config.env/.env
        # Bỏ qua trong CI/CD thông thường
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key and api_key != "test-key-for-mocking", "API key phải được load từ config.env"
        # TODO: Implement test với real API calls
        pass

