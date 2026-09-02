import datetime
from typing import Dict, Any
from app.services.tools.base import Tool, ToolContext, ToolResult

class TimeTool(Tool):
    @property
    def name(self) -> str:
        return "current_time"

    @property
    def description(self) -> str:
        return "Returns the current local time of the user."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        # In a real app, timezone could be fetched from user context.
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        return ToolResult(
            success=True,
            data={"time": current_time, "timezone": "local"}
        )
