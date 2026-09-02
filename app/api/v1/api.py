from fastapi import APIRouter
from app.api.v1.endpoints import users, chat, memory, auth, planner, notifications, study, calendar

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="", tags=["Users"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(memory.router, prefix="/memory", tags=["Memory"])
api_router.include_router(planner.router, prefix="/planner", tags=["Planner"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(study.router, prefix="/study", tags=["Study"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
