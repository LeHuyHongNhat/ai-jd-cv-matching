"""Test cases cho các services"""
import pytest
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch
import json

from app.services.parser_service import ParserService
from app.services.structuring_service import StructuringService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.scoring_service import ScoringService
from core.schemas import StructuredData
from tests.test_data import SAMPLE_CV_TEXT, SAMPLE_JD_TEXT


class TestParserService:
    """Test ParserService"""
    
    def test_clean_text(self):
        """Test phương thức dọn dẹp văn bản"""
        parser = ParserService()
        
        dirty_text = "  Line 1  \n\n\n  Line 2  \n  Line 3  "
        cleaned = parser._clean_text(dirty_text)
        
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned
        assert len(cleaned.split("\n\n")) <= 2  # Không có nhiều dòng trống liên tiếp
    
    def test_parse_file_invalid_extension(self):
        """Test parse file với định dạng không hợp lệ"""
        parser = ParserService()
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"Test content")
            tmp_path = tmp_file.name
        
        try:
            with pytest.raises(ValueError, match="Định dạng file không được hỗ trợ"):
                parser.parse_file(tmp_path)
        finally:
            os.remove(tmp_path)
    
    def test_parse_file_not_found(self):
        """Test parse file không tồn tại"""
        parser = ParserService()
        
        with pytest.raises(FileNotFoundError):
            parser.parse_file("nonexistent_file.pdf")


class TestStructuringService:
    """Test StructuringService"""
    
    @patch('app.services.structuring_service.OpenAI')
    def test_get_structured_data(self, mock_openai_class):
        """Test trích xuất structured data"""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "full_name": "Nguyễn Văn A",
            "skills": ["Python", "JavaScript"],
            "job_titles": ["Software Engineer"],
            "degrees": ["Cử nhân CNTT"],
            "certifications": []
        })
        
        mock_client.chat.completions.create.return_value = mock_response
        
        service = StructuringService(mock_client)
        result = service.get_structured_data(SAMPLE_CV_TEXT, StructuredData)
        
        assert isinstance(result, dict)
        assert "skills" in result
        assert "job_titles" in result
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('app.services.structuring_service.OpenAI')
    def test_get_structured_data_invalid_json(self, mock_openai_class):
        """Test với JSON không hợp lệ"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Invalid JSON"
        
        mock_client.chat.completions.create.return_value = mock_response
        
        service = StructuringService(mock_client)
        
        with pytest.raises(ValueError, match="Không thể parse JSON"):
            service.get_structured_data(SAMPLE_CV_TEXT, StructuredData)


class TestEmbeddingService:
    """Test EmbeddingService"""
    
    @patch('app.services.embedding_service.OpenAI')
    def test_get_embedding(self, mock_openai_class):
        """Test tạo embedding cho một text"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_data = MagicMock()
        mock_data.embedding = [0.1, 0.2, 0.3] * 100  # Giả lập vector 1536 dimensions
        mock_response.data = [mock_data]
        
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService(mock_client)
        result = service.get_embedding("Test text")
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(x, float) for x in result)
        mock_client.embeddings.create.assert_called_once()
    
    @patch('app.services.embedding_service.OpenAI')
    def test_get_embeddings_batch(self, mock_openai_class):
        """Test tạo embeddings hàng loạt"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response với nhiều embeddings
        mock_response = MagicMock()
        mock_data1 = MagicMock()
        mock_data1.embedding = [0.1] * 100
        mock_data2 = MagicMock()
        mock_data2.embedding = [0.2] * 100
        mock_response.data = [mock_data1, mock_data2]
        
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService(mock_client)
        texts = ["Text 1", "Text 2"]
        results = service.get_embeddings_batch(texts)
        
        assert len(results) == 2
        assert all(isinstance(emb, list) for emb in results)
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input=texts
        )


class TestVectorStoreService:
    """Test VectorStoreService"""
    
    def test_init(self):
        """Test khởi tạo VectorStoreService"""
        import shutil
        import time
        
        tmp_dir = tempfile.mkdtemp()
        try:
            service = VectorStoreService(persist_directory=tmp_dir)
            
            assert service.cv_collection is not None
            assert service.jd_collection is not None
            
            # Đóng connection để tránh lock file trên Windows
            # ChromaDB cần thời gian để đóng connections
            del service
            time.sleep(0.1)  # Chờ một chút để ChromaDB đóng file
            
        finally:
            # Force cleanup với retry
            for _ in range(3):
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    break
                except PermissionError:
                    time.sleep(0.2)
            else:
                # Nếu vẫn không xóa được, bỏ qua (file sẽ bị xóa sau)
                pass
    
    def test_add_and_get_document(self):
        """Test thêm và lấy document"""
        import shutil
        import time
        
        tmp_dir = tempfile.mkdtemp()
        try:
            service = VectorStoreService(persist_directory=tmp_dir)
            
            doc_id = "test_doc_1"
            embedding = [0.1] * 100  # Giả lập embedding vector
            metadata = {"skills": ["Python", "JavaScript"], "name": "Test CV"}
            
            # Thêm document
            service.add_document("cv_collection", doc_id, embedding, metadata)
            
            # Lấy document
            result = service.get_document_by_id("cv_collection", doc_id)
            
            assert result is not None
            assert result["metadata"] == metadata
            assert len(result["embedding"]) == len(embedding)
            
            # Đóng connection
            del service
            time.sleep(0.1)
        finally:
            # Cleanup với retry
            for _ in range(3):
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    break
                except PermissionError:
                    time.sleep(0.2)
    
    def test_get_collection_invalid_name(self):
        """Test với collection name không hợp lệ"""
        import shutil
        import time
        
        tmp_dir = tempfile.mkdtemp()
        try:
            service = VectorStoreService(persist_directory=tmp_dir)
            
            with pytest.raises(ValueError, match="Collection không hợp lệ"):
                service._get_collection("invalid_collection")
            
            # Đóng connection
            del service
            time.sleep(0.1)
        finally:
            # Cleanup với retry
            for _ in range(3):
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    break
                except PermissionError:
                    time.sleep(0.2)


class TestScoringService:
    """Test ScoringService (new structured schema only)"""

    @staticmethod
    def _build_structured_payload():
        return {
            "hard_skills": {
                "programming_languages": ["Python", "JavaScript"],
                "technologies_frameworks": ["FastAPI", "React"],
                "tools_software": ["Git", "Docker"],
                "certifications": ["AWS"],
                "industry_specific_skills": ["NLP", "Data Pipelines"],
            },
            "work_experience": {
                "job_titles": ["Senior Software Engineer"],
                "industries": ["Technology", "FinTech"],
                "total_years": 6,
            },
            "responsibilities_achievements": {
                "key_responsibilities": ["Design APIs", "Lead team"],
                "achievements": ["Improved latency by 30%"],
                "project_types": ["Microservices", "Cloud"],
            },
            "soft_skills": {
                "communication_teamwork": ["Cross-functional collaboration"],
                "leadership_management": ["Mentoring juniors"],
                "problem_solving": ["Root cause analysis"],
                "adaptability": ["Fast learner"],
            },
            "education_training": {
                "degrees": ["Bachelor of Computer Science"],
                "majors": ["Computer Science"],
                "additional_courses": ["Machine Learning Bootcamp"],
            },
            "additional_factors": {
                "languages": ["English", "Vietnamese"],
                "availability": "Immediate",
                "relocation_willingness": True,
            },
        }

    def test_calculate_match_score_new_structure(self):
        """Scoring uses new schema and returns breakdown for 6 categories."""
        mock_embedding_service = MagicMock()

        def fake_embeddings(texts):
            return [[0.1] * 16 for _ in texts]

        mock_embedding_service.get_embeddings_batch.side_effect = fake_embeddings

        scoring_service = ScoringService(mock_embedding_service)

        cv_data = {
            "embedding": [0.1] * 10,
            "structured_json": self._build_structured_payload(),
        }
        jd_data = {
            "embedding": [0.2] * 10,
            "structured_json": self._build_structured_payload(),
        }

        result = scoring_service.calculate_match_score(cv_data, jd_data)

        assert "total_score" in result
        assert "breakdown" in result
        assert 0.0 <= result["total_score"] <= 1.0
        expected_categories = {
            "hard_skills",
            "work_experience",
            "responsibilities",
            "soft_skills",
            "education",
            "additional_factors",
        }
        assert set(result["breakdown"].keys()) == expected_categories
        assert "category_weights" in result

    def test_calculate_match_score_requires_new_schema(self):
        """Raise error when structured data does not include new schema."""
        mock_embedding_service = MagicMock()
        scoring_service = ScoringService(mock_embedding_service)

        legacy_structured = {"skills": ["Python"], "job_titles": ["Engineer"]}

        cv_data = {"embedding": [0.1] * 10, "structured_json": legacy_structured}
        jd_data = {"embedding": [0.2] * 10, "structured_json": legacy_structured}

        with pytest.raises(ValueError, match="Structured data must include new schema fields"):
            scoring_service.calculate_match_score(cv_data, jd_data)

