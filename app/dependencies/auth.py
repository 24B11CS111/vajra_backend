from typing import Dict, Any
from fastapi import Depends, HTTPException
from app.core.security import get_current_user
from app.dependencies.services import get_profile_service
from app.services.user_service import ProfileService
from app.models.user import User

def get_current_db_user(
    jwt_payload: Dict[str, Any] = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
) -> User:
    # This automatically gets or creates the user record based on the Supabase JWT
    user = profile_service.get_or_create_user(jwt_payload)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
