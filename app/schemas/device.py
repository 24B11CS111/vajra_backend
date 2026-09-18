from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime

class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., description="Unique hardware or installation identifier for this client")
    device_type: str = Field("desktop", description="Device class: 'desktop', 'mobile', or 'web'")
    device_name: str = Field(..., description="User-friendly device name, e.g. 'VAJRA Workstation' or 'Nothing Phone (2a)'")
    platform: str = Field("windows", description="OS platform: windows, android, macos, linux, ios, etc.")
    app_version: Optional[str] = Field("1.0.0", description="Client version string")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities supported by this device")

class DeviceUpdateRequest(BaseModel):
    device_name: Optional[str] = None
    capabilities: Optional[List[str]] = None
    is_active: Optional[bool] = None

class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    device_id: str
    device_type: str
    device_name: str
    platform: str
    app_version: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    is_active: bool
    last_seen: datetime
    created_at: datetime
    updated_at: datetime

class DeviceListResponse(BaseModel):
    devices: List[DeviceResponse]
    total: int
