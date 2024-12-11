from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.jd_drafter.dao import DAO
from app.core.logger_setup import setup_logger

router = APIRouter()
logger = setup_logger()

@router.post("/generated-jd")
async def save_generated_jd(request: Request, db: Session = Depends(get_db)):
    try:
        # Get data from request
        data = await request.json()
        logger.info("Received generated JD data from bot")

        # Log the exact content being received
        content = data.get('content')
        user_id = data.get('user_id')

        logger.info(f"""
        Received Data Details:
        - Content type: {type(content)}
        - Content length: {len(content) if content else 0}
        - Content preview: {content[:100] if content else 'None'}
        - User ID: {user_id}
        """)

        if not content:
            raise HTTPException(status_code=400, detail="JD content is required")

        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        # Initialize DAO
        dao = DAO(db)

        # Save with explicit content
        generated_jd = dao.add_generated_jd(
            content=str(content).strip(),  # Ensure content is string and stripped
            user_id=user_id
        )

        # Verify saved data
        saved_jd = dao.get_generated_jd(generated_jd.id)
        logger.info(f"""
        Verification of Saved Data:
        - ID: {saved_jd.id}
        - Content exists: {bool(saved_jd.content)}
        - Content length: {len(saved_jd.content) if saved_jd.content else 0}
        - Content preview: {saved_jd.content[:100] if saved_jd.content else 'None'}
        - User ID: {saved_jd.user_id}
        """)

        return JSONResponse(
            content={
                "message": "Generated JD saved successfully",
                "jd_id": generated_jd.id,
                "content_preview": content[:50] if content else None
            },
            status_code=201
        )

    except Exception as e:
        logger.error(f"Error saving generated JD: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))