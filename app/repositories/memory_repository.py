from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
import uuid
from datetime import datetime, timezone

from app.models.memory import Memory, MemoryType
from app.schemas.memory import MemoryCreate, MemoryUpdate
from app.repositories.base_repository import BaseRepository

class MemoryRepository(BaseRepository[Memory, MemoryCreate, MemoryUpdate]):
    def get_by_user(
        self, db: Session, *, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Memory]:
        return (
            db.query(self.model)
            .filter(Memory.user_id == user_id, Memory.deleted == False)
            .order_by(desc(Memory.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_id_and_user(
        self, db: Session, *, id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Memory]:
        return db.query(self.model).filter(
            Memory.id == id,
            Memory.user_id == user_id,
            Memory.deleted == False
        ).first()

    def get_deleted_by_id_and_user(
        self, db: Session, *, id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Memory]:
        return db.query(self.model).filter(
            Memory.id == id,
            Memory.user_id == user_id,
            Memory.deleted == True
        ).first()

    def create_with_user(
        self, db: Session, *, obj_in: MemoryCreate, user_id: uuid.UUID
    ) -> Memory:
        obj_in_data = obj_in.model_dump(by_alias=True, exclude_unset=True)
        db_obj = self.model(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def search_memories(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        query: str,
        memory_type: Optional[MemoryType] = None,
        favorite: Optional[bool] = None,
        archived: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Memory]:
        qs = db.query(self.model).filter(
            Memory.user_id == user_id,
            Memory.deleted == False
        )

        if memory_type:
            qs = qs.filter(Memory.memory_type == memory_type)
        if favorite is not None:
            qs = qs.filter(Memory.favorite == favorite)
        if archived is not None:
            qs = qs.filter(Memory.archived == archived)

        if query:
            search_filter = or_(
                Memory.title.ilike(f"%{query}%"),
                Memory.content.ilike(f"%{query}%"),
                Memory.tags.any(query)
            )
            qs = qs.filter(search_filter)

        return qs.order_by(desc(Memory.importance), desc(Memory.created_at)).offset(skip).limit(limit).all()

    def soft_delete(self, db: Session, *, db_obj: Memory) -> Memory:
        db_obj.deleted = True
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def restore(self, db: Session, *, db_obj: Memory) -> Memory:
        db_obj.deleted = False
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def toggle_favorite(self, db: Session, *, db_obj: Memory) -> Memory:
        db_obj.favorite = not db_obj.favorite
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def toggle_archive(self, db: Session, *, db_obj: Memory) -> Memory:
        db_obj.archived = not db_obj.archived
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def mark_accessed(self, db: Session, *, db_obj: Memory) -> Memory:
        db_obj.last_accessed = datetime.now(timezone.utc)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

memory_repository = MemoryRepository(Memory)
