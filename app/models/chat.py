import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, func, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.types import GUID, JSONBType
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(255), nullable=True)
    pinned = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)
    
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    user = relationship("User", backref="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    memories = relationship(
        "Memory",
        back_populates="conversation",
        foreign_keys="Memory.conversation_id",
    )

class Message(Base):
    __tablename__ = "messages"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    conversation_id = Column(GUID(), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(String(50), nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)
    
    assistant_metadata = Column(JSONBType, nullable=True)
    status = Column(String(50), default="sent") # sent, delivered, read, error
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    conversation = relationship("Conversation", back_populates="messages")
