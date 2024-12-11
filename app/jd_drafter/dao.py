
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from .models import GeneratedJD

logger = logging.getLogger(__name__)


class DAO:
    def __init__(self, db: Session):
        self.db = db

    def _commit_with_rollback(self, operation: str) -> None:
        """Helper method to handle commit and rollback"""
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error during {operation}: {str(e)}")
            raise

    def add_generated_jd(self, content: str, user_id: str) -> GeneratedJD:
        """
        Insert generated job description data

        Args:
            content (str): The JD content
            user_id (str): ID of the user who generated the JD

        Returns:
            GeneratedJD: The created job description record
        """
        try:
            logger.info(f"Adding generated JD for user: {user_id}")
            logger.info(f"Content length: {len(content)}")

            # Create new GeneratedJD instance with all fields
            generated_jd = GeneratedJD(
                content=content,
                user_id=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(generated_jd)
            self._commit_with_rollback("adding generated JD")

            # Verify data was saved
            self.db.refresh(generated_jd)
            logger.info(f"""
               Successfully saved GeneratedJD:
               - ID: {generated_jd.id}
               - User ID: {generated_jd.user_id}
               - Created At: {generated_jd.created_at}
               - Content Length: {len(generated_jd.content)}
               """)

            return generated_jd

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding generated JD: {str(e)}")
            raise Exception(f"Error adding generated JD: {str(e)}")

    def get_generated_jd(self, jd_id: int) -> Optional[GeneratedJD]:
        """
        Get generated JD by ID
        """
        try:
            return self.db.query(GeneratedJD).filter(
                GeneratedJD.id == jd_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting generated JD: {str(e)}")
            raise Exception(f"Error getting generated JD: {str(e)}")
