from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class DefaultConfig:
    PORT = 3978
    APP_ID = os.getenv("MicrosoftAppId", "")
    APP_PASSWORD = os.getenv("MicrosoftAppPassword", "")
    CONNECTION_NAME = os.getenv("ConnectionName", "")
    BC_OPENAI_API_KEY = os.getenv("BC_OPENAI_API_KEY","")