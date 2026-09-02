from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from app.models.chat import Conversation, Message

class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Conversations ---

    def create_conversation(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(self, conversation_id: UUID, user_id: UUID) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()

    def list_conversations(self, user_id: UUID, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[Conversation]:
        query = self.db.query(Conversation).filter(Conversation.user_id == user_id)

        if search:
            # Basic search by title for now. Advanced search can involve joining messages.
            query = query.filter(Conversation.title.ilike(f"%{search}%"))

        return query.order_by(desc(Conversation.last_message_at), desc(Conversation.created_at)).offset(skip).limit(limit).all()

    def update_conversation(self, conversation: Conversation) -> Conversation:
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def delete_conversation(self, conversation: Conversation) -> None:
        self.db.delete(conversation)
        self.db.commit()

    # --- Messages ---

    def create_message(self, message: Message) -> Message:
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        # Update conversation last_message_at
        conversation = self.db.query(Conversation).filter(Conversation.id == message.conversation_id).first()
        if conversation:
            conversation.last_message_at = message.created_at
            self.db.commit()

        return message

    def list_messages(self, conversation_id: UUID, skip: int = 0, limit: int = 100) -> List[Message]:
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).offset(skip).limit(limit).all()
