# from fastapi import APIRouter, Depends, Request, HTTPException
# from fastapi.responses import JSONResponse
# from sqlalchemy.orm import Session
# from app.database import get_db
# from app.greenhouse_applications.dao import DAO
# import hmac
# import hashlib
# import logging
# from app.greenhouse_applications.greenhouse_api import GreenhouseService
#
# router = APIRouter()
# logger = logging.getLogger(__name__)
#
#
# @router.post("/simulate_webhook")
# async def simulate_webhook(request: Request, db: Session = Depends(get_db)):
#     secret_key = "your_secret_key_here"
#     signature = request.headers.get("Signature")
#
#     # Verify signature
#     if not signature or not verify_signature(secret_key, await request.body(), signature):
#         logger.warning("Invalid signature received.")
#         raise HTTPException(status_code=403, detail="Invalid signature")
#
#     try:
#         # 1. Get webhook data
#         data = await request.json()
#         logger.info("Incoming webhook data received")
#
#         application_data = data['payload']['application']
#         candidate_data = application_data['candidate']
#         job_data = application_data['jobs'][0]  # Assuming the first job in the array
#
#         # Fix: Correct way to get job_id from job_data
#         job_id = job_data['id']  # Changed from application_data['jobs']['id']
#
#         # 2. Initialize DAO
#         dao = DAO(db)
#
#         # 3. Process candidate and attachments
#         logger.info("Processing candidate data")
#         candidate_record = dao.add_candidate(candidate_data)
#
#         logger.info("Processing attachments")
#         for attachment in candidate_data.get('attachments', []):
#             dao.add_candidate_attachment(candidate_record.candidate_id, attachment)
#
#         # 4. Process job and application
#         logger.info("Processing job data")
#         job_record = dao.add_job(job_data)
#
#         logger.info("Processing application data")
#         application_record = dao.add_application(
#             application_data,
#             candidate_record.candidate_id,
#             job_record.job_id
#         )
#
#         # 5. Fetch and save job content using the job_id
#         logger.info(f"Fetching job content for job_id: {job_id}")
#         greenhouse_service = GreenhouseService(board_token="your_board_token")
#         job_content_data = await greenhouse_service.fetch_job_content(job_id)
#
#         logger.info("Saving job content")
#         # Fix: Use job_record.job_id instead of job_id for consistency
#         job_content_record = dao.add_job_content(job_record.job_id, job_content_data)
#
#         logger.info(
#             f"Webhook processed successfully for candidate: {candidate_data['first_name']} {candidate_data['last_name']}")
#
#         return JSONResponse(
#             content={
#                 "message": "Webhook received and processed",
#                 "candidate_id": candidate_record.candidate_id,
#                 "job_id": job_record.job_id,  # Changed from job_id to job_record.job_id
#                 "application_id": application_record.application_id
#             },
#             status_code=200
#         )
#
#     except Exception as e:
#         logger.error("Error processing webhook: %s", str(e))
#         raise HTTPException(status_code=500, detail=str(e))  # Changed to include error message
#
#
# def verify_signature(secret_key: str, message_body: bytes, signature: str) -> bool:
#     hash = hmac.new(secret_key.encode(), message_body, hashlib.sha256).hexdigest()
#     return hmac.compare_digest(hash, signature)
from typing import Dict, List

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.greenhouse_applications.dao import DAO
import hmac
import hashlib
import logging
from app.greenhouse_applications.greenhouse_api import GreenhouseService

from app.greenhouse_applications.services import format_jd_with_gpt, job_content, format_resume_with_gpt, \
    resume_content_sample, generate_similarity_scores

router = APIRouter()
from app.core.logger_setup import setup_logger

# Set up the logger
logger = setup_logger()


@router.post("/simulate_webhook")
async def simulate_webhook(request: Request, db: Session = Depends(get_db)):
    global processed_resume_record
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
        job_id = job_data['id']

        # 2. Initialize DAO
        dao = DAO(db)

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
            attachment_record = dao.add_candidate_attachment(candidate_record.candidate_id, attachment)

            # Identify and store resume attachment specifically
            if attachment.get('type') == 'resume':
                resume_attachment = attachment_record
                logger.info(f"Resume attachment identified: {attachment.get('filename')}")

        # 5. Process job and application
        logger.info("Processing job data")
        job_record = dao.add_job(job_data)

        logger.info("Processing application data")
        application_record = dao.add_application(
            application_data,
            candidate_record.candidate_id,
            job_record.job_id
        )

        # 6. Fetch and save job content
        logger.info(f"Fetching job content for job_id: {job_id}")
        greenhouse_service = GreenhouseService(board_token="your_board_token")
        job_content_data = await greenhouse_service.fetch_job_content(job_id)

        logger.info("Saving job content")
        job_content_record = dao.add_job_content(job_record.job_id, job_content_data)

        # Save Formatted JD
        # Process job content and save formatted JD
        logger.info(f"Processing job description for job ID: {job_record.job_id}")
        try:
            analysis = format_jd_with_gpt(job_content)

            # Save processed JD
            processed_jd_record = dao.add_processed_jd(
                job_record.job_id,
                job_content_record.id,
                analysis
            )

            logger.info(f"Successfully processed and saved JD for job ID: {job_record.job_id}")

        except Exception as e:
            logger.error(f"Failed to process or save JD: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing job description: {str(e)}")

        # Save formatted Resume:
        if resume_attachment:
            try:
                logger.info(f"Processing resume for candidate ID: {candidate_record.candidate_id}")

                # Format resume with GPT
                analysis = format_resume_with_gpt(resume_content_sample)

                # Save processed resume
                processed_resume_record = dao.add_processed_resume(
                    candidate_id=candidate_record.candidate_id,
                    attachment_id=resume_attachment.id,
                    formatted_resume=analysis
                )

                logger.info(
                    f"Successfully processed resume for candidate: {candidate_data['first_name']} {candidate_data['last_name']}")

            except Exception as e:
                logger.error(f"Error processing resume: {str(e)}")

        #Insering Background data:

        resume_bg_record = processed_resume_record.experience_section

        # SIMILARITY SCORE:
        # After processing resume and JD
        if processed_resume_record and processed_jd_record and application_record:
            try:
                # Generate similarity scores
                similarity_analysis = await generate_similarity_scores(
                    resume_data={
                        "experience": processed_resume_record.experience_section,
                        "skills": processed_resume_record.skills_section,
                        "qualifications": processed_resume_record.qualifcation_section,
                        "projects": processed_resume_record.project_section,
                        "certifications": processed_resume_record.certifications
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

            except Exception as e:
                logger.error(f"Error processing similarity scores: {str(e)}")
        logger.info(
            f"Webhook processed successfully for candidate: {candidate_data['first_name']} {candidate_data['last_name']}")

        return JSONResponse(
            content={
                "message": "Webhook received and processed",
                "candidate_id": candidate_record.candidate_id,
                "processed_resume_record.id": processed_resume_record.id,
                "job_id": job_record.job_id,
                "application_id": application_record.application_id,
                "status": "new"
            },
            status_code=201  # Created status code
        )

    except Exception as e:
        logger.error("Error processing webhook: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


def verify_signature(secret_key: str, message_body: bytes, signature: str) -> bool:
    hash = hmac.new(secret_key.encode(), message_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(hash, signature)


@router.get("/top-resumes/{job_id}", response_model=List[Dict[str, str]])
async def get_top_resumes(job_id: int, db: Session = Depends(get_db)):
    """
    Fetch the top 10 resumes for the given job ID, along with the candidate details.

    Args:
        job_id (int): The ID of the job for which to fetch the top resumes.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing the candidate details.
    """
    try:
        dao = DAO(db)
        top_resumes = dao.get_top_resumes_for_job(job_id)

        result = []
        for resume_score in top_resumes:
            candidate = dao.get_candidate_by_id(resume_score.candidate_id)
            result.append({
                "candidate_id": str(candidate.candidate_id),
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "overall_score": str(resume_score.overall_score)
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from app.greenhouse_applications.models import ProcessedResume

@router.get("/fetch-top-resumes/{job_id}")
async def get_top_resumes_db(job_id: int, db: Session = Depends(get_db)):
    try:
        dao = DAO(db)
        top_resumes = dao.get_top_resumes_for_job(job_id)

        result = []
        for resume_score in top_resumes:
            candidate = dao.get_candidate_by_id(resume_score.candidate_id)
            processed_resume = (
                dao.db.query(ProcessedResume)
                .filter(ProcessedResume.candidate_id == candidate.candidate_id)
                .first()
            )

            match_details = resume_score.match_details if resume_score.match_details else []

            # Construct the response as a dictionary
            result.append({
                "candidate_id": str(candidate.candidate_id),
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "overall_score": str(resume_score.overall_score),
                "match_details": match_details,  # List of dictionaries
                "company_bg_details": processed_resume.company_bg_details if processed_resume else "",  # Empty string if None
                "url": candidate.url
            })

        return result  # Return the constructed result directly

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
