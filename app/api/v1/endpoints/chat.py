from fastapi import APIRouter, Depends, Query, BackgroundTasks
from typing import List, Optional
from uuid import UUID

from app.schemas.chat import ConversationCreate, ConversationUpdate, ConversationResponse, MessageCreate, MessageResponse
from app.models.user import User
from app.dependencies.auth import get_current_db_user
from app.dependencies.services import get_chat_service
from app.services.chat_service import ChatService

router = APIRouter()

@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_db_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    return chat_service.list_conversations(current_user, skip, limit, search)

@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_db_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    return chat_service.create_conversation(current_user, data)

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_db_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    return chat_service.get_conversation(current_user, conversation_id)

@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_db_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    return chat_service.update_conversation(current_user, conversation_id, data)

@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_db_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    chat_service.delete_conversation(current_user, conversation_id)

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
def list_messages(
    conversation_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_db_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    return chat_service.list_messages(current_user, conversation_id, skip, limit)

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
def create_message(
    conversation_id: UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_db_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    return chat_service.create_message(current_user, conversation_id, data)

@router.post("/conversations/{conversation_id}/messages/stream")
def stream_message(
    conversation_id: UUID,
    data: MessageCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_db_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        chat_service.stream_assistant_response(current_user, conversation_id, data, background_tasks),
        media_type="text/event-stream"
    )
