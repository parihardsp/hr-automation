from decouple import config


class Settings:
    DATABASE_URL = config('DATABASE_URL')
    SECRET_KEY = config('SECRET_KEY', default='your_default_secret_key')
    DEBUG = config('DEBUG', default=False, cast=bool)


settings = Settings()

