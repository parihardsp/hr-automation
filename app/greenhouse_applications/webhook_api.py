from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.greenhouse_applications.dao import DAO
import hmac
import hashlib
import logging

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
        data = await request.json()
        logger.info("Incoming Data: %s", data)  # Log the incoming data

        application_data = data['payload']['application']
        candidate = application_data['candidate']
        job = application_data['jobs'][0]  # Assuming the first job in the array

        # Create DAO instance
        dao = DAO(db)

        # Add candidate and job, then application
        candidate_record = dao.add_candidate(candidate)
        job_record = dao.add_job(job)
        application_record = dao.add_application(application_data, candidate_record.candidate_id, job_record.job_id)

        # Process attachments
        for attachment in candidate.get('attachments', []):
            dao.add_candidate_attachment(candidate_record.candidate_id, attachment)

        logger.info("Webhook processed successfully for candidate: %s", candidate['name'])  # Log success
        return JSONResponse(content={"message": "Webhook received and processed"}, status_code=200)

    except Exception as e:
        logger.error("Error processing webhook: %s", str(e))  # Log the error
        raise HTTPException(status_code=500, detail="Internal Server Error")

def verify_signature(secret_key: str, message_body: bytes, signature: str) -> bool:
    hash = hmac.new(secret_key.encode(), message_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(hash, signature)
