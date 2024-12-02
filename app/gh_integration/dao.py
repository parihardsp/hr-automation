"""
Data Access Object (DAO) module for managing database interactions.

This module provides a comprehensive set of methods for creating,
retrieving, and managing database records across various entities
in the HR automation system.
"""
# pylint: disable=C0301

import json
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from app.core.logger_setup import setup_logger

from .models import (
    Candidate, CandidateAttachment, Job, Application,
    JobContent, ProcessedJD, ProcessedResume, SimilarityScore
)



logger = setup_logger(__name__)

class DAO:
    """
       Data Access Object for managing database operations.

       Provides methods to interact with various database entities,
       including candidates, jobs, applications, and processed data.
    """
    def __init__(self, db: Session):
        self.db = db

    def _commit_with_rollback(self, operation: str) -> None:
        """Helper method to handle commit and rollback"""
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error during {operation}: {str(e)}")
            raise

    def add_candidate(self, candidate_data: Dict[str, Any]) -> Candidate:
        """
        Always creates a new candidate record, even if candidate_id exists
        This maintains history of candidate changes
        """
        try:
            logger.info(f"Creating new candidate record for candidate_id: {candidate_data['id']}")

            new_candidate = Candidate(
                candidate_id=candidate_data['id'],
                first_name=candidate_data['first_name'],
                last_name=candidate_data['last_name'],
                title=candidate_data.get('title'),
                company=candidate_data.get('company'),
                url=candidate_data.get('url'),
                phone_numbers=candidate_data.get('phone_numbers', []),
                email_addresses=candidate_data.get('email_addresses', []),
                education=candidate_data.get('educations', []),
                addresses=candidate_data.get('addresses', []),
                tags=candidate_data.get('tags', []),
                custom_fields=candidate_data.get('custom_fields', {})
            )

            self.db.add(new_candidate)
            self._commit_with_rollback("adding new candidate")

            logger.info(f"Successfully created new candidate record with ID: {new_candidate.id}")
            return new_candidate

        except Exception as e:
            logger.error(f"Error creating candidate record: {str(e)}")
            raise

    def add_candidate_attachment(self, candidate_id: int, attachment_data: Dict[str, Any]) -> CandidateAttachment:
        """
        Creates a new attachment record for each resume submission
        """
        try:
            logger.info(f"Creating new attachment for candidate ID: {candidate_id}")

            new_attachment = CandidateAttachment(
                candidate_id=candidate_id,  # This is candidates.id, not greenhouse candidate_id
                filename=attachment_data['filename'],
                url=attachment_data['url'],
                type=attachment_data['type'],
                status='pending'
            )

            self.db.add(new_attachment)
            self._commit_with_rollback("adding new attachment")

            logger.info(f"Successfully created attachment with ID: {new_attachment.id}")
            return new_attachment

        except Exception as e:
            logger.error(f"Error creating attachment record: {str(e)}")
            raise

    def update_attachment_storage_path(self, attachment_id: int, storage_path: str) -> CandidateAttachment:
        """
        Updates the blob storage path and status for a specific attachment record.

        Args:
            attachment_id (int): The ID of the specific attachment record
            storage_path (str): The path where the attachment file is stored

        Returns:
            CandidateAttachment: The updated attachment record

        Raises:
            Exception: If attachment not found or update fails
        """
        try:
            logger.info(f"Updating storage path for attachment ID: {attachment_id}")

            attachment = self.db.query(CandidateAttachment).filter(
                CandidateAttachment.id == attachment_id
            ).first()

            if not attachment:
                error_msg = f"Attachment not found with ID: {attachment_id}"
                logger.error(error_msg)
                raise Exception(error_msg)

            attachment.blob_storage_path = storage_path
            attachment.status = 'downloaded'  # Update status when path is set

            self._commit_with_rollback("updating attachment storage path")

            logger.info(f"Successfully updated storage path for attachment ID: {attachment_id}")
            return attachment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating attachment storage path: {str(e)}")
            raise

    def get_or_create_job(self, job_data: Dict[str, Any]) -> Job:
        """
        Returns existing job if job_id exists, creates new if it doesn't
        Jobs are unique by job_id and can be reused
        """
        try:
            logger.info(f"Looking up job with ID: {job_data['id']}")

            existing_job = self.db.query(Job).filter(
                Job.job_id == job_data['id']
            ).first()

            if existing_job:
                logger.info(f"Found existing job with ID: {job_data['id']}")
                return existing_job

            logger.info(f"Creating new job record for job_id: {job_data['id']}")
            new_job = Job(
                job_id=job_data['id'],
                title=job_data['name'],
                status=job_data['status'],
                departments=job_data.get('departments', []),
                offices=job_data.get('offices', [])
            )

            self.db.add(new_job)
            self._commit_with_rollback("adding new job")

            logger.info(f"Successfully created new job with ID: {new_job.job_id}")
            return new_job

        except Exception as e:
            logger.error(f"Error in get_or_create_job: {str(e)}")
            raise

    def get_or_create_job_content(self, job_id: int, content_data: Dict[str, Any]) -> JobContent:
        """
        Returns existing job content if exists for job_id, creates new if it doesn't
        """
        try:
            logger.info(f"Looking up job content for job_id: {job_id}")

            existing_content = self.db.query(JobContent).filter(
                JobContent.job_id == job_id
            ).first()

            if existing_content:
                logger.info(f"Found existing job content for job_id: {job_id}")
                return existing_content

            logger.info(f"Creating new job content for job_id: {job_id}")
            new_content = JobContent(
                job_id=job_id,
                internal_job_id=content_data['internal_job_id'],
                title=content_data['title'],
                content=content_data['content'],
                absolute_url=content_data.get('absolute_url'),
                location=content_data.get('location', {}).get('name'),
                pay_range=content_data.get('pay_range'),
                status='pending'
            )

            self.db.add(new_content)
            self._commit_with_rollback("adding new job content")

            logger.info(f"Successfully created job content with ID: {new_content.id}")
            return new_content

        except Exception as e:
            logger.error(f"Error in get_or_create_job_content: {str(e)}")
            raise

    def add_application(self, application_data: Dict[str, Any], candidate_id: int, job_id: int) -> Application:
        """
        Creates new application record
        Applications are always unique and tied to specific candidate record
        """
        try:
            logger.info(f"Creating new application for candidate ID: {candidate_id} and job ID: {job_id}")

            # Check if application already exists
            existing_application = self.db.query(Application).filter(
                Application.application_id == application_data['id']
            ).first()

            if existing_application:
                logger.info(f"Application already exists with ID: {application_data['id']}")
                return existing_application

            new_application = Application(
                application_id=application_data['id'],
                candidate_id=candidate_id,  # This is candidates.id
                job_id=job_id,
                status=application_data['status'],
                applied_at=datetime.strptime(application_data['applied_at'], '%Y-%m-%dT%H:%M:%SZ'),
                last_activity_at=datetime.strptime(application_data['last_activity_at'], '%Y-%m-%dT%H:%M:%SZ')
                if application_data.get('last_activity_at') else None,
                url=application_data.get('url'),
                source=application_data.get('source'),
                current_stage=application_data.get('current_stage')
            )

            self.db.add(new_application)
            self._commit_with_rollback("adding new application")

            logger.info(f"Successfully created application with ID: {new_application.application_id}")
            return new_application

        except Exception as e:
            logger.error(f"Error creating application record: {str(e)}")
            raise

    def get_or_create_processed_jd(self, job_id: int, job_content_id: int, formatted_jd: str) -> ProcessedJD:
        """
        Get existing processed JD if exists, create new if it doesn't.
        Handles cleaning and parsing of GPT output.
        """
        try:
            logger.info(f"Looking up processed JD for job_id: {job_id}")

            existing_jd = self.db.query(ProcessedJD).filter(
                ProcessedJD.job_id == job_id
            ).first()

            if existing_jd:
                logger.info(f"Found existing processed JD for job_id: {job_id}")
                return existing_jd

            # Clean and parse the formatted_jd
            try:
                # Remove markdown if present
                cleaned_jd = formatted_jd.strip()
                if cleaned_jd.startswith("```json"):
                    cleaned_jd = cleaned_jd[7:-3].strip()  # Remove ```json and ``` markers
                elif cleaned_jd.startswith("```"):
                    cleaned_jd = cleaned_jd[3:-3].strip()  # Remove ``` markers

                # Parse JSON
                formatted_jd_dict = json.loads(cleaned_jd)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in formatted JD: {e}")
                logger.error(f"Raw JD content: {formatted_jd[:200]}...")  # Log first 200 chars
                raise ValueError(f"Invalid JSON format in JD: {str(e)}")

            logger.info(f"Creating new processed JD for job_id: {job_id}")
            new_jd = ProcessedJD(
                job_id=job_id,
                job_content_id=job_content_id,
                required_experience=formatted_jd_dict.get('requiredWorkExperience'),
                required_skills=formatted_jd_dict.get('requiredSkills'),
                roles_responsibilities=formatted_jd_dict.get('rolesAndResponsibilities'),
                requiredQualifications=formatted_jd_dict.get('requiredQualifications'),
                requiredCertifications=formatted_jd_dict.get('requiredCertifications'),
                processing_status='completed'
            )

            self.db.add(new_jd)
            self._commit_with_rollback("adding new processed JD")

            logger.info(f"Successfully created processed JD with ID: {new_jd.id}")
            return new_jd

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in get_or_create_processed_jd: {str(e)}")
            raise

    def add_processed_resume(self, candidate_id: int, attachment_id: int, formatted_resume: str) -> ProcessedResume:
        """
        Creates new processed resume record for each submission
        """
        try:
            logger.info(f"Creating new processed resume for candidate ID: {candidate_id}")

            formatted_resume_dict = json.loads(formatted_resume)

            new_resume = ProcessedResume(
                candidate_id=candidate_id,  # This is candidates.id
                attachment_id=attachment_id,
                personal_section=formatted_resume_dict.get('personalInfo'),
                experience_section=formatted_resume_dict.get('workExperience'),
                skills_section=formatted_resume_dict.get('skills'),
                qualifcation_section=formatted_resume_dict.get('education'),
                project_section=formatted_resume_dict.get('projects'),
                certifications=formatted_resume_dict.get('certifications'),
                company_bg_details=formatted_resume_dict.get('companyBackground'),
                processing_status='completed'
            )

            self.db.add(new_resume)
            self._commit_with_rollback("adding new processed resume")

            logger.info(f"Successfully created processed resume with ID: {new_resume.id}")
            return new_resume

        except Exception as e:
            logger.error(f"Error creating processed resume record: {str(e)}")
            raise

    def add_similarity_score(
            self,
            candidate_id: int,
            job_id: int,
            application_id: int,
            processed_resume_id: int,
            processed_jd_id: int,
            similarity_analysis: Dict[str, Any]
    ) -> SimilarityScore:
        """
        Creates new similarity score for each application
        """
        try:
            logger.info(f"Creating similarity score for application ID: {application_id}")

            # Check if score already exists for this application
            existing_score = self.db.query(SimilarityScore).filter(
                SimilarityScore.application_id == application_id
            ).first()

            if existing_score:
                logger.info(f"Similarity score already exists for application ID: {application_id}")
                return existing_score

            new_score = SimilarityScore(
                candidate_id=candidate_id,  # This is candidates.id
                job_id=job_id,
                application_id=application_id,
                processed_resume_id=processed_resume_id,
                processed_jd_id=processed_jd_id,
                overall_score=similarity_analysis['matching_score'],
                match_details=similarity_analysis['sections']
            )

            self.db.add(new_score)
            self._commit_with_rollback("adding new similarity score")

            logger.info(f"Successfully created similarity score for application ID: {application_id}")
            return new_score

        except Exception as e:
            logger.error(f"Error creating similarity score record: {str(e)}")
            raise

    def get_application_by_id(self, application_id: int) -> Optional[Application]:
        """
        Get application by application_id
        """
        try:
            logger.info(f"Checking for existing application with ID: {application_id}")
            application = self.db.query(Application).filter(
                Application.application_id == application_id
            ).first()

            if application:
                logger.info(f"Found existing application with ID: {application_id}")
            else:
                logger.info(f"No existing application found with ID: {application_id}")

            return application

        except Exception as e:
            logger.error(f"Error checking application existence: {str(e)}")
            raise Exception(f"Error checking application existence: {str(e)}")
