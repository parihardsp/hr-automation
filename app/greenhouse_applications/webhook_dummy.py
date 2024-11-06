
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.greenhouse_applications.dao import DAO
import json

#router = APIRouter()

dummy_data_path = 'app/greenhouse_applications/dummy_data.json'


#@router.post("/simulate_webhook_old")
async def simulate_webhook(db: Session = Depends(get_db)):
    dao = DAO(db)

    with open(dummy_data_path) as f:
        data = json.load(f)

    application_data = data['payload']['application']
    candidate = application_data['candidate']
    job = application_data['jobs'][0]  # Assuming the first job in the array

    # Add Job Description
    job_description = dao.add_job_description(job)

    # Add CV Detail
    cv_detail = dao.add_cv_detail(candidate)

    # Add Application
    dao.add_application(application_data, job_description.jd_id, cv_detail.cv_id)

    return JSONResponse(content={"message": "Webhook simulation successful"}, status_code=200)
