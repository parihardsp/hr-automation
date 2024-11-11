# dao.py

from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from .models import Candidate, CandidateAttachment, Job, Application, JobContent
import logging

logger = logging.getLogger(__name__)


class DAO:
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
        Insert candidate data from webhook
        """
        try:
            logger.info(f"Adding candidate: {candidate_data['first_name']} {candidate_data['last_name']}")

            # Check if candidate already exists
            existing_candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_data['id']
            ).first()

            if existing_candidate:
                logger.info(f"Candidate already exists with ID: {candidate_data['id']}")
                return existing_candidate

            candidate = Candidate(
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
                custom_fields=candidate_data.get('custom_fields', {}),
                created_at=datetime.strptime(candidate_data['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                if candidate_data.get('created_at') else datetime.utcnow()
            )

            self.db.add(candidate)
            self.db.flush()
            logger.info(f"Successfully added candidate with ID: {candidate.candidate_id}")
            return candidate

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding candidate: {str(e)}")
            raise Exception(f"Error adding candidate: {str(e)}")

    def add_candidate_attachment(self, candidate_id: int, attachment_data: Dict[str, Any]) -> CandidateAttachment:
        """
        Insert candidate attachment data.
        blob_storage_path will be updated later when file is downloaded and stored
        """
        try:
            logger.info(f"Adding attachment for candidate ID: {candidate_id}")

            # Check if attachment already exists
            existing_attachment = self.db.query(CandidateAttachment).filter(
                CandidateAttachment.candidate_id == candidate_id,
                CandidateAttachment.url == attachment_data['url']
            ).first()

            if existing_attachment:
                logger.info(f"Attachment already exists for candidate ID: {candidate_id}")
                return existing_attachment

            attachment = CandidateAttachment(
                candidate_id=candidate_id,
                filename=attachment_data['filename'],
                url=attachment_data['url'],
                type=attachment_data['type'],
                blob_storage_path=None,  # Will be filled later when file is downloaded
                status='pending'  # Initial status for download
            )

            self.db.add(attachment)
            self.db.flush()
            logger.info(f"Successfully added attachment for candidate ID: {candidate_id}")
            return attachment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding attachment: {str(e)}")
            raise Exception(f"Error adding attachment: {str(e)}")

    def update_attachment_storage_path(self, attachment_id: int, storage_path: str) -> CandidateAttachment:
        """
        Update the blob_storage_path once file is downloaded and stored.
        This method can be used later when implementing file download functionality.
        """
        try:
            logger.info(f"Updating storage path for attachment ID: {attachment_id}")

            attachment = self.db.query(CandidateAttachment).filter(
                CandidateAttachment.id == attachment_id
            ).first()

            if not attachment:
                raise Exception(f"Attachment not found with ID: {attachment_id}")

            attachment.blob_storage_path = storage_path
            attachment.status = 'downloaded'  # Update status when path is set
            self.db.commit()

            logger.info(f"Successfully updated storage path for attachment ID: {attachment_id}")
            return attachment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating attachment storage path: {str(e)}")
            raise Exception(f"Error updating attachment storage path: {str(e)}")

    def add_job(self, job_data: Dict[str, Any]) -> Job:
        """
        Insert basic job data from webhook
        """
        try:
            logger.info(f"Adding job with ID: {job_data['id']}")

            # Check if job already exists
            existing_job = self.db.query(Job).filter(
                Job.job_id == job_data['id']
            ).first()

            if existing_job:
                logger.info(f"Job already exists with ID: {job_data['id']}")
                return existing_job

            job = Job(
                job_id=job_data['id'],
                title=job_data['name'],
                status=job_data['status'],
                departments=job_data.get('departments', []),
                offices=job_data.get('offices', []),
                created_at=datetime.strptime(job_data['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                if job_data.get('created_at') else datetime.utcnow()
            )

            self.db.add(job)
            self.db.flush()
            logger.info(f"Successfully added job with ID: {job.job_id}")
            return job

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding job: {str(e)}")
            raise Exception(f"Error adding job: {str(e)}")

    def add_application(self, application_data: Dict[str, Any], candidate_id: int, job_id: int) -> Application:
        """
        Insert application data
        """
        try:
            logger.info(f"Adding application for candidate ID: {candidate_id} and job ID: {job_id}")

            # Check if application already exists
            existing_application = self.db.query(Application).filter(
                Application.application_id == application_data['id']
            ).first()

            if existing_application:
                logger.info(f"Application already exists with ID: {application_data['id']}")
                return existing_application

            application = Application(
                application_id=application_data['id'],
                candidate_id=candidate_id,
                job_id=job_id,
                status=application_data['status'],
                applied_at=datetime.strptime(application_data['applied_at'], '%Y-%m-%dT%H:%M:%SZ'),
                last_activity_at=datetime.strptime(application_data['last_activity_at'], '%Y-%m-%dT%H:%M:%SZ')
                if application_data.get('last_activity_at') else None,
                url=application_data.get('url'),
                source=application_data.get('source'),
                current_stage=application_data.get('current_stage')
            )

            self.db.add(application)
            self._commit_with_rollback("adding application")
            logger.info(f"Successfully added application with ID: {application.application_id}")
            return application

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding application: {str(e)}")
            raise Exception(f"Error adding application: {str(e)}")

    def add_job_content(self, job_id: int, content_data: dict) -> JobContent:
        """
        Insert job content data from Greenhouse API
        """
        try:
            logger.info(f"Adding/updating job content for job ID: {job_id}")

            # Convert pay range data to our format
            pay_range = None
            if content_data.get('pay_input_ranges'):
                pay_range = {
                    'ranges': [{
                        'min_value': range_data['min_cents'] / 100,
                        'max_value': range_data['max_cents'] / 100,
                        'currency': range_data['currency_type'],
                        'title': range_data['title']
                    } for range_data in content_data['pay_input_ranges']]
                }

            # Check if job content already exists
            existing_content = self.db.query(JobContent).filter(
                JobContent.job_id == job_id
            ).first()

            if existing_content:
                logger.info(f"Updating existing job content for job ID: {job_id}")
                existing_content.internal_job_id = content_data['internal_job_id']
                existing_content.title = content_data['title']
                existing_content.content = content_data['content']
                existing_content.absolute_url = content_data.get('absolute_url')
                existing_content.location = content_data.get('location', {}).get('name')
                existing_content.pay_range = pay_range
                existing_content.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating job content")
                return existing_content

            logger.info(f"Creating new job content for job ID: {job_id}")
            job_content = JobContent(
                job_id=job_id,
                internal_job_id=content_data['internal_job_id'],
                title=content_data['title'],
                content=content_data['content'],
                absolute_url=content_data.get('absolute_url'),
                location=content_data.get('location', {}).get('name'),
                pay_range=pay_range,
                status='pending'
            )

            self.db.add(job_content)
            self._commit_with_rollback("adding job content")
            logger.info(f"Successfully added job content for job ID: {job_id}")
            return job_content

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding job content: {str(e)}")
            raise Exception(f"Error adding job content: {str(e)}")

    def get_job_content(self, job_id: int) -> Optional[JobContent]:
        """
        Get job content by job_id
        """
        try:
            logger.info(f"Fetching job content for job ID: {job_id}")
            content = self.db.query(JobContent).filter(JobContent.job_id == job_id).first()
            if content:
                logger.info(f"Found job content for job ID: {job_id}")
            else:
                logger.info(f"No job content found for job ID: {job_id}")
            return content
        except Exception as e:
            logger.error(f"Error fetching job content: {str(e)}")
            raise Exception(f"Error fetching job content: {str(e)}")

    def get_job_by_job_id(self, job_id: int) -> Optional[Job]:
        """
        Get job by greenhouse job_id
        """
        try:
            logger.info(f"Fetching job with job ID: {job_id}")
            job = self.db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                logger.info(f"Found job with job ID: {job_id}")
            else:
                logger.info(f"No job found with job ID: {job_id}")
            return job
        except Exception as e:
            logger.error(f"Error fetching job: {str(e)}")
            raise Exception(f"Error fetching job: {str(e)}")