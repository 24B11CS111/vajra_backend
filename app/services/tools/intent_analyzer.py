from typing import Dict, Any, Optional
from pydantic import BaseModel
import re
import logging

logger = logging.getLogger(__name__)

class IntentResult(BaseModel):
    intent: str
    confidence: float
    required_tool: Optional[str] = None
    arguments: Dict[str, Any] = {}

class IntentAnalyzer:
    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    async def analyze(self, user_message: str) -> IntentResult:
        message = user_message.lower().strip()

        # 1. Assignment Creation
        if ("create" in message or "add" in message or "new" in message) and ("assignment" in message or "homework" in message):
            subject = "General"
            for subj in ["physics", "chemistry", "math", "mathematics", "biology", "history", "computer science", "astrophysics"]:
                if subj in message:
                    subject = subj.capitalize()
                    break
            
            day = "friday" if "friday" in message else "monday" if "monday" in message else "tomorrow" if "tomorrow" in message else "next week"
            return IntentResult(
                intent="Create Assignment",
                confidence=0.95,
                required_tool="create_assignment",
                arguments={
                    "title": f"{subject} Assignment",
                    "subject": subject,
                    "due_day": day,
                    "priority": "high" if "urgent" in message else "medium"
                }
            )

        # 2. Assignment Modification / Completion
        if ("move" in message or "reschedule" in message) and "assignment" in message:
            subject = "General"
            for subj in ["physics", "chemistry", "math", "mathematics", "biology", "history", "computer science", "astrophysics"]:
                if subj in message:
                    subject = subj.capitalize()
                    break
            day = "monday" if "monday" in message else "friday" if "friday" in message else "tomorrow"
            return IntentResult(
                intent="Update Assignment Due Date",
                confidence=0.95,
                required_tool="update_assignment",
                arguments={
                    "subject": subject,
                    "new_due_day": day
                }
            )

        if ("mark" in message or "set" in message) and ("completed" in message or "done" in message) and "assignment" in message:
            subject = "General"
            for subj in ["physics", "chemistry", "math", "mathematics", "biology", "history", "computer science", "astrophysics"]:
                if subj in message:
                    subject = subj.capitalize()
                    break
            return IntentResult(
                intent="Complete Assignment",
                confidence=0.95,
                required_tool="update_assignment",
                arguments={
                    "subject": subject,
                    "status": "COMPLETED"
                }
            )

        # 3. List Assignments
        if ("show" in message or "list" in message or "what" in message or "get" in message) and ("assignments" in message or "assignment" in message):
            return IntentResult(
                intent="List Assignments",
                confidence=0.9,
                required_tool="list_assignments",
                arguments={}
            )

        # 4. Schedule Study Session
        if ("schedule" in message or "study" in message) and ("from" in message or "at" in message or "session" in message or "pm" in message or "am" in message):
            subject = "Study Session"
            for subj in ["physics", "chemistry", "math", "mathematics", "biology", "history", "computer science", "astrophysics"]:
                if subj in message:
                    subject = f"{subj.capitalize()} Study Session"
                    break
            day = "tomorrow" if "tomorrow" in message else "today" if "today" in message else "saturday" if "saturday" in message else "monday"
            start_hour = 18
            hour_match = re.search(r"(\d+)\s*(pm|am)", message)
            if hour_match:
                hr = int(hour_match.group(1))
                if hour_match.group(2) == "pm" and hr < 12:
                    hr += 12
                start_hour = hr

            return IntentResult(
                intent="Schedule Study Session",
                confidence=0.95,
                required_tool="schedule_study_session",
                arguments={
                    "title": subject,
                    "day": day,
                    "start_hour": start_hour,
                    "duration_hours": 1
                }
            )

        # 5. Create Study Plan
        if ("study plan" in message or "plan my study" in message or "plan for tomorrow" in message):
            day = "tomorrow" if "tomorrow" in message else "today"
            return IntentResult(
                intent="Create Study Plan",
                confidence=0.95,
                required_tool="create_study_plan",
                arguments={"day": day}
            )

        # Memory triggers
        memory_terms = ["remember", "memory", "memories", "forget", "recall"]
        if any(term in message for term in memory_terms):
            return IntentResult(intent="Memory Related", confidence=0.85)

        # Time/Date tools
        if "what time is it" in message or message == "time":
            return IntentResult(intent="Query Time", confidence=0.95, required_tool="current_time", arguments={})
        if "what date is it" in message or "what day is today" in message or message == "date":
            return IntentResult(intent="Query Date", confidence=0.95, required_tool="current_date", arguments={})

        # Calculator
        if "calculate" in message or any(op in message for op in ["+", "*", "×", "/", "% of"]) and any(c.isdigit() for c in message):
            expression = user_message
            if "% of" in message:
                match = re.search(r"(\d+)%\s*of\s*(\d+)", message)
                if match:
                    expression = f"{match.group(1)} / 100 * {match.group(2)}"
            else:
                math_match = re.search(r"(\d+(?:\.\d+)?(?:\s*[\+\-\*\/\%]\s*\d+(?:\.\d+)?)+)", message.replace('×', '*'))
                if math_match:
                    expression = math_match.group(1)
                else:
                    expression = re.sub(r'[^0-9\+\-\*\/\.\(\)\s]', '', message.replace('×', '*')).strip()

            if expression:
                return IntentResult(
                    intent="Calculation",
                    confidence=0.9,
                    required_tool="calculator",
                    arguments={"expression": expression}
                )

        return IntentResult(
            intent="General Chat",
            confidence=0.8,
            required_tool=None,
            arguments={}
        )
