# app/core/config.py
from decouple import config


class Settings:
    # Project Settings
    PROJECT_NAME = config('PROJECT_NAME', default='HR-Automation-Backend')
    DEBUG = config('DEBUG', default=False, cast=bool)

    # Database Settings
    DATABASE_URL = config('DATABASE_URL')

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


# Initialize settings
settings = Settings()