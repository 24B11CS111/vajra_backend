import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, func
from app.db.session import Base
from app.db.types import GUID, JSONBType

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="briefing")
    is_read = Column(Boolean, default=False)
    action_payload = Column(JSONBType, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
