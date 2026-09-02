from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class SubjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#2563EB"
    priority: str = "medium"
    exam_date: Optional[datetime] = None

class SubjectCreate(SubjectBase):
    pass

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    priority: Optional[str] = None
    exam_date: Optional[datetime] = None

class SubjectResponse(SubjectBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AssignmentBase(BaseModel):
    title: str
    subject_id: Optional[UUID] = None
    subject_name: str = "General"
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    due_time: Optional[str] = None
    priority: str = "medium"
    status: str = "NOT_STARTED"
    attachment_url: Optional[str] = None

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    subject_id: Optional[UUID] = None
    subject_name: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    due_time: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    attachment_url: Optional[str] = None

class AssignmentResponse(AssignmentBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
