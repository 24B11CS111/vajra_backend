from typing import List, Dict, Any
from app.models.memory import Memory
from app.core.llm.llm_provider import LLMProvider
from app.services.memory_pipeline.memory_ranker import MemoryRankingService

class MemoryContextBuilder:
    def __init__(self, llm: LLMProvider, ranker: MemoryRankingService):
        self.llm = llm
        self.ranker = ranker
        self.max_tokens = 1000  # Configurable context budget

    def build_context(self, current_message: str, available_memories: List[Memory]) -> tuple[str, List[Memory]]:
        """Retrieves and ranks relevant memories, estimating token usage and packing until the Context Budget is exhausted."""

        ranked_memories = self.ranker.rank_memories(current_message, available_memories)

        selected_memories_text = []
        selected_memories_obj = []
        current_tokens = 0

        for memory in ranked_memories:
            memory_text = f"- {memory.memory_type.name}: {memory.content}"
            tokens = self.llm.estimate_tokens(memory_text)

            if current_tokens + tokens > self.max_tokens:
                break

            selected_memories_text.append(memory_text)
            selected_memories_obj.append(memory)
            current_tokens += tokens

        if not selected_memories_text:
            return "", []

        return "Relevant User Memories:\n" + "\n".join(selected_memories_text), selected_memories_obj
