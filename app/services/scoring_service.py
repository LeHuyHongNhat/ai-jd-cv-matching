from typing import Dict, Any

from app.services.embedding_service import EmbeddingService
from app.services.scoring_service_new import EnhancedScoringService


class ScoringService:
    """Public scoring interface that always uses the new 6-category structure."""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.enhanced_service = EnhancedScoringService(embedding_service)

    def calculate_match_score(self, cv_data: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate CV-JD match score using the new structured schema exclusively.

        Args:
            cv_data: Dict containing 'structured_json' using the new schema
            jd_data: Dict containing 'structured_json' using the new schema

        Returns:
            Dict with total_score, breakdown per category, and weights.
        """
        result = self.enhanced_service.calculate_enhanced_match_score(cv_data, jd_data)

        response = {
            "total_score": result["total_score"],
            "breakdown": result["category_scores"],
            "category_weights": result["category_weights"],
        }

        if "detailed_analysis" in result:
            response["detailed_analysis"] = result["detailed_analysis"]

        return response

