import json
from typing import Dict, Any
from app.core.llm.llm_provider import LLMProvider

class ConversationAnalyzer:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def needs_extraction(self, message: str) -> bool:
        """Analyzes if a user message contains extractable personal information."""
        prompt = f"""Analyze the following message and output JSON with a single boolean field 'extractable' set to true if the message contains personal facts, preferences, goals, projects, people, places, schedules, habits, relationships, education, work, health, skills, devices, or custom facts about the user. Otherwise set it to false.

        Message: "{message}"
        """

        try:
            result = await self.llm.extract_json(prompt)
            if "memories" in result and result["memories"]:
                return True
            return result.get('extractable', False)
        except Exception:
            # Fallback for basic heuristic if LLM parsing fails
            keywords = ["i", "my", "mine", "want", "need", "like", "love", "hate", "prefer", "goal", "plan"]
            return any(kw in message.lower() for kw in keywords)
