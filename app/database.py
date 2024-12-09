# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from app.core.config import settings
# import logging
#
# logger = logging.getLogger(__name__)
#
# # Create database engine
# engine = create_engine(
#     settings.DATABASE_URL,
#     pool_pre_ping=True, # Enable connection pool pre-ping
#     pool_size=5,        # Set pool size
#     max_overflow=10     # Set max overflow connections
# )
#
# # Create session maker
# SessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine
# )
#
# # Create base class for models
# Base = declarative_base()
#
#
# # Database dependency
# def get_db():
#     """
#     Dependency function to get database session
#     Yields:
#         Session: SQLAlchemy database session
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     except Exception as e:
#         logger.error(f"Database session error: {str(e)}")
#         db.rollback()
#         raise
#     finally:
#         db.close()
import urllib

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

from app.core.config import settings, DatabaseType
from app.core.logger_setup import setup_logger

# Setup logger for this module
logger = setup_logger(__name__)


class DatabaseConfig:
    def __init__(self, settings):
        """Initialize database configuration based on settings"""
        self.settings = settings
        self.connection_string = self._build_connection_string()

        try:
            # Create engine with robust configuration
            self.engine = create_engine(
                self.connection_string,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,
                echo=settings.DEBUG
            )

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            logger.info(f"Database engine created successfully for {settings.DATABASE_TYPE}")

        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def _build_connection_string(self):
        """Build database connection string based on database type"""
        try:
            # PostgreSQL Connection
            if self.settings.DATABASE_TYPE == DatabaseType.POSTGRES.value:
                return (
                    f"postgresql://{self.settings.POSTGRES_USER}:"
                    f"{quote_plus(self.settings.POSTGRES_PASSWORD)}@"
                    f"{self.settings.POSTGRES_HOST}:"
                    f"{self.settings.POSTGRES_PORT}/"
                    f"{self.settings.POSTGRES_DB}"
                )

            # # SQL Server Connection
            # elif self.settings.DATABASE_TYPE == DatabaseType.SQLSERVER.value:
            #     return (
            #         f"mssql+pyodbc://{self.settings.MSSQL_USER}:"
            #         f"{quote_plus(self.settings.MSSQL_PASSWORD)}@"
            #         f"{self.settings.MSSQL_HOST}:{self.settings.MSSQL_PORT}/"
            #         f"{self.settings.MSSQL_DB}?driver={quote_plus(self.settings.MSSQL_DRIVER)}"
            #     )

            # SQL Server Connection
            if self.settings.DATABASE_TYPE == DatabaseType.SQLSERVER.value:
                params = urllib.parse.quote_plus(
                    f'DRIVER={{ODBC Driver 18 for SQL Server}};'
                    f'SERVER={self.settings.MSSQL_HOST};'
                    f'DATABASE={self.settings.MSSQL_DB};'
                    f'UID={self.settings.MSSQL_USER};'
                    f'PWD={self.settings.MSSQL_PASSWORD};'
                    f'TrustServerCertificate=yes;'
                )

                connection_string = f"mssql+pyodbc:///?odbc_connect={params}"
                logger.debug(f"Connection string (sanitized): {connection_string.replace(self.settings.MSSQL_PASSWORD, '****')}")
                return connection_string

            else:
                raise ValueError(f"Unsupported database type: {self.settings.DATABASE_TYPE}")
        except Exception as e:
            logger.error(f"Error building connection string: {str(e)}")
            raise

    def get_db(self):
        """Database session dependency"""
        db = self.SessionLocal()
        try:
            yield db
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()

    def init_db(self, Base):
        """Initialize database by creating tables"""
        try:
            # Create schema if it doesn't exist
            with self.engine.connect() as connection:
                connection.execute(text("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'dbo') EXEC('CREATE SCHEMA dbo')"))
                connection.commit()

            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise


# Initialize database configuration
db_config = DatabaseConfig(settings)

# Export key components
engine = db_config.engine
SessionLocal = db_config.SessionLocal
Base = declarative_base()
get_db = db_config.get_db
init_db = db_config.init_db
