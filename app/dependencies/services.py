from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.services.user_service import ProfileService
from app.repositories.chat_repository import ChatRepository
from app.services.chat_service import ChatService

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_profile_service(user_repo: UserRepository = Depends(get_user_repository)) -> ProfileService:
    return ProfileService(user_repo)

def get_chat_repository(db: Session = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)

def get_chat_service(chat_repo: ChatRepository = Depends(get_chat_repository)) -> ChatService:
    return ChatService(chat_repo)
