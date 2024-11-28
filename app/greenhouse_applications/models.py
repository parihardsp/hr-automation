from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, JSON, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Candidate(Base):
    __tablename__ = 'candidates'

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(100))
    company = Column(String(255))
    url = Column(String(255))
    phone_numbers = Column(JSON)  # Array of {type, value}
    email_addresses = Column(JSON)  # Array of {type, value}
    education = Column(JSON)  # Array of education details
    addresses = Column(JSON)  # Array of addresses
    tags = Column(JSON)  # Array of candidate tags
    custom_fields = Column(JSON)  # Greenhouse custom fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attachments = relationship("CandidateAttachment", back_populates="candidate")
    applications = relationship("Application", back_populates="candidate")
    processed_resumes = relationship("ProcessedResume", back_populates="candidate")


class CandidateAttachment(Base):
    __tablename__ = 'candidate_attachments'

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.candidate_id'), nullable=False)
    filename = Column(String(255), nullable=False)
    url = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # resume, cover_letter
    blob_storage_path = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default='pending')  # pending, downloaded, processed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="attachments")
    processed_resumes = relationship("ProcessedResume", back_populates="attachment")


class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default='open')
    departments = Column(JSON)  # Array of departments
    offices = Column(JSON)  # Array of offices
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications = relationship("Application", back_populates="job")
    job_contents = relationship("JobContent", back_populates="job")
    processed_jds = relationship("ProcessedJD", back_populates="job")


class JobContent(Base):
    __tablename__ = 'job_content'

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.job_id'), nullable=False)
    internal_job_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    absolute_url = Column(String(255))
    location = Column(String(255))
    pay_range = Column(JSON)  # Salary range information
    status = Column(String(50), nullable=False, default='pending')  # pending, processed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="job_contents")
    processed_jds = relationship("ProcessedJD", back_populates="job_content")


class Application(Base):
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, unique=True, nullable=False)
    candidate_id = Column(Integer, ForeignKey('candidates.candidate_id'), nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.job_id'), nullable=False)
    status = Column(String(50), nullable=False)
    applied_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime)
    url = Column(String(255))
    source = Column(JSON)  # Source information
    current_stage = Column(JSON)  # Current application stage
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    similarity_scores = relationship("SimilarityScore", back_populates="application")


class ProcessedResume(Base):
    __tablename__ = 'processed_resumes'

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.candidate_id'), nullable=False)
    attachment_id = Column(Integer, ForeignKey('candidate_attachments.id'), nullable=False)
    personal_section = Column(JSON)  # Parsed personal information
    experience_section = Column(JSON)  # Parsed work experience
    skills_section = Column(JSON)  # Parsed skills
    qualifcation_section = Column(JSON)
    project_section = Column(JSON)
    certifications = Column(JSON)
    company_bg_details = Column(JSON)
    processing_status = Column(String(50), nullable=False, default='pending')  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="processed_resumes")
    attachment = relationship("CandidateAttachment", back_populates="processed_resumes")
    similarity_scores = relationship("SimilarityScore", back_populates="processed_resume")


class ProcessedJD(Base):
    __tablename__ = 'processed_jd'

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.job_id'), nullable=False)
    job_content_id = Column(Integer, ForeignKey('job_content.id'), nullable=False)
    required_experience = Column(JSON)  # Parsed experience requirements
    required_skills = Column(JSON)  # Parsed required skills
    roles_responsibilities = Column(JSON)  # Parsed roles and responsibilities
    requiredQualifications = Column(JSON)
    requiredCertifications = Column(JSON)
    processing_status = Column(String(50), nullable=False, default='pending')  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="processed_jds")
    job_content = relationship("JobContent", back_populates="processed_jds")
    similarity_scores = relationship("SimilarityScore", back_populates="processed_jd")


class SimilarityScore(Base):
    __tablename__ = 'similarity_scores'

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('candidates.candidate_id'), nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.job_id'), nullable=False)
    application_id = Column(Integer, ForeignKey('applications.application_id'), nullable=False)
    processed_resume_id = Column(Integer, ForeignKey('processed_resumes.id'), nullable=False)
    processed_jd_id = Column(Integer, ForeignKey('processed_jd.id'), nullable=False)
    overall_score = Column(Float, nullable=False)
    match_details = Column(JSON)  # Detailed matching information
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="similarity_scores")
    processed_resume = relationship("ProcessedResume", back_populates="similarity_scores")
    processed_jd = relationship("ProcessedJD", back_populates="similarity_scores")

class GeneratedJD(Base):
    __tablename__ = 'generated_jds'
    __table_args__ = {'schema': 'public'}  # Add schema specification

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    user_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GeneratedJD(id={self.id}, user_id={self.user_id}, created_at={self.created_at})>"