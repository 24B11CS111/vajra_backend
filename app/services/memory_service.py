from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
from fastapi import HTTPException, status

from app.models.memory import Memory, MemoryType
from app.models.chat import Conversation, Message
from app.schemas.memory import MemoryCreate, MemoryUpdate
from app.repositories.memory_repository import memory_repository

class MemoryService:
    def _validate_memory_links(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        obj_in: MemoryCreate,
    ) -> None:
        conversation_ids = [
            obj_in.conversation_id,
            obj_in.origin_conversation_id,
        ]
        for conversation_id in conversation_ids:
            if conversation_id is None:
                continue
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            ).first()
            if conversation is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )

        if obj_in.origin_message_id is not None:
            message = db.query(Message).join(Conversation).filter(
                Message.id == obj_in.origin_message_id,
                Conversation.user_id == user_id,
            ).first()
            if message is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Message not found",
                )

    def get_memories(
        self, db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Memory]:
        return memory_repository.get_by_user(db=db, user_id=user_id, skip=skip, limit=limit)

    def get_memory(
        self, db: Session, id: uuid.UUID, user_id: uuid.UUID
    ) -> Memory:
        memory = memory_repository.get_by_id_and_user(db=db, id=id, user_id=user_id)
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        # Mark as accessed
        return memory_repository.mark_accessed(db=db, db_obj=memory)

    def mark_retrieved(
        self, db: Session, memories: List[Memory]
    ) -> None:
        """Increments times_retrieved and updates last_used_at."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        for memory in memories:
            memory.times_retrieved += 1
            memory.last_used_at = now
        db.commit()

    def create_memory(
        self, db: Session, obj_in: MemoryCreate, user_id: uuid.UUID
    ) -> Memory:
        self._validate_memory_links(db=db, user_id=user_id, obj_in=obj_in)
        return memory_repository.create_with_user(db=db, obj_in=obj_in, user_id=user_id)

    def update_memory(
        self, db: Session, id: uuid.UUID, obj_in: MemoryUpdate, user_id: uuid.UUID
    ) -> Memory:
        memory = memory_repository.get_by_id_and_user(db=db, id=id, user_id=user_id)
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        return memory_repository.update(db=db, db_obj=memory, obj_in=obj_in)

    def delete_memory(
        self, db: Session, id: uuid.UUID, user_id: uuid.UUID
    ) -> Memory:
        memory = memory_repository.get_by_id_and_user(db=db, id=id, user_id=user_id)
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        return memory_repository.soft_delete(db=db, db_obj=memory)

    def restore_memory(
        self, db: Session, id: uuid.UUID, user_id: uuid.UUID
    ) -> Memory:
        memory = memory_repository.get_deleted_by_id_and_user(db=db, id=id, user_id=user_id)
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted memory not found")
        return memory_repository.restore(db=db, db_obj=memory)

    def toggle_favorite(
        self, db: Session, id: uuid.UUID, user_id: uuid.UUID
    ) -> Memory:
        memory = memory_repository.get_by_id_and_user(db=db, id=id, user_id=user_id)
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        return memory_repository.toggle_favorite(db=db, db_obj=memory)

    def toggle_archive(
        self, db: Session, id: uuid.UUID, user_id: uuid.UUID
    ) -> Memory:
        memory = memory_repository.get_by_id_and_user(db=db, id=id, user_id=user_id)
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
        return memory_repository.toggle_archive(db=db, db_obj=memory)

    def search_memories(
        self,
        db: Session,
        user_id: uuid.UUID,
        query: str,
        memory_type: Optional[MemoryType] = None,
        favorite: Optional[bool] = None,
        archived: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Memory]:
        return memory_repository.search_memories(
            db=db,
            user_id=user_id,
            query=query,
            memory_type=memory_type,
            favorite=favorite,
            archived=archived,
            skip=skip,
            limit=limit
        )

    def purge_all_memories(self, db: Session, user_id: uuid.UUID) -> int:
        count = db.query(Memory).filter(Memory.user_id == user_id).delete()
        db.commit()
        return count

memory_service = MemoryService()
