from decouple import config


class Settings:
    DATABASE_URL = config('DATABASE_URL')
    SECRET_KEY = config('SECRET_KEY', default='your_default_secret_key')
    DEBUG = config('DEBUG', default=False, cast=bool)

    PORT = 8000
    APP_ID = config("MicrosoftAppId", "")
    APP_PASSWORD = config("MicrosoftAppPassword", "")
    CONNECTION_NAME = config("ConnectionName", "")
    BC_OPENAI_API_KEY = config("BC_OPENAI_API_KEY","")



settings = Settings()
