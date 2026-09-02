from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class MessageCreate(BaseModel):
    role: str
    content: str
    assistant_metadata: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    assistant_metadata: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime

class ConversationCreate(BaseModel):
    title: Optional[str] = None
    initial_message: Optional[MessageCreate] = None

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: Optional[str] = None
    pinned: bool
    archived: bool
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
