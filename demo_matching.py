"""
Demo script để chạy CV-JD Matching với nhiều CVs
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI

from core.config import settings
from core.schemas import StructuredData
from app.services.parser_service import ParserService
from app.services.structuring_service import StructuringService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.scoring_service import ScoringService


class CVJDMatchingDemo:
    """Demo class để chạy CV-JD matching với nhiều CVs"""
    
    def __init__(self):
        """Khởi tạo các services"""
        print("\n[INIT] Khởi tạo các services...")
        
        # Khởi tạo OpenAI client
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        print("✓ OpenAI client initialized")
        
        # Khởi tạo các services
        self.parser_service = ParserService()
        print("✓ Parser service initialized")
        
        self.structuring_service = StructuringService(self.openai_client)
        print("✓ Structuring service initialized")
        
        self.embedding_service = EmbeddingService(self.openai_client)
        print("✓ Embedding service initialized")
        
        self.vector_store_service = VectorStoreService()
        print("✓ Vector store service initialized")
        
        self.scoring_service = ScoringService(self.embedding_service)
        print("✓ Scoring service initialized")
        
        # Lưu trữ IDs
        self.cv_ids = []
        self.jd_id = None
    
    def process_cv(self, cv_path: Path) -> str:
        """
        Xử lý một CV file
        
        Args:
            cv_path: Đường dẫn đến file CV
            
        Returns:
            CV ID
        """
        print(f"\n[STEP 1] Parsing CV file: {cv_path.name}...")
        text_content = self.parser_service.parse_file(str(cv_path))
        print(f"✓ Extracted {len(text_content)} characters")
        
        print(f"[STEP 2] Extracting structured data with GPT-4o-mini...")
        structured_json = self.structuring_service.get_structured_data(
            text_content,
            StructuredData
        )
        print("✓ Structured data extracted")
        
        print(f"[STEP 3] Creating embedding...")
        embedding = self.embedding_service.get_embedding(text_content)
        print("✓ Embedding created")
        
        print(f"[STEP 4] Storing in vector database...")
        cv_id = str(uuid.uuid4())
        self.vector_store_service.add_document(
            collection_name="cv_collection",
            doc_id=cv_id,
            embedding=embedding,
            metadata=structured_json
        )
        print(f"✓ CV stored with ID: {cv_id}")
        
        self.cv_ids.append(cv_id)
        return cv_id
    
    def process_jd(self, jd_path: Path) -> str:
        """
        Xử lý một JD file
        
        Args:
            jd_path: Đường dẫn đến file JD
            
        Returns:
            JD ID
        """
        print(f"\n{'='*80}")
        print(f"[PROCESS JD] {jd_path.name}")
        print(f"{'='*80}")
        
        print(f"\n[STEP 1] Parsing JD file...")
        text_content = self.parser_service.parse_file(str(jd_path))
        print(f"✓ Extracted {len(text_content)} characters")
        
        print(f"\n--- Text Preview (first 500 chars) ---")
        print(text_content[:500])
        print("--- End Preview ---\n")
        
        print(f"[STEP 2] Extracting structured data with GPT-4o-mini...")
        structured_json = self.structuring_service.get_structured_data(
            text_content,
            StructuredData
        )
        print("✓ Structured data extracted")
        
        print(f"[STEP 3] Creating embedding...")
        embedding = self.embedding_service.get_embedding(text_content)
        print("✓ Embedding created")
        
        print(f"[STEP 4] Storing in vector database...")
        jd_id = str(uuid.uuid4())
        self.vector_store_service.add_document(
            collection_name="jd_collection",
            doc_id=jd_id,
            embedding=embedding,
            metadata=structured_json
        )
        print(f"✓ JD stored with ID: {jd_id}")
        
        self.jd_id = jd_id
        return jd_id
    
    def match_cv_jd(self, cv_id: str, jd_id: str) -> Dict[str, Any]:
        """
        So khớp CV và JD
        
        Args:
            cv_id: ID của CV
            jd_id: ID của JD
            
        Returns:
            Kết quả matching
        """
        # Lấy dữ liệu từ vector store
        cv_doc = self.vector_store_service.get_document_by_id("cv_collection", cv_id)
        jd_doc = self.vector_store_service.get_document_by_id("jd_collection", jd_id)
        
        if not cv_doc or not jd_doc:
            raise ValueError(f"CV or JD not found")
        
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
        score_result = self.scoring_service.calculate_match_score(cv_data, jd_data)
        
        return score_result
    
    def run_demo(self, cv_folder: str, jd_path: str):
        """
        Chạy demo với nhiều CVs và 1 JD
        
        Args:
            cv_folder: Đường dẫn đến folder chứa CVs
            jd_path: Đường dẫn đến file JD
        """
        cv_folder_path = Path(cv_folder)
        jd_path_obj = Path(jd_path)
        
        # Kiểm tra paths
        if not cv_folder_path.exists():
            raise FileNotFoundError(f"CV folder not found: {cv_folder}")
        if not jd_path_obj.exists():
            raise FileNotFoundError(f"JD file not found: {jd_path}")
        
        # Tìm các CV files
        cv_files = list(cv_folder_path.glob("*.pdf")) + list(cv_folder_path.glob("*.docx"))
        
        if not cv_files:
            raise ValueError(f"No CV files found in {cv_folder}")
        
        print(f"\n{'='*80}")
        print("CV-JD MATCHING SYSTEM DEMO")
        print(f"{'='*80}")
        print(f"\nFound {len(cv_files)} CV files")
        print(f"JD file: {jd_path_obj.name}")
        
        # Xử lý JD trước
        self.process_jd(jd_path_obj)
        
        # Xử lý từng CV
        print(f"\n{'='*80}")
        print(f"[PROCESSING {len(cv_files)} CVs]")
        print(f"{'='*80}")
        
        for i, cv_file in enumerate(cv_files, 1):
            print(f"\n{'='*80}")
            print(f"[CV {i}/{len(cv_files)}] {cv_file.name}")
            print(f"{'='*80}")
            try:
                self.process_cv(cv_file)
            except Exception as e:
                print(f"❌ Error processing {cv_file.name}: {e}")
                continue
        
        # Matching
        print(f"\n{'='*80}")
        print("[MATCHING] Calculating scores...")
        print(f"{'='*80}")
        
        results = []
        for i, cv_id in enumerate(self.cv_ids, 1):
            try:
                cv_file = cv_files[i - 1]
                print(f"\n[Matching {i}/{len(self.cv_ids)}] {cv_file.name}...")
                
                score_result = self.match_cv_jd(cv_id, self.jd_id)
                
                result = {
                    "cv_file": cv_file.name,
                    "cv_id": cv_id,
                    "jd_file": jd_path_obj.name,
                    "jd_id": self.jd_id,
                    "total_score": score_result["total_score"],
                    "breakdown": score_result.get("breakdown", {}),
                    "category_weights": score_result.get("category_weights", {}),
                    "detailed_analysis": score_result.get("detailed_analysis", {})
                }
                
                results.append(result)
                print(f"✓ Total Score: {score_result['total_score']:.4f}")
                
                # Hiển thị breakdown nếu có
                if "breakdown" in score_result and score_result["breakdown"]:
                    print("  Category Scores:")
                    for category, score in score_result["breakdown"].items():
                        print(f"    - {category}: {score:.4f}")
                
            except Exception as e:
                print(f"❌ Error matching {cv_file.name}: {e}")
                continue
        
        # Sắp xếp theo điểm số
        results.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Hiển thị kết quả
        print(f"\n{'='*80}")
        print("[RESULTS] Ranking by Score")
        print(f"{'='*80}")
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['cv_file']}")
            print(f"   Total Score: {result['total_score']:.4f}")
            if "breakdown" in result and result["breakdown"]:
                print("   Category Breakdown:")
                for category, score in result["breakdown"].items():
                    weight = result.get("category_weights", {}).get(category, 0)
                    weighted = score * weight
                    print(f"     - {category}: {score:.4f} (weight: {weight:.0%}, contribution: {weighted:.4f})")
        
        # Lưu kết quả
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"matching_results_{timestamp}.json"
        
        output_data = {
            "timestamp": timestamp,
            "jd_file": jd_path_obj.name,
            "jd_id": self.jd_id,
            "total_cvs": len(results),
            "results": results
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*80}")
        print(f"✅ Results saved to: {output_file}")
        print(f"{'='*80}")


def main():
    """Main function để chạy từ command line"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python demo_matching.py <cv_folder> <jd_file>")
        print("\nExample:")
        print("  python demo_matching.py ./input/cvs ./input/jds/jd_AIE.docx")
        sys.exit(1)
    
    cv_folder = sys.argv[1]
    jd_file = sys.argv[2]
    
    demo = CVJDMatchingDemo()
    demo.run_demo(cv_folder, jd_file)


if __name__ == "__main__":
    main()

