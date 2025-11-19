import os
from typing import Optional
import pdfplumber
from docx import Document


class ParserService:
    """Dịch vụ phân tích cú pháp để trích xuất văn bản từ PDF và DOCX"""
    
    def parse_file(self, file_path: str) -> str:
        """
        Trích xuất văn bản thô từ file PDF hoặc DOCX
        
        Args:
            file_path: Đường dẫn đến file cần parse
            
        Returns:
            Chuỗi văn bản thô đã được dọn dẹp
            
        Raises:
            ValueError: Nếu file không phải là PDF hoặc DOCX
            FileNotFoundError: Nếu file không tồn tại
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File không tồn tại: {file_path}")
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self._parse_pdf(file_path)
        elif file_extension == '.docx':
            return self._parse_docx(file_path)
        else:
            raise ValueError(f"Định dạng file không được hỗ trợ: {file_extension}. Chỉ hỗ trợ .pdf và .docx")
    
    def _parse_pdf(self, file_path: str) -> str:
        """Trích xuất văn bản từ file PDF"""
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        raw_text = "\n".join(text_parts)
        return self._clean_text(raw_text)
    
    def _parse_docx(self, file_path: str) -> str:
        """Trích xuất văn bản từ file DOCX"""
        doc = Document(file_path)
        text_parts = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        raw_text = "\n".join(text_parts)
        return self._clean_text(raw_text)
    
    def _clean_text(self, text: str) -> str:
        """Dọn dẹp văn bản: loại bỏ khoảng trắng thừa, chuẩn hóa"""
        # Loại bỏ khoảng trắng thừa
        lines = [line.strip() for line in text.split('\n')]
        # Loại bỏ dòng trống liên tiếp
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            if line:
                cleaned_lines.append(line)
                prev_empty = False
            elif not prev_empty:
                cleaned_lines.append(line)
                prev_empty = True
        
        return "\n".join(cleaned_lines).strip()

