from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.schemas.user import UserResponse, UpdateUserRequest
from app.core.security import get_current_user
from app.dependencies.services import get_profile_service
from app.services.user_service import ProfileService

router = APIRouter()

def map_user_to_response(user) -> UserResponse:
    user_dict = {
        "id": user.id,
        "supabase_user_id": user.supabase_user_id,
        "email": user.email,
        "full_name": user.full_name,
        "display_name": user.display_name,
        "name": user.display_name or user.full_name or user.email,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "timezone": user.timezone,
        "language": user.language,
        "theme": user.theme,
        "ai_personality": user.ai_personality,
        "preferred_voice": user.preferred_voice,
        "notification_preferences": user.notification_preferences,
        "onboarding_completed": user.onboarding_completed,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    return UserResponse(**user_dict)

@router.get("/me", response_model=UserResponse)
def get_me(
    jwt_payload: Dict[str, Any] = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    user = profile_service.get_or_create_user(jwt_payload)
    return map_user_to_response(user)

@router.put("/me", response_model=UserResponse)
def update_me(
    update_data: UpdateUserRequest,
    jwt_payload: Dict[str, Any] = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    user = profile_service.get_or_create_user(jwt_payload)
    updated_user = profile_service.update_user(user, update_data)
    return map_user_to_response(updated_user)

@router.delete("/me")
def delete_me(
    jwt_payload: Dict[str, Any] = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    user = profile_service.get_or_create_user(jwt_payload)
    profile_service.delete_user(user)
    return {"status": "ok", "message": "User account and associated data deleted successfully"}
