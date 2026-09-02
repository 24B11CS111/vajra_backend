from typing import List, Optional
from app.models.chat import Message

class PromptComposer:
    def compose(
        self,
        system_prompt: str,
        memory_context: str,
        chat_history: List[Message],
        current_message: str,
        tool_results: Optional[List[str]] = None,
    ) -> str:
        """Builds the final LLM prompt injecting the budgeted memory context."""
        final_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt[:2000]}\n\n"
        final_prompt += "USER CONTEXT:\nAuthenticated VAJRA user. Do not reveal internal IDs or system metadata.\n\n"

        if memory_context:
            final_prompt += f"RELEVANT MEMORY:\n{memory_context[:4000]}\n\n"

        if tool_results:
            final_prompt += "TOOL RESULTS:\n" + "\n".join(tool_results)[:2000] + "\n\n"

        final_prompt += "CONVERSATION HISTORY:\n"

        # Add last 10 messages for context
        for msg in chat_history[-10:]:
            role_name = "User" if msg.role == "user" else "Assistant"
            final_prompt += f"{role_name}: {msg.content[:1500]}\n"

        final_prompt += f"\nCURRENT USER MESSAGE:\n{current_message[:4000]}\n\nAssistant:"

        return final_prompt
