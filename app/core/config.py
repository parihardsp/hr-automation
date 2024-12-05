# app/core/config.py
from decouple import config
from enum import Enum
from pathlib import Path

class DatabaseType(Enum):
    POSTGRES = 'postgres'
    SQLSERVER = 'mssql'

class Settings:
    # Project Settings
    PROJECT_NAME = config('PROJECT_NAME', default='HR Automation')
    VERSION = config('VERSION', default='1.0.0')

    # Database Type Selection
    DATABASE_TYPE = config('DATABASE_TYPE', default=DatabaseType.POSTGRES.value)

    # Postgres Configuration
    POSTGRES_HOST = config('POSTGRES_HOST', default='localhost')
    POSTGRES_PORT = config('POSTGRES_PORT', default=5432, cast=int)
    POSTGRES_DB = config('POSTGRES_DB', default='hr_automation_db')
    POSTGRES_USER = config('POSTGRES_USER')
    POSTGRES_PASSWORD = config('POSTGRES_PASSWORD')

    # SQL Server Configuration
    MSSQL_HOST = config('MSSQL_HOST')
    MSSQL_PORT = config('MSSQL_PORT', default=1433, cast=int)
    MSSQL_DB = config('MSSQL_DB')
    MSSQL_USER = config('MSSQL_USER')
    MSSQL_PASSWORD = config('MSSQL_PASSWORD')
    #MSSQL_DRIVER = config('MSSQL_DRIVER', default='ODBC Driver 17 for SQL Server')

    # Application Settings
    SECRET_KEY = config('SECRET_KEY')
    JWT_SECRET = config('JWT_SECRET')
    DEBUG = config('DEBUG', default=False, cast=bool)
    LOG_LEVEL = config('LOG_LEVEL', default='INFO')

    # Feature Flags
    GITHUB_INTEGRATION_ENABLED = config('GITHUB_INTEGRATION_ENABLED', default=False, cast=bool)
    AI_FEATURES_ENABLED = config('AI_FEATURES_ENABLED', default=False, cast=bool)

    # Azure Blob Storage Settings
    ACCOUNT_NAME = config('ACCOUNT_NAME')
    CONTAINER_NAME = config('CONTAINER_NAME')
    ACCOUNT_KEY = config('ACCOUNT_KEY')
    BLOB_ACCOUNT_URL = f"https://{ACCOUNT_NAME}.blob.core.windows.net"

    # Azure OpenAI Settings
    OPENAI_API_KEY = config('BC_OPENAI_API_KEY')
    OPENAI_API_BASE = config('BASE_URL')
    OPENAI_API_VERSION = config('OPENAI_API_VERSION', default="2023-03-15-preview")
    OPENAI_DEPLOYMENT_NAME = config('DEPLOYMENT_NAME', default="gpt-4-32k")
    OPENAI_API_TYPE = config('OPENAI_API_TYPE', default="azure")

    URL_SECRET_KEY = config('URL_SECRET_KEY' , default="your_secret_key_here")

    # Define the base directory for your project
    BASE_DIR = Path(__file__).resolve().parents[2]  # hr-automation directory

    # Directory paths
    RESUMES_DIR = BASE_DIR / "Resumes"
    LOGS_DIR = BASE_DIR / "logs"


# Initialize settings
settings = Settings()
