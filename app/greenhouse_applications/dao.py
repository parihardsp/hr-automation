"""Importing all the necessary libraries"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from .models import Candidate, CandidateAttachment, Job, Application, JobContent,  ProcessedJD, ProcessedResume, SimilarityScore

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
            logger.error("Error during %s: %s", operation, str(e))
            raise

    def add_candidate(self, candidate_data: Dict[str, Any]) -> Candidate:
        """
        Insert candidate data from webhook.

        Args:
            candidate_data: Dictionary containing candidate information.

        Returns:
            Candidate: The added candidate record.
        """
        try:
            logger.info("Adding candidate: %s %s", candidate_data['first_name'], candidate_data['last_name'])

            # Check if candidate already exists
            existing_candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_data['id']
            ).first()

            if existing_candidate:
                logger.info("Candidate already exists with ID: %s", candidate_data['id'])
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
            logger.info("Successfully added candidate with ID: %s", candidate.candidate_id)
            return candidate

        except Exception as e:
            self.db.rollback()
            logger.error("Error adding candidate: %s", str(e))
            raise Exception(f"Error adding candidate: {str(e)}")
        
    def update_candidate_from_resume(self, candidate_id: int, processed_resume: Dict[str, Any]) -> Candidate:
        """
        Update candidate information from processed resume data.
        
        Args:
            candidate_id: The ID of the candidate to update
            processed_resume: Dictionary containing processed resume information
            
        Returns:
            Candidate: Updated candidate record
        """
        try:
            logger.info("Updating candidate %d with processed resume data", candidate_id)

            # Get existing candidate
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()

            if not candidate:
                raise Exception(f"Candidate not found with ID: {candidate_id}")

            # Get personal info from processed resume
            personal_info = processed_resume.get('personalInfo', {})
            
            # Update candidate fields if they exist in the resume
            if personal_info.get('name'):
                name_parts = personal_info['name'].split(maxsplit=1)
                candidate.first_name = name_parts[0]
                candidate.last_name = name_parts[1] if len(name_parts) > 1 else ''
            if personal_info.get('email'):
                candidate.email_addresses = [personal_info['email']]
            if personal_info.get('phone'):
                candidate.phone_numbers = [personal_info['phone']]
            if personal_info.get('location'):
                candidate.addresses = [personal_info['location']]
            # Update professional information
            work_experience = processed_resume.get('workExperience', [])
            if work_experience:
                latest_job = work_experience[0]  # Most recent job
                candidate.title = latest_job.get('position')
                candidate.company = latest_job.get('companyName')

            # Update education with exact format matching
            education = processed_resume.get('education', [])
            if education:
                candidate.education = [
                    {
                        'degree': edu.get('degree'),
                        'field_of_study': edu.get('field'),
                        'school_name': edu.get('institution'),
                        'graduation_year': edu.get('graduationYear'),
                        'gpa': edu.get('gpa')
                    }
                    for edu in education
                    if any(edu.values())  # Only include education entries that have any values
                ]

            # Update skills as tags
            skills = processed_resume.get('skills', {})
            all_skills = []
            all_skills.extend(skills.get('technical', []))
            all_skills.extend(skills.get('soft', []))
            all_skills.extend(skills.get('languages', []))
            if all_skills:
                candidate.tags = all_skills
            custom_fields = {}
            # Get existing custom_fields if any
            if candidate.custom_fields:
                custom_fields = candidate.custom_fields.copy()
            certifications = processed_resume.get('certifications', [])
            if certifications:
                custom_fields['certifications'] = certifications
            projects = processed_resume.get('projects', [])
            if projects:
                custom_fields['projects'] = projects
            company_background = processed_resume.get('companyBackground')
            if company_background:
                custom_fields['company_background'] = company_background
            
            logger.info("Previous custom_fields: %s", candidate.custom_fields)
            logger.info("New custom_fields: %s", custom_fields)
            candidate.custom_fields = custom_fields
            candidate.updated_at = datetime.utcnow()

            self.db.commit()
            logger.info("Successfully updated candidate %d with resume data", candidate_id)
            logger.info("Final custom_fields: %s", candidate.custom_fields)

            return candidate

        except Exception as e:
            self.db.rollback()
            logger.error("Error updating candidate from resume: %s", str(e))
            raise Exception(f"Error updating candidate from resume: {str(e)}")

    def add_candidate_attachment(self, candidate_id: int, attachment_data: Dict[str, Any]) -> CandidateAttachment:
        """
        Insert candidate attachment data.
        blob_storage_path will be updated later when file is downloaded and stored
        """
        try:
            logger.info("Adding attachment for candidate ID: %d", candidate_id)

            # Check if attachment already exists
            existing_attachment = self.db.query(CandidateAttachment).filter(
                CandidateAttachment.candidate_id == candidate_id,
                CandidateAttachment.url == attachment_data['url']
            ).first()

            if existing_attachment:
                logger.info("Attachment already exists for candidate ID: %d", candidate_id)
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
            logger.info("Successfully added attachment for candidate ID: %d",candidate_id)
            return attachment

        except Exception as e:
            self.db.rollback()
            logger.error("Error adding attachment: %s", str(e))
            raise Exception(f"Error adding attachment: {str(e)}")

    def update_attachment_storage_path(self, attachment_id: int, storage_path: str) -> CandidateAttachment:
        """
        Update the blob_storage_path once file is downloaded and stored.
        This method can be used later when implementing file download functionality.
        """
        try:
            logger.info("Updating storage path for attachment ID: %d",attachment_id)

            attachment = self.db.query(CandidateAttachment).filter(
                CandidateAttachment.id == attachment_id
            ).first()

            if not attachment:
                raise Exception(f"Attachment not found with ID: {attachment_id}")

            attachment.blob_storage_path = storage_path
            attachment.status = 'downloaded'  # Update status when path is set
            self.db.commit()

            logger.info("Successfully updated storage path for attachment ID: %d", attachment_id)
            return attachment

        except Exception as e:
            self.db.rollback()
            logger.error("Error updating attachment storage path: %s", str(e))
            raise Exception(f"Error updating attachment storage path: {str(e)}")

    def add_job(self, job_data: Dict[str, Any]) -> Job:
        """
        Insert basic job data from webhook
        """
        try:
            logger.info("Adding job with ID: %s", job_data['id'])

            # Check if job already exists
            existing_job = self.db.query(Job).filter(
                Job.job_id == job_data['id']
            ).first()

            if existing_job:
                logger.info("Job already exists with ID: %s", job_data['id'])
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
            logger.info("Successfully added job with ID: %s", job.job_id)
            return job

        except Exception as e:
            self.db.rollback()
            logger.error("Error adding job: %s", str(e))
            raise Exception(f"Error adding job: {str(e)}")


    def add_application(self, application_data: Dict[str, Any], candidate_id: int, job_id: int) -> Application:
        """
        Insert application data
        """
        try:
            logger.info("Adding application for candidate ID: %d and job ID: %d", candidate_id, job_id)

            # Check if application already exists
            existing_application = self.db.query(Application).filter(
                Application.application_id == application_data['id']
            ).first()

            if existing_application:
                logger.info("Application already exists with ID: %s", application_data['id'])
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
            logger.info("Successfully added application with ID: %s", application.application_id)
            return application

        except Exception as e:
            self.db.rollback()
            logger.error("Error adding application: %s", str(e))
            raise Exception(f"Error adding application: {str(e)}")
            
    def add_job_content(self, job_id: int, content_data: dict) -> JobContent:
        """
        Insert job content data from Greenhouse API
        """
        try:
            logger.info("Adding/updating job content for job ID: %d", job_id)

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
                logger.info("Updating existing job content for job ID: %d", job_id)
                existing_content.internal_job_id = content_data['internal_job_id']
                existing_content.title = content_data['title']
                existing_content.content = content_data['content']
                existing_content.absolute_url = content_data.get('absolute_url')
                existing_content.location = content_data.get('location', {}).get('name')
                existing_content.pay_range = pay_range
                existing_content.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating job content")
                return existing_content

            logger.info("Creating new job content for job ID: %d", job_id)
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
            logger.info("Successfully added job content for job ID: %d", job_id)
            return job_content

        except Exception as e:
            self.db.rollback()
            logger.error("Error adding job content: %s", str(e))
            raise Exception(f"Error adding job content: {str(e)}")
        
    def get_application_by_id(self, application_id: int) -> Optional[Application]:
        """
        Get application by application_id
        """
        try:
            logger.info("Checking for existing application with ID: %d", application_id)
            application = self.db.query(Application).filter(
                Application.application_id == application_id
            ).first()

            if application:
                logger.info("Found existing application with ID: %d", application_id)
            else:
                logger.info("No existing application found with ID: %d", application_id)

            return application

        except Exception as e:
            logger.error("Error checking application existence: %s", str(e))
            raise Exception(f"Error checking application existence: {str(e)}")

    def get_job_content(self, job_id: int) -> Optional[JobContent]:
        """
        Get job content by job_id
        """
        try:
            logger.info("Fetching job content for job ID: %d", job_id)
            content = self.db.query(JobContent).filter(JobContent.job_id == job_id).first()
            if content:
                logger.info("Found job content for job ID: %d", job_id)
            else:
                logger.info("No job content found for job ID: %d", job_id)
            return content
        except Exception as e:
            logger.error("Error fetching job content: %s", str(e))
            raise Exception(f"Error fetching job content: {str(e)}")

    def get_job_by_job_id(self, job_id: int) -> Optional[Job]:
        """
        Get job by greenhouse job_id
        """
        try:
            logger.info("Fetching job with job ID: %d", job_id)
            job = self.db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                logger.info("Found job with job ID: %d", job_id)
            else:
                logger.info("No job found with job ID: %d", job_id)
            return job
        except Exception as e:
            logger.error("Error fetching job: %s", str(e))
            raise Exception(f"Error fetching job: {str(e)}")

    def get_top_resumes_for_job(self, job_id: int) -> List[SimilarityScore]:
        """
        Fetch the top 10 resumes for the given job ID, ordered by the overall score.

        Args:
            job_id (int): The ID of the job for which to fetch the top resumes.

        Returns:
            List[SimilarityScore]: A list of the top 10 SimilarityScore records for the given job ID.
        """
        try:
            logger.info("Fetching top 10 resumes for job ID: %d", job_id)
            top_resumes = self.db.query(SimilarityScore) \
                .filter(SimilarityScore.job_id == job_id) \
                .order_by(SimilarityScore.overall_score.desc()) \
                .limit(10) \
                .all()

            return top_resumes

        except Exception as e:
            logger.error("Error fetching top resumes for job ID %d: %s", job_id, str(e))
            raise Exception(f"Error fetching top resumes for job ID {job_id}: {str(e)}")

    def get_candidate_by_id(self, candidate_id: int) -> Candidate:
        """
        Fetch a candidate by their ID.

        Args:
            candidate_id (int): The ID of the candidate to fetch.

        Returns:
            Candidate: The Candidate record with the given ID.
        """
        try:
            logger.info("Fetching candidate with ID: %d", candidate_id)
            candidate = self.db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()

            if not candidate:
                logger.info("No candidate found with ID: %d", candidate_id)
                raise Exception(f"No candidate found with ID: {candidate_id}")

            return candidate

        except Exception as e:
            logger.error("Error fetching candidate with ID %d: %s", candidate_id, str(e))
            raise Exception(f"Error fetching candidate with ID {candidate_id}: {str(e)}")

    def add_processed_jd(self, job_id: int, job_content_id: int, formatted_jd: str) -> ProcessedJD:
        """
        Insert processed job description data

        Args:
            job_id: The ID of the job
            job_content_id: The ID of the job content
            formatted_jd: String containing the formatted JD JSON from GPT

        Returns:
            ProcessedJD: The created or updated processed JD record
        """
        try:
            logger.info("Adding processed JD for job ID:%d",job_id)

            # Clean and parse the JSON string
            cleaned_jd = formatted_jd.strip("```json").strip("```").strip()
            formatted_jd_dict = json.loads(cleaned_jd)

            # Check if processed JD already exists
            existing_processed_jd = self.db.query(ProcessedJD).filter(
                ProcessedJD.job_id == job_id,
                ProcessedJD.job_content_id == job_content_id
            ).first()

            if existing_processed_jd:
                logger.info("Updating existing processed JD for job ID:%d",job_id)
                existing_processed_jd.required_experience = formatted_jd_dict.get('requiredWorkExperience')
                existing_processed_jd.required_skills = formatted_jd_dict.get('requiredSkills')
                existing_processed_jd.roles_responsibilities = formatted_jd_dict.get('rolesAndResponsibilities')
                existing_processed_jd.requiredQualifications = formatted_jd_dict.get('requiredQualifications')
                existing_processed_jd.requiredCertifications = formatted_jd_dict.get('requiredCertifications')
                existing_processed_jd.processing_status = 'completed'
                existing_processed_jd.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating processed JD")
                return existing_processed_jd

            processed_jd = ProcessedJD(
                job_id=job_id,
                job_content_id=job_content_id,
                required_experience=formatted_jd_dict.get('requiredWorkExperience'),
                required_skills=formatted_jd_dict.get('requiredSkills'),
                roles_responsibilities=formatted_jd_dict.get('rolesAndResponsibilities'),
                requiredQualifications=formatted_jd_dict.get('requiredQualifications'),
                requiredCertifications=formatted_jd_dict.get('requiredCertifications'),
                processing_status='completed'
            )

            self.db.add(processed_jd)
            self._commit_with_rollback("adding processed JD")
            logger.info("Successfully added processed JD for job ID:%d",job_id)
            return processed_jd

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON for job ID {job_id}: {str(e)}")
            raise Exception(f"Invalid JSON format in formatted JD: {str(e)}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding processed JD: {str(e)}")
            raise Exception(f"Error adding processed JD: {str(e)}")

    def add_processed_resume(self, candidate_id: int, attachment_id: int, formatted_resume: str) -> ProcessedResume:
        """
        Insert processed resume data

        Args:
            candidate_id: The ID of the candidate
            attachment_id: The ID of the candidate attachment (resume file)
            formatted_resume: String containing the formatted resume JSON from GPT

        Returns:
            ProcessedResume: The created or updated processed resume record
        """
        try:
            logger.info("Adding processed resume for candidate ID: %d, attachment ID: %d", candidate_id, attachment_id)

            # Clean and parse the JSON string
            # cleaned_resume = formatted_resume.strip("```json").strip("```").strip()
            formatted_resume_dict = json.loads(formatted_resume)

            # Check if processed resume already exists for this candidate and attachment
            existing_processed_resume = self.db.query(ProcessedResume).filter(
                ProcessedResume.candidate_id == candidate_id,
                ProcessedResume.attachment_id == attachment_id
            ).first()

            if existing_processed_resume:
                logger.info("Updating existing processed resume for candidate ID:%d",candidate_id)
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

            processed_resume = ProcessedResume(
                candidate_id=candidate_id,
                attachment_id=attachment_id,
                personal_section=formatted_resume_dict.get('personalInfo'),
                qualifcation_section=formatted_resume_dict.get('education'),
                experience_section=formatted_resume_dict.get('workExperience'),
                skills_section=formatted_resume_dict.get('skills'),
                certifications=formatted_resume_dict.get('certifications'),
                project_section=formatted_resume_dict.get('projects'),
                company_bg_details=formatted_resume_dict.get('companyBackground'),
                processing_status='completed'
            )

            self.db.add(processed_resume)
            self._commit_with_rollback("adding processed resume")
            logger.info("Successfully added processed resume for candidate ID: %d",candidate_id)
            return processed_resume

        except json.JSONDecodeError as e:
            logger.error("Error decoding JSON for candidate ID %d: %s", candidate_id, str(e))
            # Update status to failed in case of JSON error
            if 'processed_resume' in locals():
                processed_resume.processing_status = 'failed'
                self._commit_with_rollback("updating failed status")
            raise Exception(f"Invalid JSON format in formatted resume: {str(e)}")
        except Exception as e:
            self.db.rollback()
            logger.error("Error adding processed resume: %s", str(e))
            # Update status to failed in case of any other error
            if 'processed_resume' in locals():
                processed_resume.processing_status = 'failed'
                self._commit_with_rollback("updating failed status")
            raise Exception(f"Error adding processed resume: {str(e)}")

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
        Insert similarity score data

        Args:
            candidate_id: ID of the candidate
            job_id: ID of the job
            application_id: ID of the application
            processed_resume_id: ID of the processed resume record
            processed_jd_id: ID of the processed JD record
            similarity_analysis: Dict containing overall score and detailed section analysis
        """
        try:
            logger.info("Adding similarity score for application ID:%d",application_id)

            # Check if similarity score already exists
            existing_score = self.db.query(SimilarityScore).filter(
                SimilarityScore.application_id == application_id
            ).first()

            if existing_score:
                logger.info("Updating existing similarity score for application ID:%d",application_id)
                existing_score.overall_score = similarity_analysis['matching_score']
                existing_score.match_details = similarity_analysis['sections']
                existing_score.updated_at = datetime.utcnow()

                self._commit_with_rollback("updating similarity score")
                return existing_score

            # Create new similarity score record
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
            self._commit_with_rollback("adding similarity score")
            logger.info("Successfully added similarity score for application ID:%d",application_id)
            return new_score

        except Exception as e:
            self.db.rollback()
            logger.error("Error adding similarity score: %s", str(e))
            raise Exception(f"Error adding similarity score: {str(e)}")