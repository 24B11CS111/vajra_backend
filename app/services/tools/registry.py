from typing import Dict, List, Optional
from app.services.tools.base import Tool
from app.services.tools.implementations.calculator import CalculatorTool
from app.services.tools.implementations.date_tool import DateTool
from app.services.tools.implementations.time_tool import TimeTool
from app.services.tools.implementations.study_tools import (
    CreateAssignmentTool,
    UpdateAssignmentTool,
    ListAssignmentsTool,
    ScheduleStudySessionTool,
    CreateStudyPlanTool
)

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        if tool.name in self._tools:
            return  # Allow idempotency
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def get_tools_schema(self) -> List[Dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema
            }
            for tool in self._tools.values()
        ]

# Global registry instance
tool_registry = ToolRegistry()

for builtin_tool in (
    CalculatorTool(),
    DateTool(),
    TimeTool(),
    CreateAssignmentTool(),
    UpdateAssignmentTool(),
    ListAssignmentsTool(),
    ScheduleStudySessionTool(),
    CreateStudyPlanTool()
):
    tool_registry.register(builtin_tool)
