from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class UserPreferences(BaseModel):
    timezone: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    ai_personality: Optional[str] = None
    preferred_voice: Optional[str] = None
    notification_preferences: Optional[Dict[str, Any]] = None

class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[UserPreferences] = None
    onboarding_completed: Optional[bool] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supabase_user_id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    display_name: Optional[str] = None
    
    # We alias name to full_name or display_name in the router if needed, 
    # but the API contract will return these exact model fields.
    name: Optional[str] = Field(None, description="Convenience field mapped to full_name or display_name for Flutter compatibility")
    
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    
    timezone: str
    language: str
    theme: str
    
    ai_personality: str
    preferred_voice: Optional[str] = None
    
    notification_preferences: Dict[str, Any]
    onboarding_completed: bool
    
    created_at: datetime
    updated_at: datetime
