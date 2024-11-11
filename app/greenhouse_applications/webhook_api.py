from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.greenhouse_applications.dao import DAO
import hmac
import hashlib
import logging
from app.greenhouse_applications.greenhouse_api import GreenhouseService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/simulate_webhook")
async def simulate_webhook(request: Request, db: Session = Depends(get_db)):
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

        # 2. Initialize DAO
        dao = DAO(db)

        # 3. Process candidate and attachments
        logger.info("Processing candidate data")
        candidate_record = dao.add_candidate(candidate_data)

        logger.info("Processing attachments")
        for attachment in candidate_data.get('attachments', []):
            dao.add_candidate_attachment(candidate_record.candidate_id, attachment)

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


def verify_signature(secret_key: str, message_body: bytes, signature: str) -> bool:
    hash = hmac.new(secret_key.encode(), message_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(hash, signature)