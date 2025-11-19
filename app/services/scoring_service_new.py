"""
Enhanced Scoring Service with detailed breakdown
Implements new 6-category scoring system
"""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any
from app.services.embedding_service import EmbeddingService


class EnhancedScoringService:
    """
    Enhanced scoring service implementing the 6-category evaluation system:
    1. Hard Skills (35-40%)
    2. Work Experience (25-30%)
    3. Responsibilities & Achievements (15-20%)
    4. Soft Skills (10-15%)
    5. Education & Training (5-10%)
    6. Additional Factors (5%)
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        """
        Initialize Enhanced Scoring Service
        
        Args:
            embedding_service: Service for creating embeddings
        """
        self.embedding_service = embedding_service
        
        # Weights for each category
        self.category_weights = {
            "hard_skills": 0.375,              # 37.5%
            "work_experience": 0.275,          # 27.5%
            "responsibilities": 0.175,         # 17.5%
            "soft_skills": 0.125,              # 12.5%
            "education": 0.075,                # 7.5%
            "additional_factors": 0.05         # 5%
        }
    
    def calculate_enhanced_match_score(self, cv_data: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive matching score using new structure
        
        Args:
            cv_data: Dictionary with 'embedding' and 'structured_json'
            jd_data: Dictionary with 'embedding' and 'structured_json'
            
        Returns:
            Detailed matching result with category breakdown
        """
        cv_struct = cv_data["structured_json"]
        jd_struct = jd_data["structured_json"]
        
        # Check if new structure is available
        has_new_structure = self._check_new_structure(cv_struct, jd_struct)
        
        if has_new_structure:
            # Use new detailed scoring
            scores = self._calculate_detailed_scores(cv_struct, jd_struct)
        else:
            # Fallback to legacy scoring
            scores = self._calculate_legacy_scores(cv_data, jd_data)
        
        # Calculate total score
        total_score = sum(
            scores[category] * self.category_weights[category]
            for category in self.category_weights
            if category in scores
        )
        
        return {
            "total_score": round(total_score, 4),
            "category_scores": scores,
            "category_weights": self.category_weights,
            "detailed_analysis": self._generate_detailed_analysis(cv_struct, jd_struct)
        }
    
    def _check_new_structure(self, cv_struct: Dict, jd_struct: Dict) -> bool:
        """Check if data has new structure"""
        return ("hard_skills" in cv_struct and "hard_skills" in jd_struct)
    
    def _calculate_detailed_scores(self, cv_struct: Dict, jd_struct: Dict) -> Dict[str, float]:
        """Calculate scores for each category using new structure"""
        scores = {}
        
        # 1. Hard Skills (37.5%)
        scores["hard_skills"] = self._score_hard_skills(
            cv_struct.get("hard_skills", {}),
            jd_struct.get("hard_skills", {})
        )
        
        # 2. Work Experience (27.5%)
        scores["work_experience"] = self._score_work_experience(
            cv_struct.get("work_experience", {}),
            jd_struct.get("work_experience", {})
        )
        
        # 3. Responsibilities & Achievements (17.5%)
        scores["responsibilities"] = self._score_responsibilities(
            cv_struct.get("responsibilities_achievements", {}),
            jd_struct.get("responsibilities_achievements", {})
        )
        
        # 4. Soft Skills (12.5%)
        scores["soft_skills"] = self._score_soft_skills(
            cv_struct.get("soft_skills", {}),
            jd_struct.get("soft_skills", {})
        )
        
        # 5. Education & Training (7.5%)
        scores["education"] = self._score_education(
            cv_struct.get("education_training", {}),
            jd_struct.get("education_training", {})
        )
        
        # 6. Additional Factors (5%)
        scores["additional_factors"] = self._score_additional_factors(
            cv_struct.get("additional_factors", {}),
            jd_struct.get("additional_factors", {})
        )
        
        return scores
    
    def _score_hard_skills(self, cv_skills: Dict, jd_skills: Dict) -> float:
        """Score hard skills with emphasis on technical match"""
        all_cv_skills = []
        all_jd_skills = []
        
        # Collect all skills with appropriate weights
        skill_categories = [
            ("programming_languages", 2.0),      # Higher weight for core skills
            ("technologies_frameworks", 1.5),
            ("tools_software", 1.0),
            ("certifications", 1.2),
            ("industry_specific_skills", 1.3)
        ]
        
        for category, weight in skill_categories:
            cv_items = cv_skills.get(category, [])
            jd_items = jd_skills.get(category, [])
            
            # Add with weights
            all_cv_skills.extend([(item, weight) for item in cv_items])
            all_jd_skills.extend([(item, weight) for item in jd_items])
        
        if not all_jd_skills:
            return 1.0
        if not all_cv_skills:
            return 0.0
        
        # Calculate weighted semantic similarity
        try:
            cv_skill_names = [s[0] for s in all_cv_skills]
            jd_skill_names = [s[0] for s in all_jd_skills]
            jd_weights = [s[1] for s in all_jd_skills]
            
            # Get embeddings
            all_skills = cv_skill_names + jd_skill_names
            embeddings = self.embedding_service.get_embeddings_batch(all_skills)
            
            cv_embeddings = embeddings[:len(cv_skill_names)]
            jd_embeddings = embeddings[len(cv_skill_names):]
            
            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(jd_embeddings, cv_embeddings)
            
            # Get max similarity for each JD skill with weighting
            max_similarities = np.max(similarity_matrix, axis=1)
            weighted_similarities = max_similarities * jd_weights
            
            score = float(np.sum(weighted_similarities) / np.sum(jd_weights))
            return max(0.0, min(1.0, score))
            
        except Exception:
            # Fallback to simple matching
            return self._simple_match_score(
                [s[0] for s in all_cv_skills],
                [s[0] for s in all_jd_skills]
            )
    
    def _score_work_experience(self, cv_exp: Dict, jd_exp: Dict) -> float:
        """Score work experience comprehensively"""
        scores = []
        
        # Job titles matching
        cv_titles = cv_exp.get("job_titles", [])
        jd_titles = jd_exp.get("job_titles", [])
        if jd_titles:
            title_score = self._semantic_list_match(cv_titles, jd_titles)
            scores.append((title_score, 0.4))  # 40% weight for titles
        
        # Industry matching
        cv_industries = cv_exp.get("industries", [])
        jd_industries = jd_exp.get("industries", [])
        if jd_industries:
            industry_score = self._simple_match_score(cv_industries, jd_industries)
            scores.append((industry_score, 0.3))  # 30% weight for industry
        
        # Experience years
        cv_years = cv_exp.get("total_years", 0)
        jd_years = jd_exp.get("total_years", 0)
        if jd_years and cv_years:
            # Gradual scoring: 100% if exceeds requirement, proportional if less
            year_score = min(1.0, cv_years / jd_years) if jd_years > 0 else 1.0
            scores.append((year_score, 0.3))  # 30% weight for years
        
        if not scores:
            return 1.0
        
        # Weighted average
        total_weight = sum(w for _, w in scores)
        weighted_score = sum(s * w for s, w in scores) / total_weight if total_weight > 0 else 0.0
        
        return weighted_score
    
    def _score_responsibilities(self, cv_resp: Dict, jd_resp: Dict) -> float:
        """Score responsibilities and achievements"""
        scores = []
        
        # Key responsibilities
        cv_responsibilities = cv_resp.get("key_responsibilities", [])
        jd_responsibilities = jd_resp.get("key_responsibilities", [])
        if jd_responsibilities:
            resp_score = self._semantic_list_match(cv_responsibilities, jd_responsibilities)
            scores.append((resp_score, 0.6))  # 60% for responsibilities
        
        # Achievements
        cv_achievements = cv_resp.get("achievements", [])
        jd_achievements = jd_resp.get("achievements", [])
        if jd_achievements or cv_achievements:
            # Having achievements is a plus
            achievement_score = 1.0 if cv_achievements else 0.5
            scores.append((achievement_score, 0.2))  # 20% for achievements
        
        # Project types
        cv_projects = cv_resp.get("project_types", [])
        jd_projects = jd_resp.get("project_types", [])
        if jd_projects:
            project_score = self._simple_match_score(cv_projects, jd_projects)
            scores.append((project_score, 0.2))  # 20% for project types
        
        if not scores:
            return 1.0
        
        total_weight = sum(w for _, w in scores)
        return sum(s * w for s, w in scores) / total_weight if total_weight > 0 else 0.0
    
    def _score_soft_skills(self, cv_soft: Dict, jd_soft: Dict) -> float:
        """Score soft skills"""
        all_cv_soft = []
        all_jd_soft = []
        
        categories = [
            "communication_teamwork",
            "leadership_management",
            "problem_solving",
            "adaptability"
        ]
        
        for category in categories:
            all_cv_soft.extend(cv_soft.get(category, []))
            all_jd_soft.extend(jd_soft.get(category, []))
        
        if not all_jd_soft:
            return 1.0
        if not all_cv_soft:
            return 0.5  # Soft skills often implicit
        
        return self._semantic_list_match(all_cv_soft, all_jd_soft)
    
    def _score_education(self, cv_edu: Dict, jd_edu: Dict) -> float:
        """Score education and training"""
        scores = []
        
        # Degrees
        cv_degrees = cv_edu.get("degrees", [])
        jd_degrees = jd_edu.get("degrees", [])
        if jd_degrees:
            degree_score = self._simple_match_score(cv_degrees, jd_degrees)
            scores.append((degree_score, 0.5))
        
        # Majors
        cv_majors = cv_edu.get("majors", [])
        jd_majors = jd_edu.get("majors", [])
        if jd_majors:
            major_score = self._semantic_list_match(cv_majors, jd_majors)
            scores.append((major_score, 0.3))
        
        # Additional courses (shows continuous learning)
        cv_courses = cv_edu.get("additional_courses", [])
        if cv_courses:
            scores.append((1.0, 0.2))
        
        if not scores:
            return 1.0
        
        total_weight = sum(w for _, w in scores)
        return sum(s * w for s, w in scores) / total_weight if total_weight > 0 else 0.0
    
    def _score_additional_factors(self, cv_add: Dict, jd_add: Dict) -> float:
        """Score additional factors"""
        scores = []
        
        # Languages
        cv_langs = cv_add.get("languages", [])
        jd_langs = jd_add.get("languages", [])
        if jd_langs:
            lang_score = self._simple_match_score(cv_langs, jd_langs)
            scores.append((lang_score, 0.4))
        
        # Availability
        cv_avail = cv_add.get("availability")
        jd_avail = jd_add.get("availability")
        if jd_avail and cv_avail:
            # Simple check
            avail_score = 1.0 if "immediate" in str(cv_avail).lower() else 0.7
            scores.append((avail_score, 0.3))
        
        # Relocation
        jd_reloc = jd_add.get("relocation_willingness")
        cv_reloc = cv_add.get("relocation_willingness")
        if jd_reloc is not None and cv_reloc is not None:
            reloc_score = 1.0 if jd_reloc == cv_reloc else 0.5
            scores.append((reloc_score, 0.3))
        
        if not scores:
            return 1.0
        
        total_weight = sum(w for _, w in scores)
        return sum(s * w for s, w in scores) / total_weight if total_weight > 0 else 0.0
    
    def _semantic_list_match(self, cv_list: List[str], jd_list: List[str]) -> float:
        """Match two lists using semantic similarity"""
        if not jd_list:
            return 1.0
        if not cv_list:
            return 0.0
        
        try:
            all_items = cv_list + jd_list
            embeddings = self.embedding_service.get_embeddings_batch(all_items)
            
            cv_embeddings = embeddings[:len(cv_list)]
            jd_embeddings = embeddings[len(cv_list):]
            
            similarity_matrix = cosine_similarity(jd_embeddings, cv_embeddings)
            max_similarities = np.max(similarity_matrix, axis=1)
            
            return float(np.mean(max_similarities))
        except Exception:
            return self._simple_match_score(cv_list, jd_list)
    
    def _simple_match_score(self, cv_list: List[str], jd_list: List[str]) -> float:
        """Simple exact match scoring"""
        if not jd_list:
            return 1.0
        if not cv_list:
            return 0.0
        
        cv_normalized = {item.lower().strip() for item in cv_list}
        jd_normalized = [item.lower().strip() for item in jd_list]
        
        matches = sum(1 for jd_item in jd_normalized if jd_item in cv_normalized)
        return matches / len(jd_list)
    
    def _calculate_legacy_scores(self, cv_data: Dict, jd_data: Dict) -> Dict[str, float]:
        """Fallback to legacy scoring if new structure not available"""
        # Import legacy scoring logic
        from app.services.scoring_service import ScoringService
        legacy_service = ScoringService(self.embedding_service)
        
        result = legacy_service.calculate_match_score(cv_data, jd_data)
        
        # Map to new structure
        return {
            "hard_skills": result["breakdown"]["skill_match"],
            "work_experience": result["breakdown"]["job_title_match"],
            "responsibilities": result["breakdown"]["overall_semantic"],
            "soft_skills": 0.8,  # Default
            "education": result["breakdown"]["education_cert_match"],
            "additional_factors": 0.9  # Default
        }
    
    def _generate_detailed_analysis(self, cv_struct: Dict, jd_struct: Dict) -> Dict[str, Any]:
        """Generate detailed textual analysis"""
        analysis = {
            "strengths": [],
            "gaps": [],
            "recommendations": []
        }
        
        # Analyze hard skills
        if "hard_skills" in cv_struct and "hard_skills" in jd_struct:
            cv_skills = cv_struct["hard_skills"]
            jd_skills = jd_struct["hard_skills"]
            
            # Find strengths
            cv_all_skills = []
            for key in ["programming_languages", "technologies_frameworks", "tools_software"]:
                cv_all_skills.extend(cv_skills.get(key, []))
            
            if cv_all_skills:
                analysis["strengths"].append(f"Possesses {len(cv_all_skills)} technical skills")
            
            # Find gaps
            jd_all_skills = []
            for key in ["programming_languages", "technologies_frameworks", "tools_software"]:
                jd_all_skills.extend(jd_skills.get(key, []))
            
            missing = set(jd_all_skills) - set(cv_all_skills)
            if missing:
                analysis["gaps"].append(f"Missing skills: {', '.join(list(missing)[:5])}")
                analysis["recommendations"].append(f"Consider acquiring: {', '.join(list(missing)[:3])}")
        
        return analysis

