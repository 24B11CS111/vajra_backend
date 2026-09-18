from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.dependencies.auth import get_current_db_user
from app.models.user import User
from app.schemas.device import (
    DeviceRegisterRequest,
    DeviceUpdateRequest,
    DeviceResponse,
    DeviceListResponse,
)
from app.schemas.device_action import (
    RemoteActionDispatchRequest,
    RemoteActionAckRequest,
    RemoteActionResponse,
    RemoteActionListResponse,
)
from app.repositories.device_repository import device_repository
from app.repositories.device_action_repository import device_action_repository

router = APIRouter()

# ---------------- Remote Device Actions ----------------

@router.post("/actions/dispatch", response_model=RemoteActionResponse, status_code=status.HTTP_201_CREATED)
def dispatch_remote_action(
    req: RemoteActionDispatchRequest,
    source_device_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Dispatch a remote action to a registered, active, online device with capability verification.
    """
    return device_action_repository.dispatch_action(
        db=db,
        user_id=current_user.id,
        req=req,
        source_device_id=source_device_id,
    )

@router.get("/actions/pending", response_model=RemoteActionListResponse)
def get_pending_remote_actions(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Target device retrieves all PENDING actions assigned to it.
    Also updates device heartbeat.
    """
    actions = device_action_repository.get_pending_actions(
        db=db,
        user_id=current_user.id,
        device_id=device_id,
    )
    return RemoteActionListResponse(actions=actions, total=len(actions))

@router.post("/actions/{action_id}/ack", response_model=RemoteActionResponse)
def acknowledge_remote_action(
    action_id: UUID,
    req: RemoteActionAckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Target device posts final execution status (SUCCESS / FAILED).
    """
    action = device_action_repository.acknowledge_action(
        db=db,
        user_id=current_user.id,
        action_id=action_id,
        req=req,
    )
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found or unauthorized",
        )
    return action

@router.get("/actions/{action_id}", response_model=RemoteActionResponse)
def get_remote_action_status(
    action_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Sender polls status of dispatched remote action.
    """
    action = device_action_repository.get_action_by_id(
        db=db,
        user_id=current_user.id,
        action_id=action_id,
    )
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found or unauthorized",
        )
    return action

@router.post("/register", response_model=DeviceResponse, status_code=status.HTTP_200_OK)
def register_device(
    req: DeviceRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Register a device or update its heartbeat and capabilities.
    Enforces user isolation.
    """
    device = device_repository.register_or_heartbeat(
        db=db,
        user_id=current_user.id,
        req=req,
    )
    return device

@router.get("/", response_model=DeviceListResponse)
def list_devices(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    List all ecosystem devices registered to the current user.
    """
    devices = device_repository.get_user_devices(
        db=db,
        user_id=current_user.id,
        active_only=active_only,
    )
    return DeviceListResponse(devices=devices, total=len(devices))

@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Get details for a specific device owned by the current user.
    """
    device = device_repository.get_by_device_id(db=db, user_id=current_user.id, device_id=device_id)
    if not device:
        try:
            uuid_id = UUID(device_id)
            device = device_repository.get_by_id(db=db, user_id=current_user.id, id=uuid_id)
        except ValueError:
            pass

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return device

@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: str,
    req: DeviceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Update device metadata (name, capabilities, status).
    """
    device = device_repository.update_device(
        db=db,
        user_id=current_user.id,
        device_id=device_id,
        req=req,
    )
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return device

@router.delete("/{device_id}", status_code=status.HTTP_200_OK)
def delete_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
) -> Any:
    """
    Disconnect and remove a device from the user's ecosystem.
    """
    success = device_repository.delete_device(
        db=db,
        user_id=current_user.id,
        device_id=device_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return {"status": "success", "message": f"Device {device_id} disconnected"}
