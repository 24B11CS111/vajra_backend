from typing import List, Dict, Any
from app.models.memory import Memory
from datetime import datetime, timezone
import math

class MemoryRankingService:
    def rank_memories(self, context_query: str, memories: List[Memory]) -> List[Memory]:
        """Ranks memories based on importance, recency, frequency, and favorites."""
        if not memories:
            return []

        now = datetime.now(timezone.utc)

        def calculate_score(memory: Memory) -> float:
            score = 0.0

            # Base importance
            score += memory.importance * 40.0

            # Recency decay (half-life of 30 days)
            updated_at = memory.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            days_old = (now - updated_at).days
            recency_multiplier = math.exp(-0.023 * days_old)  # ln(2)/30 approx 0.023
            score += recency_multiplier * 30.0

            # Favorites get a big boost
            if memory.favorite:
                score += 20.0

            # Confidence
            score += memory.confidence * 10.0

            return score

        ranked_memories = sorted(memories, key=calculate_score, reverse=True)
        return ranked_memories
