"""Test cases cho API endpoints"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock
import tempfile
import os
import uuid

from app.api.main import app
from core.schemas import StructuredData
from tests.test_data import SAMPLE_CV_TEXT, SAMPLE_JD_TEXT


@pytest.fixture
def client():
    """Tạo test client"""
    return TestClient(app)


@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    with patch('app.api.main.OpenAI') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        
        # Mock embedding response
        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = [0.1] * 100
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [mock_embedding_data]
        mock_client.embeddings.create.return_value = mock_embedding_response
        
        # Mock chat completion response
        mock_chat_response = MagicMock()
        mock_chat_choice = MagicMock()
        mock_chat_choice.message.content = json.dumps({
            "full_name": "Nguyễn Văn A",
            "email": "test@example.com",
            "phone": "0123456789",
            "skills": ["Python", "JavaScript"],
            "job_titles": ["Software Engineer"],
            "degrees": ["Cử nhân CNTT"],
            "certifications": ["AWS"]
        })
        mock_chat_response.choices = [mock_chat_choice]
        mock_client.chat.completions.create.return_value = mock_chat_response
        
        yield mock_client


class TestRootEndpoint:
    """Test root endpoint"""
    
    def test_root(self, client):
        """Test GET /"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data


class TestProcessCV:
    """Test POST /process/cv endpoint"""
    
    @patch('app.api.main.parser_service')
    @patch('app.api.main.structuring_service')
    @patch('app.api.main.embedding_service')
    @patch('app.api.main.vector_store_service')
    def test_process_cv_success(self, mock_vector_store, mock_embedding, 
                                  mock_structuring, mock_parser, client, mock_openai):
        """Test xử lý CV thành công"""
        # Mock parser
        mock_parser.parse_file.return_value = SAMPLE_CV_TEXT
        
        # Mock structuring
        mock_structuring.get_structured_data.return_value = {
            "full_name": "Nguyễn Văn A",
            "skills": ["Python", "JavaScript"],
            "job_titles": ["Software Engineer"],
            "degrees": ["Cử nhân CNTT"],
            "certifications": []
        }
        
        # Mock embedding
        mock_embedding.get_embedding.return_value = [0.1] * 100
        
        # Mock vector store
        mock_vector_store.add_document = Mock()
        
        # Tạo file PDF giả
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"fake pdf content")
            tmp_file_path = tmp_file.name
        
        try:
            # Gửi request
            with open(tmp_file_path, "rb") as f:
                response = client.post(
                    "/process/cv",
                    files={"file": ("test.pdf", f, "application/pdf")}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert "doc_id" in data
            assert "structured_data" in data
            mock_vector_store.add_document.assert_called_once()
        
        finally:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
    
    def test_process_cv_invalid_format(self, client):
        """Test với định dạng file không hợp lệ"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, "rb") as f:
                response = client.post(
                    "/process/cv",
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            assert response.status_code == 400
            assert "Định dạng file không được hỗ trợ" in response.json()["detail"]
        
        finally:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)


class TestProcessJD:
    """Test POST /process/jd endpoint"""
    
    @patch('app.api.main.structuring_service')
    @patch('app.api.main.embedding_service')
    @patch('app.api.main.vector_store_service')
    def test_process_jd_success(self, mock_vector_store, mock_embedding,
                                 mock_structuring, client, mock_openai):
        """Test xử lý JD thành công"""
        # Mock structuring
        mock_structuring.get_structured_data.return_value = {
            "skills": ["Python", "FastAPI"],
            "job_titles": ["Senior Software Engineer"],
            "degrees": ["Cử nhân CNTT"],
            "certifications": []
        }
        
        # Mock embedding
        mock_embedding.get_embedding.return_value = [0.1] * 100
        
        # Mock vector store
        mock_vector_store.add_document = Mock()
        
        # Gửi request
        response = client.post(
            "/process/jd",
            json={"text": SAMPLE_JD_TEXT}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "doc_id" in data
        assert "structured_data" in data
        mock_vector_store.add_document.assert_called_once()
    
    def test_process_jd_empty_text(self, client):
        """Test với text rỗng"""
        response = client.post(
            "/process/jd",
            json={"text": ""}
        )
        
        assert response.status_code == 400
        assert "không được để trống" in response.json()["detail"]


class TestMatchCVJD:
    """Test GET /match/{cv_id}/{jd_id} endpoint"""
    
    @patch('app.api.main.vector_store_service')
    @patch('app.api.main.scoring_service')
    def test_match_cv_jd_success(self, mock_scoring, mock_vector_store, client):
        """Test so khớp CV-JD thành công"""
        # Mock vector store
        mock_vector_store.get_document_by_id.side_effect = [
            {
                "embedding": [0.1] * 100,
                "metadata": {
                    "skills": ["Python", "JavaScript"],
                    "job_titles": ["Software Engineer"],
                    "degrees": ["Cử nhân CNTT"],
                    "certifications": []
                }
            },
            {
                "embedding": [0.11] * 100,
                "metadata": {
                    "skills": ["Python", "FastAPI"],
                    "job_titles": ["Senior Software Engineer"],
                    "degrees": ["Cử nhân CNTT"],
                    "certifications": []
                }
            }
        ]
        
        # Mock scoring service
        mock_scoring.calculate_match_score.return_value = {
            "total_score": 0.85,
            "breakdown": {
                "overall_semantic": 0.8,
                "skill_match": 0.9,
                "job_title_match": 0.7,
                "education_cert_match": 1.0
            }
        }
        
        # Gửi request
        response = client.get("/match/cv_id_123/jd_id_456")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_score" in data
        assert "breakdown" in data
        assert data["total_score"] == 0.85
        assert "overall_semantic" in data["breakdown"]
    
    @patch('app.api.main.vector_store_service')
    def test_match_cv_jd_not_found(self, mock_vector_store, client):
        """Test với CV/JD không tồn tại"""
        mock_vector_store.get_document_by_id.return_value = None
        
        response = client.get("/match/nonexistent_cv/nonexistent_jd")
        
        assert response.status_code == 404
        assert "Không tìm thấy" in response.json()["detail"]

