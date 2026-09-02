from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str = "briefing"
    is_read: bool = False
    action_payload: Dict[str, Any] = {}

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
