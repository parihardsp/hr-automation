from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, JSON, Text, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Candidate(Base):
    __tablename__ = 'candidates'
    __table_args__ = (
        Index('idx_candidate_greenhouse_id', 'candidate_id'),
    )

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, nullable=False)  # Greenhouse candidate ID
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(100))
    company = Column(String(255))
    url = Column(String(255))
    phone_numbers = Column(JSON)
    email_addresses = Column(JSON)
    education = Column(JSON)
    addresses = Column(JSON)
    tags = Column(JSON)
    custom_fields = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attachments = relationship("CandidateAttachment", back_populates="candidate")
    applications = relationship("Application", back_populates="candidate")
    processed_resumes = relationship("ProcessedResume", back_populates="candidate")

class CandidateAttachment(Base):
    __tablename__ = 'candidate_attachments'
    __table_args__ = (
        Index('idx_attachment_candidate', 'candidate_id'),
    )

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    url = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    blob_storage_path = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="attachments")
    processed_resumes = relationship("ProcessedResume", back_populates="attachment")

class Job(Base):
    __tablename__ = 'jobs'
    __table_args__ = (
        Index('idx_job_greenhouse_id', 'job_id'),
    )

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, unique=True, nullable=False)  # Greenhouse job ID
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default='open')
    departments = Column(JSON)
    offices = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications = relationship("Application", back_populates="job")
    job_contents = relationship("JobContent", back_populates="job")
    processed_jds = relationship("ProcessedJD", back_populates="job")

class JobContent(Base):
    __tablename__ = 'job_content'
    __table_args__ = (
        Index('idx_job_content_job', 'job_id'),
    )

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.job_id'), nullable=False)
    internal_job_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    absolute_url = Column(String(255))
    location = Column(String(255))
    pay_range = Column(JSON)
    status = Column(String(50), nullable=False, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="job_contents")
    processed_jds = relationship("ProcessedJD", back_populates="job_content")

class Application(Base):
    __tablename__ = 'applications'
    __table_args__ = (
        Index('idx_application_greenhouse_id', 'application_id'),
        Index('idx_application_candidate_job', 'candidate_id', 'job_id'),
    )

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, unique=True, nullable=False)  # Greenhouse application ID
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)  # Changed to reference candidates.id
    job_id = Column(Integer, ForeignKey('jobs.job_id'), nullable=False)
    status = Column(String(50), nullable=False)
    applied_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime)
    url = Column(String(255))
    source = Column(JSON)
    current_stage = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    similarity_scores = relationship("SimilarityScore", back_populates="application")

class ProcessedResume(Base):
    __tablename__ = 'processed_resumes'
    __table_args__ = (
        Index('idx_processed_resume_candidate', 'candidate_id'),
        Index('idx_processed_resume_attachment', 'attachment_id'),
    )

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    attachment_id = Column(Integer, ForeignKey('candidate_attachments.id'), nullable=False)
    personal_section = Column(JSON)
    experience_section = Column(JSON)
    skills_section = Column(JSON)
    qualifcation_section = Column(JSON)
    project_section = Column(JSON)
    certifications = Column(JSON)
    company_bg_details = Column(JSON)
    processing_status = Column(String(50), nullable=False, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="processed_resumes")
    attachment = relationship("CandidateAttachment", back_populates="processed_resumes")
    similarity_scores = relationship("SimilarityScore", back_populates="processed_resume")

class ProcessedJD(Base):
    __tablename__ = 'processed_jd'
    __table_args__ = (
        Index('idx_processed_jd_job', 'job_id'),
        Index('idx_processed_jd_content', 'job_content_id'),
    )

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.job_id'), nullable=False)
    job_content_id = Column(Integer, ForeignKey('job_content.id'), nullable=False)
    required_experience = Column(JSON)
    required_skills = Column(JSON)
    roles_responsibilities = Column(JSON)
    requiredQualifications = Column(JSON)
    requiredCertifications = Column(JSON)
    processing_status = Column(String(50), nullable=False, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="processed_jds")
    job_content = relationship("JobContent", back_populates="processed_jds")
    similarity_scores = relationship("SimilarityScore", back_populates="processed_jd")

class SimilarityScore(Base):
    __tablename__ = 'similarity_scores'
    __table_args__ = (
        Index('idx_similarity_application', 'application_id'),
        Index('idx_similarity_candidate_job', 'candidate_id', 'job_id'),
    )

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)  # Changed to reference candidates.id
    job_id = Column(Integer, ForeignKey('jobs.job_id'), nullable=False)
    application_id = Column(Integer, ForeignKey('applications.application_id'), nullable=False)
    processed_resume_id = Column(Integer, ForeignKey('processed_resumes.id'), nullable=False)
    processed_jd_id = Column(Integer, ForeignKey('processed_jd.id'), nullable=False)
    overall_score = Column(Float, nullable=False)
    match_details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="similarity_scores")
    processed_resume = relationship("ProcessedResume", back_populates="similarity_scores")
    processed_jd = relationship("ProcessedJD", back_populates="similarity_scores")