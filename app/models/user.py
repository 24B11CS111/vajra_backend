import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.types import GUID, JSONBType
class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    supabase_user_id = Column(GUID(), unique=True, index=True, nullable=False)

    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(1024), nullable=True)
    bio = Column(Text, nullable=True)

    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    theme = Column(String(20), default="system")

    ai_personality = Column(String(50), default="reflective")
    preferred_voice = Column(String(50), nullable=True)

    notification_preferences = Column(JSONBType, default=dict)

    onboarding_completed = Column(Boolean, default=False)

    # Relationships
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
