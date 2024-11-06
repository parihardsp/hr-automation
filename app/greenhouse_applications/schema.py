from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CandidateBase(BaseModel):
    candidate_id: int
    first_name: str
    last_name: str
    title: Optional[str]
    company: Optional[str]
    url: Optional[str]
    phone_numbers: Optional[List[str]]
    email_addresses: Optional[List[str]]
    education: Optional[Dict[str, Any]]  # Using Dict for JSON structure
    addresses: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    applied_at: Optional[str]
    custom_fields: Optional[Dict[str, Any]]  # Keeping custom fields

class JobBase(BaseModel):
    job_id: int
    name: str
    requisition_id: Optional[str]
    status: Optional[str]
    url: Optional[str]
    departments: Optional[Dict[str, Any]]  # Using Dict for JSON structure
    offices: Optional[Dict[str, Any]]  # Using Dict for JSON structure
    created_by_id: Optional[int]
    created_at: Optional[str]
    opened_at: Optional[str]
    closed_at: Optional[str]

class ApplicationBase(BaseModel):
    application_id: int
    candidate_id: int
    job_id: int
    status: Optional[str]
    applied_at: Optional[str]
    last_activity_at: Optional[str]
    url: Optional[str]
    source: Optional[Dict[str, Any]]  # Using Dict for JSON structure
    current_stage: Optional[Dict[str, Any]]  # Using Dict for JSON structure

class ScoreBase(BaseModel):
    application_id: int
    score: float

class CandidateAttachmentBase(BaseModel):
    candidate_id: int
    filename: str
    url: str
    type: str
