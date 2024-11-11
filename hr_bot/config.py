from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class DefaultConfig:
    PORT = int(os.getenv("WEBSITES_PORT", 8000))  # Changed to use WEBSITES_PORT
    #PORT = 3978
    APP_ID = os.getenv("MicrosoftAppId", "")
    APP_PASSWORD = os.getenv("MicrosoftAppPassword", "")
    CONNECTION_NAME = os.getenv("ConnectionName", "")
    BC_OPENAI_API_KEY = os.getenv("BC_OPENAI_API_KEY", "")

    SMTP_FROM_EMAIL = "your-bot@example.com"
    SMTP_SERVER = "smtp.your-server.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "your-username"
    SMTP_PASSWORD = "your-password"
