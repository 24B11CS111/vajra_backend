import datetime
from typing import Dict, Any
from app.services.tools.base import Tool, ToolContext, ToolResult

class DateTool(Tool):
    @property
    def name(self) -> str:
        return "current_date"

    @property
    def description(self) -> str:
        return "Returns the current date."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        day_of_week = datetime.datetime.now().strftime("%A")
        return ToolResult(
            success=True,
            data={"date": current_date, "day_of_week": day_of_week}
        )
