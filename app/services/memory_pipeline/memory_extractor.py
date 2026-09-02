from typing import List, Dict, Any
from app.core.llm.llm_provider import LLMProvider

class MemoryExtractionService:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def extract_memories(self, message: str) -> List[Dict[str, Any]]:
        """Extracts raw memories (Preferences, Goals, Facts, etc.) from text."""
        system_prompt = (
            "You are a Memory Extraction Engine. Extract all explicit personal facts, "
            "preferences, goals, and details from the user's message. Output JSON with a "
            "'memories' array. Each object should have: 'content' (str, the extracted fact)."
        )

        try:
            result = await self.llm.extract_json(message, system_prompt=system_prompt)
            return result.get('memories', [])
        except Exception as e:
            return []
