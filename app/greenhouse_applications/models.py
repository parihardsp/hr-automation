from sqlalchemy import Column, Integer, Float, String, JSON, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class TimestampMixin:
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class Candidate(Base, TimestampMixin):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    title = Column(String(100))
    company = Column(String(255))
    url = Column(String(255))
    phone_numbers = Column(JSON)  # Store multiple phone numbers as JSONB if using PostgreSQL
    email_addresses = Column(JSON)  # Store multiple email addresses as JSONB
    education = Column(JSON)  # Store education information as JSONB
    addresses = Column(JSON)
    tags = Column(JSON)  # Store tags as JSONB
    custom_fields = Column(JSON)  # Add this line
    applied_at = Column(TIMESTAMP)

    applications = relationship("Application", back_populates="candidate")
    attachments = relationship("CandidateAttachment", back_populates="candidate")

class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(255))
    requisition_id = Column(String(100))
    status = Column(String(50))
    url = Column(String(255))
    departments = Column(JSON)  # Store departments as JSONB
    offices = Column(JSON)  # Store offices as JSONB
    created_by_id = Column(Integer)
    opened_at = Column(TIMESTAMP)
    closed_at = Column(TIMESTAMP)

    applications = relationship("Application", back_populates="job")

class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, unique=True, nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"))
    job_id = Column(Integer, ForeignKey("jobs.job_id"))
    status = Column(String(50))
    applied_at = Column(TIMESTAMP)
    last_activity_at = Column(TIMESTAMP)
    url = Column(String(255))
    source = Column(JSON)  # Store source as JSONB
    current_stage = Column(JSON)  # Store current stage as JSONB

    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    scores = relationship("Score", back_populates="application")

class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.application_id"))
    score = Column(Float)  # Change to Column(Float) if needed
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    application = relationship("Application", back_populates="scores")

class CandidateAttachment(Base):
    __tablename__ = "candidate_attachments"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    filename = Column(String(255))
    url = Column(String(255))
    type = Column(String(50))  # e.g., 'resume', 'cover_letter'
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="attachments")
