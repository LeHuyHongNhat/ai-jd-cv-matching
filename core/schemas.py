from pydantic import BaseModel, Field
from typing import List, Optional


class HardSkills(BaseModel):
    """Hard Skills - Technical/Professional Skills (35-40%)"""
    programming_languages: List[str] = Field(
        default_factory=list,
        description="Programming languages"
    )
    technologies_frameworks: List[str] = Field(
        default_factory=list,
        description="Technologies, frameworks, libraries"
    )
    tools_software: List[str] = Field(
        default_factory=list,
        description="Professional tools and software"
    )
    certifications: List[str] = Field(
        default_factory=list,
        description="Professional certifications"
    )
    industry_specific_skills: List[str] = Field(
        default_factory=list,
        description="Industry-specific technical skills"
    )


class WorkExperience(BaseModel):
    """Work Experience (25-30%)"""
    total_years: Optional[float] = Field(
        None,
        description="Total years of work experience"
    )
    job_titles: List[str] = Field(
        default_factory=list,
        description="Job titles/positions held"
    )
    industries: List[str] = Field(
        default_factory=list,
        description="Industries/sectors worked in"
    )
    companies: List[str] = Field(
        default_factory=list,
        description="Companies/organizations worked for"
    )
    company_sizes: List[str] = Field(
        default_factory=list,
        description="Company sizes or project scales (startup, SME, enterprise, etc.)"
    )


class ResponsibilitiesAchievements(BaseModel):
    """Tasks, Responsibilities & Achievements (15-20%)"""
    key_responsibilities: List[str] = Field(
        default_factory=list,
        description="Main responsibilities and tasks performed"
    )
    achievements: List[str] = Field(
        default_factory=list,
        description="Notable achievements, results, and impacts"
    )
    project_types: List[str] = Field(
        default_factory=list,
        description="Types of projects worked on"
    )


class SoftSkills(BaseModel):
    """Soft Skills (10-15%)"""
    communication_teamwork: List[str] = Field(
        default_factory=list,
        description="Communication and teamwork skills"
    )
    leadership_management: List[str] = Field(
        default_factory=list,
        description="Leadership and management skills"
    )
    problem_solving: List[str] = Field(
        default_factory=list,
        description="Problem-solving and analytical thinking"
    )
    adaptability: List[str] = Field(
        default_factory=list,
        description="Adaptability and learning ability"
    )


class EducationTraining(BaseModel):
    """Education & Training (5-10%)"""
    degrees: List[str] = Field(
        default_factory=list,
        description="Academic degrees (Bachelor, Master, PhD, etc.)"
    )
    majors: List[str] = Field(
        default_factory=list,
        description="Academic majors/specializations"
    )
    universities: List[str] = Field(
        default_factory=list,
        description="Universities/institutions attended"
    )
    additional_courses: List[str] = Field(
        default_factory=list,
        description="Additional courses, training programs, or bootcamps"
    )


class AdditionalFactors(BaseModel):
    """Additional Factors (5%)"""
    languages: List[str] = Field(
        default_factory=list,
        description="Languages spoken and proficiency levels"
    )
    availability: Optional[str] = Field(
        None,
        description="Availability to start (immediate, 1 month, 2 months, etc.)"
    )
    relocation_willingness: Optional[bool] = Field(
        None,
        description="Willingness to relocate"
    )
    travel_willingness: Optional[bool] = Field(
        None,
        description="Willingness to travel for work"
    )
    expected_salary: Optional[str] = Field(
        None,
        description="Expected salary range if mentioned"
    )


class StructuredData(BaseModel):
    """Complete Structured Data for CV/JD Matching"""
    # Basic Information
    full_name: Optional[str] = Field(None, description="Full name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    
    # Main Scoring Categories (aligned with matching criteria)
    hard_skills: HardSkills = Field(
        default_factory=HardSkills,
        description="Technical and professional skills (35-40% weight)"
    )
    work_experience: WorkExperience = Field(
        default_factory=WorkExperience,
        description="Work experience details (25-30% weight)"
    )
    responsibilities_achievements: ResponsibilitiesAchievements = Field(
        default_factory=ResponsibilitiesAchievements,
        description="Responsibilities and achievements (15-20% weight)"
    )
    soft_skills: SoftSkills = Field(
        default_factory=SoftSkills,
        description="Soft skills (10-15% weight)"
    )
    education_training: EducationTraining = Field(
        default_factory=EducationTraining,
        description="Education and training (5-10% weight)"
    )
    additional_factors: AdditionalFactors = Field(
        default_factory=AdditionalFactors,
        description="Additional factors (5% weight)"
    )
    
    # Legacy fields for backward compatibility
    skills: List[str] = Field(
        default_factory=list,
        description="All skills combined (for backward compatibility)"
    )
    job_titles: List[str] = Field(
        default_factory=list,
        description="Job titles (for backward compatibility)"
    )
    degrees: List[str] = Field(
        default_factory=list,
        description="Degrees (for backward compatibility)"
    )
    certifications: List[str] = Field(
        default_factory=list,
        description="Certifications (for backward compatibility)"
    )


# Schema cho API responses
class ScoreBreakdown(BaseModel):
    overall_semantic: float
    skill_match: float
    job_title_match: float
    education_cert_match: float


class ScoreResponse(BaseModel):
    total_score: float
    breakdown: ScoreBreakdown


class ProcessResponse(BaseModel):
    doc_id: str
    structured_data: StructuredData


class JDInput(BaseModel):
    text: str

