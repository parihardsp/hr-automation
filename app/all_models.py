
from app.gh_integration.models import (
    Candidate,
    CandidateAttachment,
    Job,
    JobContent,
    Application,
    ProcessedResume,
    ProcessedJD,
    SimilarityScore,
)

from app.jd_drafter.models import  GeneratedJD

# Export all models for easy import
__all__ = [
    'Candidate',
    'CandidateAttachment',
    'Job',
    'JobContent',
    'Application',
    'ProcessedResume',
    'ProcessedJD',
    'SimilarityScore',
    'GeneratedJD'
]