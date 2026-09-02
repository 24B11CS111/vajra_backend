import time
import logging
from typing import Any, Dict
from app.services.tools.base import ToolContext, ToolResult
from app.services.tools.registry import tool_registry

logger = logging.getLogger(__name__)

class ToolExecutor:
    @staticmethod
    async def execute(tool_name: str, context: ToolContext, kwargs: Dict[str, Any]) -> ToolResult:
        tool = tool_registry.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{tool_name}' not found."
            )

        kwargs = kwargs or {}
        required = tool.parameters_schema.get("required", [])
        missing = [name for name in required if name not in kwargs]
        if missing:
            return ToolResult(
                success=False,
                data=None,
                error=f"Missing required tool argument(s): {', '.join(missing)}"
            )

        start_time = time.time()
        try:
            result = await tool.execute(context, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time

            logger.info(f"Executed tool '{tool_name}' in {execution_time:.2f}ms. Success: {result.success}")
            return result
        except Exception:
            execution_time = (time.time() - start_time) * 1000
            logger.exception("Tool execution failed for '%s'.", tool_name)
            return ToolResult(
                success=False,
                data=None,
                error="Tool execution failed.",
                execution_time_ms=execution_time
            )
