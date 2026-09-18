from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.device import Device
from app.models.device_action import DeviceAction
from app.schemas.device_action import RemoteActionDispatchRequest, RemoteActionAckRequest

# Explicit safety allowlist - never allow arbitrary remote commands
ALLOWED_REMOTE_ACTIONS = {
    "device.flashlight": "flashlight",
    "device.timer": "mobile_alarms",
    "device.settings": "settings",
    "device.media": "media",
}

# Maximum age for active device heartbeat to be considered online (5 minutes)
OFFLINE_THRESHOLD_SECONDS = 300

class DeviceActionRepository:
    def dispatch_action(
        self,
        db: Session,
        user_id: UUID,
        req: RemoteActionDispatchRequest,
        source_device_id: Optional[str] = None,
    ) -> DeviceAction:
        """
        Validates safety, ownership, online state, and capability before creating a PENDING remote action.
        """
        # 1. Allowlist validation (Phase 6 safety model)
        if req.action_type not in ALLOWED_REMOTE_ACTIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action '{req.action_type}' is not permitted by VAJRA Remote Action Safety Policy (UNSUPPORTED)",
            )

        required_capability = ALLOWED_REMOTE_ACTIONS[req.action_type]

        # 2. Target Device Resolution with Strict User Isolation
        target_device: Optional[Device] = None
        if req.target_device_id:
            target_device = (
                db.query(Device)
                .filter(
                    Device.user_id == user_id,
                    Device.device_id == req.target_device_id,
                )
                .first()
            )
        else:
            # Resolve default active mobile device for current user
            target_type = req.target_device_type or "mobile"
            target_device = (
                db.query(Device)
                .filter(
                    Device.user_id == user_id,
                    Device.device_type == target_type,
                    Device.is_active.is_(True),
                )
                .order_by(Device.last_seen.desc())
                .first()
            )

        if not target_device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target device not found or does not belong to your account",
            )

        # 3. Active & Online State Check
        if not target_device.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target device is inactive (OFFLINE)",
            )

        now = datetime.now(timezone.utc)
        last_seen = target_device.last_seen
        if last_seen:
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            if (now - last_seen).total_seconds() > OFFLINE_THRESHOLD_SECONDS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target device is currently offline (OFFLINE)",
                )

        # 4. Capability Check
        capabilities = target_device.capabilities or []
        if required_capability not in capabilities and req.action_type not in capabilities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target device does not support required capability '{required_capability}' (UNSUPPORTED)",
            )

        # 5. Create PENDING DeviceAction
        action = DeviceAction(
            user_id=user_id,
            source_device_id=source_device_id,
            target_device_id=target_device.device_id,
            action_type=req.action_type,
            parameters=req.parameters,
            status="PENDING",
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        return action

    def get_pending_actions(
        self,
        db: Session,
        user_id: UUID,
        device_id: str,
    ) -> List[DeviceAction]:
        """
        Retrieves all PENDING actions for the calling device, marks them SENT,
        and automatically updates the device's last_seen heartbeat.
        """
        # Update heartbeat for calling device
        device = (
            db.query(Device)
            .filter(
                Device.user_id == user_id,
                Device.device_id == device_id,
            )
            .first()
        )
        if device:
            device.last_seen = datetime.now(timezone.utc)
            device.is_active = True

        # Query pending actions for this device
        actions = (
            db.query(DeviceAction)
            .filter(
                DeviceAction.user_id == user_id,
                DeviceAction.target_device_id == device_id,
                DeviceAction.status == "PENDING",
            )
            .order_by(DeviceAction.created_at.asc())
            .all()
        )

        for action in actions:
            action.status = "SENT"

        db.commit()
        for action in actions:
            db.refresh(action)

        return actions

    def acknowledge_action(
        self,
        db: Session,
        user_id: UUID,
        action_id: UUID,
        req: RemoteActionAckRequest,
    ) -> Optional[DeviceAction]:
        """
        Records the final execution result (SUCCESS/FAILED) from the target device.
        """
        action = (
            db.query(DeviceAction)
            .filter(
                DeviceAction.id == action_id,
                DeviceAction.user_id == user_id,
            )
            .first()
        )
        if not action:
            return None

        action.status = req.status.upper()
        action.result_message = req.result_message
        action.error_code = req.error_code
        action.executed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(action)
        return action

    def get_action_by_id(
        self,
        db: Session,
        user_id: UUID,
        action_id: UUID,
    ) -> Optional[DeviceAction]:
        """
        Returns a single action verifying user ownership.
        """
        return (
            db.query(DeviceAction)
            .filter(
                DeviceAction.id == action_id,
                DeviceAction.user_id == user_id,
            )
            .first()
        )

device_action_repository = DeviceActionRepository()
