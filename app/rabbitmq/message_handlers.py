"""
RabbitMQ Message Handlers

Xử lý messages từ Spring Boot theo format:
{
  "applicationId": 12345,
  "fileUrl": "https://example.com/cv.pdf",
  "version": 1,
  "jobTitle": "Senior Python Developer",
  "jobDescription": "We are looking for...",
  "jobResponsibilities": "Design and implement...",
  "educationLevel": "Bachelor's degree in Computer Science",
  "experienceLevel": "5+ years of experience"
}
"""

import json
import logging
import requests
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, Tuple
from openai import OpenAI
from openai import BadRequestError

from core.config import settings
from core.schemas import StructuredData
from app.services.parser_service import ParserService
from app.services.structuring_service import StructuringService
from app.services.embedding_service import EmbeddingService
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


class MessageHandlers:
    """Xử lý messages từ RabbitMQ"""
    
    def __init__(self):
        # Khởi tạo OpenAI client
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Khởi tạo các services
        self.parser_service = ParserService()
        self.structuring_service = StructuringService(self.openai_client)
        self.embedding_service = EmbeddingService(self.openai_client)
        self.scoring_service = ScoringService(self.embedding_service)
        
        logger.info("MessageHandlers đã được khởi tạo")
    
    def handle_message(self, message_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """
        Xử lý message chính từ Spring Boot
        
        Args:
            message_data: Dữ liệu message từ RabbitMQ
            
        Returns:
            Tuple[success, response_data, error_type]
            - success: True/False
            - response_data: Dữ liệu kết quả
            - error_type: "DATA_ERROR" hoặc "SYSTEM_ERROR"
        """
        try:
            # Validate message structure
            if not isinstance(message_data, dict):
                return False, {
                    "applicationId": None,
                    "isSuccess": False,
                    "version": None,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": "Invalid message format",
                    "data": None
                }, "DATA_ERROR"
            
            # Validate required fields theo format mới của Spring Boot
            required_fields = ["applicationId", "fileUrl", "jobTitle", "jobDescription"]
            missing_fields = [field for field in required_fields if field not in message_data]
            
            if missing_fields:
                app_id = message_data.get("applicationId")
                version = message_data.get("version")
                return False, {
                    "applicationId": app_id,
                    "isSuccess": False,
                    "version": version,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                    "data": None
                }, "DATA_ERROR"
            
            # Extract data
            application_id = message_data["applicationId"]
            file_url = message_data["fileUrl"]
            version = message_data.get("version", 1)
            job_title = message_data["jobTitle"]
            job_description = message_data["jobDescription"]
            job_responsibilities = message_data.get("jobResponsibilities", "")
            education_level = message_data.get("educationLevel", "")
            experience_level = message_data.get("experienceLevel", "")
            
            logger.info(f"Xử lý matching cho applicationId={application_id}, version={version}")
            
            # Validate fileUrl
            if not file_url or not file_url.strip():
                return False, {
                    "applicationId": application_id,
                    "isSuccess": False,
                    "version": version,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": "fileUrl is empty",
                    "data": None
                }, "DATA_ERROR"
            
            # Bước 1: Tải và parse CV từ fileUrl
            logger.info(f"Bước 1: Tải CV từ URL: {file_url}")
            cv_content = self._download_and_parse_cv(file_url)
            
            if not cv_content:
                return False, {
                    "applicationId": application_id,
                    "isSuccess": False,
                    "version": version,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": "Failed to download or parse CV file",
                    "data": None
                }, "SYSTEM_ERROR"
            
            # Bước 2: Kết hợp thông tin JD thành một đoạn text
            logger.info("Bước 2: Tổng hợp thông tin Job Description...")
            jd_content = self._build_jd_content(
                job_title, 
                job_description, 
                job_responsibilities,
                education_level,
                experience_level
            )
            
            # Bước 3: Trích xuất structured data từ CV
            logger.info("Bước 3: Trích xuất thông tin từ CV...")
            try:
                cv_structured_json = self.structuring_service.get_structured_data(
                    cv_content,
                    StructuredData
                )
            except BadRequestError as e:
                if "maximum context length" in str(e):
                    logger.error(f"CV content quá dài, vượt quá token limit: {len(cv_content)} chars")
                    return False, {
                        "applicationId": application_id,
                        "isSuccess": False,
                        "version": version,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "error": "CV content is too long and exceeds token limit. Please provide a shorter CV file",
                        "data": None
                    }, "DATA_ERROR"
                raise
            
            # Bước 4: Trích xuất structured data từ JD
            logger.info("Bước 4: Trích xuất thông tin từ Job Description...")
            try:
                jd_structured_json = self.structuring_service.get_structured_data(
                    jd_content,
                    StructuredData
                )
            except BadRequestError as e:
                if "maximum context length" in str(e):
                    logger.error(f"JD content quá dài, vượt quá token limit: {len(jd_content)} chars")
                    return False, {
                        "applicationId": application_id,
                        "isSuccess": False,
                        "version": version,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "error": "Job description is too long and exceeds token limit. Please provide a shorter job description",
                        "data": None
                    }, "DATA_ERROR"
                raise
            
            # Bước 5: Tạo embeddings
            logger.info("Bước 5: Tạo embeddings...")
            try:
                cv_embedding = self.embedding_service.get_embedding(cv_content)
            except BadRequestError as e:
                if "maximum context length" in str(e):
                    logger.error(f"CV content quá dài cho embedding: {len(cv_content)} chars")
                    return False, {
                        "applicationId": application_id,
                        "isSuccess": False,
                        "version": version,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "error": "CV content is too long for embedding generation. Please provide a shorter CV file",
                        "data": None
                    }, "DATA_ERROR"
                raise
            except RuntimeError as e:
                # RuntimeError được raise từ embedding_service khi có BadRequestError
                if "maximum context length" in str(e):
                    logger.error(f"CV content quá dài cho embedding: {len(cv_content)} chars")
                    return False, {
                        "applicationId": application_id,
                        "isSuccess": False,
                        "version": version,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "error": "CV content is too long for embedding generation. Please provide a shorter CV file",
                        "data": None
                    }, "DATA_ERROR"
                raise
            
            try:
                jd_embedding = self.embedding_service.get_embedding(jd_content)
            except BadRequestError as e:
                if "maximum context length" in str(e):
                    logger.error(f"JD content quá dài cho embedding: {len(jd_content)} chars")
                    return False, {
                        "applicationId": application_id,
                        "isSuccess": False,
                        "version": version,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "error": "Job description is too long for embedding generation. Please provide a shorter job description",
                        "data": None
                    }, "DATA_ERROR"
                raise
            except RuntimeError as e:
                # RuntimeError được raise từ embedding_service khi có BadRequestError
                if "maximum context length" in str(e):
                    logger.error(f"JD content quá dài cho embedding: {len(jd_content)} chars")
                    return False, {
                        "applicationId": application_id,
                        "isSuccess": False,
                        "version": version,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "error": "Job description is too long for embedding generation. Please provide a shorter job description",
                        "data": None
                    }, "DATA_ERROR"
                raise
            
            # Bước 6: Tính điểm matching
            logger.info("Bước 6: Tính điểm matching...")
            cv_data = {
                "embedding": cv_embedding,
                "structured_json": cv_structured_json
            }
            
            jd_data = {
                "embedding": jd_embedding,
                "structured_json": jd_structured_json
            }
            
            score_result = self.scoring_service.calculate_match_score(cv_data, jd_data)
            
            # Prepare response với 6 tiêu chí đánh giá
            breakdown = score_result.get("breakdown", {})
            
            # Tạo response theo format mới
            response_data = {
                "applicationId": application_id,
                "isSuccess": True,
                "version": version,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": None,
                "data": {
                    "applicationId": application_id,
                    "matchScore": round(score_result["total_score"] * 100, 2),  # Convert to 0-100 scale
                    "breakdown": {
                        "hardSkillsScore": round(breakdown.get("hard_skills", 0) * 100, 2),
                        "workExperienceScore": round(breakdown.get("work_experience", 0) * 100, 2),
                        "responsibilitiesAchievementsScore": round(breakdown.get("responsibilities", 0) * 100, 2),
                        "softSkillsScore": round(breakdown.get("soft_skills", 0) * 100, 2),
                        "educationTrainingScore": round(breakdown.get("education", 0) * 100, 2),
                        "additionalFactorsScore": round(breakdown.get("additional_factors", 0) * 100, 2)
                    }
                }
            }
            
            logger.info(f"Hoàn thành matching: score={score_result['total_score']:.2f}")
            return True, response_data, None
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            app_id = message_data.get("applicationId") if isinstance(message_data, dict) else None
            version = message_data.get("version") if isinstance(message_data, dict) else None
            return False, {
                "applicationId": app_id,
                "isSuccess": False,
                "version": version,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": f"Invalid JSON: {str(e)}",
                "data": None
            }, "DATA_ERROR"
        except KeyError as e:
            logger.error(f"Missing field error: {str(e)}")
            app_id = message_data.get("applicationId") if isinstance(message_data, dict) else None
            version = message_data.get("version") if isinstance(message_data, dict) else None
            return False, {
                "applicationId": app_id,
                "isSuccess": False,
                "version": version,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": f"Missing required field: {str(e)}",
                "data": None
            }, "DATA_ERROR"
        except Exception as e:
            logger.error(f"System error in handle_message: {str(e)}", exc_info=True)
            app_id = message_data.get("applicationId") if isinstance(message_data, dict) else None
            version = message_data.get("version") if isinstance(message_data, dict) else None
            return False, {
                "applicationId": app_id,
                "isSuccess": False,
                "version": version,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": f"System error: {str(e)}",
                "data": None
            }, "SYSTEM_ERROR"
    
    def _download_and_parse_cv(self, file_url: str) -> str:
        """
        Tải CV từ URL và parse thành text
        
        Args:
            file_url: URL của file CV (PDF hoặc DOCX)
            
        Returns:
            str: Nội dung text của CV
        """
        try:
            # Download file
            logger.info(f"Đang tải file từ: {file_url}")
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            
            # Xác định extension từ URL hoặc Content-Type
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' in content_type or file_url.lower().endswith('.pdf'):
                extension = '.pdf'
            elif 'word' in content_type or file_url.lower().endswith('.docx'):
                extension = '.docx'
            else:
                # Try to guess from filename in URL
                if '.pdf' in file_url.lower():
                    extension = '.pdf'
                elif '.docx' in file_url.lower():
                    extension = '.docx'
                else:
                    logger.error(f"Không xác định được loại file từ URL: {file_url}")
                    return None
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
                tmp_file.write(response.content)
                tmp_file_path = tmp_file.name
            
            try:
                # Parse file
                logger.info(f"Đang parse file: {tmp_file_path}")
                text_content = self.parser_service.parse_file(tmp_file_path)
                return text_content
            finally:
                # Clean up temp file
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
                    
        except requests.RequestException as e:
            logger.error(f"Lỗi khi download file từ URL {file_url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Lỗi khi parse CV: {str(e)}", exc_info=True)
            return None
    
    def _build_jd_content(
        self, 
        job_title: str, 
        job_description: str, 
        job_responsibilities: str = "",
        education_level: str = "",
        experience_level: str = ""
    ) -> str:
        """
        Kết hợp các thông tin JD thành một đoạn text hoàn chỉnh
        
        Args:
            job_title: Tiêu đề công việc
            job_description: Mô tả công việc
            job_responsibilities: Trách nhiệm công việc
            education_level: Yêu cầu học vấn
            experience_level: Yêu cầu kinh nghiệm
            
        Returns:
            str: Nội dung JD đầy đủ
        """
        sections = []
        
        # Job Title
        if job_title:
            sections.append(f"JOB TITLE: {job_title}")
        
        # Job Description
        if job_description:
            sections.append(f"\nJOB DESCRIPTION:\n{job_description}")
        
        # Responsibilities
        if job_responsibilities:
            sections.append(f"\nRESPONSIBILITIES:\n{job_responsibilities}")
        
        # Education Level
        if education_level:
            sections.append(f"\nEDUCATION REQUIREMENTS:\n{education_level}")
        
        # Experience Level
        if experience_level:
            sections.append(f"\nEXPERIENCE REQUIREMENTS:\n{experience_level}")
        
        jd_content = "\n".join(sections)
        logger.info(f"Đã tổng hợp JD content: {len(jd_content)} characters")
        
        return jd_content
