import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, func
from app.db.session import Base
from app.db.types import GUID
import app.models.user  # Ensure User model is loaded for foreign key resolution

class CalendarEventModel(Base):
    __tablename__ = "calendar_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(50), default="study_session")  # study_session, assignment, exam, reminder, task
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    is_all_day = Column(Boolean, default=False)
    location = Column(String(255), nullable=True)
    color = Column(String(20), default="#2563EB")
    status = Column(String(20), default="scheduled")
    related_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
