from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from app.repositories.chat_repository import ChatRepository
from app.models.chat import Conversation, Message
from app.schemas.chat import ConversationCreate, ConversationUpdate, MessageCreate
from app.models.user import User

class ChatService:
    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo

    def create_conversation(self, user: User, data: ConversationCreate) -> Conversation:
        conversation = Conversation(
            user_id=user.id,
            title=data.title or "New Conversation"
        )
        conversation = self.chat_repo.create_conversation(conversation)

        if data.initial_message:
            self.create_message(user, conversation.id, data.initial_message)

        return conversation

    def get_conversation(self, user: User, conversation_id: UUID) -> Conversation:
        conversation = self.chat_repo.get_conversation(conversation_id, user.id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    def list_conversations(self, user: User, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[Conversation]:
        return self.chat_repo.list_conversations(user.id, skip, limit, search)

    def update_conversation(self, user: User, conversation_id: UUID, data: ConversationUpdate) -> Conversation:
        conversation = self.get_conversation(user, conversation_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(conversation, key, value)

        return self.chat_repo.update_conversation(conversation)

    def delete_conversation(self, user: User, conversation_id: UUID) -> None:
        conversation = self.get_conversation(user, conversation_id)
        self.chat_repo.delete_conversation(conversation)

    def create_message(self, user: User, conversation_id: UUID, data: MessageCreate) -> Message:
        # Validate ownership
        self.get_conversation(user, conversation_id)

        message = Message(
            conversation_id=conversation_id,
            role=data.role,
            content=data.content,
            assistant_metadata=data.assistant_metadata
        )
        return self.chat_repo.create_message(message)

    def list_messages(self, user: User, conversation_id: UUID, skip: int = 0, limit: int = 100) -> List[Message]:
        # Validate ownership
        self.get_conversation(user, conversation_id)

        return self.chat_repo.list_messages(conversation_id, skip, limit)

    async def stream_assistant_response(self, user: User, conversation_id: UUID, user_message: MessageCreate, background_tasks: "BackgroundTasks"):
        import json
        import logging

        from app.core.llm.llm_provider import LLMFactory, LLMProviderError
        from app.services.tools.base import ToolContext
        from app.services.tools.executor import ToolExecutor
        from app.services.tools.intent_analyzer import IntentAnalyzer

        logger = logging.getLogger(__name__)

        # 1. Validate ownership and save user message.
        conversation = self.get_conversation(user, conversation_id)
        persisted_user_message = self.create_message(user, conversation.id, user_message)

        from app.services.memory_pipeline.context_retriever import MemoryContextBuilder
        from app.services.memory_pipeline.memory_ranker import MemoryRankingService
        from app.services.memory_pipeline.prompt_composer import PromptComposer
        from app.services.memory_service import memory_service
        from app.db.session import SessionLocal

        llm_provider = LLMFactory.get_provider()
        intent = await IntentAnalyzer(llm_provider).analyze(user_message.content)
        tool_prompt_results: List[str] = []

        if intent.required_tool:
            tool_result = await ToolExecutor.execute(
                intent.required_tool,
                ToolContext(
                    user_id=user.id,
                    conversation_id=conversation.id,
                    message_id=persisted_user_message.id,
                ),
                intent.arguments,
            )
            if tool_result.success:
                tool_prompt_results.append(
                    f"{intent.required_tool}: {json.dumps(tool_result.data, default=str)}"
                )
            else:
                tool_prompt_results.append(
                    f"{intent.required_tool}: unavailable ({tool_result.error})"
                )

        # 2. Retrieve bounded user-owned memory context.
        db = None
        try:
            db = SessionLocal()
            available_memories = memory_service.get_memories(db=db, user_id=user.id)
        except Exception:
            logger.exception("Memory retrieval failed during chat orchestration.")
            available_memories = []
        finally:
            if db is not None:
                db.close()

        context_builder = MemoryContextBuilder(llm_provider, MemoryRankingService())
        memory_context, selected_memories_obj = context_builder.build_context(user_message.content, available_memories)

        # Mark retrieved
        if selected_memories_obj:
            try:
                db = SessionLocal()
                memory_service.mark_retrieved(db, selected_memories_obj)
                db.close()
            except Exception:
                logger.exception("Failed to mark memories as retrieved.")

        composer = PromptComposer()
        personality = (user.ai_personality or "reflective").lower()
        personality_styles = {
            "direct": "Communicate succinctly with direct bullet points and minimal conversation.",
            "reflective": "Communicate thoughtfully with in-depth explanations and contextual rationale.",
            "encouraging": "Communicate with a warm, supportive, and motivating tone focused on habit building.",
            "academic": "Communicate with academic rigor, precise conceptual frameworks, and analytical depth.",
        }
        style_instruction = personality_styles.get(personality, "Communicate thoughtfully and helpfully.")
        user_name_clause = f" Address the user as {user.display_name}." if user.display_name else ""
        system_prompt = f"You are VAJRA, an intelligent personal AI assistant.{user_name_clause} Communication style: {style_instruction}"

        chat_history = self.list_messages(user, conversation_id, skip=0, limit=10)

        final_prompt = composer.compose(
            system_prompt,
            memory_context,
            chat_history,
            user_message.content,
            tool_prompt_results,
        )

        full_response = ""
        completed_successfully = False
        try:
            async for chunk in llm_provider.stream_generate(final_prompt, system_prompt=system_prompt):
                full_response += chunk
                yield f"data: {json.dumps({'delta': chunk})}\n\n"

            completed_successfully = True
            yield f"data: {json.dumps({'done': True})}\n\n"
        except LLMProviderError:
            logger.warning("LLM provider failed while streaming assistant response.")
            yield f"data: {json.dumps({'error': 'LLM provider unavailable', 'done': True})}\n\n"
        finally:
            if completed_successfully and full_response.strip():
                assistant_msg = MessageCreate(
                    role="assistant",
                    content=full_response.strip(),
                    assistant_metadata={
                        "intent": intent.intent,
                        "tool_used": intent.required_tool,
                    }
                )
                self.create_message(user, conversation.id, assistant_msg)
                from app.services.memory_pipeline.pipeline import pipeline
                background_tasks.add_task(
                    pipeline.process_message_background,
                    user,
                    user_message.content,
                    conversation.id,
                )
