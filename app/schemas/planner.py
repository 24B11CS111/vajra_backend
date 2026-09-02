from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "General"
    priority: str = "medium"
    is_completed: bool = False
    order_index: int = 0
    due_date: Optional[datetime] = None
    subtasks: List[Dict[str, Any]] = []

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    is_completed: Optional[bool] = None
    order_index: Optional[int] = None
    due_date: Optional[datetime] = None
    subtasks: Optional[List[Dict[str, Any]]] = None

class TaskReorder(BaseModel):
    task_ids: List[UUID]

class TaskResponse(TaskBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
