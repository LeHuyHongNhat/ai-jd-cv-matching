from openai import OpenAI
from typing import List, Union


class EmbeddingService:
    """Dịch vụ nhúng văn bản sử dụng text-embedding-3-small"""
    
    def __init__(self, openai_client: OpenAI):
        """
        Khởi tạo EmbeddingService
        
        Args:
            openai_client: Client OpenAI đã được khởi tạo
        """
        self.client = openai_client
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Tạo vector nhúng cho một đoạn văn bản
        
        Args:
            text: Văn bản cần nhúng
            
        Returns:
            List các số float biểu diễn vector nhúng
        """
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"Lỗi khi tạo embedding: {e}")
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Tạo vector nhúng cho nhiều đoạn văn bản cùng lúc (tối ưu hóa)
        
        Args:
            texts: Danh sách các văn bản cần nhúng
            
        Returns:
            List các list float, mỗi list là một vector nhúng
        """
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise RuntimeError(f"Lỗi khi tạo embeddings hàng loạt: {e}")

