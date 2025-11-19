import chromadb
import json
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional


class VectorStoreService:
    """Dịch vụ quản lý kho vector sử dụng ChromaDB"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Khởi tạo VectorStoreService
        
        Args:
            persist_directory: Thư mục lưu trữ dữ liệu ChromaDB
        """
        # Khởi tạo ChromaDB client với persistent storage
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Tạo hoặc lấy collections
        self.cv_collection = self.client.get_or_create_collection(
            name="cv_collection",
            metadata={"description": "Collection lưu trữ CV embeddings và metadata"}
        )
        
        self.jd_collection = self.client.get_or_create_collection(
            name="jd_collection",
            metadata={"description": "Collection lưu trữ Job Description embeddings và metadata"}
        )
    
    def add_document(self, collection_name: str, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        """
        Thêm document vào collection
        
        Args:
            collection_name: Tên collection ("cv_collection" hoặc "jd_collection")
            doc_id: ID duy nhất của document
            embedding: Vector nhúng của document
            metadata: Metadata chứa structured JSON và các thông tin khác
        """
        collection = self._get_collection(collection_name)
        
        # ChromaDB chỉ chấp nhận str, int, float, bool trong metadata
        # Cần serialize các list/dict thành JSON string
        sanitized_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (list, dict)):
                # Chuyển list/dict thành JSON string
                sanitized_metadata[key] = json.dumps(value, ensure_ascii=False)
            elif value is None:
                # Bỏ qua None
                continue
            else:
                # Giữ nguyên str, int, float, bool
                sanitized_metadata[key] = value
        
        collection.add(
            embeddings=[embedding],
            ids=[doc_id],
            metadatas=[sanitized_metadata]
        )
    
    def get_document_by_id(self, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy document theo ID
        
        Args:
            collection_name: Tên collection
            doc_id: ID của document
            
        Returns:
            Dictionary chứa embedding và metadata, hoặc None nếu không tìm thấy
        """
        collection = self._get_collection(collection_name)
        
        try:
            result = collection.get(
                ids=[doc_id],
                include=["embeddings", "metadatas"]
            )
            
            if result["ids"]:
                raw_metadata = result["metadatas"][0]
                
                # Deserialize JSON strings về list/dict
                deserialized_metadata = {}
                for key, value in raw_metadata.items():
                    if isinstance(value, str):
                        # Thử parse JSON string
                        try:
                            deserialized_metadata[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            # Nếu không phải JSON, giữ nguyên string
                            deserialized_metadata[key] = value
                    else:
                        deserialized_metadata[key] = value
                
                return {
                    "embedding": result["embeddings"][0],
                    "metadata": deserialized_metadata
                }
            return None
            
        except Exception as e:
            raise RuntimeError(f"Lỗi khi lấy document từ collection: {e}")
    
    def _get_collection(self, collection_name: str):
        """Lấy collection theo tên"""
        if collection_name == "cv_collection":
            return self.cv_collection
        elif collection_name == "jd_collection":
            return self.jd_collection
        else:
            raise ValueError(f"Collection không hợp lệ: {collection_name}. Chỉ hỗ trợ 'cv_collection' và 'jd_collection'")

