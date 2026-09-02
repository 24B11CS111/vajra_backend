from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class CalendarEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: str = "study_session"  # study_session, assignment, exam, reminder, task
    start_time: datetime
    end_time: Optional[datetime] = None
    is_all_day: bool = False
    location: Optional[str] = None
    color: str = "#2563EB"
    status: str = "scheduled"
    related_id: Optional[str] = None

class CalendarEventCreate(CalendarEventBase):
    pass

class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    location: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None
    related_id: Optional[str] = None

class CalendarEventResponse(CalendarEventBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
