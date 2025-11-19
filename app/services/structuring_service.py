import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from pydantic import BaseModel
from typing import Dict, Any


class StructuringService:
    """Dịch vụ cấu trúc hóa dữ liệu sử dụng GPT-4o-mini"""
    
    def __init__(self, openai_client: OpenAI):
        """
        Khởi tạo StructuringService
        
        Args:
            openai_client: Client OpenAI đã được khởi tạo
        """
        self.client = openai_client
    
    def get_structured_data(self, text_content: str, schema: BaseModel) -> dict:
        """
        Trích xuất và cấu trúc hóa dữ liệu từ văn bản sử dụng GPT-4o-mini
        
        Args:
            text_content: Văn bản thô cần phân tích
            schema: Pydantic model định nghĩa cấu trúc dữ liệu mong muốn
            
        Returns:
            Dictionary chứa dữ liệu đã được cấu trúc hóa
        """
        # Lấy JSON schema từ Pydantic model
        json_schema = schema.model_json_schema()
        
        # Create system prompt in English
        system_prompt = f"""You are an expert in extracting structured data from CVs and Job Descriptions with extensive experience in recruitment and talent matching.

Your task is to analyze the provided text and extract important information following this JSON schema structure:

{json.dumps(json_schema, indent=2, ensure_ascii=False)}

EXTRACTION GUIDELINES:

1. HARD SKILLS (30.0% importance) - Extract:
   - Programming languages (Python, Java, C++, etc.)
   - Technologies and frameworks (React, Django, TensorFlow, Docker, etc.)
   - Professional tools and software (Git, Jira, Adobe Suite, etc.)
   - Professional certifications (AWS Certified, PMP, etc.)
   - Industry-specific technical skills

2. WORK EXPERIENCE (25.0% importance) - Extract:
   - Total years of experience (calculate from dates if provided)
   - All job titles/positions held
   - Industries/sectors worked in
   - Company names
   - Company sizes or project scales (startup, SME, enterprise)

3. RESPONSIBILITIES & ACHIEVEMENTS (15.0% importance) - Extract:
   - Key responsibilities from each role
   - Notable achievements, results, quantifiable impacts
   - Types of projects worked on
   - Scope and scale of work

4. SOFT SKILLS (10.0% importance) - Extract:
   - Communication and teamwork abilities
   - Leadership and management skills
   - Problem-solving and analytical thinking
   - Adaptability and learning capability

5. EDUCATION & TRAINING (5.0% importance) - Extract:
   - Academic degrees (Bachelor, Master, PhD, etc.)
   - Majors/specializations
   - Universities/institutions
   - Additional courses, bootcamps, training programs

6. ADDITIONAL FACTORS (15.0% importance) - Extract:
   - Languages spoken and proficiency levels
   - Availability to start work
   - Willingness to relocate or travel
   - Expected salary if mentioned

IMPORTANT RULES:
- Return ONLY valid JSON matching the schema exactly
- If information is not found for a field, use empty array [] or null
- For JD (Job Description): Focus on REQUIREMENTS and pay attention to keywords like "required", "must have", "essential"
- For CV: Extract ALL relevant information mentioned
- Be thorough and comprehensive - extract everything relevant
- Maintain consistency in terminology
- Use English for all extracted data

LEGACY FIELDS (for backward compatibility):
- Also populate 'skills', 'job_titles', 'degrees', 'certifications' fields by combining relevant data from the structured categories"""
        
        # Create user message in English
        user_message = f"""Please analyze and extract structured information from the following text:

{text_content}"""
        
        # Tạo timestamp để match prompts và responses
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Lưu prompts vào folder prompts
        self._dump_prompts(timestamp, {
            "system_prompt": system_prompt,
            "user_message": user_message,
            "json_schema": json_schema
        })

        try:
            # Gọi API Chat Completions
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1  # Giảm temperature để kết quả nhất quán hơn
            )
            
            # Lấy nội dung phản hồi
            content = response.choices[0].message.content
            
            # Lưu response vào folder responses
            self._dump_response(timestamp, {
                "model": response.model,
                "content": content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "total_tokens": response.usage.total_tokens if response.usage else None
                },
                "finish_reason": response.choices[0].finish_reason if response.choices else None
            })
            
            # Parse JSON
            structured_data = json.loads(content)
            
            return structured_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Không thể parse JSON từ phản hồi của OpenAI: {e}")
        except Exception as e:
            raise RuntimeError(f"Lỗi khi gọi OpenAI API: {e}")

    def _dump_prompts(self, timestamp: str, payload: Dict[str, Any]) -> None:
        """
        Lưu prompts vào thư mục io_dump/prompts để tiện kiểm tra
        
        Args:
            timestamp: Timestamp để match với response
            payload: Dữ liệu prompts cần lưu
        """
        try:
            prompts_dir = Path("io_dump") / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            file_path = prompts_dir / f"prompt_{timestamp}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            # Không để việc ghi file ảnh hưởng flow chính
            pass
    
    def _dump_response(self, timestamp: str, payload: Dict[str, Any]) -> None:
        """
        Lưu response từ LLM vào thư mục io_dump/responses
        
        Args:
            timestamp: Timestamp để match với prompt (cùng timestamp)
            payload: Dữ liệu response cần lưu
        """
        try:
            responses_dir = Path("io_dump") / "responses"
            responses_dir.mkdir(parents=True, exist_ok=True)
            file_path = responses_dir / f"response_{timestamp}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            # Không để việc ghi file ảnh hưởng flow chính
            pass

