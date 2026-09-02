from typing import List, Dict, Any, Tuple
from app.models.memory import Memory
from app.core.llm.llm_provider import LLMProvider

class DuplicateDetector:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def check_duplicates(self, new_memory: Dict[str, Any], existing_memories: List[Memory]) -> Tuple[str, Any]:
        """
        Detects existing, updated, or contradicting memories.
        Returns a tuple: (action, target_memory_id)
        action can be: "create", "update", "ignore"
        """
        if not existing_memories:
            return "create", None

        # Simplified: compare against top existing memories using LLM
        existing_list = [{"id": str(m.id), "content": m.content} for m in existing_memories[:10]]

        prompt = (
            f"New Memory: {new_memory['content']}\n"
            f"Existing Memories: {existing_list}\n\n"
            f"Determine if the New Memory is a duplicate, an update, or completely new compared to the Existing Memories. "
            f"Output JSON with 'action' (one of: create, update, ignore) and 'target_id' (the UUID of the existing memory if action is update or ignore, otherwise null)."
        )

        try:
            result = await self.llm.extract_json(prompt)
            action = result.get("action", "create")
            target_id = result.get("target_id")

            if action in ["update", "ignore"] and target_id:
                valid_ids = {str(memory.id) for memory in existing_memories}
                if str(target_id) not in valid_ids:
                    return "create", None
                return action, target_id
            return "create", None
        except Exception:
            return "create", None
