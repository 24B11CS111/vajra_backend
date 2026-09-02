from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
import uuid

from app.db.session import Base
from app.db.types import GUID, JSONBType, StringList

class MemoryType(str, enum.Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    GOAL = "goal"
    TASK = "task"
    REMINDER = "reminder"
    PROJECT = "project"
    CONVERSATION_SUMMARY = "conversation_summary"
    PERSON = "person"
    PLACE = "place"
    KNOWLEDGE = "knowledge"
    DEVICE = "device"
    AUTOMATION = "automation"
    CUSTOM = "custom"

class Memory(Base):
    __tablename__ = "memories"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(GUID(), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    memory_type = Column(SQLEnum(MemoryType, native_enum=False), nullable=False, default=MemoryType.FACT, index=True)

    importance = Column(Float, nullable=False, default=0.5)
    confidence = Column(Float, nullable=False, default=1.0)

    tags = Column(StringList(), nullable=False, default=list)
    source = Column(String(100), nullable=False, default="VAJRA Core")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_accessed = Column(DateTime(timezone=True), nullable=True)

    favorite = Column(Boolean, nullable=False, default=False)
    archived = Column(Boolean, nullable=False, default=False)
    deleted = Column(Boolean, nullable=False, default=False, index=True)

    memory_metadata = Column("metadata", JSONBType, nullable=False, default=dict)

    future_embedding_id = Column(String, nullable=True)
    future_graph_node_id = Column(String, nullable=True)

    # Provenance
    origin_conversation_id = Column(GUID(), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    origin_message_id = Column(GUID(), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    created_from = Column(String(50), nullable=False, default="extraction")
    confidence_reason = Column(Text, nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    times_retrieved = Column(Integer, nullable=False, default=0)
    times_updated = Column(Integer, nullable=False, default=0)

    # Relationships
    user = relationship("User", back_populates="memories")
    conversation = relationship(
        "Conversation",
        back_populates="memories",
        foreign_keys=[conversation_id],
    )
    origin_conversation = relationship(
        "Conversation",
        foreign_keys=[origin_conversation_id],
    )
    origin_message = relationship(
        "Message",
        foreign_keys=[origin_message_id],
    )
