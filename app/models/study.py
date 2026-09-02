import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, func
from app.db.session import Base
from app.db.types import GUID
import app.models.user  # Ensure User model is loaded for foreign key resolution

class SubjectModel(Base):
    __tablename__ = "subjects"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(20), default="#2563EB")
    priority = Column(String(20), default="medium")
    exam_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class AssignmentModel(Base):
    __tablename__ = "assignments"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(GUID(), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    subject_name = Column(String(100), default="General")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    due_time = Column(String(20), nullable=True)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="NOT_STARTED")  # NOT_STARTED, IN_PROGRESS, COMPLETED, OVERDUE
    attachment_url = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
