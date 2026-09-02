import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.services.tools.base import Tool, ToolContext, ToolResult
from app.db.session import SessionLocal
import app.models  # Cleanly register all models
from app.models.study import SubjectModel, AssignmentModel
from app.models.calendar import CalendarEventModel
from app.models.planner import PlannerTask

def _parse_relative_day(day_str: str) -> datetime:
    today = datetime.utcnow()
    day_lower = day_str.lower()
    if "today" in day_lower:
        return today
    if "tomorrow" in day_lower:
        return today + timedelta(days=1)
    
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, d in enumerate(days):
        if d in day_lower:
            current_weekday = today.weekday()
            target_weekday = i
            diff = (target_weekday - current_weekday) % 7
            if diff == 0:
                diff = 7
            return today + timedelta(days=diff)
    return today + timedelta(days=2)

class CreateAssignmentTool(Tool):
    @property
    def name(self) -> str:
        return "create_assignment"

    @property
    def description(self) -> str:
        return "Creates a new academic assignment in the database."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "subject": {"type": "string"},
                "due_day": {"type": "string"},
                "priority": {"type": "string"}
            },
            "required": ["title"]
        }

    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        title = kwargs.get("title", "Study Assignment")
        subject_name = kwargs.get("subject", "General").capitalize()
        due_day_str = kwargs.get("due_day", "tomorrow")
        priority = kwargs.get("priority", "medium").lower()

        due_date = _parse_relative_day(due_day_str)

        db: Session = SessionLocal()
        try:
            # Check or create subject
            subject = db.query(SubjectModel).filter(
                SubjectModel.user_id == context.user_id,
                SubjectModel.name.ilike(subject_name)
            ).first()

            if not subject:
                subject = SubjectModel(
                    user_id=context.user_id,
                    name=subject_name,
                    description=f"{subject_name} coursework",
                    color="#2563EB",
                    priority=priority
                )
                db.add(subject)
                db.commit()
                db.refresh(subject)

            assignment = AssignmentModel(
                user_id=context.user_id,
                subject_id=subject.id,
                subject_name=subject.name,
                title=title,
                description=f"{subject.name} assignment due {due_date.strftime('%A, %b %d')}",
                due_date=due_date,
                due_time="11:59 PM",
                priority=priority,
                status="NOT_STARTED"
            )
            db.add(assignment)
            db.commit()
            db.refresh(assignment)

            return ToolResult(
                success=True,
                data={
                    "assignment_id": str(assignment.id),
                    "title": assignment.title,
                    "subject": assignment.subject_name,
                    "due_date": due_date.strftime("%A, %B %d, %Y"),
                    "status": assignment.status
                }
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
        finally:
            db.close()

class UpdateAssignmentTool(Tool):
    @property
    def name(self) -> str:
        return "update_assignment"

    @property
    def description(self) -> str:
        return "Modifies an existing assignment's due date or marks it completed."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "new_due_day": {"type": "string"},
                "status": {"type": "string"}
            }
        }

    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        subject_name = kwargs.get("subject", "").strip()
        new_due_day = kwargs.get("new_due_day")
        new_status = kwargs.get("status")

        db: Session = SessionLocal()
        try:
            assignment = None
            if subject_name:
                # 1. Try exact subject or title match first
                assignment = db.query(AssignmentModel).filter(
                    AssignmentModel.user_id == context.user_id,
                    or_(
                        AssignmentModel.subject_name.ilike(subject_name),
                        AssignmentModel.title.ilike(subject_name)
                    )
                ).order_by(AssignmentModel.created_at.desc()).first()

                # 2. Try partial match
                if not assignment:
                    assignment = db.query(AssignmentModel).filter(
                        AssignmentModel.user_id == context.user_id,
                        or_(
                            AssignmentModel.subject_name.ilike(f"%{subject_name}%"),
                            AssignmentModel.title.ilike(f"%{subject_name}%")
                        )
                    ).order_by(AssignmentModel.created_at.desc()).first()
            
            if not assignment:
                assignment = db.query(AssignmentModel).filter(AssignmentModel.user_id == context.user_id).order_by(AssignmentModel.created_at.desc()).first()

            if not assignment:
                return ToolResult(success=False, data=None, error="No matching assignment found to update.")

            if new_due_day:
                new_date = _parse_relative_day(new_due_day)
                assignment.due_date = new_date
            if new_status:
                assignment.status = new_status.upper()

            db.commit()
            db.refresh(assignment)

            return ToolResult(
                success=True,
                data={
                    "assignment_id": str(assignment.id),
                    "title": assignment.title,
                    "subject": assignment.subject_name,
                    "due_date": assignment.due_date.strftime("%A, %B %d, %Y") if assignment.due_date else None,
                    "status": assignment.status
                }
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
        finally:
            db.close()

class ListAssignmentsTool(Tool):
    @property
    def name(self) -> str:
        return "list_assignments"

    @property
    def description(self) -> str:
        return "Retrieves the active academic assignments for the user."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        db: Session = SessionLocal()
        try:
            assignments = db.query(AssignmentModel).filter(
                AssignmentModel.user_id == context.user_id
            ).order_by(AssignmentModel.due_date.asc().nulls_last()).limit(10).all()

            data = [
                {
                    "title": a.title,
                    "subject": a.subject_name,
                    "due_date": a.due_date.strftime("%a, %b %d") if a.due_date else "No deadline",
                    "status": a.status
                }
                for a in assignments
            ]
            return ToolResult(success=True, data={"assignments": data, "count": len(data)})
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
        finally:
            db.close()

class ScheduleStudySessionTool(Tool):
    @property
    def name(self) -> str:
        return "schedule_study_session"

    @property
    def description(self) -> str:
        return "Schedules a study session or calendar event in the user calendar."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "day": {"type": "string"},
                "start_hour": {"type": "integer"},
                "duration_hours": {"type": "integer"}
            },
            "required": ["title"]
        }

    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        title = kwargs.get("title", "Study Session")
        day_str = kwargs.get("day", "tomorrow")
        start_hour = kwargs.get("start_hour", 18)
        duration = kwargs.get("duration_hours", 1)

        target_date = _parse_relative_day(day_str)
        start_time = target_date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=duration)

        db: Session = SessionLocal()
        try:
            event = CalendarEventModel(
                user_id=context.user_id,
                title=title,
                description=f"Scheduled by VAJRA: {title}",
                event_type="study_session",
                start_time=start_time,
                end_time=end_time,
                color="#8B5CF6",
                status="scheduled"
            )
            db.add(event)
            db.commit()
            db.refresh(event)

            return ToolResult(
                success=True,
                data={
                    "event_id": str(event.id),
                    "title": event.title,
                    "start_time": start_time.strftime("%A, %b %d at %I:%M %p"),
                    "end_time": end_time.strftime("%I:%M %p"),
                }
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
        finally:
            db.close()

class CreateStudyPlanTool(Tool):
    @property
    def name(self) -> str:
        return "create_study_plan"

    @property
    def description(self) -> str:
        return "Generates structured study tasks in the planner for upcoming days."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "day": {"type": "string"},
                "topics": {"type": "array", "items": {"type": "string"}}
            }
        }

    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        day_str = kwargs.get("day", "tomorrow")
        topics = kwargs.get("topics") or ["Physics Problem Set", "Chemistry Chapter Review", "Math Practice"]
        target_date = _parse_relative_day(day_str)

        db: Session = SessionLocal()
        try:
            created_tasks = []
            for idx, topic in enumerate(topics):
                task = PlannerTask(
                    user_id=context.user_id,
                    title=f"Study: {topic}",
                    description=f"Automated study block scheduled for {target_date.strftime('%A')}",
                    category="Study",
                    priority="high" if idx == 0 else "medium",
                    due_date=target_date,
                    order_index=idx
                )
                db.add(task)
                created_tasks.append(task)
            
            db.commit()
            return ToolResult(
                success=True,
                data={
                    "day": target_date.strftime("%A, %B %d"),
                    "tasks_created": len(created_tasks),
                    "topics": [t.title for t in created_tasks]
                }
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
        finally:
            db.close()
