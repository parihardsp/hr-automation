# dao.py

from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
from .models import Candidate, CandidateAttachment, Job, Application, JobContent, ProcessedJD, ProcessedResume, \
    SimilarityScore
import json

from app.core.logger_setup import setup_logger

# Set up the logger
logger = setup_logger()


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
        """Insert or update candidate data from webhook"""
        try:
            logger.info(f"Adding/updating candidate: {candidate_data['first_name']} {candidate_data['last_name']}")

            existing_candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_data['id']
            ).first()

            if existing_candidate:
                logger.info(f"Updating existing candidate with ID: {candidate_data['id']}")
                # Update existing candidate fields
                existing_candidate.first_name = candidate_data['first_name']
                existing_candidate.last_name = candidate_data['last_name']
                existing_candidate.title = candidate_data.get('title')
                existing_candidate.company = candidate_data.get('company')
                existing_candidate.url = candidate_data.get('url')
                existing_candidate.phone_numbers = candidate_data.get('phone_numbers', [])
                existing_candidate.email_addresses = candidate_data.get('email_addresses', [])
                existing_candidate.education = candidate_data.get('educations', [])
                existing_candidate.addresses = candidate_data.get('addresses', [])
                existing_candidate.tags = candidate_data.get('tags', [])
                existing_candidate.custom_fields = candidate_data.get('custom_fields', {})
                existing_candidate.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating candidate")
                return existing_candidate

            # Create new candidate
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
                custom_fields=candidate_data.get('custom_fields', {}),
                created_at=datetime.strptime(candidate_data['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                if candidate_data.get('created_at') else datetime.utcnow()
            )

            self.db.add(new_candidate)
            self._commit_with_rollback("adding new candidate")
            logger.info(f"Successfully added new candidate with ID: {new_candidate.candidate_id}")
            return new_candidate

        except Exception as e:
            logger.error(f"Error in add_candidate: {str(e)}")
            raise

    def add_candidate_attachment(self, candidate_id: int, attachment_data: Dict[str, Any]) -> CandidateAttachment:
        """Insert or update candidate attachment data"""
        try:
            logger.info(f"Adding/updating attachment for candidate ID: {candidate_id}")

            existing_attachment = self.db.query(CandidateAttachment).filter(
                CandidateAttachment.candidate_id == candidate_id,
                CandidateAttachment.url == attachment_data['url']
            ).first()

            if existing_attachment:
                logger.info(f"Updating existing attachment for candidate ID: {candidate_id}")
                existing_attachment.filename = attachment_data['filename']
                existing_attachment.type = attachment_data['type']
                existing_attachment.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating attachment")
                return existing_attachment

            new_attachment = CandidateAttachment(
                candidate_id=candidate_id,
                filename=attachment_data['filename'],
                url=attachment_data['url'],
                type=attachment_data['type'],
                blob_storage_path=None,
                status='pending'
            )

            self.db.add(new_attachment)
            self._commit_with_rollback("adding new attachment")
            return new_attachment

        except Exception as e:
            logger.error(f"Error in add_candidate_attachment: {str(e)}")
            raise

    def add_job(self, job_data: Dict[str, Any]) -> Job:
        """Insert or update job data"""
        try:
            logger.info(f"Adding/updating job with ID: {job_data['id']}")

            existing_job = self.db.query(Job).filter(
                Job.job_id == job_data['id']
            ).first()

            if existing_job:
                logger.info(f"Updating existing job with ID: {job_data['id']}")
                existing_job.title = job_data['name']
                existing_job.status = job_data['status']
                existing_job.departments = job_data.get('departments', [])
                existing_job.offices = job_data.get('offices', [])
                existing_job.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating job")
                return existing_job

            new_job = Job(
                job_id=job_data['id'],
                title=job_data['name'],
                status=job_data['status'],
                departments=job_data.get('departments', []),
                offices=job_data.get('offices', []),
                created_at=datetime.strptime(job_data['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                if job_data.get('created_at') else datetime.utcnow()
            )

            self.db.add(new_job)
            self._commit_with_rollback("adding new job")
            return new_job

        except Exception as e:
            logger.error(f"Error in add_job: {str(e)}")
            raise

    def add_job_content(self, job_id: int, content_data: dict) -> JobContent:
        """Insert or update job content data"""
        try:
            logger.info(f"Adding/updating job content for job ID: {job_id}")

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

            new_content = JobContent(
                job_id=job_id,
                internal_job_id=content_data['internal_job_id'],
                title=content_data['title'],
                content=content_data['content'],
                absolute_url=content_data.get('absolute_url'),
                location=content_data.get('location', {}).get('name'),
                pay_range=pay_range,
                status='pending'
            )

            self.db.add(new_content)
            self._commit_with_rollback("adding new job content")
            return new_content

        except Exception as e:
            logger.error(f"Error in add_job_content: {str(e)}")
            raise

    def add_application(self, application_data: Dict[str, Any], candidate_id: int, job_id: int) -> Application:
        """Insert application data - applications should be unique records"""
        try:
            logger.info(f"Adding application for candidate ID: {candidate_id} and job ID: {job_id}")

            existing_application = self.db.query(Application).filter(
                Application.application_id == application_data['id']
            ).first()

            if existing_application:
                logger.info(f"Application already exists with ID: {application_data['id']}")
                return existing_application

            new_application = Application(
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

            self.db.add(new_application)
            self._commit_with_rollback("adding new application")
            return new_application

        except Exception as e:
            logger.error(f"Error in add_application: {str(e)}")
            raise

    def add_processed_resume(self, candidate_id: int, attachment_id: int, formatted_resume: str) -> ProcessedResume:
        """Insert or update processed resume data"""
        try:
            logger.info(f"Adding/updating processed resume for candidate ID: {candidate_id}")

            cleaned_resume = formatted_resume.strip("```json").strip("```").strip()
            formatted_resume_dict = json.loads(cleaned_resume)

            existing_processed_resume = self.db.query(ProcessedResume).filter(
                ProcessedResume.candidate_id == candidate_id,
                ProcessedResume.attachment_id == attachment_id
            ).first()

            if existing_processed_resume:
                logger.info(f"Updating existing processed resume for candidate ID: {candidate_id}")
                existing_processed_resume.personal_section = formatted_resume_dict.get('personalInfo')
                existing_processed_resume.experience_section = formatted_resume_dict.get('workExperience')
                existing_processed_resume.skills_section = formatted_resume_dict.get('skills')
                existing_processed_resume.qualifcation_section = formatted_resume_dict.get('education')
                existing_processed_resume.project_section = formatted_resume_dict.get('projects')
                existing_processed_resume.certifications = formatted_resume_dict.get('certifications')
                existing_processed_resume.company_bg_details = formatted_resume_dict.get('companyBackground')
                existing_processed_resume.processing_status = 'completed'
                existing_processed_resume.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating processed resume")
                return existing_processed_resume

            new_processed_resume = ProcessedResume(
                candidate_id=candidate_id,
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

            self.db.add(new_processed_resume)
            self._commit_with_rollback("adding new processed resume")
            return new_processed_resume

        except Exception as e:
            logger.error(f"Error in add_processed_resume: {str(e)}")
            raise

    def add_processed_jd(self, job_id: int, job_content_id: int, formatted_jd: str) -> ProcessedJD:
        """Insert or update processed job description data"""
        try:
            logger.info(f"Adding/updating processed JD for job ID: {job_id}")

            cleaned_jd = formatted_jd.strip("```json").strip("```").strip()
            formatted_jd_dict = json.loads(cleaned_jd)

            existing_processed_jd = self.db.query(ProcessedJD).filter(
                ProcessedJD.job_id == job_id,
                ProcessedJD.job_content_id == job_content_id
            ).first()

            if existing_processed_jd:
                logger.info(f"Updating existing processed JD for job ID: {job_id}")
                existing_processed_jd.required_experience = formatted_jd_dict.get('requiredWorkExperience')
                existing_processed_jd.required_skills = formatted_jd_dict.get('requiredSkills')
                existing_processed_jd.roles_responsibilities = formatted_jd_dict.get('rolesAndResponsibilities')
                existing_processed_jd.requiredQualifications = formatted_jd_dict.get('requiredQualifications')
                existing_processed_jd.requiredCertifications = formatted_jd_dict.get('requiredCertifications')
                existing_processed_jd.processing_status = 'completed'
                existing_processed_jd.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating processed JD")
                return existing_processed_jd

            new_processed_jd = ProcessedJD(
                job_id=job_id,
                job_content_id=job_content_id,
                required_experience=formatted_jd_dict.get('requiredWorkExperience'),
                required_skills=formatted_jd_dict.get('requiredSkills'),
                roles_responsibilities=formatted_jd_dict.get('rolesAndResponsibilities'),
                requiredQualifications=formatted_jd_dict.get('requiredQualifications'),
                requiredCertifications=formatted_jd_dict.get('requiredCertifications'),
                processing_status='completed'
            )

            self.db.add(new_processed_jd)
            self._commit_with_rollback("adding new processed JD")
            return new_processed_jd

        except Exception as e:
            logger.error(f"Error in add_processed_jd: {str(e)}")
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
        """Insert or update similarity score data"""
        try:
            logger.info(f"Adding/updating similarity score for application ID: {application_id}")

            existing_score = self.db.query(SimilarityScore).filter(
                SimilarityScore.application_id == application_id
            ).first()

            if existing_score:
                logger.info(f"Updating existing similarity score for application ID: {application_id}")
                existing_score.overall_score = similarity_analysis['matching_score']
                existing_score.match_details = similarity_analysis['sections']
                existing_score.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating similarity score")
                return existing_score

            new_score = SimilarityScore(
                candidate_id=candidate_id,
                job_id=job_id,
                application_id=application_id,
                processed_resume_id=processed_resume_id,
                processed_jd_id=processed_jd_id,
                overall_score=similarity_analysis['matching_score'],
                match_details=similarity_analysis['sections']
            )

            self.db.add(new_score)
            self._commit_with_rollback("adding new similarity score")
            return new_score

        except Exception as e:
            logger.error(f"Error in add_similarity_score: {str(e)}")
            raise

    def get_application_by_id(self, application_id: int) -> Optional[Application]:
        """Get application by application_id"""
        try:
            logger.info(f"Fetching application with ID: {application_id}")
            application = self.db.query(Application).filter(
                Application.application_id == application_id
            ).first()

            if application:
                logger.info(f"Found application with ID: {application_id}")
            else:
                logger.info(f"No application found with ID: {application_id}")

            return application

        except Exception as e:
            logger.error(f"Error in get_application_by_id: {str(e)}")
            raise

    def get_job_content(self, job_id: int) -> Optional[JobContent]:
        """Get job content by job_id"""
        try:
            logger.info(f"Fetching job content for job ID: {job_id}")
            content = self.db.query(JobContent).filter(
                JobContent.job_id == job_id
            ).first()

            if content:
                logger.info(f"Found job content for job ID: {job_id}")
            else:
                logger.info(f"No job content found for job ID: {job_id}")

            return content

        except Exception as e:
            logger.error(f"Error in get_job_content: {str(e)}")
            raise

    def get_job_by_job_id(self, job_id: int) -> Optional[Job]:
        """Get job by greenhouse job_id"""
        try:
            logger.info(f"Fetching job with job ID: {job_id}")
            job = self.db.query(Job).filter(
                Job.job_id == job_id
            ).first()

            if job:
                logger.info(f"Found job with job ID: {job_id}")
            else:
                logger.info(f"No job found with job ID: {job_id}")

            return job

        except Exception as e:
            logger.error(f"Error in get_job_by_job_id: {str(e)}")
            raise

    def get_candidate_by_id(self, candidate_id: int) -> Optional[Candidate]:
        """Get candidate by candidate_id"""
        try:
            logger.info(f"Fetching candidate with ID: {candidate_id}")
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()

            if candidate:
                logger.info(f"Found candidate with ID: {candidate_id}")
            else:
                logger.info(f"No candidate found with ID: {candidate_id}")

            return candidate

        except Exception as e:
            logger.error(f"Error in get_candidate_by_id: {str(e)}")
            raise

    def get_top_resumes_for_job(self, job_id: int) -> List[SimilarityScore]:
        """
        Fetch the top 10 resumes for the given job ID, ordered by overall score
        """
        try:
            logger.info(f"Fetching top 10 resumes for job ID: {job_id}")

            top_resumes = self.db.query(SimilarityScore) \
                .filter(SimilarityScore.job_id == job_id) \
                .order_by(SimilarityScore.overall_score.desc()) \
                .limit(10) \
                .all()

            return top_resumes

        except Exception as e:
            logger.error(f"Error in get_top_resumes_for_job: {str(e)}")
            raise

    def update_attachment_storage_path(self, attachment_id: int, storage_path: str) -> CandidateAttachment:
        """Update the blob_storage_path and status of an attachment"""
        try:
            logger.info(f"Updating storage path for attachment ID: {attachment_id}")

            attachment = self.db.query(CandidateAttachment).filter(
                CandidateAttachment.id == attachment_id
            ).first()

            if not attachment:
                raise Exception(f"Attachment not found with ID: {attachment_id}")

            attachment.blob_storage_path = storage_path
            attachment.status = 'downloaded'
            attachment.updated_at = datetime.utcnow()

            self._commit_with_rollback("updating attachment storage path")
            logger.info(f"Successfully updated storage path for attachment ID: {attachment_id}")

            return attachment

        except Exception as e:
            logger.error(f"Error in update_attachment_storage_path: {str(e)}")
            raise
