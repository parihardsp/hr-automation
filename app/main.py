from fastapi import FastAPI
from app.database import engine, Base, init_db
from app.all_models import *  # Ensure all models are imported
from app.core.logger_setup import setup_logger
from app.core.config import settings

# Feature Routers
from app.gh_integration.endpoints import router as webhook_router
from app.jd_drafter.endpoints import router as jd_router
import uvicorn

# Set up the logger
logger = setup_logger(__name__)

# Initialize the FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Create database tables
try:
    init_db(Base)
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    raise

# Include routers
app.include_router(webhook_router, prefix="/api", tags=["CV-Filter"])
app.include_router(jd_router, prefix="/api", tags=["JD-Drafter"])

@app.get("/", tags=["Root"])
async def default():
    logger.info("Received request to the root endpoint.")
    return {
        "Welcome": "HR-Automation-Backend-Services",
        "Debug": settings.DEBUG,
        "Database": settings.DATABASE_TYPE
    }

@app.get("/health-check", tags=["Root"])
async def health_check():
    logger.info("Health check endpoint accessed.")
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "database": settings.DATABASE_TYPE
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )