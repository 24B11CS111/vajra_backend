from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import uuid
import datetime

class ToolContext(BaseModel):
    user_id: uuid.UUID
    conversation_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    extra: Dict[str, Any] = {}

class ToolResult(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0

class ToolResponse(BaseModel):
    tool_name: str
    result: ToolResult
    executed_at: datetime.datetime

class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the tool"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does for the LLM"""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema for the tool's required arguments"""
        pass

    @abstractmethod
    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        """Executes the tool with the given context and arguments"""
        pass
