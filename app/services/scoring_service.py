import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any
from app.services.embedding_service import EmbeddingService


class ScoringService:
    """Multi-dimensional scoring service for CV-JD matching"""
    
    def __init__(self, embedding_service: EmbeddingService):
        """
        Initialize ScoringService
        
        Args:
            embedding_service: EmbeddingService for creating skill embeddings
        """
        self.embedding_service = embedding_service
        
        # Weight for scoring components (aligned with new structure)
        self.weights = {
            "hard_skills": 0.375,              # 37.5% (35-40%)
            "work_experience": 0.275,          # 27.5% (25-30%)
            "responsibilities": 0.175,         # 17.5% (15-20%)
            "soft_skills": 0.125,              # 12.5% (10-15%)
            "education": 0.075,                # 7.5% (5-10%)
            "additional_factors": 0.05,        # 5%
            # Fallback to old weights if new structure not available
            "overall_semantic": 0.4,           # 40%
            "skill_match": 0.3,                # 30%
            "job_title_match": 0.2,            # 20%
            "education_cert_match": 0.1        # 10%
        }
    
    def calculate_match_score(self, cv_data: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tính điểm tổng hợp và chi tiết cho việc khớp CV-JD
        
        Args:
            cv_data: Dictionary chứa 'embedding' và 'structured_json'
            jd_data: Dictionary chứa 'embedding' và 'structured_json'
            
        Returns:
            Dictionary chứa total_score và breakdown
        """
        # Điểm thành phần 1: Ngữ nghĩa tổng thể
        overall_score = self._calculate_overall_semantic_score(
            cv_data["embedding"],
            jd_data["embedding"]
        )
        
        # Trích xuất dữ liệu từ structured_json
        cv_structured = cv_data["structured_json"]
        jd_structured = jd_data["structured_json"]
        
        cv_skills = cv_structured.get("skills", [])
        jd_skills = jd_structured.get("skills", [])
        
        cv_job_titles = cv_structured.get("job_titles", [])
        jd_job_titles = jd_structured.get("job_titles", [])
        
        cv_degrees = cv_structured.get("degrees", [])
        jd_degrees = jd_structured.get("degrees", [])
        
        cv_certs = cv_structured.get("certifications", [])
        jd_certs = jd_structured.get("certifications", [])
        
        # Điểm thành phần 2: Khớp kỹ năng
        skill_score = self._calculate_skill_score(cv_skills, jd_skills)
        
        # Điểm thành phần 3: Khớp job titles
        job_title_score = self._calculate_entity_match_score(cv_job_titles, jd_job_titles)
        
        # Điểm thành phần 4: Khớp education và certifications
        education_cert_jd = jd_degrees + jd_certs
        education_cert_cv = cv_degrees + cv_certs
        education_cert_score = self._calculate_entity_match_score(education_cert_cv, education_cert_jd)
        
        # Tính điểm tổng hợp
        total_score = (
            overall_score * self.weights["overall_semantic"] +
            skill_score * self.weights["skill_match"] +
            job_title_score * self.weights["job_title_match"] +
            education_cert_score * self.weights["education_cert_match"]
        )
        
        return {
            "total_score": round(total_score, 4),
            "breakdown": {
                "overall_semantic": round(overall_score, 4),
                "skill_match": round(skill_score, 4),
                "job_title_match": round(job_title_score, 4),
                "education_cert_match": round(education_cert_score, 4)
            }
        }
    
    def _calculate_overall_semantic_score(self, cv_embedding: List[float], jd_embedding: List[float]) -> float:
        """
        Tính điểm tương đồng ngữ nghĩa tổng thể
        
        Args:
            cv_embedding: Vector nhúng tổng thể của CV
            jd_embedding: Vector nhúng tổng thể của JD
            
        Returns:
            Điểm cosine similarity (0-1)
        """
        cv_array = np.array(cv_embedding).reshape(1, -1)
        jd_array = np.array(jd_embedding).reshape(1, -1)
        
        similarity = cosine_similarity(cv_array, jd_array)[0][0]
        # Đảm bảo điểm số nằm trong khoảng [0, 1]
        return max(0.0, min(1.0, similarity))
    
    def _calculate_skill_score(self, cv_skills: List[str], jd_skills: List[str]) -> float:
        """
        Tính điểm khớp kỹ năng sử dụng semantic similarity
        
        Args:
            cv_skills: Danh sách kỹ năng trong CV
            jd_skills: Danh sách kỹ năng trong JD
            
        Returns:
            Điểm khớp kỹ năng (0-1)
        """
        if not jd_skills:
            return 1.0
        
        if not cv_skills:
            return 0.0
        
        try:
            # Tạo embeddings cho tất cả skills cùng lúc (tối ưu hóa)
            all_skills = cv_skills + jd_skills
            all_embeddings = self.embedding_service.get_embeddings_batch(all_skills)
            
            cv_embeddings = all_embeddings[:len(cv_skills)]
            jd_embeddings = all_embeddings[len(cv_skills):]
            
            # Chuyển đổi sang numpy arrays
            cv_array = np.array(cv_embeddings)
            jd_array = np.array(jd_embeddings)
            
            # Tính ma trận tương đồng cosine
            similarity_matrix = cosine_similarity(jd_array, cv_array)
            
            # Với mỗi kỹ năng JD, tìm điểm tương đồng cao nhất với bất kỳ kỹ năng CV nào
            max_similarities = np.max(similarity_matrix, axis=1)
            
            # Trả về điểm trung bình
            avg_score = float(np.mean(max_similarities))
            
            # Đảm bảo điểm số nằm trong khoảng [0, 1]
            return max(0.0, min(1.0, avg_score))
            
        except Exception as e:
            raise RuntimeError(f"Lỗi khi tính điểm khớp kỹ năng: {e}")
    
    def _calculate_entity_match_score(self, cv_entities: List[str], jd_entities: List[str]) -> float:
        """
        Tính điểm khớp thực thể (exact match sau khi chuẩn hóa)
        
        Args:
            cv_entities: Danh sách thực thể trong CV
            jd_entities: Danh sách thực thể trong JD
            
        Returns:
            Tỷ lệ phần trăm thực thể JD xuất hiện trong CV (0-1)
        """
        if not jd_entities:
            return 1.0
        
        if not cv_entities:
            return 0.0
        
        # Chuẩn hóa văn bản
        def normalize_text(text: str) -> str:
            return text.lower().strip().replace(" ", "")
        
        normalized_cv = {normalize_text(entity) for entity in cv_entities}
        normalized_jd = [normalize_text(entity) for entity in jd_entities]
        
        # Đếm số thực thể JD xuất hiện trong CV
        matches = sum(1 for jd_entity in normalized_jd if jd_entity in normalized_cv)
        
        # Trả về tỷ lệ phần trăm
        return matches / len(normalized_jd)

