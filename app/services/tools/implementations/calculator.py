import ast
import operator
from typing import Dict, Any
from app.services.tools.base import Tool, ToolContext, ToolResult

class CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates basic mathematical expressions. Supports +, -, *, /, %, and parenthesis."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate (e.g., '25 * 48')"
                }
            },
            "required": ["expression"]
        }

    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        expression = kwargs.get("expression", "")
        if not expression:
            return ToolResult(success=False, data=None, error="No expression provided.")

        try:
            import re
            # Extract valid math expression e.g. "2 + 2" or clean arithmetic string
            match = re.search(r"(\d+(?:\.\d+)?(?:\s*[\+\-\*\/\%]\s*\d+(?:\.\d+)?)+)", expression)
            clean_expr = match.group(1) if match else re.sub(r"[^\d+\-*/%().\s]", "", expression).strip()

            if not clean_expr:
                return ToolResult(success=False, data=None, error="No valid arithmetic expression found.")

            # Safe evaluation of mathematical expressions
            def _eval(node):
                operators = {
                    ast.Add: operator.add, ast.Sub: operator.sub,
                    ast.Mult: operator.mul, ast.Div: operator.truediv,
                    ast.Mod: operator.mod,
                    ast.USub: operator.neg, ast.UAdd: operator.pos
                }
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    return node.value
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    if type(node.op) not in operators:
                        raise TypeError("Unsupported mathematical operation.")
                    return operators[type(node.op)](_eval(node.left), _eval(node.right))
                elif isinstance(node, ast.UnaryOp):
                    if type(node.op) not in operators:
                        raise TypeError("Unsupported mathematical operation.")
                    return operators[type(node.op)](_eval(node.operand))
                else:
                    raise TypeError(f"Unsupported mathematical operation: {node}")

            tree = ast.parse(clean_expr, mode='eval').body
            result = _eval(tree)

            return ToolResult(
                success=True,
                data={"result": result, "expression": clean_expr}
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"Failed to evaluate expression: {e}")
