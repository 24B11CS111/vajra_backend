from typing import Any, List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies.auth import get_current_db_user
from app.models.user import User
from app.models.memory import MemoryType
from app.schemas.memory import Memory, MemoryCreate, MemoryUpdate
from app.services.memory_service import memory_service

router = APIRouter()

@router.get("/", response_model=List[Memory])
def get_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
    skip: int = 0,
    limit: int = 100,
    query: Optional[str] = None,
    memory_type: Optional[MemoryType] = None,
    favorite: Optional[bool] = None,
    archived: Optional[bool] = None,
) -> Any:
    """
    Retrieve or search memories.
    """
    if query or memory_type or favorite is not None or archived is not None:
        return memory_service.search_memories(
            db=db,
            user_id=current_user.id,
            query=query,
            memory_type=memory_type,
            favorite=favorite,
            archived=archived,
            skip=skip,
            limit=limit,
        )
    return memory_service.get_memories(db=db, user_id=current_user.id, skip=skip, limit=limit)

@router.post("/", response_model=Memory, status_code=status.HTTP_201_CREATED)
def create_memory(
    *,
    db: Session = Depends(get_db),
    memory_in: MemoryCreate,
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Create new memory.
    """
    return memory_service.create_memory(db=db, obj_in=memory_in, user_id=current_user.id)

@router.delete("/purge", status_code=status.HTTP_200_OK)
def purge_memories(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Permanently purge all memories for the authenticated user.
    """
    deleted_count = memory_service.purge_all_memories(db=db, user_id=current_user.id)
    return {"status": "ok", "deleted_count": deleted_count}

@router.get("/{id}", response_model=Memory)
def get_memory(
    *,
    db: Session = Depends(get_db),
    id: uuid.UUID,
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Get memory by ID.
    """
    return memory_service.get_memory(db=db, id=id, user_id=current_user.id)

@router.put("/{id}", response_model=Memory)
def update_memory(
    *,
    db: Session = Depends(get_db),
    id: uuid.UUID,
    memory_in: MemoryUpdate,
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Update a memory.
    """
    return memory_service.update_memory(db=db, id=id, obj_in=memory_in, user_id=current_user.id)

@router.delete("/{id}", response_model=Memory)
def delete_memory(
    *,
    db: Session = Depends(get_db),
    id: uuid.UUID,
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Delete a memory (soft delete).
    """
    return memory_service.delete_memory(db=db, id=id, user_id=current_user.id)

@router.post("/{id}/restore", response_model=Memory)
def restore_memory(
    *,
    db: Session = Depends(get_db),
    id: uuid.UUID,
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Restore a deleted memory.
    """
    return memory_service.restore_memory(db=db, id=id, user_id=current_user.id)

@router.post("/{id}/favorite", response_model=Memory)
def favorite_memory(
    *,
    db: Session = Depends(get_db),
    id: uuid.UUID,
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Toggle favorite status of a memory.
    """
    return memory_service.toggle_favorite(db=db, id=id, user_id=current_user.id)

@router.post("/{id}/archive", response_model=Memory)
def archive_memory(
    *,
    db: Session = Depends(get_db),
    id: uuid.UUID,
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Toggle archive status of a memory.
    """
    return memory_service.toggle_archive(db=db, id=id, user_id=current_user.id)
