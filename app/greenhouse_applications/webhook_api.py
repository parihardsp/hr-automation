# pylint: disable=C0301
# pylint: disable=E0401

"""Importing all the necessary libraries"""
import os
import sys
import json
import hmac
import hashlib
from pathlib import Path
#from typing import Dict, List
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.greenhouse_applications.greenhouse_api import GreenhouseService
from app.greenhouse_applications.services import CandidateJobEvaluator
from app.core.logger_setup import setup_logger
from app.greenhouse_applications.dao import DAO
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))



router = APIRouter()
logger = setup_logger()


def verify_signature(secret_key: str, message_body: bytes, signature: str) -> bool:
    """
    Verify the webhook signature using HMAC SHA256.

    Args:
        secret_key (str): The secret key for signature verification
        message_body (bytes): The body of the message
        signature (str): The signature to verify

    Returns:
        bool: True if signature is valid, False otherwise
    """
    computed_hash = hmac.new(secret_key.encode(), message_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, signature)


@router.post("/simulate_webhook")
async def simulate_webhook(request: Request, db: Session = Depends(get_db)):
    """Process incoming webhook from Greenhouse application tracking system."""
    secret_key = "your_secret_key_here"
    signature = request.headers.get("Signature")

    # Verify signature
    if not signature or not verify_signature(secret_key, await request.body(), signature):
        logger.warning("Invalid signature received.")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        # 1. Get webhook data
        data = await request.json()
        logger.info("Incoming webhook data received")

        application_data = data['payload']['application']
        candidate_data = application_data['candidate']
        job_data = application_data['jobs'][0]  # Assuming the first job in the array

        # Fix: Correct way to get job_id from job_data
        job_id = job_data['id']  # Changed from application_data['jobs']['id']

        # 2. Initialize DAO & CandidateJobEvaluator
        dao = DAO(db)
        processor = CandidateJobEvaluator()

        # 3. Check if application already exists
        existing_application = dao.get_application_by_id(application_data['id'])
        if existing_application:
            logger.warning(f"Application already exists with ID: {application_data['id']}")
            return JSONResponse(
                content={
                    "message": "Application already exists",
                    "application_id": existing_application.application_id,
                    "status": "existing"
                },
                status_code=409  # Conflict status code
            )

        # 4. Process candidate and attachments
        logger.info("Processing candidate data")
        candidate_record = dao.add_candidate(candidate_data)

        logger.info("Processing attachments")
        resume_attachment = None
        for attachment in candidate_data.get('attachments', []):
            attachment_record = dao.add_candidate_attachment(
                candidate_record.candidate_id, attachment)
            # Identify and store resume attachment specifically
            if attachment.get('type') == 'resume':
                resume_attachment = attachment_record
                logger.info(f"Resume attachment identified: {attachment.get('filename')}")

        # 4. Process job and application
        logger.info("Processing job data")
        job_record = dao.add_job(job_data)

        logger.info("Processing application data")
        application_record = dao.add_application(
            application_data,
            candidate_record.candidate_id,
            job_record.job_id
        )

        # 5. Fetch and save job content using the job_id
        logger.info(f"Fetching job content for job_id: {job_id}")
        greenhouse_service = GreenhouseService(board_token="your_board_token")
        job_content_data = await greenhouse_service.fetch_job_content(job_id)

        logger.info("Saving job content")
        # Fix: Use job_record.job_id instead of job_id for consistency
        job_content_record = dao.add_job_content(job_record.job_id, job_content_data)

        # Save Formatted JD
        # Process job content and save formatted JD
        logger.info(f"Processing job description for job ID:{job_record.job_id}")
        job_content = """job_content = "Job Title: Software Engineer Department: Technology &amp; Development Location:Remote / [Your Location] Employment Type: Full-Time Job Summary: We are seeking a highly motivated and skilled Software Engineer to join our dynamic development team. The successful candidate will be responsible for designing,developing, and implementing software solutions to address complex business challenges. This role involves working with cross-functional teams to define system requirements, troubleshoot issues, and deploy high-quality software.Responsibilities: Design, develop, test, and deploy high-quality software applications. Collaborate with product management,design, and other teams to understand requirements and deliver solutions. Perform code reviews and provide constructive feedback to peers. Write and maintain documentation for all software solutions. Troubleshoot and debug applications to optimize performance and functionality. Stay up-to-date with industry trends and technologies to improve skills and enhance software capabilities. Ensure application security, maintainability, and scalability are addressed in the design.Required Skills &amp; Qualifications: Bachelor&#39;s degree in Computer Science, Software Engineering, or related field.3+ years of experience in software development. Proficiency in Python, JavaScript, and related frameworks (e.g., React, Django).Experience with RESTful API design and development. Knowledge of database systems like PostgreSQL, MySQL, or MongoDB.Familiarity with version control systems, especially Git. Strong analytical and problem-solving skills. Excellent communication and collaboration abilities. Preferred Qualifications: Experience with cloud platforms like AWS, Azure, or Google Cloud.Knowledge of containerization tools (e.g., Docker) and CI/CD pipelines. Familiarity with Agile and Scrum development methodologies.Benefits: Competitive salary and performance-based incentives. Flexible working hours and remote work options. Comprehensive health,dental, and vision insurance. Opportunities for professional growth and development. A collaborative and innovative work environment.We are committed to creating a diverse and inclusive workplace and encourage applications from candidates of all backgrounds.Any HTML included through the hosted job application editor will be automatically converted into corresponding HTML entities.&amp;lt;/p&amp;gt;"""
        try:
            analysis = processor.format_jd_with_gpt(job_content)

            # Save processed JD
            processed_jd_record = dao.add_processed_jd(
                job_record.job_id,
                job_content_record.id,
                analysis
            )

            logger.info(f"Successfully processed and saved JD for job ID:{job_record.job_id}")

        except Exception as e:
            logger.error(f"Failed to process or save JD: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing job description: {str(e)}")

        # Save formatted Resume:
        processed_resume_record_dummy = None

        if resume_attachment:
            try:
                logger.info(f"Processing resume for candidate ID:{candidate_record.candidate_id}")
                # pdf_filename = resume_attachment.filename
                pdf_filename = 'AnjaliDaya_2.4 years_Finance assocaite.pdf'
                # result = processor.process_resume(resume_attachment.filename)
                #  Process the resume fetch the filename from the webhook data
                pdf_path =Path('/Users/maitreekatiyar/Desktop/Agilysis_Projects/hr-automation/Resumes').joinpath(pdf_filename)
                logger.info(f"Looking for file at path: {pdf_path}")

                if not os.path.exists(pdf_path):
                    logger.error(f"File not found: {pdf_path}")
                    return False
                result = processor.process_resume(pdf_filename)
                if result["status"] == "success":
                    logger.info(f"Resume processed successfully for candidate ID:{candidate_record.candidate_id}"
                                )

                    # Update blob storage path using the DAO method
                    dao.update_attachment_storage_path(
                        attachment_id=resume_attachment.id,
                        storage_path=result["blob_pdf_url"]
                    )
                    analysis = json.dumps(result["formatted_resume"])

                    processed_resume_record = dao.add_processed_resume(
                    candidate_id=candidate_record.candidate_id,
                    attachment_id=resume_attachment.id,
                    formatted_resume=analysis
                )

                    processed_resume_record_dummy = processed_resume_record

                

                    # dao.update_candidate_from_resume(
                    #     candidate_id=candidate_record.candidate_id,
                    #     processed_resume=result["formatted_resume"])   
                logger.info(f"Successfully processed resume for candidate:{candidate_data['first_name']} {candidate_data['last_name']}")
            except Exception as e:
                logger.error(f"Error processing resume: {str(e)}")

        # SIMILARITY SCORE:
        # After processing resume and JD
        if processed_resume_record_dummy and processed_jd_record and application_record:
            try:
                logger.info("Preparing resume data for similarity analysis")


                experience_section = (
                    json.loads(processed_resume_record.experience_section)
                    if isinstance(processed_resume_record.experience_section, str)
                    else processed_resume_record.experience_section
                )
                skills_section = (
                    json.loads(processed_resume_record.skills_section)
                    if isinstance(processed_resume_record.skills_section, str)
                    else processed_resume_record.skills_section
                )
                qualifications_section = (
                    json.loads(processed_resume_record.qualifcation_section)
                    if isinstance(processed_resume_record.qualifcation_section, str)
                    else processed_resume_record.qualifcation_section
                )
                projects_section = (
                    json.loads(processed_resume_record.project_section)
                    if isinstance(processed_resume_record.project_section, str)
                    else processed_resume_record.project_section
                )
                certifications_section = (
                    json.loads(processed_resume_record.certifications)
                    if isinstance(processed_resume_record.certifications, str)
                    else processed_resume_record.certifications
                )

                # Generate similarity scores
                similarity_analysis =  processor.generate_similarity_scores(
                    resume_text={
                        "experience": experience_section,
                        "skills": skills_section,
                        "qualifications": qualifications_section,
                        "projects": projects_section,
                        "certifications": certifications_section
                    },
                    jd_data={
                        "required_experience": processed_jd_record.required_experience,
                        "required_skills": processed_jd_record.required_skills,
                        "roles_responsibilities": processed_jd_record.roles_responsibilities,
                        "required_qualifications": processed_jd_record.requiredQualifications,
                        "required_certifications": processed_jd_record.requiredCertifications
                    },
                    application_id=application_record.application_id

                )

                # Save similarity scores using DAO
                similarity_score_record = dao.add_similarity_score(
                    candidate_id=candidate_record.candidate_id,
                    job_id=job_record.job_id,
                    application_id=application_record.application_id,
                    processed_resume_id=processed_resume_record.id,
                    processed_jd_id=processed_jd_record.id,
                    similarity_analysis=similarity_analysis
                )

                logger.info(
                    f"Successfully processed similarity scores. Overall score: {similarity_score_record.overall_score}")

            except Exception as similarity_error:
                logger.error(f"Error processing similarity scores: {str(similarity_error)}")
        logger.info(
            f"Webhook processed successfully for candidate: {candidate_data['first_name']} {candidate_data['last_name']}")

        return JSONResponse(
            content={
                "message": "Webhook received and processed",
                "candidate_id": candidate_record.candidate_id,
                "job_id": job_record.job_id,  # Changed from job_id to job_record.job_id
                "application_id": application_record.application_id
            },
            status_code=200
        )

    except Exception as e:
        logger.error("Error processing webhook: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))  # Changed to include error message
