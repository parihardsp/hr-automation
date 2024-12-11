import hashlib
import hmac
import json
import os
import sys
import traceback
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
from sqlalchemy import desc, exists
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

        job_content = """Title: Talent Executive Location: White City, London (4 days a week) Division: Talent Reports to: Talent Manager Are you ready to drive digital transformation and innovation within a dynamic organisation focused on delivering exceptional public services? Do you want to thrive in a fast-paced environment where you can identify, attract, and secure top talent? Do you want to have the opportunity to contribute directly to Agilisys' continued growth and success? If so, we would love to hear from you! ABOUT US Agilisys is at the forefront of digital transformation and innovation in the public services sector. With over two decades of experience, we have established ourselves as a trusted partner for governments, local authorities, and organizations nationwide. Our mission is to empower our clients to deliver exceptional public services by harnessing the full potential of technology and data. OUR VALUES Partnership:we become one team and family with organisations, helping them to navigate change and stay agile. Integrity: our people really care, going beyond the brief to make change happen for organisations and citizens. Innovation:we bring together the right technologies and services to design solutions that work. Passion: we are passionate about - and dedicated to - public services and improving people's lives. THE ROLE Key responsibilities The Talent Executive is a vital role within Agilisys and will be instrumental in leading the attraction, selection and placement process within the business and on a project basis. Specific duties Depending on the project, you will need to be comfortable doing the following: Support the talent function of Agilisys by managing the end-to-end recruitment processes. Facilitate administration for all stages of the recruitment process, including liaising with key stakeholders, and updating people systems. Demonstrate a growth mindset to continuously improve the processes and activities. Consistently build strong relationships with stakeholders internally and externally. ABOUT YOU The ideal candidate will have a track-record in delivering results while embracing change. Excellent stakeholder management experience is essential to being successful in this role. The Ideal Candidate An ambitious and driven individual with 2 + years' work experience in a recruitment role (in-house, agency, RPO or executive search). A bachelor's degree. Experience using recruitment systems such as LinkedIn Recruiter and Greenhouse (or equivalent) is preferred. A problem solver who takes ownership and won't settle until the problem is resolved. Resilient and loves to use any learnings to improve a process next time round. Thrives from working in a fast-paced environment and is comfortable with ambiguity. Collaborative by nature, looking to work with & elevate those around you. Experience setting up new processes and ways of working. Excellent stakeholder management. Passion for innovation. WHAT WE CAN OFFER YOU: This role will offer exposure to the right mix of challenges, within a culture that promotes continuous learning and development. Benefits include: Enhanced Pension Scheme Health Insurance Private Medical Insurance Life Assurance Access to exclusive discounts and offers through the company's "Perks at Work" scheme 25 days annual leave (with the option to buy more) PROCESS Simply submit your CV. By submitting your CV, you understand that we have a legitimate interest to use your personal data for the purposes of assessing your eligibility for this role. This means that we may use your personal data to contact you to discuss your CV or arrange an interview or transfer your CV to the hiring manager(s) of the role you have applied for. You can ask us at any time to remove your CV from our database by emailing talentacquisition@agilisys.co.uk – but please note that this means we will no longer consider you for the role you have applied for. We have a rigorous recruitment process, which we use for all our roles to ensure we attract the very best talent. Individuals seeking employment at Agilisys must note that we see diversity as something that creates a better workplace and delivers better outcomes. As such, we are keen to maximise the diversity of our workforce and actively encourage applications from all. We encourage diversity through perspective, background, identity, and thought whilst also fostering an environment where everyone can express themselves regardless of your race, religion, sex, gender, colour, national origin, disability, or any other applicable legally protected characteristic. We are committed to continuing to nurture an inclusive environment and building a diverse workforce.;"""
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

                pdf_filename = 'David Walker.docx'
                pdf_path = settings.RESUMES_DIR / pdf_filename

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

                logger.info("Successfully created sections to fetch similarity_analysis function")
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


# @router.get("/jobs/{job_id}/resumes")
# async def get_resumes_by_job(
#         job_id: int,
#         sort_by: SortCriteria = Query(SortCriteria.overall_score, description="Sort criteria"),
#         limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
#         db: Session = Depends(get_db)
# ):
#     try:
#         query = (
#             db.query(
#                 Job.title.label('job_title'),
#                 Candidate.id.label('id'),
#                 Candidate.candidate_id.label('candidate_id'),
#                 Candidate.first_name,
#                 Candidate.last_name,
#                 SimilarityScore.overall_score,
#                 SimilarityScore.match_details,
#                 ProcessedResume.company_bg_details
#             )
#             .join(SimilarityScore, Job.job_id == SimilarityScore.job_id)
#             .join(Candidate, SimilarityScore.candidate_id == Candidate.id)
#             .join(ProcessedResume, Candidate.id == ProcessedResume.candidate_id)
#             .filter(Job.job_id == job_id)
#         )
#
#         # Only sort by overall_score in database query
#         if sort_by == SortCriteria.overall_score:
#             query = query.order_by(desc(SimilarityScore.overall_score))
#
#         results = query.all()  # Get all results first
#
#         if not results:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"No resumes found for job ID {job_id}"
#             )
#
#         formatted_results = []
#         for result in results:
#             try:
#                 match_details = result.match_details
#                 if isinstance(match_details, str):
#                     match_details = json.loads(match_details)
#
#                 company_bg_details = result.company_bg_details
#                 if isinstance(company_bg_details, str):
#                     company_bg_details = json.loads(company_bg_details)
#
#                 # Find specific score based on sort criteria
#                 specific_score = 0
#                 if sort_by != SortCriteria.overall_score:
#                     score_type_map = {
#                         SortCriteria.skills_match: "Skills Match",
#                         SortCriteria.experience_match: "Experience Match",
#                         SortCriteria.education_match: "Education Match"
#                     }
#                     for detail in match_details:
#                         if detail.get('name') == score_type_map[sort_by]:
#                             specific_score = float(detail.get('score', 0))
#                             break
#
#                 formatted_result = {
#                     "title": result.job_title,
#                     "id": result.id,
#                     "candidate_id": result.candidate_id,
#                     "candidate_name": f"{result.first_name} {result.last_name}".strip(),
#                     "overall_score": float(result.overall_score),
#                     "match_details": match_details,
#                     "company_bg_details": company_bg_details,
#                     "_sort_score": specific_score if sort_by != SortCriteria.overall_score else float(
#                         result.overall_score)
#                 }
#                 formatted_results.append(formatted_result)
#             except Exception as e:
#                 logger.error(f"Error formatting result: {str(e)}")
#                 continue
#
#         # Sort results based on criteria
#         if sort_by != SortCriteria.overall_score:
#             formatted_results.sort(key=lambda x: x['_sort_score'], reverse=True)
#
#         # Apply limit after sorting
#         formatted_results = formatted_results[:limit]
#
#         # Remove temporary sort score
#         for result in formatted_results:
#             del result['_sort_score']
#
#         return formatted_results
#
#     except Exception as e:
#         logger.error(f"Error fetching resumes for job {job_id}: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error fetching resumes: {str(e)}"
#         )

@router.get("/jobs/{job_id}/resumes")
async def get_resumes_by_job(
        job_id: int,
        sort_by: SortCriteria = Query(SortCriteria.overall_score, description="Sort criteria"),
        limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
        db: Session = Depends(get_db)
):
    try:
        # Log initial input parameters
        logger.info(f"Received request for job_id: {job_id}, sort_by: {sort_by}, limit: {limit}")

        # Log database connection and query preparation
        logger.debug("Preparing database query...")

        # Modified job existence check for SQL Server
        job_exists = db.query(Job).filter(Job.job_id == job_id).first() is not None
        if not job_exists:
            logger.warning(f"No job found with ID {job_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID {job_id} does not exist"
            )

        # Rest of your existing code remains the same
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

        # Log the raw SQL query for debugging
        logger.debug(f"Raw SQL Query: {query.statement}")

        # Only sort by overall_score in database query
        if sort_by == SortCriteria.overall_score:
            query = query.order_by(desc(SimilarityScore.overall_score))

        # Log number of total results before pagination
        total_results_count = query.count()
        logger.info(f"Total results found: {total_results_count}")

        results = query.all()  # Get all results first

        if not results:
            logger.warning(f"No resumes found for job ID {job_id}")
            raise HTTPException(
                status_code=404,
                detail=f"No resumes found for job ID {job_id}"
            )

        formatted_results = []
        for idx, result in enumerate(results):
            try:
                # Log each result for detailed inspection
                logger.debug(f"Processing result {idx}: {result}")

                match_details = result.match_details
                if isinstance(match_details, str):
                    try:
                        match_details = json.loads(match_details)
                    except json.JSONDecodeError as json_err:
                        logger.error(f"JSON decode error for match_details: {json_err}")
                        match_details = []

                company_bg_details = result.company_bg_details
                if isinstance(company_bg_details, str):
                    if not company_bg_details:  # Handle None or empty string
                        company_bg_details = {}
                    else:
                        # Remove any extra quotes at the beginning and end if present
                        company_bg_details = company_bg_details.strip('"')
                        if company_bg_details:  # If there's still content after stripping quotes
                            try:
                                company_bg_details = json.loads(company_bg_details)
                            except json.JSONDecodeError:
                                # If it's just a plain string (not JSON), keep it as is
                                logger.debug("company_bg_details is a plain string, keeping as is")
                else:
                    company_bg_details = {}
                    # else:
                    #     try:
                    #         company_bg_details = json.loads(company_bg_details)
                    #     except json.JSONDecodeError as json_err:
                    #         logger.error(f"JSON decode error for company_bg_details: {json_err}")
                    #         company_bg_details = {}

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
                logger.error(f"Error formatting result {idx}: {str(e)}")
                # Log the full traceback for more details
                logger.error(traceback.format_exc())
                continue

        # Log number of formatted results
        logger.info(f"Number of formatted results: {len(formatted_results)}")

        # Sort results based on criteria
        if sort_by != SortCriteria.overall_score:
            formatted_results.sort(key=lambda x: x['_sort_score'], reverse=True)

        # Apply limit after sorting
        formatted_results = formatted_results[:limit]

        # Remove temporary sort score
        for result in formatted_results:
            del result['_sort_score']

        logger.info(f"Returning {len(formatted_results)} results")
        return formatted_results

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching resumes for job {job_id}: {str(e)}")
        # Log the full traceback for unexpected errors
        logger.error(traceback.format_exc())
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
