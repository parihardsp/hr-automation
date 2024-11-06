from fastapi import FastAPI
from app.database import engine
from app.greenhouse_applications import models
from app.greenhouse_applications.webhook_api import router as webhook_router
from app.core.logger_setup import setup_logger
from app.core.config import settings

# Set up the logger
logger = setup_logger()

# Create the database tables
try:
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

# Initialize the FastAPI app
app = FastAPI()

# Include the webhook router
app.include_router(webhook_router, prefix="/api")


@app.get("/")
async def read_root():
    logger.info("Received request to the root endpoint.")
    return {"Hello": "World", "Debug": settings.DEBUG}


@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed.")
    return {"status": "healthy"}
