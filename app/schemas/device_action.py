from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

class RemoteActionDispatchRequest(BaseModel):
    target_device_id: Optional[str] = Field(None, description="Specific target device identifier, e.g. 'android_xxx'")
    target_device_type: Optional[str] = Field("mobile", description="Device type fallback, e.g. 'mobile' or 'desktop'")
    action_type: str = Field(..., description="Action type identifier, e.g. 'device.flashlight'")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters, e.g. {'enabled': true}")

class RemoteActionAckRequest(BaseModel):
    status: str = Field(..., description="Execution status: 'SUCCESS' or 'FAILED'")
    result_message: Optional[str] = Field(None, description="Descriptive status message or error details")
    error_code: Optional[str] = Field(None, description="Specific error code if failed, e.g. 'DEVICE_ERROR'")

class RemoteActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    source_device_id: Optional[str] = None
    target_device_id: str
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str
    result_message: Optional[str] = None
    error_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    executed_at: Optional[datetime] = None

class RemoteActionListResponse(BaseModel):
    actions: List[RemoteActionResponse]
    total: int
