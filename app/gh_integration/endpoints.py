import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.database import get_db
from app.gh_integration.dao import DAO
from fastapi import Request
from app.gh_integration.job_board_api import SimulateJobUrl
from app.gh_integration.services import CandidateJobEvaluator

from app.gh_integration.models import (
    Job,
    Candidate,
    SimilarityScore,
    ProcessedResume
)
from app.gh_integration.schema import (
    ResumeResponse,
    SortCriteria
)
from sqlalchemy import desc
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.core.config import settings

from app.core.logger_setup import setup_logger

# Set up the logger
logger = setup_logger(__name__)

# Set up router
router = APIRouter()

url_secret_key = settings.URL_SECRET_KEY

@router.post("/simulate_webhook")
async def simulate_webhook(request: Request, db: Session = Depends(get_db)):
    secret_key = url_secret_key
    signature = request.headers.get("Signature")

    if not signature or not verify_signature(secret_key, await request.body(), signature):
        logger.warning("Invalid signature received.")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        # 1. Get webhook data
        data = await request.json()
        logger.info("Incoming webhook data received")

        application_data = data['payload']['application']
        candidate_data = application_data['candidate']
        job_data = application_data['jobs'][0]
        job_id = job_data['id']

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
                status_code=409
            )

        # 4. Process candidate (creates new record each time)
        logger.info("Creating new candidate record")
        candidate_record = dao.add_candidate(candidate_data)

        # 5. Process attachments (creates new record for each attachment)
        logger.info("Processing attachments")
        resume_attachment = None
        for attachment in candidate_data.get('attachments', []):
            attachment_record = dao.add_candidate_attachment(candidate_record.id, attachment)  # Using candidate.id now
            if attachment.get('type') == 'resume':
                resume_attachment = attachment_record
                logger.info(f"Resume attachment identified: {attachment.get('filename')}")

        # 6. Process job (get existing or create new)
        logger.info("Processing job data")
        job_record = dao.get_or_create_job(job_data)

        # 7. Process application
        logger.info("Processing application data")
        application_record = dao.add_application(
            application_data,
            candidate_record.id,  # Using candidate.id
            job_record.job_id  # Using job.job_id as it's unique
        )

        # 8. Process job content
        logger.info(f"Fetching job content for job_id: {job_id}")
        job_ulr_service = SimulateJobUrl(board_token="your_board_token")
        job_content_data = await job_ulr_service.fetch_job_content(job_id)

        logger.info("Saving job content")
        job_content_record = dao.get_or_create_job_content(job_record.job_id, job_content_data)

        # 9. Process and save JD
        logger.info(f"Processing job description for job ID: {job_record.job_id}")

        job_content = """Job Title: Senior Software Engineer Department: Technology &amp; Development Location: Remote / Hybrid (Bangalore, India) Employment Type: Full-Time Job Summary: We are seeking a highly motivated and skilled Senior Software Engineer to join our dynamic development team. The successful candidate will be responsible for designing, developing, and implementing software solutions to address complex business challenges. This role involves working with cross-functional teams to define system requirements, troubleshoot issues, and deploy high-quality software. Key Responsibilities: &amp;lt;ul&amp;gt;&amp;lt;li&amp;gt;Design, develop, test, and deploy high-quality software applications&amp;lt;/li&amp;gt;&amp;lt;li&amp;gt;Lead technical design discussions and architecture planning&amp;lt;/li&amp;gt;&amp;lt;li&amp;gt;Collaborate with product management and design teams&amp;lt;/li&amp;gt;&amp;lt;li&amp;gt;Mentor junior developers and perform code reviews&amp;lt;/li&amp;gt;&amp;lt;/ul&amp;gt; Required Skills &amp; Qualifications: &amp;lt;ul&amp;gt;&amp;lt;li&amp;gt;Bachelor's degree in Computer Science or related field&amp;lt;/li&amp;gt;&amp;lt;li&amp;gt;5+ years of experience in software development&amp;lt;/li&amp;gt;&amp;lt;li&amp;gt;Strong proficiency in Python, JavaScript, React, Django&amp;lt;/li&amp;gt;&amp;lt;li&amp;gt;Experience with microservices and RESTful APIs&amp;lt;/li&amp;gt;&amp;lt;/ul&amp;gt; Benefits: Competitive salary (15-25 LPA), health insurance, flexible work hours. &amp;lt;p&amp;gt;Any HTML included through the hosted job application editor will be automatically converted into corresponding HTML entities.&amp;lt;/p&amp;gt;"""
        try:
            if not job_content:
                raise ValueError("Empty job content")

            analysis = processor.format_jd_with_gpt(job_content)
            if not analysis:
                raise ValueError("Failed to format job description with GPT")

            processed_jd_record = dao.get_or_create_processed_jd(
                job_record.job_id,
                job_content_record.id,
                analysis
            )
            logger.info(f"Successfully processed and saved JD")

            # # Use actual content from job_content_record
            # if job_content_record and job_content_record.content:
            #     analysis = processor.format_jd_with_gpt(job_content_record.content)
            #     processed_jd_record = dao.get_or_create_processed_jd(
            #         job_record.job_id,
            #         job_content_record.id,
            #         analysis
            #     )
            #     logger.info(f"Successfully processed and saved JD")
            # else:
            #     raise ValueError("No job content available")

        except Exception as e:
            logger.error(f"Failed to process or save JD: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing job description: {str(e)}")

        # 10. Process resume
        processed_resume_record = None
        if resume_attachment:
            try:
                logger.info(f"Processing resume for candidate ID: {candidate_record.id}")
                pdf_filename = 'AkshayRodi.pdf'  # Your test file
                pdf_path = Path('./Resumes') / pdf_filename

                if not os.path.exists(pdf_path):
                    logger.error(f"File not found: {pdf_path}")
                else:
                    result = processor.process_resume(pdf_filename)
                    if result["status"] == "success":
                        logger.info("Resume processed successfully")

                        # Update blob storage path
                        dao.update_attachment_storage_path(
                            attachment_id=resume_attachment.id,
                            storage_path=result["blob_pdf_url"]
                        )

                        # Save processed resume
                        processed_resume_record = dao.add_processed_resume(
                            candidate_id=candidate_record.id,  # Using candidate.id
                            attachment_id=resume_attachment.id,
                            formatted_resume=json.dumps(result["formatted_resume"])
                        )

            except Exception as e:
                logger.error(f"Error processing resume: {str(e)}")

        else:
            logger.warning(f"No resume attachment found for candidate ID: {candidate_record.id}")

        # 11. Calculate similarity score
        if processed_resume_record and processed_jd_record and application_record:
            try:
                logger.info("Calculating similarity scores")

                # Convert JSON strings if needed

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
                # ... Future [similar conversions for other sections]

                similarity_analysis = processor.generate_similarity_scores(
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

                similarity_score_record = dao.add_similarity_score(
                    candidate_id=candidate_record.id,  # Using candidate.id
                    job_id=job_record.job_id,
                    application_id=application_record.application_id,
                    processed_resume_id=processed_resume_record.id,
                    processed_jd_id=processed_jd_record.id,
                    similarity_analysis=similarity_analysis
                )

                logger.info(f"Successfully calculated similarity score: {similarity_score_record.overall_score}")

            except Exception as e:
                logger.error(f"Error calculating similarity scores: {str(e)}")

        return JSONResponse(
            content={
                "message": "Webhook processed successfully",
                "candidate_id": candidate_record.id,  # Using candidate.id
                "job_id": job_record.job_id,
                "application_id": application_record.application_id
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def verify_signature(secret_key: str, message_body: bytes, signature: str) -> bool:
    hash = hmac.new(secret_key.encode(), message_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(hash, signature)


@router.get("/jobs/{job_id}/resumes")
async def get_resumes_by_job(
        job_id: int,
        sort_by: SortCriteria = Query(SortCriteria.overall_score, description="Sort criteria"),
        limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
        db: Session = Depends(get_db)
):
    try:
        query = (
            db.query(
                Job.title.label('job_title'),
                Candidate.id.label('id'),
                Candidate.candidate_id.label('candidate_id'),
                Candidate.first_name,
                Candidate.last_name,
                SimilarityScore.overall_score,
                SimilarityScore.match_details,
                ProcessedResume.company_bg_details
            )
            .join(SimilarityScore, Job.job_id == SimilarityScore.job_id)
            .join(Candidate, SimilarityScore.candidate_id == Candidate.id)
            .join(ProcessedResume, Candidate.id == ProcessedResume.candidate_id)
            .filter(Job.job_id == job_id)
        )

        # Only sort by overall_score in database query
        if sort_by == SortCriteria.overall_score:
            query = query.order_by(desc(SimilarityScore.overall_score))

        results = query.all()  # Get all results first

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No resumes found for job ID {job_id}"
            )

        formatted_results = []
        for result in results:
            try:
                match_details = result.match_details
                if isinstance(match_details, str):
                    match_details = json.loads(match_details)

                company_bg_details = result.company_bg_details
                if isinstance(company_bg_details, str):
                    company_bg_details = json.loads(company_bg_details)

                # Find specific score based on sort criteria
                specific_score = 0
                if sort_by != SortCriteria.overall_score:
                    score_type_map = {
                        SortCriteria.skills_match: "Skills Match",
                        SortCriteria.experience_match: "Experience Match",
                        SortCriteria.education_match: "Education Match"
                    }
                    for detail in match_details:
                        if detail.get('name') == score_type_map[sort_by]:
                            specific_score = float(detail.get('score', 0))
                            break

                formatted_result = {
                    "title": result.job_title,
                    "id": result.id,
                    "candidate_id": result.candidate_id,
                    "candidate_name": f"{result.first_name} {result.last_name}".strip(),
                    "overall_score": float(result.overall_score),
                    "match_details": match_details,
                    "company_bg_details": company_bg_details,
                    "_sort_score": specific_score if sort_by != SortCriteria.overall_score else float(
                        result.overall_score)
                }
                formatted_results.append(formatted_result)
            except Exception as e:
                logger.error(f"Error formatting result: {str(e)}")
                continue

        # Sort results based on criteria
        if sort_by != SortCriteria.overall_score:
            formatted_results.sort(key=lambda x: x['_sort_score'], reverse=True)

        # Apply limit after sorting
        formatted_results = formatted_results[:limit]

        # Remove temporary sort score
        for result in formatted_results:
            del result['_sort_score']

        return formatted_results

    except Exception as e:
        logger.error(f"Error fetching resumes for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching resumes: {str(e)}"
        )


@router.post("/jobs/{job_id}/query", response_model=List[ResumeResponse])
async def query_resumes(
        job_id: int,
        query: str = Query(..., description="Natural language query"),
        db: Session = Depends(get_db)
):
    """
    Handle natural language queries about resumes
    """
    try:
        # Parse query
        if "top" in query.lower():
            import re
            numbers = re.findall(r'\d+', query)
            limit = int(numbers[0]) if numbers else 10

            # Determine sorting criteria
            sort_by = SortCriteria.overall_score
            if "skill" in query.lower():
                sort_by = SortCriteria.skills_match
            elif "experience" in query.lower():
                sort_by = SortCriteria.experience_match
            elif "education" in query.lower():
                sort_by = SortCriteria.education_match

            return await get_resumes_by_job(job_id, sort_by, limit, db)

        raise HTTPException(
            status_code=400,
            detail="Could not understand query. Try: 'top 5 resumes by skills'"
        )

    except Exception as e:
        logger.error(f"Error processing query for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )
