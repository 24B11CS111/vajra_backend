from typing import Dict, Any, List
from app.core.llm.llm_provider import LLMProvider
from app.models.memory import MemoryType

class MemoryClassifier:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def classify(self, memory_content: str) -> Dict[str, Any]:
        """Classifies extracted memories, calculating confidence, initial importance, and tags."""

        valid_types = [m.value for m in MemoryType]
        types_str = ", ".join(valid_types)

        system_prompt = (
            f"Classify the following memory. Output JSON with fields: "
            f"'memory_type' (one of: {types_str}), "
            f"'confidence' (float 0.0-1.0), "
            f"'importance' (float 0.0-1.0), "
            f"'tags' (list of strings)."
        )

        try:
            result = await self.llm.extract_json(memory_content, system_prompt=system_prompt)
            # Apply defaults if LLM misses fields
            return {
                "memory_type": result.get("memory_type", MemoryType.FACT.value),
                "confidence": float(result.get("confidence", 0.9)),
                "importance": float(result.get("importance", 0.5)),
                "tags": result.get("tags", [])
            }
        except Exception:
            # Safe fallback
            return {
                "memory_type": MemoryType.FACT.value,
                "confidence": 0.8,
                "importance": 0.5,
                "tags": []
            }
