from fastapi import FastAPI
from app.database import engine, Base
from app.all_models import *
from app.core.logger_setup import setup_logger
from app.core.config import settings

#Feature Routers
from app.gh_integration.endpoints import router as webhook_router
from app.jd_drafter.endpoints import router as jd_router
import uvicorn

# Set up the logger
logger = setup_logger(__name__)

# Initialize the FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)


# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")
    raise

# Include the webhook router
app.include_router(webhook_router, prefix="/api", tags=["CV-Filter"])
app.include_router(jd_router, prefix="/api", tags=["JD-Drafter"])


@app.get("/", tags=["Root"])
async def default():
    logger.info("Received request to the root endpoint.")
    return {"Welcome": "HR-Automation-Backend-Services", "Debug": settings.DEBUG}


@app.get("/health-check", tags=["Root"])
async def health_check():
    logger.info("Health check endpoint accessed.")
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )