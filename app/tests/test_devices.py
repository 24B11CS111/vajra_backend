import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.user import User
from app.models.device import Device
from app.schemas.device import DeviceRegisterRequest, DeviceUpdateRequest
from app.repositories.device_repository import device_repository

def get_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()

def run_device_tests():
    db_session = get_test_db()
    try:
        user_id = uuid.uuid4()
        supa_id = uuid.uuid4()
        user = User(
            id=user_id,
            supabase_user_id=supa_id,
            email="testuser@vajra.ai",
            full_name="Vajra Tester",
        )
        db_session.add(user)
        db_session.commit()

        # 1. Register new desktop device
        req = DeviceRegisterRequest(
            device_id="desktop_win_001",
            device_type="desktop",
            device_name="VAJRA Workstation",
            platform="windows",
            app_version="1.0.0",
            capabilities=["files", "terminal", "developer", "browser", "apps"],
        )
        dev = device_repository.register_or_heartbeat(db_session, user_id, req)
        assert dev is not None, "Device registration returned None"
        assert dev.device_id == "desktop_win_001"
        assert dev.device_name == "VAJRA Workstation"
        assert dev.is_active is True
        assert "developer" in dev.capabilities
        print("[PASS] Registered desktop device successfully")

        # 2. Register mobile device for same user
        req_mobile = DeviceRegisterRequest(
            device_id="android_phone_002",
            device_type="mobile",
            device_name="Nothing Phone (2a)",
            platform="android",
            app_version="2.0.0",
            capabilities=["call", "sms", "gps", "camera", "flashlight"],
        )
        dev_mob = device_repository.register_or_heartbeat(db_session, user_id, req_mobile)
        assert dev_mob.device_id == "android_phone_002"
        print("[PASS] Registered mobile device successfully")

        # 3. List devices for user
        devices = device_repository.get_user_devices(db_session, user_id)
        assert len(devices) == 2
        device_ids = [d.device_id for d in devices]
        assert "desktop_win_001" in device_ids
        assert "android_phone_002" in device_ids
        print(f"[PASS] Listed {len(devices)} ecosystem devices for user")

        # 4. Heartbeat update
        req_update = DeviceRegisterRequest(
            device_id="desktop_win_001",
            device_type="desktop",
            device_name="VAJRA Studio Workstation",
            platform="windows",
            app_version="1.0.1",
            capabilities=["files", "terminal", "developer", "browser", "apps", "screen_context"],
        )
        dev_updated = device_repository.register_or_heartbeat(db_session, user_id, req_update)
        assert dev_updated.device_name == "VAJRA Studio Workstation"
        assert dev_updated.app_version == "1.0.1"
        assert "screen_context" in dev_updated.capabilities
        print("[PASS] Device heartbeat updated capabilities and name")

        # 5. User isolation check
        other_user_id = uuid.uuid4()
        other_user = User(
            id=other_user_id,
            supabase_user_id=uuid.uuid4(),
            email="other@vajra.ai",
            full_name="Other User",
        )
        db_session.add(other_user)
        db_session.commit()

        other_devices = device_repository.get_user_devices(db_session, other_user_id)
        assert len(other_devices) == 0, "User isolation violated: other user saw devices"

        dev_from_b = device_repository.get_by_device_id(db_session, other_user_id, "desktop_win_001")
        assert dev_from_b is None, "User B should not be able to query User A device"

        deleted_by_b = device_repository.delete_device(db_session, other_user_id, "desktop_win_001")
        assert deleted_by_b is False, "User B should not be able to delete User A device"
        print("[PASS] Strict user isolation verified: cross-user access prevented")

        # 6. Delete device
        deleted = device_repository.delete_device(db_session, user_id, "desktop_win_001")
        assert deleted is True, "Device deletion failed"
        remaining = device_repository.get_user_devices(db_session, user_id)
        assert len(remaining) == 1
        assert remaining[0].device_id == "android_phone_002"
        print("[PASS] Device deletion/disconnect verified")

        print("\nALL BACKEND DEVICE TESTS PASSED: 100% SUCCESS!")
    finally:
        db_session.close()

if __name__ == "__main__":
    run_device_tests()
