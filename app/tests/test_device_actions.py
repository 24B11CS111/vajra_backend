import os
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.db.session import Base
from app.models.user import User
from app.models.device import Device
from app.models.device_action import DeviceAction
from app.schemas.device import DeviceRegisterRequest
from app.schemas.device_action import RemoteActionDispatchRequest, RemoteActionAckRequest
from app.repositories.device_repository import device_repository
from app.repositories.device_action_repository import device_action_repository

def get_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()

def run_device_action_tests():
    db = get_test_db()
    try:
        # 1. Setup User A and Devices
        user_a_id = uuid.uuid4()
        user_a = User(
            id=user_a_id,
            supabase_user_id=uuid.uuid4(),
            email="usera@vajra.ai",
            full_name="User A",
        )
        db.add(user_a)

        # Setup User B
        user_b_id = uuid.uuid4()
        user_b = User(
            id=user_b_id,
            supabase_user_id=uuid.uuid4(),
            email="userb@vajra.ai",
            full_name="User B",
        )
        db.add(user_b)
        db.commit()

        # Register User A's Phone (Online, has flashlight)
        phone_req = DeviceRegisterRequest(
            device_id="android_phone_001",
            device_type="mobile",
            device_name="Nothing Phone (2a)",
            platform="android",
            app_version="2.0.0",
            capabilities=["call", "sms", "gps", "flashlight", "mobile_alarms"],
        )
        phone_dev = device_repository.register_or_heartbeat(db, user_a_id, phone_req)
        assert phone_dev is not None

        # 2. Test Authorized Dispatch (Flashlight ON)
        dispatch_req = RemoteActionDispatchRequest(
            target_device_id="android_phone_001",
            action_type="device.flashlight",
            parameters={"enabled": True},
        )
        action = device_action_repository.dispatch_action(
            db=db,
            user_id=user_a_id,
            req=dispatch_req,
            source_device_id="desktop_win_001",
        )
        assert action is not None
        assert action.status == "PENDING"
        assert action.target_device_id == "android_phone_001"
        assert action.action_type == "device.flashlight"
        assert action.parameters.get("enabled") is True
        print("[PASS] Test 1: Desktop dispatches authorized flashlight ON action (status: PENDING)")

        # 3. Test Cross-User Isolation
        try:
            device_action_repository.dispatch_action(
                db=db,
                user_id=user_b_id,
                req=dispatch_req, # User B trying to target User A's phone
            )
            assert False, "Security Violation: User B was able to target User A's device"
        except HTTPException as e:
            assert e.status_code == 404
            print("[PASS] Test 2: Cross-user isolation verified (User B cannot target User A device)")

        # 4. Test Safety Policy: Arbitrary / Unapproved Actions Blocked
        try:
            bad_req = RemoteActionDispatchRequest(
                target_device_id="android_phone_001",
                action_type="system.shell_exec",
                parameters={"cmd": "rm -rf /"},
            )
            device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=bad_req)
            assert False, "Security Violation: Arbitrary action was allowed"
        except HTTPException as e:
            assert e.status_code == 400
            assert "not permitted by VAJRA Remote Action Safety Policy" in e.detail
            print("[PASS] Test 3: Safety allowlist verified (arbitrary shell commands blocked)")

        # 5. Test Offline Device Rejection
        # Simulate phone going offline by setting last_seen 10 minutes ago
        phone_dev.last_seen = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()

        try:
            device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=dispatch_req)
            assert False, "Offline device was incorrectly accepted"
        except HTTPException as e:
            assert e.status_code == 400
            assert "offline" in e.detail.lower()
            print("[PASS] Test 4: Offline device rejected with OFFLINE status")

        # Restore phone online
        phone_dev.last_seen = datetime.now(timezone.utc)
        db.commit()

        # 6. Test Missing Capability Rejection
        phone_without_flash_req = DeviceRegisterRequest(
            device_id="android_phone_noflash",
            device_type="mobile",
            device_name="Old Phone",
            platform="android",
            capabilities=["call", "sms"], # NO flashlight
        )
        device_repository.register_or_heartbeat(db, user_a_id, phone_without_flash_req)

        try:
            noflash_req = RemoteActionDispatchRequest(
                target_device_id="android_phone_noflash",
                action_type="device.flashlight",
                parameters={"enabled": True},
            )
            device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=noflash_req)
            assert False, "Device without flashlight capability was incorrectly accepted"
        except HTTPException as e:
            assert e.status_code == 400
            assert "does not support required capability" in e.detail
            print("[PASS] Test 5: Missing capability rejected with UNSUPPORTED status")

        # 7. Test Phone Pending Action Retrieval
        pending_actions = device_action_repository.get_pending_actions(
            db=db,
            user_id=user_a_id,
            device_id="android_phone_001",
        )
        assert len(pending_actions) == 1
        retrieved_action = pending_actions[0]
        assert retrieved_action.id == action.id
        assert retrieved_action.status == "SENT"
        print("[PASS] Test 6: Target phone retrieves pending action (status transitioned to SENT)")

        # 8. Test Execution Acknowledgement (SUCCESS)
        ack_success = RemoteActionAckRequest(
            status="SUCCESS",
            result_message="Physical flashlight enabled via CameraManager",
        )
        acked = device_action_repository.acknowledge_action(
            db=db,
            user_id=user_a_id,
            action_id=action.id,
            req=ack_success,
        )
        assert acked is not None
        assert acked.status == "SUCCESS"
        assert acked.result_message == "Physical flashlight enabled via CameraManager"
        assert acked.executed_at is not None
        print("[PASS] Test 7: Mobile posts SUCCESS acknowledgement with execution timestamp")

        # 9. Test Status Polling
        polled = device_action_repository.get_action_by_id(
            db=db,
            user_id=user_a_id,
            action_id=action.id,
        )
        assert polled.status == "SUCCESS"
        print("[PASS] Test 8: Desktop polls and receives SUCCESS acknowledgement")

        print("\nALL BACKEND REMOTE ACTION TESTS PASSED: 100% SUCCESS!")
    finally:
        db.close()

if __name__ == "__main__":
    run_device_action_tests()
