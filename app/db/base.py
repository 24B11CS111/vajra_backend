from app.db.session import Base

# Import all models here so Alembic can discover them
from app.models.user import User
from app.models.chat import Conversation, Message
from app.models.memory import Memory
from app.models.planner import PlannerTask
from app.models.notification import Notification
from app.models.study import SubjectModel, AssignmentModel
from app.models.calendar import CalendarEventModel

__all__ = [
    "Base",
    "User",
    "Conversation",
    "Message",
    "Memory",
    "PlannerTask",
    "Notification",
    "SubjectModel",
    "AssignmentModel",
    "CalendarEventModel",
]
