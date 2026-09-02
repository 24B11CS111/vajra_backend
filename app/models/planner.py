import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, func
from app.db.session import Base
from app.db.types import GUID, JSONBType

class PlannerTask(Base):
    __tablename__ = "planner_tasks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="General")
    priority = Column(String(20), default="medium")
    is_completed = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)
    due_date = Column(DateTime(timezone=True), nullable=True)
    subtasks = Column(JSONBType, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
