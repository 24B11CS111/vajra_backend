from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.device import Device
from app.schemas.device import DeviceRegisterRequest, DeviceUpdateRequest

class DeviceRepository:
    def get_by_device_id(self, db: Session, user_id: UUID, device_id: str) -> Optional[Device]:
        return db.query(Device).filter(
            Device.user_id == user_id,
            Device.device_id == device_id
        ).first()

    def get_by_id(self, db: Session, user_id: UUID, id: UUID) -> Optional[Device]:
        return db.query(Device).filter(
            Device.user_id == user_id,
            Device.id == id
        ).first()

    def get_user_devices(self, db: Session, user_id: UUID, active_only: bool = False) -> List[Device]:
        query = db.query(Device).filter(Device.user_id == user_id)
        if active_only:
            query = query.filter(Device.is_active == True)
        return query.order_by(Device.last_seen.desc()).all()

    def register_or_heartbeat(self, db: Session, user_id: UUID, req: DeviceRegisterRequest) -> Device:
        device = self.get_by_device_id(db, user_id, req.device_id)
        now = datetime.now(timezone.utc)
        if device:
            device.device_name = req.device_name
            device.device_type = req.device_type
            device.platform = req.platform
            if req.app_version:
                device.app_version = req.app_version
            if req.capabilities:
                device.capabilities = req.capabilities
            device.is_active = True
            device.last_seen = now
        else:
            device = Device(
                user_id=user_id,
                device_id=req.device_id,
                device_type=req.device_type,
                device_name=req.device_name,
                platform=req.platform,
                app_version=req.app_version,
                capabilities=req.capabilities or [],
                is_active=True,
                last_seen=now,
            )
            db.add(device)
            
        db.commit()
        db.refresh(device)
        return device

    def update_device(self, db: Session, user_id: UUID, device_id: str, req: DeviceUpdateRequest) -> Optional[Device]:
        device = self.get_by_device_id(db, user_id, device_id)
        if not device:
            return None
        if req.device_name is not None:
            device.device_name = req.device_name
        if req.capabilities is not None:
            device.capabilities = req.capabilities
        if req.is_active is not None:
            device.is_active = req.is_active
        db.commit()
        db.refresh(device)
        return device

    def delete_device(self, db: Session, user_id: UUID, device_id: str) -> bool:
        device = self.get_by_device_id(db, user_id, device_id)
        if not device:
            # Fallback to check by UUID id
            try:
                id_val = UUID(device_id)
                device = self.get_by_id(db, user_id, id_val)
            except ValueError:
                pass
        if not device:
            return False
        db.delete(device)
        db.commit()
        return True

device_repository = DeviceRepository()
