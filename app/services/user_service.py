from typing import Dict, Any
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.schemas.user import UpdateUserRequest

class ProfileService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def get_or_create_user(self, jwt_payload: Dict[str, Any]) -> User:
        supabase_id = jwt_payload.get("sub")
        email = jwt_payload.get("email")
        
        user = self.user_repo.get_by_supabase_id(supabase_id)
        if not user:
            # Create user if it doesn't exist
            # Extract name from JWT if available (e.g. from Google login)
            user_metadata = jwt_payload.get("user_metadata", {})
            full_name = user_metadata.get("full_name") or user_metadata.get("name")
            avatar_url = user_metadata.get("avatar_url")
            
            new_user = User(
                supabase_user_id=supabase_id,
                email=email,
                full_name=full_name,
                display_name=full_name,
                avatar_url=avatar_url
            )
            user = self.user_repo.create(new_user)
            
        return user

    def update_user(self, user: User, update_data: UpdateUserRequest) -> User:
        update_dict = update_data.model_dump(exclude_unset=True)
        
        if "preferences" in update_dict and update_dict["preferences"]:
            prefs = update_dict.pop("preferences")
            for k, v in prefs.items():
                if hasattr(user, k):
                    setattr(user, k, v)
                    
        for k, v in update_dict.items():
            if hasattr(user, k):
                setattr(user, k, v)
                
        return self.user_repo.update(user)

    def delete_user(self, user: User) -> None:
        self.user_repo.delete(user)
