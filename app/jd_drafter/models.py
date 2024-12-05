from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, JSON, Text, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class GeneratedJD(Base):
    __tablename__ = 'generated_jds'
    __table_args__ = {'schema': 'public'}  # Add schema specification

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    user_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GeneratedJD(id={self.id}, user_id={self.user_id}, created_at={self.created_at})>"