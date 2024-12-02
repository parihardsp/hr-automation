from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from enum import Enum


class Candidate(BaseModel):
    id: Optional[int] = None
    candidate_id: int
    first_name: str
    last_name: str
    title: Optional[str] = None
    company: Optional[str] = None
    url: Optional[str] = None
    phone_numbers: List[Dict[str, str]] = []  # [{type: str, value: str}]
    email_addresses: List[Dict[str, str]] = []  # [{type: str, value: str}]
    education: List[Dict[str, Any]] = []
    addresses: List[Dict[str, Any]] = []
    tags: List[str] = []
    custom_fields: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CandidateAttachment(BaseModel):
    id: Optional[int] = None
    candidate_id: int
    filename: str
    url: str
    type: str
    blob_storage_path: Optional[str] = None
    status: str = "pending"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Job(BaseModel):
    id: Optional[int] = None
    job_id: int
    title: str
    status: str = "open"
    departments: List[Dict[str, Any]] = []
    offices: List[Dict[str, Any]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobContent(BaseModel):
    id: Optional[int] = None
    job_id: int
    internal_job_id: int
    title: str
    content: str
    absolute_url: Optional[str] = None
    location: Optional[str] = None
    pay_range: Optional[Dict[str, Any]] = None
    status: str = "pending"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Application(BaseModel):
    id: Optional[int] = None
    application_id: int
    candidate_id: int
    job_id: int
    status: str
    applied_at: datetime
    last_activity_at: Optional[datetime] = None
    url: Optional[str] = None
    source: Optional[Dict[str, Any]] = None
    current_stage: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProcessedResume(BaseModel):
    id: Optional[int] = None
    candidate_id: int
    attachment_id: int
    personal_section: Optional[Dict[str, Any]] = None
    experience_section: Optional[Dict[str, Any]] = None
    skills_section: Optional[Dict[str, Any]] = None
    qualifcation_section: Optional[Dict[str, Any]] = None
    project_section: Optional[Dict[str, Any]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    company_bg_details: Optional[Dict[str, Any]] = None
    processing_status: str = "pending"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProcessedJD(BaseModel):
    id: Optional[int] = None
    job_id: int
    job_content_id: int
    required_experience: Optional[Dict[str, Any]] = None
    required_skills: Optional[Dict[str, Any]] = None
    roles_responsibilities: Optional[Dict[str, Any]] = None
    requiredQualifications: Optional[Dict[str, Any]] = None
    requiredCertifications: Optional[List[Dict[str, Any]]] = None
    processing_status: str = "pending"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SimilarityScore(BaseModel):
    id: Optional[int] = None
    candidate_id: int
    job_id: int
    application_id: int
    processed_resume_id: int
    processed_jd_id: int
    overall_score: float
    match_details: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SortCriteria(str, Enum):
    overall_score = "overall_score"
    skills_match = "skills_match"
    experience_match = "experience_match"
    education_match = "education_match"


class ResumeResponse(BaseModel):
    title: str
    id: int
    candidate_id: int
    candidate_name: str
    overall_score: float
    match_details: List[Dict]  # Simplified from complex nested structure
    company_bg_details: Optional[Dict] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True  # Add this to allow arbitrary types
