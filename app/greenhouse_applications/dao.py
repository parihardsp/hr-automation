import logging
from sqlalchemy.orm import Session
from datetime import datetime
from app.greenhouse_applications.models import Application, Candidate, Job, Score, CandidateAttachment

# Set up logging
logger = logging.getLogger(__name__)

class DAO:
    def __init__(self, db: Session):
        self.db = db

    def add_candidate(self, candidate_data):
        candidate = Candidate(
            candidate_id=candidate_data['id'],
            first_name=candidate_data['first_name'],
            last_name=candidate_data['last_name'],
            title=candidate_data.get('title'),
            company=candidate_data.get('company'),
            url=candidate_data.get('url'),
            phone_numbers=[phone['value'] for phone in candidate_data.get('phone_numbers', [])],
            email_addresses=[email['value'] for email in candidate_data.get('email_addresses', [])],
            education=candidate_data.get('educations', {}),
            addresses=candidate_data.get('addresses', {}),
            tags=candidate_data.get('tags', []),
            custom_fields=candidate_data.get('custom_fields', {})
        )
        try:
            self.db.add(candidate)
            self.db.commit()
            self.db.refresh(candidate)
            logger.info("Candidate added successfully: %s", candidate.first_name + " " + candidate.last_name)
        except Exception as e:
            self.db.rollback()
            logger.error("Error adding candidate: %s", str(e))
            raise e

        return candidate

    def add_job(self, job_data):
        job = Job(
            job_id=job_data['id'],
            name=job_data['name'],
            requisition_id=job_data.get('requisition_id'),
            status=job_data.get('status'),
            url=job_data.get('url'),
            departments=job_data.get('departments', {}),
            offices=job_data.get('offices', {}),
            created_by_id=job_data.get('created_by_id'),
            created_at=job_data.get('created_at'),
            opened_at=job_data.get('opened_at'),
            closed_at=job_data.get('closed_at')
        )
        try:
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            logger.info("Job added successfully: %s", job.name)
        except Exception as e:
            self.db.rollback()
            logger.error("Error adding job: %s", str(e))
            raise e

        return job

    def add_application(self, application_data, candidate_id, job_id):
        application = Application(
            application_id=application_data['id'],
            candidate_id=candidate_id,
            job_id=job_id,
            status=application_data.get('status'),
            applied_at=application_data.get('applied_at'),
            last_activity_at=application_data.get('last_activity_at'),
            url=application_data['url'],
            source=application_data.get('source', {}),
            current_stage=application_data.get('current_stage'),
        )
        try:
            self.db.add(application)
            self.db.commit()
            self.db.refresh(application)
            logger.info("Application added successfully: %s", application.application_id)
        except Exception as e:
            self.db.rollback()
            logger.error("Error adding application: %s", str(e))
            raise e

        return application

    def add_candidate_attachment(self, candidate_id: int, attachment_data):
        attachment = CandidateAttachment(
            candidate_id=candidate_id,
            filename=attachment_data['filename'],
            url=attachment_data['url'],
            type=attachment_data['type'],
            created_at=datetime.utcnow()
        )
        try:
            self.db.add(attachment)
            self.db.commit()
            logger.info("Candidate attachment added successfully for candidate_id: %d", candidate_id)
        except Exception as e:
            self.db.rollback()
            logger.error("Error adding candidate attachment: %s", str(e))
            raise e

    def add_score(self, application_id, score_value):
        score = Score(
            application_id=application_id,
            score=score_value,
            created_at=datetime.utcnow()
        )
        try:
            self.db.add(score)
            self.db.commit()
            self.db.refresh(score)
            logger.info("Score added successfully for application_id: %s", application_id)
        except Exception as e:
            self.db.rollback()
            logger.error("Error adding score: %s", str(e))
            raise e

        return score
