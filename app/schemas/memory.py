from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.memory import MemoryType

class MemoryBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    content: str
    memory_type: MemoryType = MemoryType.FACT
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    source: str = "VAJRA Core"
    favorite: bool = False
    archived: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="memory_metadata")
    conversation_id: Optional[UUID] = None

    origin_conversation_id: Optional[UUID] = None
    origin_message_id: Optional[UUID] = None
    created_from: str = "extraction"
    confidence_reason: Optional[str] = None
    times_retrieved: int = 0
    times_updated: int = 0

class MemoryCreate(MemoryBase):
    pass

class MemoryUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    content: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    favorite: Optional[bool] = None
    archived: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = Field(None, alias="memory_metadata")

class MemoryInDBBase(MemoryBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime] = None
    deleted: bool = False
    future_embedding_id: Optional[str] = None
    future_graph_node_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class Memory(MemoryInDBBase):
    pass
